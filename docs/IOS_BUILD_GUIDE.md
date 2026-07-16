# iOS 应用构建指南

## 📋 前提条件

### 开发环境
- **Xcode**: 15.0+ (推荐最新稳定版)
- **Swift**: 5.9+
- **iOS SDK**: 17.0+
- **macOS**: Ventura 13.0+

### 依赖库
- **libopus**: iOS 静态库 (用于音频编解码)
- **Xcode Project**: 已配置好的 FT710Mobile.xcodeproj

## 🚀 快速开始

### 1. 克隆项目
```bash
git clone <repository-url>
cd mrrc_ft710
```

### 2. 打开项目
```bash
open FT710Mobile/FT710Mobile.xcodeproj
```

### 3. 配置签名
1. 选择项目 → Signing & Capabilities
2. 选择你的 Apple ID 或开发团队
3. 设置 Bundle Identifier (如: com.yourname.ft710mobile)

### 4. 链接 libopus
```bash
# 下载 libopus iOS 静态库
# 添加到 Xcode 项目:
# 1. Build Phases → Link Binary With Libraries
# 2. 点击 + → Add Other
# 3. 选择 libopus.a 文件

# 设置 Header Search Paths:
# Build Settings → Header Search Paths
# 添加: $(SRCROOT)/Headers
```

### 5. 构建和运行
```bash
# 使用 Xcode
# 选择模拟器或真机 → Cmd+R

# 或使用命令行
cd FT710Mobile
xcodebuild -scheme FT710Mobile \
           -destination 'platform=iOS Simulator,name=iPhone 15' \
           build
```

## 🔧 详细配置

### Audio Permissions
在 `Info.plist` 中添加:
```xml
<key>NSMicrophoneUsageDescription</key>
<string>需要访问麦克风以进行无线电通话</string>

<key>NSCameraUsageDescription</key>
<string>需要访问相机以扫描二维码连接电台</string>
```

### Background Modes
在 `Signing & Capabilities` → `Background Modes`:
- [x] Audio, AirPlay, and Picture in Picture

### App Transport Security
在 `Info.plist` 中添加:
```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <true/>
</dict>
```

## 🧪 测试

### 运行单元测试
```bash
xcodebuild test \
  -project FT710Mobile.xcodeproj \
  -scheme FT710Mobile \
  -destination 'platform=iOS Simulator,name=iPhone 15' \
  -only-testing:FT710MobileTests
```

### 性能测试
1. 启用 Instruments → Time Profiler
2. 录制 30 秒使用过程
3. 分析 CPU 使用热点

### 内存测试
1. 启用 Xcode Memory Graph Debugger
2. 检查是否有内存泄漏
3. 验证音频缓冲区管理

## 📦 发布准备

### 1. 代码审查
- [ ] 所有测试通过
- [ ] 无编译器警告
- [ ] 代码符合 Swift 风格指南

### 2. 优化
- [ ] 启用 Bitcode
- [ ] 优化图片资源
- [ ] 减小二进制大小

### 3. 构建 Release
```bash
xcodebuild archive \
  -project FT710Mobile.xcodeproj \
  -scheme FT710Mobile \
  -configuration Release \
  -archivePath build/FT710Mobile.xcarchive
```

### 4. 导出 IPA
```bash
xcodebuild -exportArchive \
  -archivePath build/FT710Mobile.xcarchive \
  -exportPath build/Exported \
  -exportOptionsPlist ExportOptions.plist
```

## 🐛 故障排除

### 常见问题

**Q: libopus 链接失败**
A: 确保正确添加了 libopus.a 和头文件路径

**Q: 音频无输出**
A: 检查音频会话配置和权限设置

**Q: WebSocket 连接失败**
A: 验证服务器地址和密码配置

**Q: 频谱渲染卡顿**
A: 检查设备性能和内存使用

### 调试技巧

1. **启用详细日志**
   ```swift
   #if DEBUG
   print("Debug: \(message)")
   #endif
   ```

2. **使用 Simulate Location**
   - 测试不同网络条件下的表现

3. **Network Link Conditioner**
   - 模拟弱网环境

## 📞 技术支持

- **文档**: 查看 `docs/IOS_APP_*.md` 系列文档
- **测试**: 参考 `docs/IOS_TESTING_GUIDE.md`
- **修复**: 查看 `IOS_FIXES_SUMMARY.md`

---

**版本**: v1.1.0  
**最后更新**: 2026-07-14
