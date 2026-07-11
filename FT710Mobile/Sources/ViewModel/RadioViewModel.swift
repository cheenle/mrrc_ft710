import SwiftUI
import Combine
import AVFoundation

/// Central ViewModel — coordinates networking, audio, and UI state.
@MainActor
final class RadioViewModel: ObservableObject {
    let state = RadioState()
    let connection: ConnectionManager

    let audioPlayback = AudioPlaybackManager()
    let audioCapture = AudioCaptureManager()
    let favorites = FavoritesManager()
    let spectrumProc = SpectrumProcessor()
    let fftProc = FFTProcessor()
    private var cancellables = Set<AnyCancellable>()

    // MARK: - Init

    init(serverHost: String = "radio.vlsc.net:8889",
         password: String? = nil) {
        connection = ConnectionManager(serverHost: serverHost, password: password)
        bindSockets()
        // Reset FFT EMA buffer on IQ sample rate change
        state.onSampleRateChanged = { [weak self] in
            self?.fftProc.reset()
        }
        // Re-send setOpus:false if Opus frames detected (server may have reset)
        NotificationCenter.default.addObserver(forName: .audioOpusDetected, object: nil, queue: .main) { [weak self] _ in
            self?.connection.sendControl("setOpus:false")
        }
    }

    // MARK: - Public API

    private var pingTimer: Timer?
    private let pingInterval: TimeInterval = 2.0

    /// Power on: connect all sockets + start audio session + start heartbeat.
    func powerOn() {
        state.powerOn = true
        connection.connectAll()
        audioPlayback.start()
        startPing()
    }

