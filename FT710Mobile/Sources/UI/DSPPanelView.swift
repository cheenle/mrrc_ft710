import SwiftUI

/// WDSP control panel with notch visualization, NR2, AGC, noise processing.
struct DSPPanelView: View {
    @EnvironmentObject var viewModel: RadioViewModel
    @State private var notchFreq = "1000"
    @State private var notchBW = "100"
    @State private var showShareSheet = false
    @State private var recordedWAV: Data?

    var body: some View {
        ScrollView {
            VStack(spacing: 10) {
                // ── WDSP Master + Record ──────────────────────
                HStack {
                    Toggle("WDSP", isOn: Binding(
                        get: { viewModel.state.wdspEnabled },
                        set: { viewModel.setWDSPEnabled($0) }
                    )).tint(Color.orange).font(.subheadline.weight(.medium))

                    Spacer()

                    Button(action: {
                        let ap = viewModel.audioPlayback
                        if ap.isRecording {
                            recordedWAV = ap.stopRecording()
                            if recordedWAV != nil { showShareSheet = true }
                        } else { ap.startRecording() }
                    }) {
                        HStack(spacing: 4) {
                            Circle().fill(viewModel.audioPlayback.isRecording ? Color.red : Color.gray)
                                .frame(width: 8, height: 8)
                            Text(viewModel.audioPlayback.isRecording
                                 ? String(format: "%.1fs", viewModel.audioPlayback.recordingDuration)
                                 : "录音")
                                .font(.subheadline.monospaced())
                        }
                        .foregroundColor(viewModel.audioPlayback.isRecording ? Color.red : Color.gray)
                        .padding(.horizontal, 12).padding(.vertical, 8)
                        .background(viewModel.audioPlayback.isRecording ? Color.red.opacity(0.15) : Color.radioSurface)
                        .cornerRadius(8)
                    }
                    .sheet(isPresented: $showShareSheet) { if let w = recordedWAV { ShareSheet(items: [w]) } }
                }
                .padding(.horizontal, 16).padding(.top, 8)

                // ── Notch chart ───────────────────────────────
                NotchChartView(notches: viewModel.state.notches,
                               filterLow: viewModel.state.filterLow,
                               filterHigh: viewModel.state.filterHigh, maxFreq: 5000)
                    .frame(height: 50).padding(.horizontal, 16)

                // ── NR2 ───────────────────────────────────────
                dspCard(title: "NR2 降噪", icon: "waveform.and.magnifyingglass") {
                    Toggle("启用", isOn: Binding(get: { viewModel.state.nr2Enabled },
                                                 set: { viewModel.setNR2Enabled($0) }))
                        .tint(Color.orange).font(.subheadline)
                    if viewModel.state.nr2Enabled {
                        VStack(spacing: 2) {
                            Slider(value: Binding(get: { Double(viewModel.state.nr2Level) },
                                                   set: { viewModel.setNR2Level(Int($0)) }),
                                   in: 0...100, step: 25).tint(Color.orange)
                            HStack {
                                Text("关").font(.system(size: 9)).foregroundColor(.radioMuted)
                                Spacer()
                                Text("轻").font(.system(size: 9)).foregroundColor(.radioMuted)
                                Spacer()
                                Text("中").font(.system(size: 9)).foregroundColor(.radioMuted)
                                Spacer()
                                Text("强").font(.system(size: 9)).foregroundColor(.radioMuted)
                                Spacer()
                                Text("最大").font(.system(size: 9)).foregroundColor(.radioMuted)
                            }.padding(.horizontal, 2)
                            Text(nr2Tier).font(.caption.monospaced()).foregroundColor(.radioAccent)
                        }
                    }
                }

                // ── Noise processing ──────────────────────────
                dspCard(title: "噪声处理", icon: "ear.badge.waveform") {
                    ToggleRow("NB 噪声消除", isOn: Binding(get: { viewModel.state.nbEnabled },
                                                            set: { viewModel.setNBEnabled($0) }))
                    ToggleRow("ANF 自动陷波", isOn: Binding(get: { viewModel.state.anfEnabled },
                                                             set: { viewModel.setANFEnabled($0) }))
                    ToggleRow("NF 陷波滤波", isOn: Binding(get: { viewModel.state.nfEnabled },
                                                           set: { viewModel.setNFEnabled($0) }))
                }

                // ── AGC ───────────────────────────────────────
                dspCard(title: "AGC 自动增益", icon: "dial.low") {
                    HStack(spacing: 0) {
                        ForEach(["关", "慢", "中", "快"].indices, id: \.self) { i in
                            Button(action: { viewModel.setWDSPAGCMode(i) }) {
                                Text(["关", "慢", "中", "快"][i])
                                    .font(.subheadline.weight(.medium))
                                    .foregroundColor(viewModel.state.agcMode == i ? .black : Color.orange)
                                    .frame(maxWidth: .infinity).frame(height: 36)
                                    .background(viewModel.state.agcMode == i ? Color.orange : .clear)
                            }
                        }
                    }
                    .background(Color.white.opacity(0.04)).cornerRadius(8)
                }

                // ── Notch list ────────────────────────────────
                dspCard(title: "陷波器", icon: "scissors") {
                    HStack(spacing: 6) {
                        TextField("Hz", text: $notchFreq).keyboardType(.numberPad)
                            .font(.subheadline.monospaced()).foregroundColor(.radioAccent)
                        TextField("BW", text: $notchBW).keyboardType(.numberPad)
                            .font(.subheadline.monospaced()).foregroundColor(.radioAccent)
                        Button("添加") {
                            guard let f = Float(notchFreq), let b = Float(notchBW), f > 0 else { return }
                            viewModel.addNotch(freqHz: f, bandwidthHz: b)
                            notchFreq = ""; notchBW = ""
                        }
                        .font(.subheadline.weight(.medium)).padding(.horizontal, 10).padding(.vertical, 6)
                        .background(Color.radioAccent).foregroundColor(.black).cornerRadius(6)
                    }
                    ForEach(viewModel.state.notches) { n in
                        HStack {
                            Circle().fill(Color.radioAccent).frame(width: 6)
                            Text("\(Int(n.freqHz)) Hz").font(.subheadline.monospaced())
                            Text("±\(Int(n.bandwidthHz))").font(.caption).foregroundColor(.radioMuted)
                            Spacer()
                            Button(action: { viewModel.deleteNotch(index: n.index) }) {
                                Image(systemName: "xmark.circle.fill").font(.subheadline).foregroundColor(.radioRed)
                            }
                        }
                    }
                }

                Spacer(minLength: 100)  // room for PTT + tab bar
            }
        }
        .background(Color.radioBg)
    }

