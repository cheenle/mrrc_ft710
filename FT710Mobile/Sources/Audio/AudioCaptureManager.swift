import AVFoundation
import Combine

/// Captures microphone audio, downsamples to 16 kHz Int16 PCM,
/// and publishes chunks for TX over /WSaudioTX.
final class AudioCaptureManager: NSObject, ObservableObject, @unchecked Sendable {
    private let engine = AVAudioEngine()
    private let ioQueue = DispatchQueue(label: "audio.capture", qos: .userInitiated)

    private let targetSampleRate: Double = 16000
    private var downscaleFactor: Int = 3   // nativeRate / 16000 (48k → 3)

    // Frame accumulator — matches web frontend's 20ms frames
    private let frameSize = 320  // 16000 * 0.020 = 320 samples
    private var accumulator: [Float] = []

    @Published var isCapturing = false
    @Published var txLevel: Float = 0.0    // RMS 0–1
    @Published var captureError: String?
    var micGain: Float = 1.0               // 0.0–2.0, default 100%

    /// Callback with Int16 PCM binary ready to send via WebSocket.
    var onFrame: ((Data) -> Void)?

    // MARK: - Start / Stop

    func start() {
        guard !isCapturing else { return }
        isCapturing = true
        accumulator.removeAll(keepingCapacity: true)

        configureSession()
        installTap()
        do {
            try engine.start()
            print("🎤 Microphone capture started")
        } catch {
            captureError = "Mic start: \(error.localizedDescription)"
            print("⚠️ \(captureError!)")
            isCapturing = false
        }
    }

    func stop() {
        guard isCapturing else { return }
        isCapturing = false
        engine.stop()
        engine.inputNode.removeTap(onBus: 0)
        accumulator.removeAll()
        print("🎤 Microphone capture stopped")
    }

    // MARK: - Private

    private func configureSession() {
        let session = AVAudioSession.sharedInstance()
        do {
            try session.setCategory(.playAndRecord, mode: .default,
                                    options: [.allowBluetoothHFP, .defaultToSpeaker])
            try session.setPreferredSampleRate(targetSampleRate)
            try session.setActive(true)
        } catch {
            print("⚠️ Capture AudioSession: \(error)")
        }
    }

    private func installTap() {
        let inputNode = engine.inputNode
        let inputFormat = inputNode.outputFormat(forBus: 0)
        let nativeRate = inputFormat.sampleRate
        downscaleFactor = max(1, Int(nativeRate / targetSampleRate))

        print("🎤 Native mic rate: \(nativeRate) Hz, downscale: \(downscaleFactor)x")

        // Tap at native rate, downsample manually
        inputNode.installTap(onBus: 0, bufferSize: 1024, format: inputFormat) { [weak self] buffer, _ in
            self?.processBuffer(buffer)
        }
    }

    private func processBuffer(_ buffer: AVAudioPCMBuffer) {
        guard isCapturing,
              let channelData = buffer.floatChannelData?.pointee else { return }

        let frameLength = Int(buffer.frameLength)
        let samples = UnsafeBufferPointer(start: channelData, count: frameLength)

        // Downsample by averaging
        let ds = downscaleFactor
        let downCount = frameLength / ds
        guard downCount > 0 else { return }

        var rmsSum: Float = 0
        var downsampled = [Float](repeating: 0, count: downCount)

        for i in 0..<downCount {
            var sum: Float = 0
            let base = i * ds
            for j in 0..<ds where base + j < frameLength {
                sum += samples[base + j]
            }
            sum /= Float(ds)
            downsampled[i] = sum
            rmsSum += sum * sum
        }

        let rms = sqrt(rmsSum / Float(downCount))
        DispatchQueue.main.async { [weak self] in
            self?.txLevel = rms
        }

        // Accumulate and emit complete frames
        accumulator.append(contentsOf: downsampled)

        while accumulator.count >= frameSize {
            let frame = Array(accumulator.prefix(frameSize))
            accumulator.removeFirst(frameSize)

            // Build tagged PCM frame: 1-byte codec tag (0x00=PCM) + Int16 payload.
            // Server uses the first byte to discriminate tagged vs legacy frames.
            var int16Data = Data(capacity: 1 + frameSize * 2)
            int16Data.append(0x00)  // AUDIO_TAG_PCM
            for s in frame {
                let gained = s * micGain
                let clamped = max(-1.0, min(1.0, gained))
                var sample = Int16(clamped * 32767.0)
                int16Data.append(withUnsafeBytes(of: &sample) { Data($0) })
            }

            onFrame?(int16Data)
        }
    }
}
