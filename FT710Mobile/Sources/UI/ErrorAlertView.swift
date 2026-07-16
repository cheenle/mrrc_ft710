import SwiftUI

/// Error alert view for displaying user-friendly error messages
struct ErrorAlertView: View {
    @Binding var showError: Bool
    let title: String
    let message: String
    let actionTitle: String
    
    var body: some View {
        if showError {
            Color.black.opacity(0.4)
                .ignoresSafeArea()
                .onTapGesture { showError = false }
            
            VStack(spacing: 16) {
                Image(systemName: "exclamationmark.triangle")
                    .font(.system(size: 40))
                    .foregroundColor(.radioRed)
                
                Text(title)
                    .font(.headline)
                    .foregroundColor(.white)
                
                Text(message)
                    .font(.body)
                    .foregroundColor(.gray)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)
                
                Button(action: { showError = false }) {
                    Text(actionTitle)
                        .font(.headline)
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.radioAccent)
                        .cornerRadius(10)
                }
                .padding(.horizontal, 40)
            }
            .padding(20)
            .background(Color.black.opacity(0.9))
            .cornerRadius(15)
            .shadow(radius: 10)
        }
    }
}
