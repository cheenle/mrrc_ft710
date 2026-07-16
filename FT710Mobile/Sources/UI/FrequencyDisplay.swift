import SwiftUI

/// Frequency display: thin elongated digits with vintage digital-tube feel.
/// Format: XX.XXX.X (10Hz precision).
struct FrequencyDisplayView: View {
    let freqHz: Int

    var body: some View {
        HStack(spacing: 2) {
            ForEach(Array(digits.enumerated()), id: \.offset) { _, segment in
                Text(segment)
                    .font(.system(size: 55, weight: .thin, design: .monospaced))
                    .foregroundColor(segment == "." ? .radioAccent.opacity(0.5) : .radioAccent)
                    .lineLimit(1)
            }
        }
        .frame(maxWidth: .infinity)
        .minimumScaleFactor(0.4)
    }

    /// Format: XX.XXX.X (e.g. 14.074.0 — 10Hz precision)
    private var digits: [String] {
        let hz = freqHz
        let mhz10  = hz / 10_000_000
        let mhz1   = (hz / 1_000_000) % 10
        let khz100 = (hz / 100_000) % 10
        let khz10  = (hz / 10_000) % 10
        let khz1   = (hz / 1_000) % 10
        let hz100  = (hz / 100) % 10
        let hz10   = (hz / 10) % 10

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
        ]
    }
}