    // MARK: - Helpers

    private var nr2Tier: String {
        switch viewModel.state.nr2Level {
        case 0: return "关"
        case 1..<25: return "极轻"
        case 25..<50: return "轻"
        case 50..<75: return "中"
        case 75..<100: return "强"
        default: return "最大"
        }
    }

    private func dspCard<Content: View>(title: String, icon: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Label(title, systemImage: icon).font(.subheadline.weight(.semibold)).foregroundColor(.radioAccent)
            content()
        }
        .padding(10)
        .background(Color.radioSurface).cornerRadius(10)
        .padding(.horizontal, 16)
    }
}

// MARK: - Reused helpers

struct ToggleRow: View {
    let label: String; @Binding var isOn: Bool
    init(_ label: String, isOn: Binding<Bool>) { self.label = label; self._isOn = isOn }
    var body: some View {
        Toggle(label, isOn: $isOn).tint(Color.orange).font(.subheadline)
    }
}

struct NotchChartView: View {
    let notches: [WDSPNotch]; let filterLow: Int; let filterHigh: Int; let maxFreq: Int
    var body: some View {
        GeometryReader { geo in
            ZStack(alignment: .leading) {
                RoundedRectangle(cornerRadius: 4).fill(Color.white.opacity(0.05))
                let lf = CGFloat(filterLow)/CGFloat(maxFreq), hf = CGFloat(filterHigh)/CGFloat(maxFreq)
                RoundedRectangle(cornerRadius: 4).fill(Color.radioGreen.opacity(0.15))
                    .frame(width: (hf - lf) * geo.size.width, height: geo.size.height).offset(x: lf * geo.size.width)
                ForEach(notches) { n in
                    let x = CGFloat(n.freqHz) / CGFloat(maxFreq) * geo.size.width
                    Rectangle().fill(Color.radioRed.opacity(0.6))
                        .frame(width: max(CGFloat(n.bandwidthHz)/CGFloat(maxFreq)*geo.size.width, 3), height: geo.size.height)
                        .offset(x: x - CGFloat(n.bandwidthHz)/CGFloat(maxFreq)*geo.size.width/2)
                }
                Rectangle().fill(Color.white.opacity(0.1)).frame(width: 1, height: geo.size.height).offset(x: geo.size.width/2)
            }
        }
    }
}

struct ShareSheet: UIViewControllerRepresentable {
    let items: [Any]
    func makeUIViewController(context: Context) -> UIActivityViewController { UIActivityViewController(activityItems: items, applicationActivities: nil) }
    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {}
}
