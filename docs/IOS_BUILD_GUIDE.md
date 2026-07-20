# FT710Mobile iOS App — 构建指南

**适用**: `FT710Mobile/`(SwiftUI,iOS 17),真机部署
**更新日期**: 2026-07-20(全文重写;旧版含 Bitcode、相机权限、SunsdrMobile 工程名、模拟器构建等错误内容,已删除,勘误见 §8)

---

## 1. 环境要求

| 项 | 要求 | 说明 |
|---|---|---|
| Xcode | 15.0+ | 工程声明 Swift 5.9、iOS 17.0 deployment target |
| xcodegen | 2.45.4 | 已装于 `/opt/homebrew/bin/xcodegen`;未装则 `brew install xcodegen`。工程文件由它从 `project.yml` 生成 |
| Apple 开发者账号 | 必需 | 真机调试签名用;免费 Apple ID(Personal Team)也可以 |
| 真机 | iPhone,iOS 17+ | **模拟器不可行**,见 §4 |

## 2. 构建步骤

`FT710Mobile.xcodeproj` 是 xcodegen 的生成物,不要手改 pbxproj(重跑 xcodegen 会被覆盖)。

```bash
cd FT710Mobile
xcodegen                       # 从 project.yml 生成 FT710Mobile.xcodeproj
open FT710Mobile.xcodeproj     # 打开工程
```

然后:

1. 先配签名(见 §3);
2. 顶部设备选择器选**已连接的真机**(不要选模拟器,见 §4);
3. Cmd+R 运行。

凡是改了 `project.yml`(签名、target、构建设置),必须重跑 `xcodegen` 再构建。

## 3. 签名配置

`DEVELOPMENT_TEAM: "VQ89MM7935"` 在 `project.yml` 里硬编码了两处(`settings.base` 和 target `FT710Mobile` 的 `settings.base`)。换成你自己的 Team ID:

- 付费开发者账号:developer.apple.com → Membership Details → Team ID(10 位字符);
- 免费 Apple ID:Xcode → Settings → Accounts 登录后,同样会有一个 Personal Team ID。

签名方式已是 `CODE_SIGN_STYLE: Automatic`,Xcode 会自动处理证书与描述文件。Bundle ID 为 `com.hamradio.ft710mobile`,与他人冲突时在 `project.yml` 改 `PRODUCT_BUNDLE_IDENTIFIER`。

也可以临时在 Xcode 的 Signing & Capabilities 里改 Team——但下次 `xcodegen` 后会被覆盖,长期做法仍是改 `project.yml`。

## 4. 模拟器不可行(重要)

`Sources/Audio/opus-ios/lib/libopus.a` 只含 **arm64 真机 slice**,而 target 配置了 `OTHER_LDFLAGS: -lopus`。选模拟器构建必然链接失败(报 `building for 'iOS-simulator', but linking in object file ... built for 'iOS'` 一类错误)。

要支持模拟器,需把 libopus 重打包成包含 arm64-simulator slice 的 XCFramework——目前未做,已列入修复路线图 P2 构建配置项。在那之前:**只能真机构建与调试**。这也解释了为什么旧文档"选模拟器 Cmd+R"的步骤从未成功过。

## 5. 命令行构建

不签名编译验证(不需要连接真机,按真机架构编译):

```bash
cd FT710Mobile
xcodebuild build -project FT710Mobile.xcodeproj \
  -scheme FT710Mobile \
  -destination 'generic/platform=iOS' \
  CODE_SIGNING_ALLOWED=NO
```

连好真机并配好签名后,去掉 `CODE_SIGNING_ALLOWED=NO` 即为可部署构建;归档用 `xcodebuild archive -project FT710Mobile.xcodeproj -scheme FT710Mobile -destination 'generic/platform=iOS'`。

## 6. 服务端准备

iOS 端硬编码 `wss://` / `https://`(分析 §6),所以服务端**必须启用 SSL**;`--no-ssl` 起的服务端 iOS 连不上(只够 web 端用)。

