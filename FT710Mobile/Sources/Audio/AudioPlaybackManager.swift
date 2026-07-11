import AVFoundation
import Accelerate

/// Plays Int16 PCM audio received from /WSaudioRX using AVAudioPlayerNode.
/// Uses vDSP for fast Int16→Float32 conversion and RMS calculation.
final class AudioPlaybackManager: NSObject, ObservableObject, @unchecked Sendable {
    private let engine = AVAudioEngine()
    private let playerNode = AVAudioPlayerNode()
    private let ioQueue = DispatchQueue(label: "audio.playback", qos: .userInitiated)

    private let sourceSampleRate: Double = 48000  // matches server RX_OUT_RATE
    private var playbackFormat: AVAudioFormat!

    private(set) var isStarted = false

    // ── Diagnostics ───────────────────────────────────────────
    private var frameCount: Int = 0
    private var opusDropCount: Int = 0
    private var lastDiagTime = Date()

    // ── Observable state ──────────────────────────────────────
    @Published var isMuted: Bool = false {
        didSet { playerNode.volume = isMuted ? 0 : 1 }
    }
    @Published var rmsLevel: Float = 0.0
    @Published var audioError: String?

    // ── Recording ─────────────────────────────────────────────
    @Published var isRecording: Bool = false
    private var recordBuffer: [Float] = []
    private let recordLock = NSLock()

    func startRecording() {
        recordLock.lock(); recordBuffer.removeAll(keepingCapacity: true); recordLock.unlock()
        isRecording = true
    }

    func stopRecording() -> Data? {
        isRecording = false
        recordLock.lock(); let samples = recordBuffer; recordLock.unlock()
        guard !samples.isEmpty else { return nil }
        return makeWAV(samples: samples)
    }

    var recordingDuration: TimeInterval {
        recordLock.lock(); let c = recordBuffer.count; recordLock.unlock()
        return TimeInterval(c) / sourceSampleRate
    }

    // MARK: - Start / Stop

    func start() {
        guard !isStarted else { return }
        isStarted = true
        frameCount = 0; opusDropCount = 0; lastDiagTime = Date()

        playbackFormat = AVAudioFormat(commonFormat: .pcmFormatFloat32,
                                        sampleRate: sourceSampleRate,
                                        channels: 1,
                                        interleaved: false)!

        configureSession()
        engine.attach(playerNode)
        engine.connect(playerNode, to: engine.mainMixerNode, format: playbackFormat)
        playerNode.volume = isMuted ? 0 : 1

        do {
            try engine.start()
            playerNode.play()
            print("🔊 Audio playback started @ \(sourceSampleRate) Hz")
        } catch {
            audioError = "Engine start: \(error.localizedDescription)"
            print("⚠️ \(audioError!)")
        }
    }

    func stop() {
        guard isStarted else { return }
        isStarted = false
        playerNode.stop()
        engine.stop()
        engine.reset()
        print("🔇 Audio playback stopped  frames=\(frameCount) opusDrops=\(opusDropCount)")
    }

    // MARK: - Enqueue PCM data

