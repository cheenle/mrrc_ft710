import SwiftUI

/// Large 8-digit frequency display, styled like a physical radio.
struct FrequencyDisplayView: View {
    let freqHz: Int

    var body: some View {
        HStack(spacing: 2) {
            ForEach(Array(digits.enumerated()), id: \.offset) { _, segment in
                Text(segment)
                    .font(.system(size: 56, weight: .bold, design: .monospaced))
                    .foregroundColor(.orange)
            }
        }
    }

    /// Format: XX.XXX.XXX (e.g. 14.074.000)
    private var digits: [String] {
        let hz = freqHz
        let mhz10  = hz / 10_000_000          // 10s of MHz
        let mhz1   = (hz / 1_000_000) % 10    // 1s of MHz
        let khz100 = (hz / 100_000) % 10      // 100s of kHz
        let khz10  = (hz / 10_000) % 10       // 10s of kHz
        let khz1   = (hz / 1_000) % 10        // 1s of kHz
        let hz100  = (hz / 100) % 10          // 100s of Hz
        let hz10   = (hz / 10) % 10           // 10s of Hz
        let hz1    = hz % 10                  // 1s of Hz

        return [
            "\(mhz10)",
            "\(mhz1)",
            ".",
            "\(khz100)",
            "\(khz10)",
            "\(khz1)",
            ".",
            "\(hz100)",
            "\(hz10)",
            "\(hz1)",
        ]
    }
}
