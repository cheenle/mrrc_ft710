import Foundation

/// Manages 4 WebSocket connections to the FT710 FastAPI backend.
@MainActor
final class ConnectionManager: ObservableObject {
    let serverHost: String
    private(set) var password: String?

    private(set) var ctrl: WebSocketConnection!
    private(set) var audioRX: WebSocketConnection!
    private(set) var audioTX: WebSocketConnection!
    private(set) var spectrum: WebSocketConnection!

    @Published var ctrlConnected     = false
    @Published var audioRXConnected  = false
    @Published var audioTXConnected  = false
    @Published var spectrumConnected = false
    @Published var errorMessage: String?

    init(serverHost: String = "radio.vlsc.net:8888",
         password: String? = nil) {
        self.serverHost = serverHost
        self.password = password
        createSockets()
    }

    func updateCredentials(password: String?) {
        self.password = password
        disconnectAll()
        createSockets()
    }

    func connectAll() {
        ctrl.connect()
        audioRX.connect()
        audioTX.connect()
        spectrum.connect()
    }

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

    func sendControl(_ jsonString: String) {
        ctrl.send(text: jsonString)
    }

    // MARK: - Private

    private func createSockets() {
        ctrl     = WebSocketConnection(serverHost: serverHost, endpoint: "/WSradio",
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
        }
        audioRX.onConnected = { [weak self] in self?.audioRXConnected = true }
        audioTX.onConnected = { [weak self] in self?.audioTXConnected = true }
        spectrum.onConnected = { [weak self] in self?.spectrumConnected = true }

        ctrl.onDisconnected = { [weak self] _ in self?.ctrlConnected = false }
        audioRX.onDisconnected = { [weak self] _ in self?.audioRXConnected = false }
        audioTX.onDisconnected = { [weak self] _ in self?.audioTXConnected = false }
        spectrum.onDisconnected = { [weak self] _ in self?.spectrumConnected = false }

        ctrl.onError = { [weak self] e in self?.logError("CTRL", e) }
        audioRX.onError = { [weak self] e in self?.logError("AudioRX", e) }
        audioTX.onError = { [weak self] e in self?.logError("AudioTX", e) }
        spectrum.onError = { [weak self] e in self?.logError("Spectrum", e) }
    }

    private func logError(_ tag: String, _ err: Error) {
        let msg = "[\(tag)] \(err.localizedDescription)"
        errorMessage = msg
        print("⚠️ \(msg)")
    }
}
