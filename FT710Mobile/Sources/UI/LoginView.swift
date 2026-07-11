import SwiftUI

struct LoginView: View {
    let onLogin: (String, String) -> Void  // host, password

    @AppStorage("serverHost") private var host: String = "radio.vlsc.net:8889"
    @State private var password: String = ""
    @State private var showPassword = false
    @State private var isConnecting = false
    @FocusState private var focusedField: Field?

    enum Field { case host, pass }

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            VStack(spacing: 20) {
                Spacer()

                // Logo
                Image(systemName: "antenna.radiowaves.left.and.right")
                    .font(.system(size: 56))
                    .foregroundColor(.orange)

                Text("Ham Radio")
                    .font(.largeTitle.weight(.bold))
                    .foregroundColor(.white)

                Text("SunSDR2 DX Mobile Control")
                    .font(.subheadline)
                    .foregroundColor(.gray)

                Spacer().frame(height: 20)

                // Server field
                VStack(alignment: .leading, spacing: 4) {
                    Text("服务器地址")
                        .font(.subheadline)
                        .foregroundColor(.gray)
                    HStack {
                        Image(systemName: "network")
                            .foregroundColor(.gray)
                        TextField("radio.vlsc.net:8889", text: $host)
                            .keyboardType(.URL)
                            .autocapitalization(.none)
                            .disableAutocorrection(true)
                            .font(.callout.monospaced())
                            .foregroundColor(.white)
                            .focused($focusedField, equals: .host)
                            .submitLabel(.next)
                            .onSubmit { focusedField = .pass }
                    }
                    .padding(12)
                    .background(Color.white.opacity(0.08))
                    .cornerRadius(10)
                }

                // Password field
                VStack(alignment: .leading, spacing: 4) {
                    Text("密码")
                        .font(.subheadline)
                        .foregroundColor(.gray)
                    HStack {
                        Image(systemName: "lock")
                            .foregroundColor(.gray)
                        if showPassword {
                            TextField("密码", text: $password)
                                .autocapitalization(.none)
                                .font(.callout)
                                .foregroundColor(.white)
                        } else {
                            SecureField("密码", text: $password)
                                .font(.callout)
                                .foregroundColor(.white)
                        }
                        Button(action: { showPassword.toggle() }) {
                            Image(systemName: showPassword ? "eye.slash" : "eye")
                                .foregroundColor(.gray)
                                .font(.subheadline)
                        }
                    }
                    .padding(12)
                    .background(Color.white.opacity(0.08))
                    .cornerRadius(10)
                    .focused($focusedField, equals: .pass)
                    .submitLabel(.go)
                    .onSubmit { doLogin() }
                }

                Spacer().frame(height: 8)

                // Login button
                Button(action: doLogin) {
                    HStack {
                        if isConnecting {
                            ProgressView()
                                .tint(.black)
                        }
                        Text("连接电台")
                            .font(.headline)
                    }
                    .foregroundColor(.black)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .background(isFormValid ? Color.orange : Color.gray)
                    .cornerRadius(12)
                }
                .disabled(!isFormValid || isConnecting)

                Spacer()
            }
            .padding(.horizontal, 32)
        }
    }

    private var isFormValid: Bool {
        !host.trimmingCharacters(in: .whitespaces).isEmpty &&
        !password.isEmpty
    }

    private func doLogin() {
        guard isFormValid else { return }
        isConnecting = true
        focusedField = nil
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
            onLogin(host.trimmingCharacters(in: .whitespaces), password)
        }
    }
}
