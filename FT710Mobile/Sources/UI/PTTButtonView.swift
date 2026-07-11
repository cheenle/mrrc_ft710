import SwiftUI

/// Large PTT (Push-To-Talk) button — hold to transmit, release to receive.
struct PTTButtonView: View {
    let ptt: Bool
    let onPress: () -> Void
    let onRelease: () -> Void
    @State private var hasPressed = false

    var body: some View {
        Circle()
            .fill(ptt ? Color.red : Color.red.opacity(0.3))
            .frame(width: 96, height: 96)
            .overlay(
                Text("TX")
                    .font(.title2.weight(.bold))
                    .foregroundColor(ptt ? .white : .red)
            )
            .overlay(
                Circle()
                    .stroke(Color.red.opacity(0.5), lineWidth: 3)
            )
            .onLongPressGesture(minimumDuration: 0.05, maximumDistance: 100) {
                // on tap (when released) — nothing
            } onPressingChanged: { pressing in
                if pressing, !hasPressed {
                    hasPressed = true
                    onPress()
                } else if !pressing, hasPressed {
                    hasPressed = false
                    onRelease()
                }
            }
    }
}
