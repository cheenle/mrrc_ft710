import SwiftUI

/// Primary RX tab: waterfall + meters + gain sliders + step selector + memory channels.
/// PTT bar is in a separate overlay/tab — this view leaves room for it.
struct MainRXView: View {
    @EnvironmentObject var viewModel: RadioViewModel
    @State private var selectedStep: Int = 1000

    var body: some View {
        ScrollView {
            VStack(spacing: 3) {
                // ── Waterfall ─────────────────────────────
                WaterfallView()
                    .frame(height: 150).padding(.horizontal, 6)
                    .clipShape(RoundedRectangle(cornerRadius: 6))

                // ── S-meter ───────────────────────────────
                SMeterView()

                // ── Multi-meter (TX only) ─────────────────
                if viewModel.state.isTransmitting {
                    MeterBarView()
                }

                // ── Audio level + mute ───────────────────
                HStack(spacing: 8) {
                    Button(action: { viewModel.audioPlayback.isMuted.toggle() }) {
                        Image(systemName: viewModel.audioPlayback.isMuted ? "speaker.slash.fill" : "speaker.wave.2.fill")
                            .font(.caption).foregroundColor(viewModel.audioPlayback.isMuted ? .radioRed : .radioGreen)
                    }
                    AudioLevelBar(level: viewModel.audioPlayback.rmsLevel)
                }.padding(.horizontal, 12)

                // ── Gain sliders ──────────────────────────
                VStack(spacing: 4) {
                    GainSlider(label: "AF", value: Binding(
                        get: { Double(viewModel.state.afGain) },
                        set: { viewModel.setAFGain(Int($0)) }), range: 0...255, tint: .radioGreen)
                    GainSlider(label: "RF", value: Binding(
                        get: { Double(viewModel.state.rfGain) },
                        set: { viewModel.setRFGain(Int($0)) }), range: 0...255, tint: .yellow)
                    GainSlider(label: "SQL", value: Binding(
                        get: { Double(viewModel.state.squelch) },
                        set: { viewModel.setSquelch(Int($0)) }), range: 0...100, tint: .radioCyan)
                    GainSlider(label: "MIC", value: Binding(
                        get: { Double(viewModel.state.micGain) },
                        set: { viewModel.setMicGain(Int($0)) }), range: 0...100, tint: .radioAccent)
                }.padding(.horizontal, 12)

                // ── Step selector ─────────────────────────
                HStack(spacing: 3) {
                    ForEach([1, 5, 10, 50, 100], id: \.self) { k in
                        let s = k * 1000
                        Button(action: { selectedStep = s }) {
                            Text("\(k)K").font(.system(size: 12, design: .monospaced))
                                .foregroundColor(selectedStep == s ? .black : .radioMuted)
                                .padding(.horizontal, 6).padding(.vertical, 2)
                                .background(selectedStep == s ? Color.radioAccent : Color.radioSurface).cornerRadius(4)
                        }
                    }
                    Spacer()
                    Button("+") { viewModel.stepFrequency(up: true, step: selectedStep) }
                        .font(.caption.weight(.bold)).foregroundColor(.radioAccent).frame(width: 24, height: 24)
                    Button("-") { viewModel.stepFrequency(up: false, step: selectedStep) }
                        .font(.caption.weight(.bold)).foregroundColor(.radioAccent).frame(width: 24, height: 24)
                }.padding(.horizontal, 12)

                // ── Memory channels grid ──────────────────
                MemoryChannelsView()

                Spacer(minLength: 100)
            }
        }.background(Color.radioBg)
    }
}

// MARK: - Gain Slider

struct GainSlider: View {
    let label: String; @Binding var value: Double; let range: ClosedRange<Double>; let tint: Color
    var body: some View {
        HStack(spacing: 4) {
            Text(label).font(.system(size: 10, weight: .medium, design: .monospaced))
                .foregroundColor(tint).frame(width: 24, alignment: .leading)
            Slider(value: $value, in: range).tint(tint)
            Text("\(Int(value))").font(.system(size: 9, design: .monospaced)).foregroundColor(.radioMuted).frame(width: 30)
        }
    }
}

// MARK: - Audio Level Bar (reused)

struct AudioLevelBar: View {
    let level: Float
    var body: some View {
        Capsule().fill(Color.white.opacity(0.08)).frame(height: 6)
            .overlay(alignment: .leading) {
                Capsule().fill(level < 0.2 ? Color.green : level < 0.6 ? Color.orange : Color.red)
                    .frame(width: max(3, CGFloat(level * 3) * 300)).frame(height: 6)
            }
    }
}
