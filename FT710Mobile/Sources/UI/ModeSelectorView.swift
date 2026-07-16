import SwiftUI

/// Mode cycle: tap to advance through LSB / USB / CW-U / AM / FM / RTTY-L / DATA-L
struct ModeSelectorView: View {
    @EnvironmentObject var viewModel: RadioViewModel

    private var currentIndex: Int {
        RadioState.uiModes.firstIndex(of: viewModel.state.modeName) ?? 1
    }

    var body: some View {
        Button(action: {
            let modes = RadioState.uiModes
            let idx = (currentIndex + 1) % modes.count
            viewModel.setMode(modes[idx])
        }) {
            Text(viewModel.state.modeDisplay)
                .font(.system(size: 14, weight: .bold))
                .foregroundColor(.black)
                .frame(minWidth: 40).frame(height: 28)
                .padding(.horizontal, 8)
                .background(Color.radioAccent)
                .cornerRadius(6)
        }
    }
}
