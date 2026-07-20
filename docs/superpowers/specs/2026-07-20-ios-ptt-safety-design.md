# iOS 发射安全修复 — 设计文档(spec ① / 共 2 个)

**日期**: 2026-07-20
**状态**: 已获用户批准(方案 A:纯 SwiftUI + PTTManager 状态机)
**前置**: `docs/IOS_APP_ANALYSIS.md` §2.1 / §2.2 / §2.6(P0 安全项)
**SDD 追溯**: SC8(PTT cannot stick)· NFR-008(PTT <100ms)· NFR-012(release safety)· UC-005(PTT and Tune Control)· AD-007(PTT Release as Safety-Critical Flow)· SDD/15(PTT Safety Architecture,7 层模型)· R4(TX release command lost)
**范围声明**: 本 spec 只覆盖发射安全 3 项(PTT 释放竞态、看门狗/scenePhase、瀑布流误触 QSY)+ 1 项顺手修复(首屏假开机)。连接生命周期与音频引擎崩溃(5 项)属 spec ②,不在本文档。**不改变任何服务端代码,不新增/修改任何 AD**;多客户端 PTT 仲裁是已知开放问题 I6(last-writer-wins),明确不试图解决。

---

## 1. 问题定义

### 1.1 PTT 释放竞态(分析 §2.1)
`FT710Mobile/Sources/UI/ContentView.swift:227-235` 的 PTT 手势在 `onEnded` 里只有 `txStatus > 0` 才发 `ptt:false`,而 `txStatus` 完全依赖服务端 stateUpdate 回显。WAN 延迟下快速点按:松开瞬间回显未到 → `ptt:false` 被静默丢弃,**电台持续发射**。web 端 `static/ft710_ui.js:889-897` 是无条件发送 + 本地乐观置零。

### 1.2 无看门狗 / 无后台保护(分析 §2.2)
iOS 缺失 SDD ch15 七层模型中的 Layer 3(看门狗)、Layer 6(pagehide 等价物)、Layer 7(TX 音频收尾 `'s:'`)。DragGesture 被系统手势/来电中断时 `onEnded` 可能不触发;App 切后台无任何处理。服务端兜底(Layer 4,`server.py:1664-1673` / `1814-1825`)仅在 socket 断开时生效且多客户端在线时失效;`config.py:289 PTT_SAFETY_TIMEOUT` 从未实现。

### 1.3 瀑布流误触 QSY(分析 §2.6)
`FT710Mobile/Sources/UI/WaterfallView.swift:70-74`: `DragGesture(minimumDistance: 0).onEnded` 直接 `setFrequency`,任何滑动/误触都改频率。web 端瀑布流无点击调谐。

### 1.4 顺手修复:首屏假开机
`FT710Mobile/Sources/Model/RadioState.swift:40` `powerOn` 默认 `true` 但不连接,电源图标亮绿误导;与 PTT 指示共用电源按钮交互面,一并修。

---

## 2. 设计

### 2.1 PTTManager 状态机(核心)

新文件 `FT710Mobile/Sources/PTT/PTTManager.swift`,`@MainActor final class: ObservableObject`。

```swift
enum Phase { case idle, keying, keyed, releasing }
@Published private(set) var phase: Phase = .idle
var isTX: Bool { phase == .keying || phase == .keyed }

func press()         // 仅 idle 可进;乐观 keyed
func release()       // keying/keyed → releasing,无条件发 TX0,启动看门狗
func forceRelease()  // 任意状态可调,幂等(scenePhase/错误路径用)
```

**依赖全部闭包注入**(可单测,不碰硬件):

| 注入 | 类型 | 生产环境接线(RadioViewModel) |
|---|---|---|
| `sendPTT` | `(Bool) -> Void` | 现有 `sendSet("ptt", v)` |
| `sendTXAudioStop` | `() -> Void` | 在 `/WSaudioTX` 发 `"s:"` 文本帧 |
| `setTXAudioActive` | `(Bool) -> Void` | `audioCapture.start()` / `stop()` |
| `serverTXStatus` | `() -> Int` | `state.txStatus`(服务端回显) |
| `isCtrlConnected` | `() -> Bool` | `connection.ctrlConnected` |
| `onStuckTX` | `() -> Void` | `showError("PTT 释放未确认,请检查电台")` |

