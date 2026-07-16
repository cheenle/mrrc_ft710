import Foundation
import UIKit

/// Central state model for FT-710 radio — @MainActor for SwiftUI safety.
/// Mirrors the Python RadioState fields in radio_state.py.
@MainActor
final class RadioState: ObservableObject {
    // MARK: - VFO
    @Published var vfoAFreq: Int = 14_200_000
    @Published var vfoBFreq: Int = 7_050_000
    @Published var activeVFO: String = "A"
    @Published var mode: Int = 2             // Yaesu mode register (1=LSB,2=USB,3=CW-U,...)
    @Published var txStatus: Int = 0         // 0=RX, 1=TX, 2=TUNE

    // MARK: - Meters (raw 0-255)
    @Published var sMeter: Int = 0
    @Published var compMeter: Int = 0
    @Published var alcMeter: Int = 0
    @Published var powerMeter: Int = 0
    @Published var swrMeter: Int = 0
    @Published var idMeter: Int = 0
    @Published var vdMeter: Int = 0

    // MARK: - Radio Settings
    @Published var afGain: Int = 128
    @Published var rfGain: Int = 255
    @Published var rfPower: Int = 100
    @Published var filterWidth: Int = 5
    @Published var preamp: Int = 0           // 0=OFF,1=AMP1,2=AMP2
    @Published var attenuator: Int = 0       // 0=OFF,1=6dB,2=12dB,3=18dB
    @Published var ipo: Int = 0              // 0=OFF,1=10dB,2=20dB,3=30dB
    @Published var noiseBlanker: Bool = false
    @Published var noiseReduction: Bool = false
    @Published var autoNotch: Bool = false
    @Published var compressor: Bool = false
    @Published var compressorLevel: Int = 50
    @Published var nrLevel: Int = 8
    @Published var nbLevel: Int = 5
    @Published var tunerStatus: Int = 0      // 0=OFF,1=ON,2=Tuning
    @Published var powerOn: Bool = true
    @Published var showSettings: Bool = false
    @Published var squelch: Int = 0
    @Published var micGain: Int = 50
    @Published var split: Bool = false
    @Published var vox: Bool = false
    @Published var breakIn: Bool = false

    // MARK: - Scope
    @Published var scopeOn: Bool = true
    @Published var scopeSpan: Int = 6        // 6=100kHz
    @Published var scopeSpeed: Int = 2
    @Published var scopeMode: Int = 0
    @Published var scopeStartFreq: Int = 0

    // MARK: - Extended DSP
    @Published var antenna: Int = 1
    @Published var agc: Int = 1              // 0=OFF,1=FAST,2=MED,3=SLOW
    @Published var dnrLevel: Int = 0
    @Published var contourLevel: Int = 0

    // MARK: - Radio Info
    @Published var hiSWR: Bool = false
    @Published var recordingStatus: Int = 0
    @Published var rxtxStatus: Int = 0
    @Published var tunerTuning: Bool = false
    @Published var scanStatus: Int = 0
    @Published var squelchOpen: Bool = false
    @Published var meterDisplay: Int = 0
    @Published var amcLevel: Int = 50

    // MARK: - Connection
    @Published var serialConnected: Bool = false
    @Published var lastUpdate: Double = 0.0
    @Published var ctrlConnected: Bool = false
    @Published var audioRXConnected: Bool = false
    @Published var audioTXConnected: Bool = false
    @Published var spectrumConnected: Bool = false
    @Published var connectionError: String?

    // MARK: - Spectrum
    @Published var waterfallImage: UIImage?
    @Published var fftData: [Float] = []            // current FFT line (850 bins)

    // MARK: - Derived properties
    var activeFreq: Int { activeVFO == "A" ? vfoAFreq : vfoBFreq }
    var modeName: String { Self.modeNumToName[mode] ?? "USB" }
    var modeDisplay: String { Self.modeDisplayNames[modeName] ?? modeName }
    var bandName: String {
        for band in Self.bands {
            if band.start <= activeFreq && activeFreq <= band.end { return band.name }
        }
        return "GEN"
    }
    var sMeterDBm: Double { rawToDBm(sMeter) }
    var sUnit: String { rawToSUnit(sMeter) }
    var powerWatts: Double { rawToPower(powerMeter) }
    var swrRatio: Double { rawToSWR(swrMeter) }
    var vdVolts: Double { rawToVoltage(vdMeter) }
    var idAmps: Double { rawToCurrent(idMeter) }
    var alcPct: Double { max(0, min(100, Double(alcMeter) / 255.0 * 100)) }
    var isTransmitting: Bool { txStatus > 0 }
    var preampLabel: String { ["OFF","AMP1","AMP2"][ preamp >= 0 && preamp <= 2 ? preamp : 0 ] }
    var attenuatorLabel: String { ["OFF","6dB","12dB","18dB"][ attenuator >= 0 && attenuator <= 3 ? attenuator : 0 ] }
    static let ipoLabels: [Int: String] = [0: "OFF", 10: "10dB", 20: "20dB", 30: "30dB"]
    var ipoLabel: String { Self.ipoLabels[ipo] ?? "OFF" }
    var filterHz: Int? {
        let widths = Self.filterWidthsForMode(modeName)
        return widths.first(where: { $0.0 == filterWidth })?.1
    }
    var scopeSpanHz: Int { Self.scopeSpans[scopeSpan] ?? 100000 }

