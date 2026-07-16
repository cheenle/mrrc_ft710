import SwiftUI

/// Performance monitor view showing app health metrics
struct PerformanceMonitorView: View {
    @ObservedObject var viewModel: RadioViewModel
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("性能监控")
                .font(.headline)
                .foregroundColor(.white)
            
            HStack {
                VStack(alignment: .leading) {
                    Text("连接状态")
                        .font(.caption)
                        .foregroundColor(.gray)
                    Text(connectionStatus)
                        .font(.system(.body, design: .monospaced))
                        .foregroundColor(statusColor)
                }
                
                Spacer()
                
                VStack(alignment: .leading) {
                    Text("音频质量")
                        .font(.caption)
                        .foregroundColor(.gray)
                    Text(audioQuality)
                        .font(.system(.body, design: .monospaced))
                        .foregroundColor(audioColor)
                }
            }
            .padding()
            .background(Color.black.opacity(0.3))
            .cornerRadius(8)
        }
        .padding()
    }
    
    private var connectionStatus: String {
        if viewModel.state.ctrlConnected && viewModel.state.audioRXConnected && viewModel.state.audioTXConnected {
            return "优秀"
        } else if viewModel.state.ctrlConnected {
            return "一般"
        } else {
            return "断开"
        }
    }
    
    private var statusColor: Color {
        if viewModel.state.ctrlConnected && viewModel.state.audioRXConnected && viewModel.state.audioTXConnected {
            return .green
        } else if viewModel.state.ctrlConnected {
            return .yellow
        } else {
            return .red
        }
    }
    
    private var audioQuality: String {
        let rxRMS = viewModel.audioPlayback.rmsLevel
        if rxRMS > 0.1 {
            return "良好"
        } else if rxRMS > 0.01 {
            return "较弱"
        } else {
            return "无信号"
        }
    }
    
    private var audioColor: Color {
        let rxRMS = viewModel.audioPlayback.rmsLevel
        if rxRMS > 0.1 {
            return .green
        } else if rxRMS > 0.01 {
            return .yellow
        } else {
            return .red
        }
    }
}
