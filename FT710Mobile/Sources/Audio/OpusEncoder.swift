import Foundation

/// Opus encoder wrapper using C bridge to libopus
final class OpusEncoder {
    private var handle: Int = 0
    private let sampleRate: UInt32 = 48000
    private let channels: UInt32 = 1
    private let frameSize: UInt32 = 960  // 20ms at 48kHz

    init() {
        handle = my_create_encoder(sampleRate, channels, frameSize)
        if handle != 0 {
            print("🎤 Opus encoder created: 48kHz mono, 28kbps CBR")
        } else {
            print("⚠️ Opus encoder creation failed")
        }
    }

    deinit {
        if handle != 0 {
            my_destroy_encoder(handle)
        }
    }

    /// Encode 16-bit PCM samples to Opus
    func encode(_ samples: [Int16]) -> Data? {
        guard handle != 0, !samples.isEmpty else { return nil }

        let maxPacketSize = 1000
        var packet = [UInt8](repeating: 0, count: maxPacketSize)

        let pcmPtr = samples.withUnsafeBufferPointer { $0.baseAddress! }
        let encodedLen = my_opus_encode(handle, pcmPtr, Int32(samples.count), &packet, Int32(maxPacketSize))

        guard encodedLen > 0 else { return nil }

        return Data(packet[0..<Int(encodedLen)])
    }
}

// MARK: - C Bridge Functions

@_silgen_name("my_create_encoder")
func my_create_encoder(_ sampleRate: UInt32, _ channels: UInt32, _ frameSize: UInt32) -> Int

@_silgen_name("my_destroy_encoder")
func my_destroy_encoder(_ handle: Int)

@_silgen_name("my_opus_encode")
func my_opus_encode(_ handle: Int, _ pcm: UnsafePointer<Int16>, _ pcmSize: Int32, _ packet: UnsafeMutablePointer<UInt8>, _ maxPacketSize: Int32) -> Int32
