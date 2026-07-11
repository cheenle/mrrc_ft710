import SwiftUI

/// Hardware IF offset: RX DDS (LO) = VFO + 30500 Hz.
/// The server broadcasts LO-centred spectra (no np.roll rotation since a748bc2):
/// bin 256 = LO, VFO is IF_OFFSET below LO.
private let IF_OFFSET_HZ: Double = 30500.0

/// Displays a pre-rendered waterfall UIImage. All spectrum processing happens
/// off-main-thread in SpectrumProcessor; this view only shows the result.
struct WaterfallView: View {
    let waterfallImage: UIImage?
    let rxFrequency: Int
    var iqSampleRateHz: Int = 78125
    var onTapFrequency: ((Int) -> Void)? = nil

    private var iqSampleRate: Double { Double(iqSampleRateHz) }

    /// VFO pixel position as fraction of width.
    /// VFO is IF_OFFSET Hz below LO (bin 256), at bin (256 - shift).
    private var vfoFraction: CGFloat {
        let shift = (IF_OFFSET_HZ * 512.0 / Double(iqSampleRateHz)).rounded()
        let vfoBin = 256.0 - shift
        return CGFloat(vfoBin / 512.0)
    }

    var body: some View {
        GeometryReader { geo in
            let w = geo.size.width; let h = geo.size.height
            let loHz = Double(rxFrequency) + IF_OFFSET_HZ
            let halfSpan = iqSampleRate / 2.0
            let span = halfSpan * 2
            let (step, _) = freqStep(span: span)
            let marks = freqLabels(forWidth: w, loHz: loHz, halfSpan: halfSpan, step: step)

            // Diagnostic: log frequency mapping on first render
            let _ = {
                let leftEdge = loHz - halfSpan
                let vfoPos = (Double(rxFrequency) - leftEdge) / span
                print("📐 WF: VFO=\(rxFrequency) LO=\(Int(loHz)) SR=\(iqSampleRateHz)")
                print("📐 WF: span=[\(Int(leftEdge))..\(Int(leftEdge+span))] step=\(Int(step))")
                print("📐 WF: vfoFrac=\(vfoFraction) vfoPos=\(String(format:"%.4f",vfoPos)) image512px")
                for m in marks.prefix(4) {
                    print("📐 WF:   label '\(m.label)' x=\(String(format:"%.3f",m.xPos/w))")
                }
            }()

            ZStack(alignment: .topLeading) {
                // ── Waterfall image ──────────────────────────
                if let img = waterfallImage {
                    Image(uiImage: img).resizable().frame(width: w, height: h)
                } else {
                    Color.black
                }

                // ── Frequency grid lines (round kHz boundaries) ──
                Canvas { ctx, size in
                    let leftEdge = loHz - halfSpan
                    let gridColor = GraphicsContext.Shading.color(Color.white.opacity(0.04))
                    var f = (leftEdge / step).rounded(.down) * step
                    while f <= loHz + halfSpan + 1 {
                        let x = CGFloat((f - leftEdge) / span) * size.width
                        if x >= 0 && x <= size.width {
                            var p = Path()
                            p.move(to: CGPoint(x: x, y: 0))
                            p.addLine(to: CGPoint(x: x, y: size.height))
                            ctx.stroke(p, with: gridColor, style: .init(lineWidth: 0.5))
                        }
                        f += step
                    }
                }

                // ── VFO marker — red line at off-centre position ─
                Rectangle()
                    .fill(Color.red)
                    .frame(width: 1, height: h)
                    .position(x: vfoFraction * w, y: h / 2)

                // ── VFO frequency label (top) ────────────────
                Text(String(format: "%.3f", Double(rxFrequency) / 1_000_000))
                    .font(.system(size: 9, design: .monospaced))
                    .foregroundColor(.red)
                    .background(Color.black.opacity(0.6))
                    .position(x: vfoFraction * w, y: 10)

                // ── Frequency tick labels (bottom) ────────────
                ForEach(marks, id: \.hz) { mark in
                    Text(mark.label)
                        .font(.system(size: 10, design: .monospaced))
                        .foregroundColor(.white.opacity(0.7))
                        .background(Color.black.opacity(0.5))
                        .position(x: mark.xPos, y: h - 8)
                }
            }
            .background(Color(hex: "#020617"))
            .gesture(DragGesture(minimumDistance: 0).onEnded { v in
                // LO-centred: center pixel = LO = VFO + IF_OFFSET
                let fract = Double(v.location.x / w)
                let fOff = (fract - 0.5) * iqSampleRate
                let clickedFreq = Double(rxFrequency) + IF_OFFSET_HZ + fOff
                onTapFrequency?(Int(clickedFreq.rounded()))
            })
        }
    }

    // MARK: - Frequency helpers

    private struct FreqMark { let label: String; let hz: Int; let xPos: CGFloat }

    /// Choose step size and label-every-N based on total frequency span.
    private func freqStep(span: Double) -> (step: Double, labelEvery: Int) {
        if      span <=  50_000 { return ( 5_000, 1) }
        else if span <= 100_000 { return (10_000, 1) }
        else if span <= 200_000 { return (25_000, 2) }
        else                    { return (50_000, 2) }
    }

    /// Build frequency tick marks at round kHz boundaries, aligned with grid lines.
    /// Labels show absolute frequency in MHz (e.g. "14.100", "14.150").
    private func freqLabels(forWidth w: CGFloat, loHz: Double,
                            halfSpan: Double, step: Double) -> [FreqMark] {
        let span = halfSpan * 2
        let leftEdge = loHz - halfSpan
        var marks: [FreqMark] = []

        var f = (leftEdge / step).rounded(.down) * step
        while f <= loHz + halfSpan + 1 {
            let xPos = CGFloat((f - leftEdge) / span) * w
            let label = String(format: "%.3f", f / 1_000_000)

            if xPos >= -20 && xPos <= w + 20 {
                marks.append(FreqMark(label: label, hz: Int(f), xPos: xPos))
            }
            f += step
        }
        return marks
    }
}