```bash
# 仓库根目录
FT710_SERIAL_PORT=/dev/cu.usbserial-XXXX python server.py
```

- 默认端口 8888(`FT710_WEB_PORT` 或 `--port` 可改);
- SSL 证书默认取 `certs/fullchain.pem` + `certs/radio.vlsc.net.key`(`--ssl-cert/--ssl-key` 或环境变量 `FT710_SSL_CERT`/`FT710_SSL_KEY` 可改)。**证书文件存在才启用 SSL**,不存在会静默回退 plain HTTP——启动日志里确认 SSL 生效,否则 iOS 必然连不上;
- 防火墙放行 8888/tcp;真机与服务器之间网络可达;
- App 默认主机 `radio.vlsc.net:8888`,登录页可改成你的 `主机:端口`;密码即服务端 `FT710_WEB_PASSWORD` / `--password`;
- TLS 校验照常执行:自签名证书不受设备信任时照样握手失败,`NSAllowsArbitraryLoads` 对此没有豁免作用(见 §8)。

## 7. 常见构建错误

| 错误 | 原因 | 处理 |
|---|---|---|
| `Undefined symbol: _opus_encoder_create` 等 / `library not found for -lopus` | libopus.a 缺失或搜索路径失效 | 确认 `Sources/Audio/opus-ios/lib/libopus.a` 在库内;`LIBRARY_SEARCH_PATHS` / `HEADER_SEARCH_PATHS` / `-lopus` 由 project.yml 配置,重跑 `xcodegen` |
| `building for 'iOS-simulator', but linking in object file ... built for 'iOS'` | 选了模拟器目标(§4) | 换真机。这是当前预期行为,不是配置损坏 |
| `No signing certificate` / provisioning profile 报错 | DEVELOPMENT_TEAM 还是别人的 ID | 按 §3 改成自己的 Team ID;确认 Xcode 已登录 Apple 账号 |
| 命令行报 `Signing for "FT710Mobile" requires a development team` | 未配签名 | 纯编译验证请加 `CODE_SIGNING_ALLOWED=NO`(§5) |
| 警告:duplicate output file / Info.plist 副本被打进 bundle | `project.yml` 把整个 `Resources/` 目录列为 resources,Info.plist 随之进 bundle | 警告级,不影响运行;彻底修复(从 resources 排除 Info.plist)已列入路线图 P2 构建配置项 |
| 手改 pbxproj 后设置丢失 | 工程文件是生成物 | 所有工程设置只改 `project.yml`,再 `xcodegen` |
| 构建行为异常、与 project.yml 不符 | 派生数据/工程缓存陈旧 | 重跑 `xcodegen`;必要时清 DerivedData |

## 8. 勘误(相对 2026-07-14 旧版)

- **Bitcode**:Xcode 14 起已废弃,Apple 不再接受含 bitcode 的提交,"启用 Bitcode"无从谈起;
- **相机权限**:App 没有相机/扫码功能,旧文档的 `NSCameraUsageDescription` 是臆造。实际只有 `NSMicrophoneUsageDescription`(已在 Info.plist);
- **SunsdrMobile**:仓库里的 `FT710Mobile/SunsdrMobile.xcodeproj/` 是陈旧产物,不是本工程,勿打开;待 P2 清理;
- **模拟器构建**:旧文档给的就是模拟器 destination,因 §4 所述原因从未可行;
- **ATS 误解**:`NSAllowsArbitraryLoads=true` 不绕过 TLS 服务端证书校验,自签名证书照样失败;且代码硬编码 https/wss,该键对本 App 无实际作用(审核减分项,去留归 P2 构建配置项)。

## 相关文档

- [IOS_APP_FIX_GUIDE.md](IOS_APP_FIX_GUIDE.md) — 修复路线图
- [IOS_TESTING_GUIDE.md](IOS_TESTING_GUIDE.md) — 测试指南
- [IOS_APP_ANALYSIS.md](IOS_APP_ANALYSIS.md) §7 — 构建配置问题清单