    /// Async — logs in via API, gets session token, then connects.
    func powerOnAsync() {
        state.powerOn = true
        startPing()

        let scheme = connection.serverHost.contains("localhost") ? "http" : "https"
        guard let loginURL = URL(string: "\(scheme)://\(connection.serverHost)/api/auth/login") else {
            connection.connectAll(); return
        }

        var req = URLRequest(url: loginURL)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let body: [String: String] = ["password": connection.password ?? ""]
        req.httpBody = try? JSONSerialization.data(withJSONObject: body)

        URLSession.shared.dataTask(with: req) { [weak self] data, response, error in
            DispatchQueue.main.async {
                guard let self = self else { return }

                // Extract token from Set-Cookie header
                var token: String?
                if let httpResp = response as? HTTPURLResponse,
                   httpResp.statusCode == 200,
                   let headerFields = httpResp.allHeaderFields as? [String: String],
                   let url = httpResp.url {
                    let cookies = HTTPCookie.cookies(withResponseHeaderFields: headerFields, for: url)
                    token = cookies.first(where: { $0.name == "sunmrrc_auth" })?.value
                    // Also try JSON body fallback
                    if token == nil, let data = data,
                       let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                        token = json["token"] as? String
                    }
                }

                if let tok = token, !tok.isEmpty {
                    self.connection.updateCredentials(password: tok)
                    self.bindSockets()  // re-bind after socket recreation!
                } else {
                    self.state.connectionError = "认证失败，请检查密码"
                }
                self.connection.connectAll()
            }
            Task.detached { [weak self] in
                self?.audioPlayback.start()
            }
        }.resume()
    }

    /// Power off: disconnect + stop audio + stop heartbeat.
    func powerOff() {
        state.powerOn = false
        state.ptt = false
        stopPing()
        connection.disconnectAll()
        audioPlayback.stop()
    }

    // MARK: - Frequency control

    /// Set RX frequency in Hz.
    func setFrequency(_ hz: Int) {
        let clamped = max(100_000, min(2_000_000_000, hz))
        state.frequency = clamped
        connection.sendControl("setFreq:\(clamped)")
    }

    /// Step frequency up or down by `stepHz`.
    func stepFrequency(up: Bool, step: Int = 1000) {
        let delta = up ? step : -step
        setFrequency(state.frequency + delta)
    }

    /// Jump to a predefined band frequency.
    func selectBand(_ hz: Int) {
        setFrequency(hz)
    }

    // MARK: - Filter

    /// Set filter bandwidth by low/high cutoff.
    func setFilter(low: Int, high: Int) {
        state.filterLow = low
        state.filterHigh = high
        connection.sendControl("setFilter:\(low),\(high)")
    }

    /// Set operating mode: USB, LSB, AM, FM, CW, etc.
    func setMode(_ mode: String) {
        state.mode = mode
        connection.sendControl("setMode:\(mode)")
    }

    /// Toggle PTT. Starts mic capture on TX, stops on RX. Mutes RX audio during TX.
    func setPTT(_ tx: Bool) {
        state.ptt = tx
        connection.sendControl("setPTT:\(tx ? "true" : "false")")

        if tx {
            audioPlayback.isMuted = true   // mute RX during TX to prevent feedback
            connection.audioTX.send(text: "m:16000,pcm,0,20")
            audioCapture.start()
        } else {
            audioCapture.stop()
            connection.audioTX.send(text: "s:")
            audioPlayback.isMuted = false  // unmute RX when back to receive
        }
    }

    /// Set AF (volume) gain 0.0–1.0.
    func setAFGain(_ gain: Float) {
        state.afGain = gain
        let val = Int(gain * 100)
        connection.sendControl("setAFGain:\(val)")
    }

    /// Set RF gain 0.0–1.0 (maps to 0–100, controls radio front-end gain).
    func setRFGain(_ gain: Float) {
        state.rfGain = gain
        let val = Int(gain * 100)
        connection.sendControl("setRFGain:\(val)")
    }

    /// Set Mic gain 0.0–2.0, default 1.0 (100%).
    func setMicGain(_ gain: Float) {
        state.micGain = gain
        audioCapture.micGain = gain
    }

    /// Set AGC mode: "off", "slow", "medium", "fast".
    func setAGC(_ mode: String) {
        connection.sendControl("setAGC:\(mode)")
    }

    // MARK: - DSP / WDSP

    func setWDSPEnabled(_ on: Bool) {
        state.wdspEnabled = on
        connection.sendControl("setWDSPEnabled:\(on ? "true" : "false")")
    }

    func setNR2Enabled(_ on: Bool) {
        state.nr2Enabled = on
        connection.sendControl("setWDSPNR2:\(on ? "true" : "false")")
    }

    func setNR2Level(_ level: Int) {
        state.nr2Level = level
        connection.sendControl("setWDSPNR2Level:\(level)")
    }

    func setNBEnabled(_ on: Bool) {
        state.nbEnabled = on
        connection.sendControl("setWDSPNB:\(on ? "true" : "false")")
    }

    func setANFEnabled(_ on: Bool) {
        state.anfEnabled = on
        connection.sendControl("setWDSPANF:\(on ? "true" : "false")")
    }

    func setNFEnabled(_ on: Bool) {
        state.nfEnabled = on
        connection.sendControl("setWDSPNFEnabled:\(on ? "true" : "false")")
    }

    func setWDSPAGCMode(_ uiIndex: Int) {
        // Map UI index to server AGC mode:
        // UI: 0=关(OFF), 1=慢(SLOW), 2=中(MED), 3=快(FAST)
        // Server: 0=OFF, 1=LONG, 2=SLOW, 3=MED, 4=FAST
        let serverMode: Int
        switch uiIndex {
        case 0: serverMode = 0  // OFF
        case 1: serverMode = 2  // SLOW
        case 2: serverMode = 3  // MED
        case 3: serverMode = 4  // FAST
        default: serverMode = 0
        }
        state.agcMode = serverMode
        connection.sendControl("setWDSPAGC:\(serverMode)")
    }

    func setIQSampleRate(_ key: String) {
        connection.sendControl("setSampleRate:\(key)")
    }

    func addNotch(freqHz: Float, bandwidthHz: Float) {
        connection.sendControl("addWDSPNotch:\(freqHz),\(bandwidthHz)")
    }

    func deleteNotch(index: Int) {
        connection.sendControl("deleteWDSPNotch:\(index)")
    }

    // MARK: - Private

    private func startPing() {
        stopPing()
        pingTimer = Timer.scheduledTimer(withTimeInterval: pingInterval, repeats: true) { [weak self] _ in
            Task { @MainActor [weak self] in
                guard let self = self,
                      self.state.powerOn,
                      self.connection.ctrlConnected else { return }
                self.state.lastPingTime = .now
                self.connection.sendControl("PING")
            }
        }
    }

    private func stopPing() {
        pingTimer?.invalidate()
        pingTimer = nil
    }

    private func bindSockets() {
        cancellables.removeAll()

        // Relay nested ObservableObject changes so SwiftUI re-renders ContentView
        state.objectWillChange.sink { [weak self] _ in
            self?.objectWillChange.send()
        }.store(in: &cancellables)

        // ── Connection status sync ────────────────────────────
        connection.$ctrlConnected.receive(on: RunLoop.main).sink { [weak self] in
            self?.state.ctrlConnected = $0
        }.store(in: &cancellables)
        connection.$audioRXConnected.receive(on: RunLoop.main).sink { [weak self] in
            self?.state.audioRXConnected = $0
        }.store(in: &cancellables)
        connection.$audioTXConnected.receive(on: RunLoop.main).sink { [weak self] in
            self?.state.audioTXConnected = $0
        }.store(in: &cancellables)
        connection.$spectrumConnected.receive(on: RunLoop.main).sink { [weak self] in
            self?.state.spectrumConnected = $0
        }.store(in: &cancellables)

        // ── Error forwarding ───────────────────────────────────
        connection.ctrl.onError = { [weak self] err in
            Task { @MainActor [weak self] in
                self?.state.connectionError = err.localizedDescription
            }
        }

        // ── Control text messages ──────────────────────────────
        connection.ctrl.onText = { [weak self] text in
            Task { @MainActor [weak self] in
                self?.state.apply(serverMessage: text)
            }
        }

        // ── Audio RX binary → playback ────────────────────────
        connection.audioRX.onBinary = { [weak self] data in
            self?.audioPlayback.enqueue(int16Data: data)
        }

        // ── Mic capture → TX WebSocket ────────────────────────
        audioCapture.onFrame = { [weak self] pcmData in
            self?.connection.audioTX.send(binary: pcmData)
        }

        // ── Spectrum → SpectrumProcessor (waterfall) + FFTProcessor (line plot) ──
        var specCount = 0
        var specLogged = false
        connection.spectrum.onBinary = { [weak self] data in
            specCount += 1
            if !specLogged && specCount == 10 {
                specLogged = true
                print("📊 SPEC: dataSize=\(data.count) vfo=\(self?.state.frequency ?? 0) sr=\(self?.state.iqSampleRateHz ?? 0)")
                // Print first 8 bytes to verify spectrum data format
                let bytes = [UInt8](data.prefix(16))
                print("📊 SPEC: raw[0..15]=\(bytes.map{String($0)}.joined(separator:","))")
            }
            if specCount % 100 == 0 {
                print("🌊 Spectrum frames: \(specCount), last=\(data.count) bytes")
            }
            // Waterfall
            self?.spectrumProc.feed(data: data) { img in
                self?.state.waterfallImage = img
            }
            // FFT line plot — every 3rd frame (~12 fps from 38 fps source)
            if specCount % 3 == 0 {
                self?.fftProc.feed(data: data) { smoothed in
                    self?.state.fftData = smoothed
                }
            }
        }
    }
}
