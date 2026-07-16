# FT710Mobile iOS App — 快速修复指南

**目标**: 快速解决 iOS App 的关键问题  
**预计时间**: 1-2 周  
**优先级**: P0 (Opus) > P1 (PTT, 错误处理)

---

## 🔴 P0 问题 (立即修复)

### 1. Opus 编解码器实现

**当前状态**:
```swift
// OpusDecoder.swift
func decode(_ opusData: Data) -> Data? {
    return nil  // placeholder
}

// OpusEncoder.swift  
func encode(_ pcmSamples: [Int16]) -> Data? {
    return nil  // placeholder
}
```

**解决方案 A: 使用 WebRTC Opus (推荐)**
```swift
import WebRTC

class OpusDecoder {
    private var decoder: RTCEngine?
    
    init(sampleRate: Double = 48000) {
        // 初始化 WebRTC Opus decoder
    }
    
    func decode(_ opusData: Data) -> Data? {
        // 使用 WebRTC 解码
        return nil  // 需要实现
    }
}
```

**解决方案 B: 集成 libopus**
```swift
// 需要 C bridge 或 Swift wrapper
// 参考: https://github.com/nicklama/SwiftOpus
```

**解决方案 C: 暂时降级到 PCM**
```swift
// 在 AudioPlaybackManager 中
func enqueue(int16Data: Data) {
    guard int16Data.count >= 3 else { return }
    let codec = int16Data[0]
    
    if codec == 0x01 {
        // Opus 帧 - 暂时跳过，等待实现
        print("⚠️ Opus not implemented, skipping frame")
        return
    }
    
    // PCM 路径
    let pcmBytes = int16Data.dropFirst()
    processPCM(pcmBytes)
}
```

---

### 2. 统一 PTT 按钮实现

**当前问题**:
- `ContentView.swift` 中有 `PTTBar`
- `PTTButtonView.swift` 是另一个实现

**解决方案**:
```swift
// 在 ContentView.swift 中删除 PTTBar，使用 PTTButtonView
// 或者在 PTTButtonView 中复用 PTTBar 的逻辑

// 推荐：统一使用 PTTBar，删除 PTTButtonView
// PTTBar 已经在底部固定显示，功能完整
```

---

## 🟡 P1 问题 (本周修复)

### 3. 完善错误处理

**添加错误模型**:
```swift
struct AppError: Identifiable {
    let id = UUID()
    let title: String
    let message: String
    let retryAction: (() -> Void)?
    let isError: Bool  // true = 严重错误，false = 警告
}

@MainActor
final class RadioViewModel: ObservableObject {
    @Published var appError: AppError?
    
    func showError(_ error: AppError) {
        self.appError = error
    }
    
    func hideError() {
        self.appError = nil
    }
}
```

**在关键位置添加错误处理**:
```swift
// WebSocketConnection.swift
func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask,
                didCompleteWithError error: Error?) {
    if let err = error {
        // 区分网络错误和认证错误
        if isAuthError(err) {
            onError?(AuthError(err))
        } else {
            onError?(NetworkError(err))
        }
        scheduleReconnect()
    }
}

// AudioPlaybackManager.swift
func start() {
    // ... 现有代码
    
    do {
        try engine.start()
        playerNode.play()
    } catch {
        audioError = "Engine start: \(error.localizedDescription)"
        // 通知用户
        NotificationCenter.default.post(
            name: .audioError,
            object: nil,
            userInfo: ["error": error]
        )
    }
}
```

### 4. 优化音频会话管理

**统一使用 .playAndRecord**:
```swift
// AudioPlaybackManager.swift
private func configureSession() {
    let session = AVAudioSession.sharedInstance()
    do {
        try session.setCategory(.playAndRecord, mode: .default,
                                options: [.mixWithOthers, .allowBluetoothA2DP, .allowBluetooth])
        try session.setPreferredIOBufferDuration(0.005)
        try session.setActive(true)
    } catch {
        print("⚠️ AudioSession: \(error)")
    }
}
```

---

