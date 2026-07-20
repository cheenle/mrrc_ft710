import SwiftUI

/// FT-710 DSP panel: NB, NR, AN, COMP toggles + AGC mode + Preamp/Attenuator + Tuner.
struct DSPPanelView: View {
    var body: some View {
        ScrollView {
            DSPPanelContent()
            Spacer(minLength: 100)
        }
        .background(Color.radioBg)
    }
}

/// DSP controls without an outer ScrollView, so it can embed in the single-page layout.
struct DSPPanelContent: View {
    @EnvironmentObject var viewModel: RadioViewModel

    var body: some View {
            VStack(spacing: 10) {
                // ── Noise Processing ─────────────────────
                dspCard(title: "噪声处理", icon: "ear.badge.waveform") {
                    ToggleRow("NB 噪声消除", isOn: Binding(
                        get: { viewModel.state.noiseBlanker },
                        set: { viewModel.setNoiseBlanker($0) }))
                    ToggleRow("NR 降噪", isOn: Binding(
                        get: { viewModel.state.noiseReduction },
                        set: { viewModel.setNoiseReduction($0) }))
                    Stepper(value: Binding(
                        get: { viewModel.state.nrLevel },
                        set: { viewModel.setNoiseReductionLevel($0) }
                    ), in: 1...15) {
                        Text("NR 等级: \(viewModel.state.nrLevel)")
                            .font(.subheadline)
                            .foregroundColor(.radioMuted)
                    }
                    ToggleRow("AN 自动陷波", isOn: Binding(
                        get: { viewModel.state.autoNotch },
                        set: { viewModel.setAutoNotch($0) }))
                    ToggleRow("COMP 压缩", isOn: Binding(
                        get: { viewModel.state.compressor },
                        set: { viewModel.setCompressor($0) }))
                }

                // ── AGC ─────────────────────────────────
                dspCard(title: "AGC 自动增益", icon: "dial.low") {
                    HStack(spacing: 0) {
                        ForEach(["关", "快", "中", "慢"].indices, id: \.self) { i in
                            Button(action: { viewModel.setAGC(i) }) {
                                Text(["关", "快", "中", "慢"][i])
                                    .font(.subheadline.weight(.medium))
                                    .foregroundColor(viewModel.state.agc == i ? .black : .radioAccent)
                                    .frame(maxWidth: .infinity)
                                    .frame(height: 36)
                                    .background(viewModel.state.agc == i ? Color.radioAccent : .clear)
                            }
                        }
                    }
                    .background(Color.white.opacity(0.04))
                    .cornerRadius(8)
                }

                // ── Preamp / Attenuator ────────────────
                dspCard(title: "前置放大 / 衰减", icon: "antenna.radiowaves.left.and.right") {
                    HStack {
                        Text("PRE")
                            .font(.caption)
                            .foregroundColor(.radioMuted)
                        Picker("", selection: Binding(
                            get: { viewModel.state.preamp },
                            set: { viewModel.setPreamp($0) }
                        )) {
                            Text("OFF").tag(0)
                            Text("AMP1").tag(1)
                            Text("AMP2").tag(2)
                        }
                        .pickerStyle(.segmented)
                        .tint(.radioAccent)
                    }
                    HStack {
                        Text("ATT")
                            .font(.caption)
                            .foregroundColor(.radioMuted)
                        Picker("", selection: Binding(
                            get: { viewModel.state.attenuator },
                            set: { viewModel.setAttenuator($0) }
                        )) {
                            Text("OFF").tag(0)
                            Text("6dB").tag(1)
                            Text("12dB").tag(2)
                            Text("18dB").tag(3)
                        }
                        .pickerStyle(.segmented)
                        .tint(.radioAccent)
                    }
                }

                // ── Tuner ──────────────────────────────
                dspCard(title: "天调", icon: "arrow.triangle.swap") {
                    HStack(spacing: 0) {
                        ForEach(["关", "开", "调谐"].indices, id: \.self) { i in
                            let vals = [0, 1, 2]
                            Button(action: { viewModel.setTuner(vals[i]) }) {
                                Text(["关", "开", "调谐"][i])
                                    .font(.subheadline.weight(.medium))
                                    .foregroundColor(viewModel.state.tunerStatus == vals[i] ? .black : .radioAccent)
                                    .frame(maxWidth: .infinity)
                                    .frame(height: 36)
                                    .background(viewModel.state.tunerStatus == vals[i] ? Color.radioAccent : .clear)
                            }
                        }
                    }
                    .background(Color.white.opacity(0.04))
                    .cornerRadius(8)
                }
            }
    }

    private func dspCard<Content: View>(title: String, icon: String,
                                        @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Label(title, systemImage: icon)
                .font(.subheadline.weight(.semibold))
                .foregroundColor(.radioAccent)
            content()
        }
        .padding(10)
        .background(Color.radioSurface)
        .cornerRadius(10)
        .padding(.horizontal, 16)
    }
}

struct ToggleRow: View {
    let label: String
    @Binding var isOn: Bool

    init(_ label: String, isOn: Binding<Bool>) {
        self.label = label
        self._isOn = isOn
    }

    var body: some View {
        Toggle(label, isOn: $isOn)
            .tint(Color.orange)
            .font(.subheadline)
    }
}
