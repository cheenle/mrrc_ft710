import SwiftUI

/// Main container — integrated radio UI with always-visible PTT.
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

    // MARK: - Off State
    private var offState: some View {
        VStack(spacing: 20) {
            Spacer()
            Image(systemName: "antenna.radiowaves.left.and.right")
                .font(.system(size: 56, weight: .thin)).foregroundColor(.radioAccent)
            Text("SunSDR2 DX").font(.title.weight(.semibold)).foregroundColor(.radioText)
            Text("Mobile Control").font(.subheadline).foregroundColor(.radioMuted)
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

    // MARK: - On State
    private var onState: some View {
        VStack(spacing: 0) {
            CompactHeaderView()
                .padding(.horizontal, 10).padding(.top, 2)
                .background(Color.radioBg)

            ZStack(alignment: .bottom) {
                TabView(selection: $selectedTab) {
                    MainRXView().tag(0).tabItem {
                        Image(systemName: "water.waves"); Text("接收") }
                    DSPPanelView().tag(1).tabItem {
                        Image(systemName: "slider.horizontal.3"); Text("DSP") }
                    SettingsView().tag(2).tabItem {
                        Image(systemName: "gearshape"); Text("设置") }
                }
                .tint(Color.orange)

                // PTT above tab bar
                VStack(spacing: 0) {
                    if viewModel.state.ptt {
                        Rectangle().fill(Color.red.opacity(0.08)).frame(height: 16)
                    }
                    PTTBar(
                        pressing: viewModel.state.ptt,
                        txLevel: viewModel.audioCapture.txLevel,
                        txPower: viewModel.state.txPowerWatts,
                        onPress: { viewModel.setPTT(true) },
                        onRelease: { viewModel.setPTT(false) }
                    )
                }
                .offset(y: -49)  // above tab bar
            }
        }
    }
}

// MARK: - Compact Header (2 rows)

struct CompactHeaderView: View {
    @EnvironmentObject var viewModel: RadioViewModel
    @State private var showFreqInput = false
    @State private var freqInputText = ""

    var body: some View {
        VStack(spacing: 1) {
            // Row 1: Status bar — S-meter, latency, WS dots + Mode + Power
            HStack(spacing: 12) {
                Text(sMeterLabel(viewModel.state.signalLevel))
                    .font(.caption.weight(.bold)).foregroundColor(.radioGreen)
                Text(viewModel.state.latency).font(.system(size: 10, design: .monospaced)).foregroundColor(.radioMuted)
                wsDot(viewModel.state.ctrlConnected)
                wsDot(viewModel.state.audioRXConnected)
                wsDot(viewModel.state.audioTXConnected)
                wsDot(viewModel.state.spectrumConnected)
                Spacer()
                Text(viewModel.state.mode).font(.caption.weight(.bold)).foregroundColor(.black)
                    .padding(.horizontal, 5).padding(.vertical, 2)
                    .background(Color.radioAccent).cornerRadius(3)
                Button(action: {
                    viewModel.state.powerOn ? viewModel.powerOff() : viewModel.powerOnAsync()
                }) {
                    Image(systemName: viewModel.state.powerOn ? "power.circle.fill" : "power.circle")
                        .font(.body).foregroundColor(viewModel.state.powerOn ? Color.green : .radioMuted)
                }
            }

            // Row 2: Frequency — alone, centered, huge
            Button(action: {
                freqInputText = "\(Int(Double(viewModel.state.frequency) / 1000.0))"
                showFreqInput = true
            }) {
                Text(formatFrequency(viewModel.state.frequency))
                    .font(.system(size: 50, weight: .bold, design: .monospaced))
                    .foregroundColor(.radioAccent)
                    .minimumScaleFactor(0.6)
            }
            .alert("输入频率 (kHz)", isPresented: $showFreqInput) {
                TextField("kHz", text: $freqInputText).keyboardType(.numberPad)
                Button("取消", role: .cancel) {}; Button("确认") {
                    if var v = Int(freqInputText), v > 0 {
                        if v < 100_000 { v *= 1000 }; viewModel.setFrequency(v)
                    }
                }
            }
        }
        .padding(.vertical, 3)
    }

    private func wsDot(_ on: Bool) -> some View {
        Circle().fill(on ? Color.green : Color.red).frame(width: 3, height: 3)
    }

    private func formatFrequency(_ hz: Int) -> String {
        let m = hz / 1_000_000, k = (hz % 1_000_000) / 1000, h = hz % 1000
        return String(format: "%d.%03d.%03d", m, k, h)
    }

    private func sMeterLabel(_ level: Int) -> String {
        if level <= 9 { return "S\(level)" }
        return "S9+\(level)dB"
    }
}

// MARK: - PTT Bar (bottom, above tab bar)

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
                            Capsule().fill(Color.radioRed).frame(width: max(6, CGFloat(txLevel * 3) * 200), height: 6)
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
