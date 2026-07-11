import SwiftUI

/// Settings tab: server config, connection status, RF power, scope span, about.
struct SettingsView: View {
    @EnvironmentObject var viewModel: RadioViewModel
    @AppStorage("serverHost") private var serverHost: String = "radio.vlsc.net:8888"

    var body: some View {
        List {
            Section("\u{670D}\u{52A1}\u{5668}") {  // 服务器
                HStack {
                    Image(systemName: "network").foregroundColor(.radioMuted)
                    TextField("\u{4E3B}\u{673A}:\u{7AEF}\u{53E3}", text: $serverHost)
                        .font(.subheadline.monospaced()).autocapitalization(.none).disableAutocorrection(true)
                }
                Button("\u{91CD}\u{65B0}\u{8FDE}\u{63A5}") {
                    viewModel.powerOff()
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) { viewModel.powerOnAsync() }
                }.foregroundColor(.radioAccent)
            }

            Section("\u{8FDE}\u{63A5}\u{72B6}\u{6001}") {  // 连接状态
                StatusLine(icon: "antenna.radiowaves.left.and.right", label: "\u{63A7}\u{5236}", dot: viewModel.state.ctrlConnected)           // 控制
                StatusLine(icon: "water.waves", label: "\u{9891}\u{8C31}", dot: viewModel.state.spectrumConnected)                             // 频谱
                StatusLine(icon: "speaker.wave.2", label: "RX \u{97F3}\u{9891}", dot: viewModel.state.audioRXConnected)                        // RX 音频
                StatusLine(icon: "mic", label: "TX \u{97F3}\u{9891}", dot: viewModel.state.audioTXConnected)                                   // TX 音频
                StatusLine(icon: "cpu", label: "\u{4E32}\u{53E3}", dot: viewModel.state.serialConnected)                                       // 串口
            }

            Section("\u{53D1}\u{5C04}") {  // 发射
                HStack {
                    Text("RF Power").font(.subheadline)
                    Spacer()
                    Text("\(viewModel.state.rfPower)W").font(.subheadline.monospaced()).foregroundColor(.radioAccent)
                }
                Slider(value: Binding(
                    get: { Double(viewModel.state.rfPower) },
                    set: { viewModel.setRFPower(Int($0)) }
                ), in: 5...100, step: 5).tint(.radioRed)
            }

            Section("\u{9891}\u{8C31}") {  // 频谱
                Picker("\u{5E26}\u{5BBD}", selection: Binding(  // 带宽
                    get: { viewModel.state.scopeSpan },
                    set: { viewModel.setScopeSpan($0) }
                )) {
                    ForEach(Array(RadioState.scopeSpanLabels.keys.sorted()), id: \.self) { k in
                        Text(RadioState.scopeSpanLabels[k] ?? "?").tag(k)
                    }
                }.tint(.radioAccent)
            }

            Section("\u{5173}\u{4E8E}") {  // 关于
                HStack { Text("\u{7248}\u{672C}").font(.subheadline); Spacer(); Text("1.0.0").font(.subheadline.monospaced()).foregroundColor(.radioMuted) }     // 版本
                HStack { Text("\u{540E}\u{7AEF}").font(.subheadline); Spacer(); Text("FT-710 / mrrc_ft710").font(.subheadline).foregroundColor(.radioMuted) }     // 后端
                HStack { Text("\u{7535}\u{53F0}").font(.subheadline); Spacer(); Text("Yaesu FT-710").font(.subheadline).foregroundColor(.radioMuted) }            // 电台
            }

            Section { Button(role: .destructive) { viewModel.powerOff() }
                label: { Text("\u{65AD}\u{5F00}\u{8FDE}\u{63A5}").font(.subheadline) } }  // 断开连接
        }
        .listStyle(.insetGrouped).scrollContentBackground(.hidden).background(Color.radioBg)
    }
}

struct StatusLine: View {
    let icon: String; let label: String; let dot: Bool
    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: icon).frame(width: 20).foregroundColor(.radioMuted)
            Text(label).font(.subheadline)
            Spacer()
            Circle().fill(dot ? Color.green : Color.red).frame(width: 8, height: 8)
        }
    }
}