    // MARK: - Static tables (from config.py)

    static let modeNumToName: [Int: String] = [
        1: "LSB", 2: "USB", 3: "CW-U", 4: "FM", 5: "AM",
        6: "RTTY-L", 7: "CW-L", 8: "DATA-L", 9: "RTTY-U",
        10: "DATA-FM", 11: "FM-N", 12: "DATA-U", 13: "AM-N", 14: "PSK",
    ]

    static let modeDisplayNames: [String: String] = [
        "LSB": "LSB", "USB": "USB", "CW-U": "CW", "CW-L": "CWR",
        "AM": "AM", "AM-N": "AM-N", "FM": "FM", "FM-N": "FM-N",
        "RTTY-L": "RTTY", "RTTY-U": "RTTY-R",
        "DATA-L": "DATA", "DATA-U": "DATA-R",
        "DATA-FM": "D-FM", "DATA-FM-N": "D-FMN", "PSK": "PSK",
    ]

    static let uiModes = ["LSB", "USB", "CW-U", "AM", "FM", "RTTY-L", "DATA-L"]

    static let scopeSpans: [Int: Int] = [
        0: 1000, 1: 2000, 2: 5000, 3: 10000, 4: 20000,
        5: 50000, 6: 100000, 7: 200000, 8: 500000, 9: 1000000,
    ]

    static let scopeSpanLabels: [Int: String] = [
        0: "1 kHz", 1: "2 kHz", 2: "5 kHz", 3: "10 kHz", 4: "20 kHz",
        5: "50 kHz", 6: "100 kHz", 7: "200 kHz", 8: "500 kHz", 9: "1 MHz",
    ]

    static let bands: [(name: String, start: Int, end: Int, defaultFreq: Int)] = [
        ("160m", 1_800_000, 2_000_000, 1_845_500),
        ("80m",  3_500_000, 4_000_000, 3_850_000),
        ("60m",  5_250_000, 5_450_000, 5_350_000),
        ("40m",  7_000_000, 7_300_000, 7_050_000),
        ("30m", 10_100_000, 10_150_000, 10_140_000),
        ("20m", 14_000_000, 14_350_000, 14_270_000),
        ("17m", 18_068_000, 18_168_000, 18_132_500),
        ("15m", 21_000_000, 21_450_000, 21_400_000),
        ("12m", 24_890_000, 24_990_000, 24_952_500),
        ("10m", 28_000_000, 29_700_000, 28_450_000),
        ("6m",  50_000_000, 54_000_000, 50_150_000),
        ("4m",  70_000_000, 70_500_000, 70_250_000),
    ]

    static let filterWidthsVoice: [(Int, Int)] = [
        (9, 1800),
        (11, 2000),
        (13, 2400),
        (17, 2700),
        (20, 3000),
        (23, 4500),
    ]

    static let filterWidthsNarrow: [(Int, Int)] = [
        (1,50),(2,100),(3,150),(4,200),(5,250),(6,300),(7,350),(8,400),
        (9,450),(10,500),(11,600),(12,800),(13,1200),(14,1400),(15,1700),
        (16,2000),(17,2400),(18,3000),(19,3200),(20,3500),(21,4000),
    ]

    static let narrowModes: Set<String> = ["CW-U","CW-L","RTTY-L","RTTY-U","DATA-L","DATA-U","PSK"]

    static func filterWidthsForMode(_ modeName: String) -> [(Int, Int)] {
        narrowModes.contains(modeName) ? filterWidthsNarrow : filterWidthsVoice
    }

    // MARK: - Calibration (from config.py)

    private let sMeterCal: [(Int, Double)] = [
        (0,-54),(12,-48),(27,-42),(40,-36),(55,-30),(65,-24),
        (80,-18),(95,-12),(112,-6),(130,0),(150,10),(172,20),
        (190,30),(220,40),(240,50),(255,60),
    ]
    private let sUnitLevels: [(Int, String)] = [
        (0,"S0"),(12,"S1"),(27,"S2"),(40,"S3"),(55,"S4"),(65,"S5"),
        (80,"S6"),(95,"S7"),(112,"S8"),(130,"S9"),(150,"+10"),
        (172,"+20"),(190,"+30"),(220,"+40"),(240,"+50"),(255,"+60"),
    ]

