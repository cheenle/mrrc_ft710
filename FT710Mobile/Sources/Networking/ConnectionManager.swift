import Foundation

/// Manages the 4 WebSocket connections to sunmrrc.
@MainActor
final class ConnectionManager: ObservableObject {
    let serverHost: String
    private(set) var password: String?

    // MARK: - Sockets (recreated on credential change)
    private(set) var ctrl: WebSocketConnection!
    private(set) var audioRX: WebSocketConnection!
    private(set) var audioTX: WebSocketConnection!
    private(set) var spectrum: WebSocketConnection!

    @Published var ctrlConnected     = false
    @Published var audioRXConnected  = false
    @Published var audioTXConnected  = false
    @Published var spectrumConnected = false
    @Published var errorMessage: String?

    init(serverHost: String = "radio.vlsc.net:8889",
         password: String? = nil) {
        self.serverHost = serverHost
        self.password = password
        createSockets()
    }

    /// Update credentials and recreate all sockets (requires reconnect).
    func updateCredentials(password: String?) {
        self.password = password
        disconnectAll()
        createSockets()
    }

    /// Connect all 4 endpoints.
    func connectAll() {
        ctrl.connect()
        audioRX.connect()
        audioTX.connect()
        spectrum.connect()
    }

    /// Disconnect all 4 endpoints.
    func disconnectAll() {
        ctrl.disconnect()
        audioRX.disconnect()
        audioTX.disconnect()
        spectrum.disconnect()
        ctrlConnected = false
        audioRXConnected = false
        audioTXConnected = false
        spectrumConnected = false
    }

    // MARK: - Control helpers

    func sendControl(_ command: String) {
        ctrl.send(text: command)
    }

    // MARK: - Private

    private func createSockets() {
        ctrl     = WebSocketConnection(serverHost: serverHost, endpoint: "/WSCTRX",
                                        password: password)
        audioRX  = WebSocketConnection(serverHost: serverHost, endpoint: "/WSaudioRX",
                                        password: password)
        audioTX  = WebSocketConnection(serverHost: serverHost, endpoint: "/WSaudioTX",
                                        password: password)
        spectrum = WebSocketConnection(serverHost: serverHost, endpoint: "/WSspectrum",
                                        password: password)
        setupCallbacks()
    }

    private func setupCallbacks() {
        ctrl.onConnected = { [weak self] in
            self?.ctrlConnected = true
            self?.ctrl.send(text: "setOpus:false")   // request PCM, not Opus
            self?.ctrl.send(text: "getFreq:")
            self?.ctrl.send(text: "getMode:")
            self?.ctrl.send(text: "getPTT:")
            self?.ctrl.send(text: "getWDSPStatus:")
            self?.ctrl.send(text: "getSampleRate")    // sync IQ sample rate for spectrum
        }

        audioRX.onConnected = { [weak self] in
            self?.audioRXConnected = true
        }

        audioTX.onConnected = { [weak self] in
            self?.audioTXConnected = true
            if let pass = self?.password, !pass.isEmpty {
                self?.audioTX.send(text: "auth:\(pass)")
            }
        }

        spectrum.onConnected = { [weak self] in
            self?.spectrumConnected = true
            if let pass = self?.password, !pass.isEmpty {
                self?.spectrum.send(text: "auth:\(pass)")
            }
        }
        ctrl.onDisconnected = { [weak self] _ in self?.ctrlConnected = false }
        ctrl.onError = { [weak self] e in self?.logError("CTRL", e) }

        audioRX.onDisconnected = { [weak self] _ in self?.audioRXConnected = false }
        audioRX.onError = { [weak self] e in self?.logError("AudioRX", e) }

        audioTX.onDisconnected = { [weak self] _ in self?.audioTXConnected = false }
        audioTX.onError = { [weak self] e in self?.logError("AudioTX", e) }

        spectrum.onDisconnected = { [weak self] _ in self?.spectrumConnected = false }
        spectrum.onError = { [weak self] e in self?.logError("Spectrum", e) }
    }

    private func logError(_ tag: String, _ err: Error) {
        let msg = "[\(tag)] \(err.localizedDescription)"
        errorMessage = msg
        print("⚠️ \(msg)")
    }
}
