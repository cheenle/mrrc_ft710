import Foundation

/// Generic WebSocket wrapper using URLSessionWebSocketTask (native, iOS 13+).
/// Handles connect / disconnect / auto-reconnect / send text & binary.
/// Checks `session === self.session` in every delegate callback to filter out
/// events from invalidated/old sessions.
final class WebSocketConnection: NSObject, @unchecked Sendable {
    private let endpoint: String
    private let serverHost: String
    private let reconnectDelay: TimeInterval = 3.0
    private var password: String?

    private var task: URLSessionWebSocketTask?
    private var session: URLSession?
    private var isActive = false
    private var shouldReconnect = true

    var onText: ((String) -> Void)?
    var onBinary: ((Data) -> Void)?
    var onConnected: (() -> Void)?
    var onDisconnected: ((Error?) -> Void)?
    var onError: ((Error) -> Void)?

    var isConnected: Bool {
        task?.state == .running && task?.closeCode == .invalid
    }

    init(serverHost: String, endpoint: String, password: String? = nil) {
        self.serverHost = serverHost
        self.endpoint = endpoint
        self.password = password
        super.init()
    }

    func updatePassword(_ password: String?) {
        self.password = password
    }

    func connect() {
        guard !isActive else { return }
        isActive = true
        shouldReconnect = true
        doConnect()
    }

    func disconnect() {
        shouldReconnect = false
        isActive = false
        task?.cancel()
        task = nil
        session?.invalidateAndCancel()
        session = nil
    }

    func send(text: String) {
        task?.send(.string(text)) { [weak self] err in
            if let err = err { self?.onError?(err) }
        }
    }

    func send(binary: Data) {
        task?.send(.data(binary)) { [weak self] err in
            if let err = err { self?.onError?(err) }
        }
    }

    // MARK: - Private

    private func makeSession() -> URLSession {
        let config = URLSessionConfiguration.default
        let scheme = "http"
        config.httpAdditionalHeaders = [
            "Origin": "\(scheme)://\(serverHost)",
            "User-Agent": "FT710Mobile/1.0",
        ]
        return URLSession(configuration: config, delegate: self, delegateQueue: nil)
    }

    private func doConnect() {
        let sess = makeSession()
        session = sess

        let scheme = "ws"
        var urlStr = "\(scheme)://\(serverHost)\(endpoint)"

        if let pass = password, !pass.isEmpty {
            let encPass = pass.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? pass
            urlStr += "?token=\(encPass)"
        }

        guard let url = URL(string: urlStr) else {
            onError?(NSError(domain: "WS", code: -1,
                             userInfo: [NSLocalizedDescriptionKey: "Bad URL"]))
            return
        }
        task = sess.webSocketTask(with: url)
        task?.resume()
        receive()
    }

    private func receive() {
        let expectSession = session  // capture current session
        task?.receive { [weak self] result in
            guard let self = self, self.session === expectSession else { return }
            switch result {
            case .success(let message):
                switch message {
                case .string(let text):
                    self.onText?(text)
                case .data(let data):
                    self.onBinary?(data)
                @unknown default:
                    break
                }
                if self.isActive { self.receive() }

            case .failure:
                break  // disconnect handles cleanup
            }
        }
    }

    private func scheduleReconnect() {
        guard shouldReconnect, isActive else { return }
        DispatchQueue.main.asyncAfter(deadline: .now() + reconnectDelay) { [weak self] in
            guard let self = self, self.isActive, self.shouldReconnect else { return }
            self.doConnect()
        }
    }
}

// MARK: - URLSessionWebSocketDelegate

extension WebSocketConnection: URLSessionWebSocketDelegate, URLSessionTaskDelegate {

    func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask,
                    didOpenWithProtocol protocol: String?) {
        guard session === self.session else { return }  // ignore stale sessions
        print("🔗 WS connected: \(endpoint)")
        DispatchQueue.main.async { [weak self] in
            self?.onConnected?()
        }
    }

    func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask,
                    didCloseWith closeCode: URLSessionWebSocketTask.CloseCode, reason: Data?) {
        guard session === self.session else { return }  // ignore stale sessions

        let reasonStr = reason.flatMap { String(data: $0, encoding: .utf8) } ?? "none"
        print("🔌 WS closed: \(endpoint) code=\(closeCode.rawValue) reason=\(reasonStr)")

        if closeCode.rawValue == 4001 {
            print("🛑 Auth required — stopping reconnect for \(endpoint)")
            shouldReconnect = false
        }

        DispatchQueue.main.async { [weak self] in
            self?.onDisconnected?(nil)
            if closeCode.rawValue != 4001 {
                self?.scheduleReconnect()
            }
        }
    }

    func urlSession(_ session: URLSession, task: URLSessionTask,
                    didCompleteWithError error: Error?) {
        guard session === self.session, let err = error else { return }  // ignore stale sessions

        let nsErr = err as NSError
        if nsErr.domain == NSURLErrorDomain && nsErr.code == NSURLErrorCancelled { return }

        print("❌ WS task error [\(endpoint)]: \(err.localizedDescription)")
        DispatchQueue.main.async { [weak self] in
            self?.onError?(err)
            self?.onDisconnected?(err)
            self?.scheduleReconnect()
        }
    }
}
