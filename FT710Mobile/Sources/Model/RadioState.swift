import Foundation
import UIKit

/// Central state model for the radio — mutable from the main actor.
/// Mirrors the JS globals: freq, mode, ptt, signal level, wdsp status, etc.
@MainActor
final class RadioState: ObservableObject {
    // ── Frequency ──────────────────────────────────────────────────
    @Published var frequency: Int = 14_074_000  // Hz (default: 20m FT8)

    // ── Mode ──────────────────────────────────────────────────────
    @Published var mode: String = "USB"

    // ── PTT ────────────────────────────────────────────────────────
    @Published var ptt: Bool = false
    @Published var powerOn: Bool = false

    // ── Signal ────────────────────────────────────────────────────
    @Published var signalLevel: Int = 0     // S0–S9+ (0–60+)
    @Published var latency: String = "--ms"

    // ── TX Telemetry ─────────────────────────────────────────────
    @Published var txPowerWatts: Float = 0.0      // forward power in watts
    @Published var txSupplyVolts: Float = 0.0     // supply voltage × 10
    @Published var txTempCelsius: Float = 0.0     // PA temperature °C

    // ── Audio gain / squelch ──────────────────────────────────────
    @Published var afGain: Float = 0.5      // 0.0 – 1.0
    @Published var rfGain: Float = 0.5      // 0.0 – 1.0 (radio front-end gain)
    @Published var micGain: Float = 1.0     // 0.0 – 2.0, default 100%
    @Published var squelch: Float = 0.0     // 0.0 – 1.0

    // ── DSP / WDSP ────────────────────────────────────────────────
    @Published var wdspEnabled: Bool = false
    @Published var nr2Enabled: Bool = false
    @Published var nr2Level: Int = 0
    @Published var nbEnabled: Bool = false
    @Published var anfEnabled: Bool = false
    @Published var nfEnabled: Bool = false
    @Published var agcMode: Int = 0         // 0=off, 1=slow, 2=medium, 3=fast
    @Published var filterLow: Int = 100
    @Published var filterHigh: Int = 3000
    @Published var notches: [WDSPNotch] = []

    // ── Connection status ─────────────────────────────────────────
    @Published var ctrlConnected: Bool = false
    @Published var audioRXConnected: Bool = false
    @Published var audioTXConnected: Bool = false
    @Published var spectrumConnected: Bool = false
    @Published var connectionError: String? = nil

    // ── Spectrum data ─────────────────────────────────────
    @Published var spectrumData: Data?
    @Published var waterfallImage: UIImage?   // pre-rendered by SpectrumProcessor
    @Published var fftData: [Float] = []      // EMA-smoothed spectrum (0..1) for FFTView
    @Published var iqSampleRateHz: Int = 78125  // 39k/78k/156k/312k

    // ── Callbacks ───────────────────────────────────────────
    /// Called when IQ sample rate changes — consumers reset EMA/accumulation buffers.
    var onSampleRateChanged: (() -> Void)?

    // ── Latency tracking ────────────────────────────────────────
    var lastPingTime: Date = .now
    @Published var latencyMs: Double = 0

    /// IQ sample rate mapping (server key → Hz).
    static let sampleRateMapping: [String: Int] = [
        "39k": 39062, "78k": 78125, "156k": 156250, "312k": 312500,
    ]
    static let sampleRateOptions: [(label: String, hz: Int)] = [
        ("39k", 39062), ("78k", 78125), ("156k", 156250), ("312k", 312500),
    ]

    /// Band preset definitions (Hz).
    static let bands: [(name: String, freq: Int)] = [
        ("160m", 1_900_000),
        ("80m",  3_650_000),
        ("60m",  5_357_000),
        ("40m",  7_074_000),
        ("30m", 10_136_000),
        ("20m", 14_074_000),
        ("17m", 18_100_000),
        ("15m", 21_074_000),
        ("12m", 24_915_000),
        ("10m", 28_074_000),
        ("6m",  50_313_000),
        ("2m", 144_300_000),
    ]

