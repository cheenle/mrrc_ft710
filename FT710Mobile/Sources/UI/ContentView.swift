import SwiftUI

/// Main container — tabs for RX, DSP, and Settings.
struct ContentView: View {
    @EnvironmentObject var viewModel: RadioViewModel
    @State private var selectedTab = 0

    var body: some View {
        ZStack {
            Color.radioBg.ignoresSafeArea()
            if !viewModel.state.powerOn { offState }
            else { onState }
        }
    }

    private var offState: some View {
        VStack(spacing: 20) {
            Spacer()
            Image(systemName: "antenna.radiowaves.left.and.right")
                .font(.system(size: 56, weight: .thin)).foregroundColor(.radioAccent)
            Text("FT-710").font(.title.weight(.semibold)).foregroundColor(.radioText)
            Text("Remote Control").font(.subheadline).foregroundColor(.radioMuted)
            if let err = viewModel.state.connectionError {
                Text(err).font(.caption).foregroundColor(.radioRed).padding(.horizontal)
            }
            Button(action: { viewModel.powerOnAsync() }) {
                Label("连接电台", systemImage: "power").font(.headline).foregroundColor(.black)
                    .frame(maxWidth: 240).frame(height: 50)
                    .background(Color.radioAccent).clipShape(RoundedRectangle(cornerRadius: 14))
            }
            Spacer()
        }
    }

    private var onState: some View {
        VStack(spacing: 0) {
            HeaderView().padding(.horizontal, 10).padding(.top, 2).background(Color.radioBg)
            ZStack(alignment: .bottom) {
                TabView(selection: $selectedTab) {
                    MainRXView().tag(0).tabItem {
                        Image(systemName: "water.waves"); Text("接收") }
                    DSPPanelView().tag(1).tabItem {
                        Image(systemName: "slider.horizontal.3"); Text("DSP") }
                    SettingsView().tag(2).tabItem {
                        Image(systemName: "gearshape"); Text("设置") }
                }.tint(Color.orange)

                VStack(spacing: 0) {
                    if viewModel.state.txStatus > 0 {
                        Rectangle().fill(Color.red.opacity(0.08)).frame(height: 16)
                    }
                    PTTBar(
                        pressing: viewModel.state.txStatus > 0,
                        txLevel: viewModel.audioCapture.txLevel,
                        txPower: Float(viewModel.state.powerWatts),
                        onPress: { viewModel.setPTT(true) },
                        onRelease: { viewModel.setPTT(false) }
                    )
                }.offset(y: -49)
            }
        }
    }
}

// MARK: - PTT Bar (reused from reference with minor adaptations)

struct PTTBar: View {
    let pressing: Bool; let txLevel: Float; let txPower: Float
    let onPress: () -> Void; let onRelease: () -> Void

    var body: some View {
        VStack(spacing: 2) {
            if pressing {
                HStack(spacing: 8) {
                    Text(String(format: "%.0fW", txPower)).font(.caption.monospaced().bold()).foregroundColor(.radioRed)
                    Capsule().fill(Color.white.opacity(0.1)).frame(height: 6)
                        .overlay(alignment: .leading) {
                            Capsule().fill(Color.radioRed)
                                .frame(width: max(6, CGFloat(txLevel * 3) * 200), height: 6)
                        }
                }.padding(.horizontal, 40)
            }
            Button(action: {}) {
                Text(pressing ? "● TX ●" : "PTT")
                    .font(.system(size: 28, weight: .heavy, design: .rounded))
                    .foregroundColor(pressing ? .black : Color.red)
                    .frame(maxWidth: 320).frame(height: 84)
                    .background(pressing ? Color.red : Color.red.opacity(0.12))
                    .clipShape(Capsule())
            }
            .buttonStyle(PTTPressStyle(onPress: onPress, onRelease: onRelease))
        }
        .padding(.horizontal, 12).padding(.vertical, 4)
        .background(Color.radioBg.opacity(0.97))
    }
}

struct PTTPressStyle: ButtonStyle {
    let onPress: () -> Void; let onRelease: () -> Void
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.95 : 1.0)
            .animation(.easeOut(duration: 0.1), value: configuration.isPressed)
            .onChange(of: configuration.isPressed) { _, p in if p { onPress() } else { onRelease() } }
    }
}