## 🟢 P2 问题 (本月优化)

### 5. 添加单元测试

**测试 RadioState**:
```swift
import XCTest
@testable import FT710Mobile

final class RadioStateTests: XCTestCase {
    func testModeNameMapping() {
        let state = RadioState()
        state.mode = 2  // USB
        XCTAssertEqual(state.modeName, "USB")
    }
    
    func testBandDetection() {
        let state = RadioState()
        state.vfoAFreq = 14_200_000
        XCTAssertEqual(state.bandName, "20m")
    }
}
```

**测试 SpectrumProcessor**:
```swift
final class SpectrumProcessorTests: XCTestCase {
    func testFeedValidData() {
        let processor = SpectrumProcessor()
        let data = createValidSpectrumData()
        var receivedImage: UIImage?
        
        processor.feed(data: data) { img in
            receivedImage = img
        }
        
        // 等待异步处理
        XCTAssertTrue(receivedImage != nil)
    }
}
```

### 6. 改进内存管理

**优化 bindSockets()**:
```swift
private func bindSockets() {
    // 先移除旧的订阅
    cancellables.removeAll()
    
    // 创建新的订阅
    let newCancellables = Set<AnyCancellable>()
    
    // ... 添加所有订阅到新集合
    
    // 最后替换
    cancellables = newCancellables
}
```

---

## 📋 修复检查清单

### Opus 编解码器
- [ ] 选择实现方案 (WebRTC / libopus / PCM 降级)
- [ ] 实现 OpusDecoder
- [ ] 实现 OpusEncoder
- [ ] 测试 RX 音频播放
- [ ] 测试 TX 音频发送
- [ ] 更新错误处理

### PTT 按钮
- [ ] 确定统一方案
- [ ] 删除冗余实现
- [ ] 测试 PTT 功能
- [ ] 更新 UI

### 错误处理
- [ ] 定义错误模型
- [ ] 添加错误通知
- [ ] 更新 UI 显示错误
- [ ] 测试各种错误场景

### 音频会话
- [ ] 统一使用 .playAndRecord
- [ ] 测试 RX/TX 切换
- [ ] 验证蓝牙支持

### 单元测试
- [ ] RadioState 测试
- [ ] SpectrumProcessor 测试
- [ ] AudioPlaybackManager 测试
- [ ] 集成测试

---

## 🧪 测试计划

### 功能测试
1. **连接测试**: 连接到服务器，验证 4 个 WebSocket 连接
2. **RX 音频测试**: 播放接收到的音频 (PCM 和 Opus)
3. **TX 音频测试**: 发送麦克风音频
4. **频谱测试**: 验证瀑布图更新
5. **PTT 测试**: 验证 PTT 功能
6. **控制测试**: 频率/模式/滤波器控制

### 性能测试
1. **内存测试**: 长时间运行监控内存使用
2. **CPU 测试**: 频谱处理 CPU 占用
3. **音频延迟测试**: RX/TX 音频延迟

### 兼容性测试
1. **iOS 版本**: iOS 17, 18
2. **设备**: iPhone, iPad
3. **网络**: WiFi, 4G/5G
4. **蓝牙**: AirPods, 蓝牙耳机

---

## 📞 支持资源

### Opus 编解码
- [WebRTC Opus](https://webrtc.org/native-code/audio-processing/)
- [SwiftOpus](https://github.com/nicklama/SwiftOpus)
- [libopus 官方](https://opus-codec.org/)

### iOS 音频
- [Apple Audio Programming](https://developer.apple.com/documentation/avfoundation/audio_processing)
- [AVAudioEngine](https://developer.apple.com/documentation/avfaudio/avaudioengine)
- [Audio Session](https://developer.apple.com/documentation/avfaudio/avaudiosession)

### SwiftUI
- [SwiftUI Performance](https://developer.apple.com/documentation/swiftui/performance-tips)
- [Combine Framework](https://developer.apple.com/documentation/combine)

---

**更新日期**: 2026-07-14  
**负责人**: iOS 开发团队  
**状态**: 待开始