看门狗参数 `watchdogInterval = 0.5s`、`maxRetries = 3` 为 var,测试可缩短。

**行为**:

- `press()`:
  1. `phase == .idle` 才受理;
  2. 查 `isCtrlConnected()`,未连接**直接拒绝**(不发命令、不进 TX——发不出去的乐观状态最危险);
  3. 已连接:`sendPTT(true)` → `setTXAudioActive(true)` → `phase = .keyed`。不等回显(fire-and-forget,满足 NFR-008 <100ms)。
- `release()`:
  1. 无条件 `sendPTT(false)` + `setTXAudioActive(false)`;
  2. `sendTXAudioStop()`(对齐 SDD ch15 Layer 7;`server.py:1796` 已有处理;iOS 此前未发);
  3. `phase = .releasing`,启动看门狗。
- 看门狗:release 后每 `watchdogInterval` 读 `serverTXStatus()`(`== 0` 视为 RX):
  - 回显 RX → `phase = .idle`,停止;
  - 仍 TX → 重发 `sendPTT(false)`,重试 ≤ `maxRetries` 次;
  - 重试耗尽仍 TX → `onStuckTX()` + `phase = .idle`;
  - 看门狗运行期间 `press()` → 取消看门狗,`phase = .keyed`(合法再发射)。
- `forceRelease()`:无条件 `sendPTT(false)` + `sendTXAudioStop()` + `setTXAudioActive(false)` + 启动看门狗。任意状态可调,重复调用无害(TX0 是 fire-and-forget,每次调用至多发一条)。

**乐观状态与回显的关系**: UI 的 TX 指示(按钮颜色/文字、Header)改读 `pttManager.phase`,**不再读 `RadioState.txStatus`**——回显延迟正是竞态根源;`txStatus` 只服务看门狗判定与仪表显示。`RadioState` 的 stateUpdate 应用逻辑不变。

### 2.2 UI 接线与 scenePhase

- `ContentView.swift` PTT 手势:
  - `onChanged`: `if pttManager.phase == .idle { pttManager.press() }`
  - `onEnded`: `pttManager.release()`(无条件,删除 `txStatus > 0` 判断)
- `RadioViewModel.swift`:
  - 持有 `PTTManager`,init 注入上表闭包;
  - 删除 `setPTT()`(逻辑迁入 PTTManager);
  - `powerOff()`、断开连接、认证失败等所有离开主界面路径统一调 `pttManager.forceRelease()`。
- `FT710MobileApp.swift`:
  ```swift
  .onChange(of: scenePhase) { phase in
      if phase != .active { viewModel?.pttManager.forceRelease() }
  }
  ```
  覆盖切后台/来电/挂起(Layer 6 等价物)。
- 顺手修复:`RadioState.swift:40` `powerOn` 默认值改 `false`。

### 2.3 瀑布流轻点 QSY

`WaterfallView.swift:70-74`: `DragGesture(minimumDistance: 0)` 换成 `SpatialTapGesture`:

```swift
.gesture(SpatialTapGesture().onEnded { value in
    // value.location → 频率换算,沿用现有映射逻辑
})
```

`SpatialTapGesture` 只在"按下-抬起且位移极小"时触发,拖动/滑动被天然过滤,无需自设阈值;iOS 16+ 可用,工程目标 iOS 17 无兼容问题。现有"按住拖动连续 QSY"行为被移除——这正是要修的风险点。

---

## 3. 错误处理与边界

