# FT710Mobile

**Yaesu FT-710 短波电台的 iOS 遥控客户端(SwiftUI,iOS 17,iPhone)。**

通过 4 路加密 WebSocket 连接到本仓库根的 Python FastAPI 服务端(`server.py`),在 iPhone 上实现频率/模式/DSP 控制、实时频谱瀑布、下行语音接收与 PTT 语音发射。

> 本 README 于 2026-07-20 重写(旧版描述的是另一个项目,已作废)。工程现状的权威审计见 [`docs/IOS_APP_ANALYSIS.md`](../docs/IOS_APP_ANALYSIS.md)。

---

## 特性

- **电台控制**: 频率(直输/步进/波段跳转)、VFO A/B、模式、滤波器宽度、Preamp/ATT、AGC、NB/NR/ANotch、射频功率、麦克风增益、静噪
- **频谱瀑布**: 850 bin 实时瀑布(服务端 ~5fps 广播)+ FFT 曲线,配色与 web 端一致
- **音频**: RX 下行 Opus 解码播放(48kHz,10× 增益补偿);TX 麦克风采集 48kHz/20ms PCM 帧上行,按住 PTT 即发
- **仪表**: S 表、功率、SWR、ALC、COMP 等发射仪表
- **其他**: 存储频道、设置页(重连/增益/音量)、深色琥珀主题、横竖屏自适应

## 系统要求

| 项 | 要求 |
|---|---|
| 设备 | **iPhone 真机**(模拟器无法构建:内置 `libopus.a` 只有 arm64 真机 slice) |
| 系统 | iOS 17.0+ |
| 开发 | Xcode 15+(iOS 17 SDK)、[XcodeGen](https://github.com/yonaskolb/XcodeGen)(`brew install xcodegen`)、Apple 开发者账号(真机签名) |
| 服务端 | 本仓库根的 FastAPI 服务端(`server.py`)已连接 FT-710 并启用 TLS,默认端口 8888。App 硬编码 `https/wss`,**需要 iOS 信任的 TLS 证书**,连不了 `--no-ssl` 服务端 |

服务端启动(仓库根,详见根 `AGENTS.md`):

```bash
pip install -r requirements.txt
FT710_SERIAL_PORT=/dev/cu.usbserial-XXXX FT710_WEB_PASSWORD='<强密码>' python server.py
```

## 构建与运行

```bash
cd FT710Mobile

# 1. 生成 Xcode 工程(已验证:xcodegen 2.45.4)
xcodegen generate

# 2. 打开工程
open FT710Mobile.xcodeproj

# 3. Xcode 中选择你的 iPhone 真机 → Run(首次需在 设置→通用→VPN与设备管理 信任开发者证书)
```

命令行无签名编译检查(不产物入库):

```bash
cd FT710Mobile
xcodebuild -project FT710Mobile.xcodeproj -scheme FT710Mobile \
  -destination 'generic/platform=iOS' CODE_SIGNING_ALLOWED=NO \
  -derivedDataPath /tmp/ft710-dd build
```

工程配置只改 `project.yml`(部署目标、bundle id、签名团队),不要在 Xcode 里手改工程文件后忘记回写。`DEVELOPMENT_TEAM` 当前硬编码为 `VQ89MM7935`,换账号请改 `project.yml`。

## 配置(App 内)

- **服务器地址**: 登录页输入 `host:port`(默认 `radio.vlsc.net:8888`),`@AppStorage("serverHost")` 持久化,下次自动填入。
- **密码**: 即服务端 `FT710_WEB_PASSWORD`。登录(`POST /api/auth/login`)成功后密码存入 **Keychain**(`kSecAttrServer=host`,account=`ft710_mobile`),下次启动自动登录。
- **注意**: 当前版本密码错误也会直接写 Keychain 并进主界面(已知问题,见下),输错密码只能删除 App 重装——输入时请仔细。

## 当前状态与已知问题

Happy path(登录 → 控制 → 音频 → 频谱)两端协议逐字段核对**匹配可用**。但 2026-07-20 深度审计([`docs/IOS_APP_ANALYSIS.md`](../docs/IOS_APP_ANALYSIS.md))发现一批待修问题,按级别摘要:

- **P0(安全)**: PTT 释放竞态——WAN 下快速点按可能丢失 `ptt:false`,电台卡死在发射态;无 PTT 看门狗/后台保护;认证失败死循环(服务端重启后 App 只能杀掉重来);密码输错即锁死;瀑布流误触即改频(QSY)。
  → 修复设计与实施计划已批准(`docs/superpowers/specs/2026-07-20-ios-ptt-safety-design.md`、`docs/superpowers/plans/2026-07-20-ios-ptt-safety.md`),**尚未实施**。
- **P1(功能)**: 存储频道协议与服务端脱节(频道列表常态为空、保存不持久);主界面 TUNE 按钮实为天调开关;蓝牙/44.1kHz 路由下 TX 语音变调;RX 无 jitter buffer(网络抖动后音频滞后累积);录音功能失效。
- **P2(工程)**: UI 目录 25 个文件中 14 个是死代码;无 test target、测试有效覆盖率为 0;功率/SWR 仪表换算与服务端标定表不一致;`Info.plist` 设备能力声明陈旧(`armv7`)。

完整清单、file:line 证据与修复优先级请读分析报告。**在真机上发射前,请知悉 P0 项的存在。**

## 文档

| 文档 | 内容 |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | 面向 AI 编码代理的工程指引(架构/协议/约束) |
| [`docs/IOS_APP_ANALYSIS.md`](../docs/IOS_APP_ANALYSIS.md) | 2026-07-20 深度审计(权威现状) |
| [`docs/superpowers/specs/2026-07-20-ios-ptt-safety-design.md`](../docs/superpowers/specs/2026-07-20-ios-ptt-safety-design.md) | PTT 安全修复设计(已批准,待实施) |
| [`docs/superpowers/plans/2026-07-20-ios-ptt-safety.md`](../docs/superpowers/plans/2026-07-20-ios-ptt-safety.md) | PTT 安全修复实施计划(待实施) |
| `docs/ARCHITECTURE.md`(本目录) | ⚠️ 已腐化(描述另一个项目),待重写,勿参考 |
