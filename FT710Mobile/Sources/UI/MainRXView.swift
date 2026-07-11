import SwiftUI

/// Primary RX tab: S-meter + FFT + Waterfall + audio + controls + favorites.
/// PTT bar is at the bottom of ContentView — this view leaves room for it.
struct MainRXView: View {
    @EnvironmentObject var viewModel: RadioViewModel
    @State private var selectedStep: Int = 1000

    private var currentBandIndex: Int {
        RadioState.bands.firstIndex(where: { abs($0.freq - viewModel.state.frequency) < 50_000 }) ?? 4
    }

    var body: some View {
        VStack(spacing: 3) {
            // ── S-meter ──────────────────────────────────────
            SMeterBar(level: viewModel.state.signalLevel, ptt: viewModel.state.ptt)
                .frame(height: 10).padding(.horizontal, 12)

            // ── FFT spectrum ────────────────────────────────
            FFTView(fftData: viewModel.state.fftData, rxFrequency: viewModel.state.frequency,
                    iqSampleRateHz: viewModel.state.iqSampleRateHz,
                    onTapFrequency: { viewModel.setFrequency($0) })
                .frame(height: 80).padding(.horizontal, 6)
                .clipShape(RoundedRectangle(cornerRadius: 6))

            // ── Waterfall ────────────────────────────────────
            WaterfallView(waterfallImage: viewModel.state.waterfallImage,
                          rxFrequency: viewModel.state.frequency,
                          iqSampleRateHz: viewModel.state.iqSampleRateHz,
                          onTapFrequency: { viewModel.setFrequency($0) })
                .frame(height: 130).padding(.horizontal, 6)
                .clipShape(RoundedRectangle(cornerRadius: 6))

            // ── Audio level + mute ───────────────────
            HStack(spacing: 8) {
                Button(action: { viewModel.audioPlayback.isMuted.toggle() }) {
                    Image(systemName: viewModel.audioPlayback.isMuted ? "speaker.slash.fill" : "speaker.wave.2.fill")
                        .font(.caption).foregroundColor(viewModel.audioPlayback.isMuted ? .radioRed : .radioGreen)
                        .frame(width: 28, height: 28)
                }
                AudioLevelBar(level: viewModel.audioPlayback.rmsLevel)
            }.padding(.horizontal, 12)

            // AF + RF — compact dot-thumb sliders
            HStack(spacing: 6) {
                HStack(spacing: 3) {
                    Text("AF").font(.system(size: 9, weight: .medium)).foregroundColor(.radioGreen)
                    DotSlider(value: Binding(get: { Double(viewModel.state.afGain) },
                                              set: { viewModel.setAFGain(Float($0)) }),
                              tint: .green)
                }
                HStack(spacing: 3) {
                    Text("MIC").font(.system(size: 9, weight: .medium)).foregroundColor(.yellow)
                    DotSlider(value: Binding(get: { Double(viewModel.state.micGain / 2.0) },
                                              set: { viewModel.setMicGain(Float($0) * 2.0) }),
                              tint: .yellow)
                }
            }.padding(.horizontal, 12)

            // ── Mode + Filter + Band (unified chips) ──────
            HStack(spacing: 4) {
                // Mode chip
                HStack(spacing: 0) {
                    Button(action: { viewModel.setMode(prevMode(viewModel.state.mode)) }) {
                        Image(systemName: "chevron.left").font(.caption2.weight(.bold))
                    }.frame(width: 22, height: 28)
                    Text(viewModel.state.mode).font(.caption2.weight(.bold)).foregroundColor(.black)
                        .frame(minWidth: 34).frame(height: 28).background(Color.radioAccent)
                    Button(action: { viewModel.setMode(nextMode(viewModel.state.mode)) }) {
                        Image(systemName: "chevron.right").font(.caption2.weight(.bold))
                    }.frame(width: 22, height: 28)
                }.foregroundColor(.radioAccent).background(Color.radioSurface).cornerRadius(6)

                // Filter chip
                FilterChip(label: currentFilterLabel,
                           onSelect: { viewModel.setFilter(low: $0.low, high: $0.high) })

                // Band chip
                HStack(spacing: 0) {
                    Button(action: { changeBand(-1) }) {
                        Image(systemName: "chevron.left").font(.caption2.weight(.bold))
                    }.frame(width: 22, height: 28)
                    Text(RadioState.bands[currentBandIndex].name)
                        .font(.caption2.weight(.bold)).foregroundColor(.black)
                        .frame(minWidth: 36).frame(height: 28).background(Color.radioAccent)
                    Button(action: { changeBand(1) }) {
                        Image(systemName: "chevron.right").font(.caption2.weight(.bold))
                    }.frame(width: 22, height: 28)
                }.foregroundColor(.radioAccent).background(Color.radioSurface).cornerRadius(6)
            }.padding(.horizontal, 12)

            // ── Step + frequency up/down ────────────────
            HStack(spacing: 3) {
                Spacer()
                Button(action: { viewModel.stepFrequency(up: false, step: outerStep) }) {
                    Image(systemName: "chevron.backward.2").font(.caption.weight(.bold)).foregroundColor(.radioAccent)
                }.frame(width: 30, height: 28)
                Button(action: { viewModel.stepFrequency(up: false, step: selectedStep) }) {
                    Image(systemName: "chevron.left").font(.caption.weight(.bold)).foregroundColor(.radioAccent)
                }.frame(width: 30, height: 28)
                ForEach([1, 5, 10, 50, 100], id: \.self) { k in
                    let s = k * 1000
                    Button(action: { selectedStep = s }) {
                        Text("\(k)K").font(.system(size: 16, design: .monospaced))
                            .foregroundColor(selectedStep == s ? .black : .radioMuted)
                            .padding(.horizontal, 6).padding(.vertical, 3)
                            .background(selectedStep == s ? Color.radioAccent : Color.radioSurface).cornerRadius(5)
                    }
                }
                Button(action: { viewModel.stepFrequency(up: true, step: selectedStep) }) {
                    Image(systemName: "chevron.right").font(.caption.weight(.bold)).foregroundColor(.radioAccent)
                }.frame(width: 30, height: 28)
                Button(action: { viewModel.stepFrequency(up: true, step: outerStep) }) {
                    Image(systemName: "chevron.forward.2").font(.caption.weight(.bold)).foregroundColor(.radioAccent)
                }.frame(width: 30, height: 28)
                Spacer()
            }.padding(.horizontal, 12)

            // ── Favorites grid ──────────────────────────────
            let chs = Array(viewModel.favorites.channels.prefix(9))
            LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 3), count: 3), spacing: 3) {
                ForEach(0..<9, id: \.self) { i in
                    if i < chs.count {
                        let ch = chs[i]
                        Button(action: { viewModel.setFrequency(ch.frequency); viewModel.setMode(ch.mode) }) {
                            VStack(spacing: 0) {
                                Text(ch.name).font(.system(size: 12, weight: .bold)).foregroundColor(.radioAccent).lineLimit(1)
                                Text(ch.freqString).font(.system(size: 10, design: .monospaced)).foregroundColor(.radioMuted)
                            }.frame(maxWidth: .infinity).padding(.vertical, 6)
                                .background(Color.radioSurface).cornerRadius(5)
                        }
                    } else {
                        VStack(spacing: 0) {
                            Text("---").font(.system(size: 9)).foregroundColor(.radioMuted.opacity(0.3))
                        }.frame(maxWidth: .infinity).padding(.vertical, 6)
                            .background(Color.white.opacity(0.02)).cornerRadius(5)
                    }
                }
            }.padding(.horizontal, 12)

            Spacer(minLength: 0)
        }
        .background(Color.radioBg)
    }

    private let filterPresets: [(label: String, low: Int, high: Int)] = [
        ("CW", 400, 800), ("SSB", 300, 2700), ("Wide", 100, 4000), ("AM", 100, 6000), ("FM", 100, 8000),
    ]
    private var currentFilterLabel: String {
        filterPresets.first(where: { $0.low == viewModel.state.filterLow && $0.high == viewModel.state.filterHigh })?.label ?? "SSB"
    }

    private var outerStep: Int {
        let steps = [1000, 5000, 10000, 50000, 100000]
        if let i = steps.firstIndex(of: selectedStep), i < steps.count - 1 {
            return steps[i + 1]
        }
        return 500000
    }

    private func changeBand(_ offset: Int) {
        var idx = currentBandIndex + offset
        if idx < 0 { idx = RadioState.bands.count - 1 }
        if idx >= RadioState.bands.count { idx = 0 }
        viewModel.selectBand(RadioState.bands[idx].freq)
    }
}