| 场景 | 行为 |
|---|---|
| press 时 ctrl 未连接 | 拒绝,phase 保持 idle,不产生任何命令 |
| release 时 ctrl 未连接 | `sendPTT` 静默丢弃;看门狗照常运行(重连后回显恢复或由服务端 Layer 4 dead-man switch 兜底) |
| 手势被系统中断(onEnded 不触发) | scenePhase 变化时 forceRelease 兜底;App 未退出的纯手势中断由看门狗在下次 release/状态查询时校正 |
| App 进程被杀死 | 客户端无能为力,依赖服务端 Layer 4(socket 关闭强制 TX0) |
| 其他客户端占用 PTT(I6) | 不处理;看门狗只在我方 release 后运行,不干预他方 |
| TX 中切后台 | scenePhase → forceRelease,电台立即回 RX |

## 4. 测试

新增 `Tests/FT710MobileTests/PTTManagerTests.swift`(注入 0.01s interval + 假 `serverTXStatus` 闭包,全部硬件无关):

1. `press` 未连接 → 拒绝,phase 保持 idle,`sendPTT` 未被调用;
2. `press→release` 快速连续 → `ptt:false` 必定发送(§1.1 竞态回归);
3. release 后回显仍 TX → 看门狗重发,第 3 次后停止并触发 `onStuckTX`;
4. 看门狗期间 `press` → 取消重试,phase 回 keyed;
5. `forceRelease` 任意状态幂等:重复调用不崩溃,每次调用至多产生一条 `ptt:false`。

**已知限制**: 工程当前无 test target(`project.yml` 未接入,见分析报告 §7),测试文件随本 spec 写好,但**接入工程留给 spec ② 的构建修复**;本 spec 的验收以真机验证为准。

## 5. 真机验证(iPhone + FT-710 + 服务端)

1. 正常按住/松开 PTT,电台 TX/RX 跟随,频谱/电平恢复;
2. WAN 下快速点按 PTT 10 次,每次都必须回 RX(原 bug 复现场景);
3. TX 中切后台 → 电台立即回 RX;
4. TX 中断网 → 服务端 dead-man switch 触发回 RX;恢复网络后 App 状态正常;
5. 瀑布流滑动浏览不改频率,轻点才 QSY;
6. web 端同时在线(多客户端),iOS PTT 行为不劣化。

## 6. SDD 层级对应与文档同步

| SDD ch15 Layer | iOS 实现 | 本 spec |
|---|---|---|
| 1 Touch-and-hold UX | DragGesture(无条件 release) | 修复 |
| 2 WS command | `sendSet("ptt", v)` fire-and-forget | 保持 |
| 3 PTT watchdog | PTTManager 500ms×3 | **新增** |
| 4 Server dead-man switch | `server.py` 已有 | 不动 |
| 5/6 unload/pagehide | scenePhase forceRelease | **新增** |
| 7 TX 音频收尾 | 停采集 + `"s:"` 帧 | **新增**(`'s:'`) |

**文档同步义务(sdd-guardian Phase 5)**: 服务端零改动 → SDD 各章不变,`SDD/14-version-history.md` 不新增条目(无服务端行为变化);`docs/IOS_APP_ANALYSIS.md` §2.1/§2.2/§2.6 及 §6 的"首屏假开机"项在实施完成后标注"已修复"并注明日期;`FT710Mobile/` 自带腐化文档(CLAUDE.md/README/ARCHITECTURE.md)的重写属 spec ② 范围,不在本 spec。

## 7. 影响文件清单

| 文件 | 变更 |
|---|---|
| `FT710Mobile/Sources/PTT/PTTManager.swift` | 新建 |
| `FT710Mobile/Sources/ViewModel/RadioViewModel.swift` | 持有 PTTManager、注入闭包、删 `setPTT`、离开路径 forceRelease |
| `FT710Mobile/Sources/UI/ContentView.swift` | PTT 手势改无回显判断;TX 指示读 phase |
| `FT710Mobile/Sources/UI/WaterfallView.swift` | DragGesture → SpatialTapGesture |
| `FT710Mobile/Sources/App/FT710MobileApp.swift` | scenePhase 监听 |
| `FT710Mobile/Sources/Model/RadioState.swift` | `powerOn` 默认值 false |
| `FT710Mobile/Tests/FT710MobileTests/PTTManagerTests.swift` | 新建 |
