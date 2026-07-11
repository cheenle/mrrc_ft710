import SwiftUI

/// FT710 waterfall — scope is centred on display centre frequency (no LO/IF offset).
/// Frequency scale based on scopeStartFreq and scopeSpanHz from state.
struct WaterfallView: View {
    @EnvironmentObject var viewModel: RadioViewModel

    var body: some View {
        GeometryReader { geo in
            let w = geo.size.width
            let h = geo.size.height
            let span = Double(viewModel.state.scopeSpanHz)
            let vfoFreq = Double(viewModel.state.activeFreq)
            // Validate scopeStartFreq against the VFO — the two values
            // arrive from different data sources (scope frame vs CAT poll)
            // and scope_start_freq can be stale for several frames after
            // a frequency change.  If the hardware value disagrees with
            // the VFO by >15 % of the span, fall back to CENTER-mode math.
            let leftEdge = validatedLeftEdge(
                raw: Double(viewModel.state.scopeStartFreq),
                vfoFreq: vfoFreq, span: span
            )
            let step = freqStep(span: span)

            // VFO position within the spectrum.
            let vfoX = CGFloat((vfoFreq - leftEdge) / span) * w

            ZStack(alignment: .topLeading) {
                // Waterfall image
                if let img = viewModel.state.waterfallImage {
                    Image(uiImage: img).resizable().frame(width: w, height: h)
                } else {
                    Color.black
                }

                // Frequency grid lines
                Canvas { ctx, size in
                    let gridColor = GraphicsContext.Shading.color(Color.white.opacity(0.04))
                    var f = (leftEdge / step).rounded(.down) * step
                    while f <= leftEdge + span + 1 {
                        let x = CGFloat((f - leftEdge) / span) * size.width
                        if x >= 0, x <= size.width {
                            var p = Path()
                            p.move(to: CGPoint(x: x, y: 0))
                            p.addLine(to: CGPoint(x: x, y: size.height))
                            ctx.stroke(p, with: gridColor, style: .init(lineWidth: 0.5))
                        }
                        f += step
                    }
                }

                // VFO red hairline — semi-transparent so the waterfall
                // data remains visible behind it.
                Rectangle().fill(Color.red.opacity(0.45)).frame(width: 1, height: h)
                    .position(x: vfoX, y: h / 2)

                // VFO frequency label above the red line.
                Text(formatVfoFreq(vfoFreq))
                    .font(.system(size: 8, weight: .bold, design: .monospaced))
                    .foregroundColor(.red)
                    .background(Color.black.opacity(0.7))
                    .position(x: vfoX, y: 9)

                // Tick labels at the bottom
                ForEach(freqLabels(w: w, leftEdge: leftEdge, span: span, step: step), id: \.hz) { m in
                    Text(m.label)
                        .font(.system(size: 10, design: .monospaced))
                        .foregroundColor(.white.opacity(0.7))
                        .background(Color.black.opacity(0.5))
                        .position(x: m.xPos, y: h - 8)
                }
            }
            .background(Color(hex: "#020617"))
            .gesture(DragGesture(minimumDistance: 0).onEnded { v in
                let fract = Double(v.location.x / w)
                let clickedFreq = Int((leftEdge + fract * span).rounded())
                viewModel.setFrequency(clickedFreq)
            })
        }
    }

    /// Validate scopeStartFreq against the VFO frequency.
    ///
    /// The FT-710 hardware stores the scope CENTER frequency (not the
    /// left edge) at offset 144 of the scope frame.  We convert it to
    /// a left-edge frequency for rendering.
    ///
    /// scopeStartFreq (from scope frame, ~30 fps) and vfoFreq (from CAT
    /// polling, ~10 fps) are two independent data sources.  After a
    /// frequency change the CAT path updates immediately while scope
    /// frames carry the old centre for several more frames.
    ///
    /// If the hardware centre places the VFO outside the displayed span
    /// (±15 % slack) we discard it and fall back to CENTER-mode math
    /// (the server always sends EX040200 at startup).
    private func validatedLeftEdge(raw: Double, vfoFreq: Double, span: Double) -> Double {
        let rawCenter = raw  // scope_start_freq from hardware is actually the centre
        guard rawCenter > 0 else {
            return vfoFreq - span / 2.0
        }
        let halfSpan = span / 2.0
        let slack = span * 0.15
        if vfoFreq >= rawCenter - halfSpan - slack &&
           vfoFreq <= rawCenter + halfSpan + slack {
            return rawCenter - halfSpan
        }
        // Stale — scope hasn't caught up with the new VFO yet.
        return vfoFreq - halfSpan
    }

    private struct FreqMark { let label: String; let hz: Int; let xPos: CGFloat }

    /// Grid step size based on spectrum span width.
    private func freqStep(span: Double) -> Double {
        if span <= 2_000      { return 200 }
        else if span <= 5_000 { return 500 }
        else if span <= 10_000 { return 1_000 }
        else if span <= 25_000 { return 2_500 }
        else if span <= 50_000 { return 5_000 }
        else if span <= 100_000 { return 10_000 }
        else if span <= 200_000 { return 25_000 }
        else if span <= 500_000 { return 50_000 }
        else                   { return 100_000 }
    }

    /// Label formatter that adapts to the step size.
    /// Narrow spans (<10 kHz step) show kHz; wider spans show MHz
    /// with enough decimal places to resolve individual grid steps.
    private func formatFreq(_ f: Double, step: Double) -> String {
        if step < 1_000 {
            // 200/500 Hz steps — show kHz with one decimal
            return String(format: "%.1fk", f / 1_000)
        } else if step <= 5_000 {
            // 1–5 kHz steps — show kHz as integer
            return String(format: "%.0fk", f / 1_000)
        } else if step <= 25_000 {
            // 10–25 kHz steps — show MHz with two decimals
            return String(format: "%.2f", f / 1_000_000)
        } else {
            // 50–100 kHz steps — show MHz with three decimals
            return String(format: "%.3f", f / 1_000_000)
        }
    }

    /// VFO frequency label: always MHz with kHz precision.
    private func formatVfoFreq(_ f: Double) -> String {
        let mhz = f / 1_000_000
        if f < 1_000_000 {
            return String(format: "%.0fkHz", f / 1_000)
        } else {
            return String(format: "%.3f", mhz)
        }
    }

    private func freqLabels(w: CGFloat, leftEdge: Double, span: Double, step: Double) -> [FreqMark] {
        var marks: [FreqMark] = []
        var f = (leftEdge / step).rounded(.down) * step
        while f <= leftEdge + span + 1 {
            let xPos = CGFloat((f - leftEdge) / span) * w
            if xPos >= -20, xPos <= w + 20 {
                marks.append(FreqMark(
                    label: formatFreq(f, step: step),
                    hz: Int(f),
                    xPos: xPos
                ))
            }
            f += step
        }
        return marks
    }
}
