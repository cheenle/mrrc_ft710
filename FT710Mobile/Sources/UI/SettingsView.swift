import SwiftUI

/// Settings tab: favorites, server config, connection status, about.
struct SettingsView: View {
    @EnvironmentObject var viewModel: RadioViewModel
    @AppStorage("serverHost") private var serverHost: String = "radio.vlsc.net:8080"
    @State private var showAddFavorite = false
    @State private var favName: String = ""

    var body: some View {
        List {
                // ── Quick save current ──────────────────────────
                Section {
                    Button(action: {
                        favName = String(format: "%.3f MHz",
                                         Double(viewModel.state.frequency) / 1_000_000.0)
                        showAddFavorite = true
                    }) {
                        HStack {
                            Image(systemName: "star.fill")
                                .foregroundColor(.radioAccent)
                            Text("收藏当前频率")
                            Spacer()
                            Text("\(viewModel.state.frequency / 1000) kHz")
                                .font(.subheadline.monospaced())
                                .foregroundColor(.radioAccent)
                            Text(viewModel.state.mode)
                                .font(.subheadline)
                                .foregroundColor(.radioMuted)
                        }
                    }
                    .alert("收藏名称", isPresented: $showAddFavorite) {
                        TextField("名称", text: $favName)
                        Button("取消", role: .cancel) {}
                        Button("保存") {
                            viewModel.favorites.add(
                                name: favName.isEmpty ? nil : favName,
                                frequency: viewModel.state.frequency,
                                mode: viewModel.state.mode
                            )
                        }
                    }
                }

                // ── Favorite channels ───────────────────────────
                if viewModel.favorites.channels.isEmpty {
                    Section("收藏频道") {
                        HStack {
                            Image(systemName: "tray")
                                .foregroundColor(.radioMuted)
                            Text("暂无收藏 — 点击上方添加当前频率")
                                .font(.subheadline)
                                .foregroundColor(.radioMuted)
                        }
                    }
                } else {
                    Section("收藏频道 (\(viewModel.favorites.channels.count))") {
                        ForEach(viewModel.favorites.channels) { ch in
                            Button(action: {
                                viewModel.setFrequency(ch.frequency)
                                viewModel.setMode(ch.mode)
                            }) {
                                HStack {
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text(ch.name)
                                            .font(.subheadline)
                                            .foregroundColor(.white)
                                        Text(ch.freqString)
                                            .font(.caption.monospaced())
                                            .foregroundColor(.radioAccent)
                                    }
                                    Spacer()
                                    Text(ch.mode)
                                        .font(.caption)
                                        .foregroundColor(.radioMuted)
                                        .padding(.horizontal, 6)
                                        .padding(.vertical, 2)
                                        .background(Color.gray.opacity(0.15))
                                        .cornerRadius(3)
                                }
                            }
                            .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                                Button(role: .destructive) {
                                    viewModel.favorites.remove(ch)
                                } label: {
                                    Image(systemName: "trash")
                                }
                            }
                        }
                        .onDelete { indexSet in
                            for i in indexSet {
                                viewModel.favorites.remove(viewModel.favorites.channels[i])
                            }
                        }
                    }
                }

                // ── Server connection ────────────────────────────
                Section("服务器") {
                    HStack {
                        Image(systemName: "network")
                            .foregroundColor(.radioMuted)
                        TextField("主机:端口", text: $serverHost)
                            .font(.subheadline.monospaced())
                            .autocapitalization(.none)
                            .disableAutocorrection(true)
                    }
                    Button("重新连接") {
                        viewModel.powerOff()
                        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                            viewModel.powerOn()
                        }
                    }
                    .foregroundColor(.radioAccent)
                    .font(.subheadline)
                }

                // ── Connection status ────────────────────────────
                Section("连接状态") {
                    StatusLine(icon: "antenna.radiowaves.left.and.right",
                               label: "控制", dot: viewModel.state.ctrlConnected)
                    StatusLine(icon: "speaker.wave.2",
                               label: "RX 音频", dot: viewModel.state.audioRXConnected)
                    StatusLine(icon: "mic",
                               label: "TX 音频", dot: viewModel.state.audioTXConnected)
                    StatusLine(icon: "water.waves",
                               label: "频谱", dot: viewModel.state.spectrumConnected)
                }

                // ── Audio ─────────────────────────────────────────
                Section("音频") {
                    HStack {
                        Image(systemName: "volume.2")
                            .foregroundColor(.radioMuted)
                        Text("AF 增益")
                            .font(.subheadline)
                        Slider(value: Binding(
                            get: { Double(viewModel.state.afGain) },
                            set: { viewModel.setAFGain(Float($0)) }
                        ), in: 0...1)
                        .tint(.green)
                    }
                    HStack {
                        Image(systemName: "waveform")
                            .foregroundColor(.radioMuted)
                        Text("IQ 采样率")
                            .font(.subheadline)
                        Spacer()
                        Picker("IQ Rate", selection: Binding(
                            get: {
                                RadioState.sampleRateOptions.first(where: {
                                    $0.hz == viewModel.state.iqSampleRateHz
                                })?.label ?? "78k"
                            },
                            set: { key in
                                viewModel.setIQSampleRate(key)
                            }
                        )) {
                            ForEach(RadioState.sampleRateOptions, id: \.label) { opt in
                                Text(opt.label).tag(opt.label)
                            }
                        }
                        .pickerStyle(.menu)
                        .tint(Color.orange)
                    }
                }

                // ── Danger zone ───────────────────────────────────
                Section {
                    Button(role: .destructive) {
                        viewModel.favorites.removeAll()
                    } label: {
                        HStack {
                            Image(systemName: "trash")
                            Text("清除所有收藏")
                                .font(.subheadline)
                        }
                    }
                }

                // ── About ─────────────────────────────────────────
                Section("关于") {
                    HStack {
                        Text("版本")
                            .font(.subheadline)
                        Spacer()
                        Text("1.0.0")
                            .font(.subheadline.monospaced())
                            .foregroundColor(.radioMuted)
                    }
                    HStack {
                        Text("后端")
                            .font(.subheadline)
                        Spacer()
                        Text("sunmrrc / SunSDR2 DX")
                            .font(.subheadline)
                            .foregroundColor(.radioMuted)
                    }
                    HStack {
                        Text("延迟")
                            .font(.subheadline)
                        Spacer()
                        Text(viewModel.state.latency)
                            .font(.subheadline.monospaced())
                            .foregroundColor(.radioMuted)
                    }
                }
            }
            .listStyle(.insetGrouped)
            .scrollContentBackground(.hidden)
            .background(Color.radioBg)
    }
}

struct StatusLine: View {
    let icon: String
    let label: String
    let dot: Bool

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: icon)
                .frame(width: 20)
                .foregroundColor(.radioMuted)
            Text(label)
                .font(.subheadline)
            Spacer()
            Circle()
                .fill(dot ? Color.green : Color.red)
                .frame(width: 8, height: 8)
        }
    }
}
