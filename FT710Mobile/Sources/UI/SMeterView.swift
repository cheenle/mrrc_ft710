import SwiftUI

/// Analog-style S-meter bar (S0–S9+60), green→yellow→red gradient.
struct SMeterView: View {
    let level: Int      // 0–60+
    let ptt: Bool

    private let maxLevel: Float = 60

    var body: some View {
        VStack(spacing: 2) {
            HStack {
                Text("S")
                    .font(.subheadline.monospaced())
                    .foregroundColor(.gray)

                // Meter bar
                GeometryReader { geo in
                    ZStack(alignment: .leading) {
                        RoundedRectangle(cornerRadius: 3)
                            .fill(Color.white.opacity(0.1))
                            .frame(height: 12)

                        RoundedRectangle(cornerRadius: 3)
                            .fill(meterColor)
                            .frame(width: barWidth(in: geo.size.width), height: 12)
                            .animation(.easeOut(duration: 0.3), value: level)
                    }
                }
                .frame(height: 12)

                // Level number
                Text(ptt ? "TX" : "S\(min(level, 9))")
                    .font(.subheadline.monospaced())
                    .foregroundColor(ptt ? .red : .green)
                    .frame(width: 30, alignment: .trailing)

                if level > 9 {
                    Text("+\(level - 9)dB")
                        .font(.system(size: 9))
                        .foregroundColor(.yellow)
                }
            }
            .padding(.horizontal, 16)

            // S-scale labels
            HStack(spacing: 0) {
                ForEach(0..<10) { s in
                    Text("\(s)")
                        .font(.system(size: 7))
                        .foregroundColor(.gray.opacity(0.5))
                        .frame(maxWidth: .infinity)
                }
            }
            .padding(.horizontal, 36)
        }
        .padding(.vertical, 4)
    }

    private var meterColor: Color {
        if ptt { return .red }
        let fraction = Float(level) / maxLevel
        switch fraction {
        case 0..<0.3:  return .green
        case 0.3..<0.7: return .yellow
        default:        return .red
        }
    }

    private func barWidth(in total: CGFloat) -> CGFloat {
        CGFloat(min(Float(level) / maxLevel, 1.0)) * total
    }
}
