import SwiftUI

/// Single rotary-knob style mode selector — tap to cycle, or use < > arrows.
struct ModeSelectorView: View {
    let currentMode: String
    let onSelect: (String) -> Void

    private let modes = ["USB", "LSB", "AM", "FM", "CW", "RTTY", "DIGI"]

    private var currentIndex: Int {
        modes.firstIndex(of: currentMode) ?? 0
    }

    var body: some View {
        HStack(spacing: 2) {
            // Left arrow
            Button(action: { select(offset: -1) }) {
                Image(systemName: "chevron.left")
                    .font(.caption.weight(.bold))
                    .foregroundColor(.orange)
            }
            .padding(.horizontal, 4)

            // Center — tap to cycle
            Button(action: { select(offset: 1) }) {
                Text(currentMode)
                    .font(.subheadline.weight(.bold))
                    .foregroundColor(.orange)
                    .frame(minWidth: 40)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 5)
                    .background(Color.orange.opacity(0.15))
                    .cornerRadius(6)
            }

            // Right arrow
            Button(action: { select(offset: 1) }) {
                Image(systemName: "chevron.right")
                    .font(.caption.weight(.bold))
                    .foregroundColor(.orange)
            }
            .padding(.horizontal, 4)
        }
    }

    private func select(offset: Int) {
        var idx = (currentIndex + offset) % modes.count
        if idx < 0 { idx += modes.count }
        onSelect(modes[idx])
    }
}
