import AVFoundation

/// Unified audio session manager for FT710 mobile app.
/// Handles .playAndRecord mode to avoid interruptions during TX/RX switching.
final class AudioSessionManager: ObservableObject {
    static let shared = AudioSessionManager()
    
    @Published var isActive: Bool = false
    @Published var isBluetoothConnected: Bool = false
    
    private let session = AVAudioSession.sharedInstance()
    
    private init() {}
    
    /// Configure audio session for both TX and RX.
    func configureForTransceiver() throws {
        try session.setCategory(.playAndRecord, mode: .voiceChat,
                               options: [.defaultToSpeaker, .allowBluetooth, .allowBluetoothA2DP])
        try session.setPreferredIOBufferDuration(0.005)  // 5ms for low latency
        try session.setActive(true)
        isActive = true
        print("✅ Audio session configured for transceiver mode")
    }
    
    /// Handle audio route changes (e.g., Bluetooth disconnect)
    func handleAudioRouteChange(notification: Notification) {
        // Reactivate session on route change to handle device switches
        print("🔄 Audio route changed")
        try? session.setActive(false)
        try? session.setActive(true)
    }
    
    /// Check if Bluetooth is currently connected
    func isBluetoothActive() -> Bool {
        return session.currentRoute.outputs.contains { $0.portType == .bluetoothHFP || 
                                                       $0.portType == .bluetoothA2DP }
    }
}
