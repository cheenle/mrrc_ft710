# iOS 应用测试套件

## 测试覆盖范围

### 1. 核心功能测试
- **RadioViewModelTests**: 测试电台状态管理、频率控制、模式切换、PTT 控制等
- **OpusCodecTests**: 测试 Opus 编解码器功能和 C 桥接稳定性

### 2. 音频系统测试
- **AudioPlaybackManager**: 测试音频播放、音量控制、静音功能
- **AudioCaptureManager**: 测试麦克风捕获、增益控制、Opus 编码

### 3. 网络通信测试
- **ConnectionManager**: 测试 WebSocket 连接、认证、断线重连
- **ProtocolHandler**: 测试 JSON 协议解析、二进制数据处理

### 4. 频谱处理测试
- **SpectrumProcessor**: 测试瀑布图渲染、性能监控、内存管理

### 5. UI 组件测试
- **ContentView**: 测试主界面布局、错误弹窗显示
- **PTTButtonView**: 测试 PTT 按钮交互
- **ErrorAlertView**: 测试错误提示显示

## 运行测试

### Xcode 测试
```bash
cd FT710Mobile
xcodebuild test -scheme FT710Mobile -destination 'platform=iOS Simulator,name=iPhone 15'
```

### 命令行测试
```bash
xcodebuild test \
  -project FT710Mobile.xcodeproj \
  -scheme FT710Mobile \
  -destination 'platform=iOS Simulator,name=iPhone 15' \
  -only-testing:FT710MobileTests
```

## 测试覆盖率目标

- **核心逻辑**: 90%+ 覆盖率
- **音频处理**: 85%+ 覆盖率  
- **网络通信**: 80%+ 覆盖率
- **UI 组件**: 70%+ 覆盖率

## 持续集成

建议在 CI/CD 管道中添加：
1. 每次提交自动运行单元测试
2. 音频功能集成测试（需要真实设备）
3. 性能基准测试（频谱渲染 FPS）
4. 内存泄漏检测

## 已知限制

- 部分音频测试需要真实 iOS 设备（蓝牙、麦克风权限）
- 网络测试需要有效的服务器连接
- Opus 编解码测试依赖 libopus 库的正确链接
