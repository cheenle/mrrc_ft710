import SwiftUI

/// FFT spectrum line plot drawn above the waterfall.
/// Shows the current frequency-domain magnitude as a filled line chart.
struct FFTLineView: View {
    @EnvironmentObject var viewModel: RadioViewModel

    var body: some View {
        GeometryReader { geo in
            let w = geo.size.width
            let h = geo.size.height
            let data = viewModel.state.fftData

            ZStack(alignment: .topLeading) {
                // Dark background
                Color(hex: "#020617")

                // FFT line plot
                if !data.isEmpty {
                    Canvas { ctx, size in
                        guard data.count > 1 else { return }

                        let stepX = size.width / CGFloat(data.count - 1)
                        let maxVal = data.max() ?? 1
                        let scaleY = maxVal > 0 ? size.height / CGFloat(maxVal) : size.height

                        // Filled area under curve (semi-transparent)
                        var fillPath = Path()
                        fillPath.move(to: CGPoint(x: 0, y: size.height))
                        for i in 0..<data.count {
                            let x = CGFloat(i) * stepX
                            let y = size.height - CGFloat(data[i]) * scaleY
                            fillPath.addLine(to: CGPoint(x: x, y: y))
                        }
                        fillPath.addLine(to: CGPoint(x: size.width, y: size.height))
                        fillPath.closeSubpath()

                        ctx.fill(fillPath, with: .color(Color.radioAccent.opacity(0.15)))

                        // Line on top
                        var linePath = Path()
                        linePath.move(to: CGPoint(x: 0, y: size.height - CGFloat(data[0]) * scaleY))
                        for i in 1..<data.count {
                            let x = CGFloat(i) * stepX
                            let y = size.height - CGFloat(data[i]) * scaleY
                            linePath.addLine(to: CGPoint(x: x, y: y))
                        }
                        ctx.stroke(linePath, with: .color(Color.radioAccent), style: .init(lineWidth: 1.0))
                    }

                    // VFO red hairline
                    Rectangle().fill(Color.red.opacity(0.45))
                        .frame(width: 1, height: h)
                        .position(x: w / 2, y: h / 2)
                }
            }
        }
    }
}