    // MARK: - Protocol handlers

    /// Apply a full state sync from server (on connect).
    func applyFullState(_ data: [String: Any]) {
        if let v = data["vfo_a_freq"] as? Int { vfoAFreq = v }
        if let v = data["vfo_b_freq"] as? Int { vfoBFreq = v }
        if let v = data["active_vfo"] as? String { activeVFO = v }
        if let v = data["mode"] as? Int { mode = v }
        if let v = data["tx_status"] as? Int { txStatus = v }
        if let v = data["s_meter"] as? Int { sMeter = v }
        if let v = data["comp_meter"] as? Int { compMeter = v }
        if let v = data["alc_meter"] as? Int { alcMeter = v }
        if let v = data["power_meter"] as? Int { powerMeter = v }
        if let v = data["swr_meter"] as? Int { swrMeter = v }
        if let v = data["id_meter"] as? Int { idMeter = v }
        if let v = data["vd_meter"] as? Int { vdMeter = v }
        if let v = data["af_gain"] as? Int { afGain = v }
        if let v = data["rf_gain"] as? Int { rfGain = v }
        if let v = data["rf_power"] as? Int { rfPower = v }
        if let v = data["filter_width"] as? Int { filterWidth = v }
        if let v = data["preamp"] as? Int { preamp = v }
        if let v = data["attenuator"] as? Int { attenuator = v }
        if let v = data["ipo"] as? Int { ipo = v }
        if let v = data["noise_blanker"] as? Bool { noiseBlanker = v }
        if let v = data["noise_reduction"] as? Bool { noiseReduction = v }
        if let v = data["auto_notch"] as? Bool { autoNotch = v }
        if let v = data["compressor"] as? Bool { compressor = v }
        if let v = data["compressor_level"] as? Int { compressorLevel = v }
        if let v = data["tuner_status"] as? Int { tunerStatus = v }
        if let v = data["power_on"] as? Bool { powerOn = v }
        if let v = data["squelch"] as? Int { squelch = v }
        if let v = data["mic_gain"] as? Int { micGain = v }
        if let v = data["split"] as? Bool { split = v }
        if let v = data["scope_span"] as? Int { scopeSpan = v }
        if let v = data["scope_mode"] as? Int { scopeMode = v }
        if let v = data["scope_start_freq"] as? Int { scopeStartFreq = v }
        if let v = data["antenna"] as? Int { antenna = v }
        if let v = data["agc"] as? Int { agc = v }
        if let v = data["serial_connected"] as? Bool { serialConnected = v }
        if let v = data["last_update"] as? Double { lastUpdate = v }
        lastUpdate = Date().timeIntervalSince1970
    }

    /// Apply an incremental stateUpdate patch from server.
    func applyStateUpdate(_ fields: [String: Any]) {
        applyFullState(fields)  // reuse same key mapping
    }

    // MARK: - Calibration helpers

    private func rawToDBm(_ raw: Int) -> Double {
        if raw <= 0 { return -54.0 }
        if raw >= 255 { return 60.0 }
        for i in 0..<(sMeterCal.count - 1) {
            let (r1, d1) = sMeterCal[i]
            let (r2, d2) = sMeterCal[i + 1]
            if r1 <= raw && raw <= r2 {
                let frac = Double(raw - r1) / Double(r2 - r1)
                return d1 + frac * (d2 - d1)
            }
        }
        return 0.0
    }

    private func rawToSUnit(_ raw: Int) -> String {
        for i in 0..<(sUnitLevels.count - 1) {
            let (r1, s1) = sUnitLevels[i]
            let (r2, _) = sUnitLevels[i + 1]
            if r1 <= raw && raw < r2 { return s1 }
        }
        return "+60"
    }

    private func rawToPower(_ raw: Int) -> Double {
        // Approximate: 0→0W, 255→100W for 100W scale
        Double(raw) / 255.0 * Double(rfPower)
    }

    private func rawToSWR(_ raw: Int) -> Double {
        1.0 + Double(raw) / 255.0 * 9.0  // 1.0–10.0
    }

    private func rawToVoltage(_ raw: Int) -> Double {
        Double(raw) / 255.0 * 15.0  // 0–15V
    }

    private func rawToCurrent(_ raw: Int) -> Double {
        Double(raw) / 255.0 * 25.0  // 0–25A
    }
}