    /// Frame format: 1-byte codec tag (0x00=PCM, 0x01=Opus) + payload.
    func enqueue(int16Data: Data) {
        guard isStarted, int16Data.count >= 3 else { return }
        let codec = int16Data[0]
        if codec == 0x01 {
            opusDropCount += 1
            // Notify ctrl channel to resend setOpus:false if Opus persists
            if opusDropCount == 10 {
                print("⚠️ Audio: received 10 Opus frames — sending setOpus:false")
                NotificationCenter.default.post(name: .audioOpusDetected, object: nil)
            }
            return
        }

        let pcmBytes = int16Data.dropFirst()
        let sampleCount = pcmBytes.count / 2
        guard sampleCount > 0 else { return }

        // ── vDSP-accelerated Int16 LE → Float32 ───────────────
        var samples = [Float](repeating: 0, count: sampleCount)
        pcmBytes.withUnsafeBytes { raw in
            let base = raw.baseAddress!.assumingMemoryBound(to: Int16.self)
            var scale = Float(1.0 / 32768.0)
            vDSP_vflt16(base, 1, &samples, 1, vDSP_Length(sampleCount))
            vDSP_vsmul(samples, 1, &scale, &samples, 1, vDSP_Length(sampleCount))
        }

        // Recording
        if isRecording {
            recordLock.lock()
            recordBuffer.append(contentsOf: samples)
            recordLock.unlock()
        }

        // ── vDSP RMS ──────────────────────────────────────────
        var rms: Float = 0
        vDSP_rmsqv(samples, 1, &rms, vDSP_Length(sampleCount))
        DispatchQueue.main.async { [weak self] in self?.rmsLevel = rms }

        // ── Schedule buffer ───────────────────────────────────
        guard let fmt = playbackFormat,
              let buf = AVAudioPCMBuffer(pcmFormat: fmt, frameCapacity: AVAudioFrameCount(sampleCount))
        else { return }

        buf.frameLength = AVAudioFrameCount(sampleCount)
        if let dst = buf.floatChannelData?.pointee {
            dst.initialize(from: samples, count: sampleCount)
        }

        ioQueue.async { [weak self] in
            self?.playerNode.scheduleBuffer(buf)
        }

        // ── 5-second diagnostic ───────────────────────────────
        frameCount += 1
        let now = Date()
        if now.timeIntervalSince(lastDiagTime) >= 5.0 {
            let fps = Double(frameCount) / now.timeIntervalSince(lastDiagTime)
            print("🔊 Audio: \(frameCount) frames @ \(String(format:"%.1f",fps))fps  sampleCount=\(sampleCount)  opusDrops=\(opusDropCount)")
            frameCount = 0; opusDropCount = 0; lastDiagTime = now
        }
    }

    // MARK: - Private

    private func configureSession() {
        let session = AVAudioSession.sharedInstance()
        do {
            try session.setCategory(.playback, mode: .default,
                                    options: [.mixWithOthers, .allowBluetoothA2DP, .allowBluetooth])
            // Lower IO buffer for reduced latency
            try session.setPreferredIOBufferDuration(0.005)  // ~5ms
            try session.setActive(true)
        } catch {
            print("⚠️ AudioSession: \(error)")
        }
    }

    // MARK: - WAV export

    private func makeWAV(samples: [Float]) -> Data {
        let sr = UInt32(sourceSampleRate)
        let ch: UInt16 = 1, bps: UInt16 = 16
        let dataSize = UInt32(samples.count * 2)
        var data = Data()
        data.append("RIFF".data(using: .ascii)!)
        data.append(withUnsafeBytes(of: UInt32(36 + dataSize).littleEndian) { Data($0) })
        data.append("WAVE".data(using: .ascii)!)
        data.append("fmt ".data(using: .ascii)!)
        data.append(withUnsafeBytes(of: UInt32(16).littleEndian) { Data($0) })
        data.append(withUnsafeBytes(of: ch.littleEndian) { Data($0) })
        data.append(withUnsafeBytes(of: bps.littleEndian) { Data($0) })
        data.append(withUnsafeBytes(of: UInt16(1).littleEndian) { Data($0) }) // PCM
        let byteRate = sr * UInt32(ch) * UInt32(bps / 8)
        data.append(withUnsafeBytes(of: byteRate.littleEndian) { Data($0) })
        data.append(withUnsafeBytes(of: UInt16(ch * (bps / 8)).littleEndian) { Data($0) })
        data.append("data".data(using: .ascii)!)
        data.append(withUnsafeBytes(of: dataSize.littleEndian) { Data($0) })
        for s in samples {
            let v = Int16(max(-1, min(1, s)) * 32767).littleEndian
            data.append(withUnsafeBytes(of: v) { Data($0) })
        }
        return data
    }
}

// MARK: - Notification for Opus detection

extension Notification.Name {
    static let audioOpusDetected = Notification.Name("audioOpusDetected")
}