// MARK: - S-Meter Bar
struct SMeterBar: View {
    let level: Int; let ptt: Bool
    var body: some View {
        GeometryReader { geo in
            ZStack(alignment: .leading) {
                RoundedRectangle(cornerRadius: 2).fill(Color.white.opacity(0.06))
                RoundedRectangle(cornerRadius: 2)
                    .fill(LinearGradient(colors: [Color.green, Color.orange, Color.red], startPoint: .leading, endPoint: .trailing))
                    .frame(width: geo.size.width * min(1, CGFloat(level) / 54))
                    .animation(.easeOut(duration: 0.3), value: level)
                HStack(spacing: 0) {
                    Text("S0").font(.system(size: 6, design: .monospaced)).foregroundColor(.radioMuted)
                    Spacer()
                    Text("S3").font(.system(size: 6, design: .monospaced)).foregroundColor(.radioMuted)
                    Spacer()
                    Text("S5").font(.system(size: 6, design: .monospaced)).foregroundColor(.radioMuted)
                    Spacer()
                    Text("S7").font(.system(size: 6, design: .monospaced)).foregroundColor(.radioMuted)
                    Spacer()
                    Text("S9").font(.system(size: 6, design: .monospaced)).foregroundColor(.radioMuted)
                    Spacer()
                    Text("+20").font(.system(size: 6, design: .monospaced)).foregroundColor(.radioMuted)
                    Spacer()
                    Text("+40").font(.system(size: 6, design: .monospaced)).foregroundColor(.radioMuted)
                    Spacer()
                    Text("+60").font(.system(size: 6, design: .monospaced)).foregroundColor(.radioMuted)
                }.padding(.horizontal, 1)
            }
        }
    }
}

