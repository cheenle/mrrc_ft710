import SwiftUI

/// Mode cycle: < LSB / USB / CW-U / AM / FM / RTTY-L / DATA-L >
struct ModeSelectorView: View {
    @EnvironmentObject var viewModel: RadioViewModel

    private var currentIndex: Int {
        RadioState.uiModes.firstIndex(of: viewModel.state.modeName) ?? 1
    }

    var body: some View {
        HStack(spacing: 0) {
            Button(action: { cycle(-1) }) {
                Image(systemName: "chevron.left").font(.caption2.weight(.bold))
            }.frame(width: 22, height: 28)
            Text(viewModel.state.modeDisplay).font(.caption2.weight(.bold)).foregroundColor(.black)
                .frame(minWidth: 34).frame(height: 28).background(Color.radioAccent)
            Button(action: { cycle(1) }) {
                Image(systemName: "chevron.right").font(.caption2.weight(.bold))
            }.frame(width: 22, height: 28)
        }
        .foregroundColor(.radioAccent).background(Color.radioSurface).cornerRadius(6)
    }

    private func cycle(_ offset: Int) {
        let modes = RadioState.uiModes
        var idx = (currentIndex + offset) % modes.count
        if idx < 0 { idx += modes.count }
        viewModel.setMode(modes[idx])
    }
}
