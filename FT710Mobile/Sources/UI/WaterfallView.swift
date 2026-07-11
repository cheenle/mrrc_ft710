import SwiftUI

/// FT710 waterfall — scope is centred on display centre frequency (no LO/IF offset).
/// Frequency scale based on scopeStartFreq and scopeSpanHz from state.
struct WaterfallView: View {
    @EnvironmentObject var viewModel: RadioViewModel

    var body: some View {
        GeometryReader { geo in
            let w = geo.size.width
            let h = geo.size.height
            let centerFreq = Double(viewModel.state.scopeStartFreq > 0
                ? viewModel.state.scopeStartFreq + viewModel.state.scopeSpanHz / 2
                : viewModel.state.activeFreq)
            let halfSpan = Double(viewModel.state.scopeSpanHz) / 2.0
            let leftEdge = centerFreq - halfSpan
            let span = halfSpan * 2
            let step = freqStep(span: span)

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
                    while f <= centerFreq + halfSpan + 1 {
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

                // VFO marker at centre
                Rectangle().fill(Color.red).frame(width: 1, height: h)
                    .position(x: w / 2, y: h / 2)

                // Centre frequency label
                Text(String(format: "%.3f", centerFreq / 1_000_000))
                    .font(.system(size: 9, design: .monospaced))
                    .foregroundColor(.red)
                    .background(Color.black.opacity(0.6))
                    .position(x: w / 2, y: 10)

                // Tick labels
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

    private struct FreqMark { let label: String; let hz: Int; let xPos: CGFloat }

    private func freqStep(span: Double) -> Double {
        if span <= 50_000 { return 5_000 }
        else if span <= 200_000 { return 25_000 }
        else { return 100_000 }
    }

    private func freqLabels(w: CGFloat, leftEdge: Double, span: Double, step: Double) -> [FreqMark] {
        var marks: [FreqMark] = []
        var f = (leftEdge / step).rounded(.down) * step
        while f <= leftEdge + span + 1 {
            let xPos = CGFloat((f - leftEdge) / span) * w
            if xPos >= -20, xPos <= w + 20 {
                marks.append(FreqMark(label: String(format: "%.3f", f / 1_000_000), hz: Int(f), xPos: xPos))
            }
            f += step
        }
        return marks
    }
}