// MARK: - Audio Level Bar
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

// MARK: - Mode Chip
struct ModeChip: View {
    let mode: String; let onPrev: () -> Void; let onNext: () -> Void
    var body: some View {
        HStack(spacing: 0) {
            Button(action: onPrev) { Image(systemName: "chevron.left").font(.caption2.weight(.bold)) }.frame(width: 22, height: 28)
            Text(mode).font(.caption2.weight(.bold)).foregroundColor(.black).frame(minWidth: 34).frame(height: 28).background(Color.radioAccent)
            Button(action: onNext) { Image(systemName: "chevron.right").font(.caption2.weight(.bold)) }.frame(width: 22, height: 28)
        }.foregroundColor(.radioAccent).background(Color.radioSurface).cornerRadius(6)
    }
}
private func prevMode(_ m: String) -> String {
    let modes = ["USB","LSB","AM","FM","CW","RTTY","DIGI"]; let i = modes.firstIndex(of: m) ?? 0
    return modes[(i - 1 + modes.count) % modes.count]
}
private func nextMode(_ m: String) -> String {
    let modes = ["USB","LSB","AM","FM","CW","RTTY","DIGI"]; let i = modes.firstIndex(of: m) ?? 0
    return modes[(i + 1) % modes.count]
}

// MARK: - Dot Slider (tiny thumb, minimal track)
struct DotSlider: UIViewRepresentable {
    let value: Binding<Double>
    let tint: Color
    func makeUIView(context: Context) -> UISlider {
        let s = UISlider()
        s.minimumTrackTintColor = UIColor(tint)
        s.maximumTrackTintColor = UIColor.white.withAlphaComponent(0.1)
        // tiny dot thumb: 8pt circle
        let dot = UIGraphicsImageRenderer(size: CGSize(width: 8, height: 8)).image { _ in
            UIColor(tint).setFill()
            UIBezierPath(ovalIn: CGRect(x: 0, y: 0, width: 8, height: 8)).fill()
        }
        s.setThumbImage(dot, for: .normal)
        s.setThumbImage(dot, for: .highlighted)
        s.addTarget(context.coordinator, action: #selector(Coordinator.changed), for: .valueChanged)
        return s
    }
    func updateUIView(_ s: UISlider, context: Context) {
        s.value = Float(value.wrappedValue)
        s.minimumTrackTintColor = UIColor(tint)
    }
    func makeCoordinator() -> Coordinator { Coordinator(value: value) }
    final class Coordinator: NSObject {
        let value: Binding<Double>
        init(value: Binding<Double>) { self.value = value }
        @objc func changed(_ sender: UISlider) { value.wrappedValue = Double(sender.value) }
    }
}

// MARK: - Filter Chip
struct FilterChip: View {
    let label: String; let onSelect: ((label: String, low: Int, high: Int)) -> Void
    private let presets: [(label: String, low: Int, high: Int)] = [
        ("CW",400,800),("SSB",300,2700),("Wide",100,4000),("AM",100,6000),("FM",100,8000)]
    var body: some View {
        Menu { ForEach(presets, id: \.label) { p in Button(p.label) { onSelect(p) } } } label: {
            HStack(spacing: 3) {
                Image(systemName: "lines.measurement.horizontal").font(.caption2)
                Text(label).font(.caption2.weight(.medium))
                Image(systemName: "chevron.down").font(.system(size: 5))
            }.foregroundColor(.radioText).frame(height: 28).padding(.horizontal, 6)
                .background(Color.radioSurface).cornerRadius(6)
        }
    }
}