    /// Parse a `getFreq:14074000`-style server push and update state.
    func apply(serverMessage: String) {
        // Handle PONG (no colon — see server.py line 184)
        if serverMessage == "PONG" {
            latencyMs = Date.now.timeIntervalSince(lastPingTime) * 1000
            let ms = Int(latencyMs)
            latency = "\(ms)ms"
            return
        }
        guard serverMessage.contains(":") else { return }
        let cmd = String(serverMessage.prefix(while: { $0 != ":" }))
        let val = String(serverMessage.dropFirst(cmd.count + 1))

        switch cmd {
        case "getFreq":
            frequency = Int(val) ?? frequency
        case "getMode":
            mode = val
        case "getPTT":
            ptt = (val == "true")
        case "getSignalLevel":
            signalLevel = Int(val) ?? signalLevel
        case "wdspStatus":
            if let data = val.data(using: .utf8),
               let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                applyWDSPStatus(json)
            }
        case "setWDSPEnabled":
            wdspEnabled = (val == "enabled" || val == "true")
        case "setWDSPNR2":
            nr2Enabled = (val == "true")
        case "setWDSPNR2Level":
            nr2Level = Int(val) ?? nr2Level
        case "setWDSPNB":
            nbEnabled = (val == "true")
        case "setWDSPANF":
            anfEnabled = (val == "true")
        case "setSampleRate":
            // Server sends key like "39k", "78k", "156k", "312k"
            iqSampleRateHz = RadioState.sampleRateMapping[val] ?? iqSampleRateHz
            onSampleRateChanged?()
        case "setWDSPNFEnabled":
            nfEnabled = (val == "true")
        case "setWDSPAGC":
            agcMode = Int(val) ?? agcMode
        case "addWDSPNotch":
            let parts = val.split(separator: ",")
            if parts.count >= 3,
               let idx = Int(parts[0]),
               let fc = Float(parts[1]),
               let fw = Float(parts[2]) {
                notches.append(WDSPNotch(index: idx, freqHz: fc, bandwidthHz: fw))
            }
        case "deleteWDSPNotch":
            if let idx = Int(val) {
                notches.removeAll { $0.index == idx }
            }
        case "editWDSPNotch":
            let parts = val.split(separator: ",")
            if parts.count >= 3,
               let idx = Int(parts[0]),
               let fc = Float(parts[1]),
               let fw = Float(parts[2]),
               let i = notches.firstIndex(where: { $0.index == idx }) {
                notches[i] = WDSPNotch(index: idx, freqHz: fc, bandwidthHz: fw)
            }
        case "getTXTelem":
            // Format: watts,volts,temp_c,raw
            let parts = val.split(separator: ",")
            if parts.count >= 3 {
                txPowerWatts = Float(parts[0]) ?? txPowerWatts
                txSupplyVolts = Float(parts[1]) ?? txSupplyVolts
                txTempCelsius = Float(parts[2]) ?? txTempCelsius
            }
        case "getSampleRate":
            iqSampleRateHz = RadioState.sampleRateMapping[val] ?? iqSampleRateHz
        // ── New server broadcasts (acknowledged but not yet acted on) ──
        case "setDrive", "setTXDriveGain", "setATT", "setPreamp",
             "setSpectrumFps", "panfft":
            break
        case "setWDSPNR2GainMethod", "setWDSPNR2NpeMethod", "setWDSPNR2AeRun",
             "setWDSPBandpass", "setWDSPEQ",
             "setWDSPAGCAttack", "setWDSPAGCDecay", "setWDSPAGCHang",
             "setWDSPAGCSlope", "setWDSPFMSquelch", "setWDSPFMSquelchThresh":
            break
        case "wdspSMeter":
            break
        default:
            break
        }
    }

    private func applyWDSPStatus(_ dict: [String: Any]) {
        wdspEnabled = dict["wdsp_enabled"] as? Bool ?? wdspEnabled
        nr2Enabled  = dict["nr2_enabled"]  as? Bool ?? nr2Enabled
        nr2Level    = dict["nr2_level"]    as? Int  ?? nr2Level
        nbEnabled   = dict["nb_enabled"]   as? Bool ?? nbEnabled
        anfEnabled  = dict["anf_enabled"]  as? Bool ?? anfEnabled
        nfEnabled   = dict["nf_enabled"]   as? Bool ?? nfEnabled
        agcMode     = dict["agc_mode"]     as? Int  ?? agcMode
        if let notchesArr = dict["notches"] as? [[String: Any]] {
            notches = notchesArr.compactMap { n in
                guard let idx = n["index"] as? Int,
                      let fc  = n["freq"]  as? Float,
                      let fw  = n["bw"]    as? Float else { return nil }
                return WDSPNotch(index: idx, freqHz: fc, bandwidthHz: fw)
            }
        }
    }
}

struct WDSPNotch: Identifiable, Equatable {
    let index: Int
    let freqHz: Float
    let bandwidthHz: Float

    var id: Int { index }
}
