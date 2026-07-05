# 15. PTT Safety Architecture (ART 0535)

> **Principle**: Release is more safety-critical than keying. A lost PTT release command can leave a radio transmitting indefinitely — causing harmful interference, overheating the radio, and violating spectrum regulations. Every layer must have an independent path to force RX.

## 15.1 Safety Model — Defense in Depth

The MRRC FT-710 PTT safety architecture provides **8 independent layers of defense** against stuck-TX scenarios.

| Layer | Location | Mechanism | Failure Mode Caught |
|-------|----------|-----------|---------------------|
| 1 | Browser UX | Touch-and-hold: release on `mouseup`/`touchend`/`mouseleave`/`touchcancel` | User intentionally releasing PTT |
| 2 | Browser → Server | `sendCommand('ptt', false)` over `/WSradio` | Normal network path |
| 3 | Server | Triple `TX;` query at 200ms intervals; re-send `TX0;` on non-zero | CAT command lost/not acknowledged |
| 4 | Browser | PTT Watchdog: 500ms interval checks `radioState.tx_status`; up to 3 retries | State broadcast lost |
| 5 | Server | Dead-man switch: force `TX0;` when last WS client disconnects during TX | Browser crash, tab close, network loss |
| 6 | Browser | `beforeunload` → `navigator.sendBeacon()` with TX0 | Tab/browser close during TX |
| 7 | Browser | `pagehide` → `sendCommand('ptt', false)` | Mobile app switch / backgrounding |
| 8 | Server + Browser | Stop TX audio stream; clear audio queue; `wsAudioTX.send('s:')` | Audio continuing to feed radio after release |

## 15.2 Layer Details

### Layer 1: Touch-and-Hold UX

PTT only transmits while the user is actively touching the PTT button:

```javascript
pttBtn.addEventListener('mousedown', handlePTTStart);
pttBtn.addEventListener('touchstart', function(e) { e.preventDefault(); handlePTTStart(); });
pttBtn.addEventListener('mouseup', handlePTTEnd);
pttBtn.addEventListener('touchend', function(e) { e.preventDefault(); handlePTTEnd(); });
pttBtn.addEventListener('mouseleave', handlePTTEnd);
pttBtn.addEventListener('touchcancel', handlePTTEnd);
```

### Layer 2: Normal WebSocket Command

```javascript
function handlePTTEnd() {
    sendCommand('ptt', false);
    // ...
}
```

Server receives `{"type":"set","field":"ptt","value":false}` → sends CAT `TX0;`.

### Layer 3: Triple TX0 Verify

```python
# In server.py _execute_set_command, ptt field:
await cat.set_ptt(False)
# Verify with 3 retries at 200ms intervals
for _ in range(3):
    await asyncio.sleep(0.2)
    ptt = await cat.get_ptt()
    if ptt == 0:
        break
    await cat.set_ptt(False)
radio.update(tx_status=0)
```

### Layer 4: PTT Watchdog (Browser)

```javascript
// ptt_manager.js
pttVerifyTimer = setInterval(function() {
    if (!pttActive && !tuneActive) {
        if (radioState.tx_status !== 0) {
            retries++;
            sendCommand('ptt', false);
            if (retries >= 3) {
                // Force locally
                radioState.tx_status = 0;
                radioState.is_transmitting = false;
                renderPTTState();
                renderStatusBar();
                stopPTTWatchdog();
            }
        } else {
            stopPTTWatchdog();
        }
    }
}, 500);
```

### Layer 5: Dead-Man Switch (Server)

```python
# In /WSradio disconnect handler:
if not ctrl_clients and radio.is_transmitting and cat and cat.connected:
    logger.warning("Last client disconnected during TX! Forcing RX.")
    await cat.set_ptt(False)
    radio.update(tx_status=0)
    if audio:
        audio.stop_tx()
```

### Layer 6: Beforeunload Beacon

```javascript
window.addEventListener('beforeunload', function() {
    if (pttActive || tuneActive) {
        if (navigator.sendBeacon) {
            const blob = new Blob([
                JSON.stringify({type:'set', field:'ptt', value:false})
            ], {type: 'application/json'});
            navigator.sendBeacon('/WSradio', blob);
        }
    }
});
```

### Layer 7: Pagehide Handler

```javascript
window.addEventListener('pagehide', function() {
    if (pttActive || tuneActive) {
        sendCommand('ptt', false);
    }
});
```

### Layer 8: TX Audio Stream Stop

Server-side on PTT release:
```python
if audio:
    audio.stop_tx()
```

Browser-side on PTT release:
```javascript
function stopTXAudio() {
    txAudioRunning = false;
    // ...
    if (wsAudioTX && wsAudioTX.readyState === WebSocket.OPEN) {
        wsAudioTX.send('s:');  // Flush server TX queue
    }
}
```

## 15.3 Safety Flow Diagram

```text
Normal Release Path:
  PTT Button Release (any trigger)
    → handlePTTEnd()
      → sendCommand('ptt', false)          [Layers 1+2]
      → stopTXAudio() + wsAudioTX.send('s:') [Layer 8]
      → Server: CAT TX0;
      → Server: triple TX; verify           [Layer 3]
      → PTT Watchdog starts                 [Layer 4]

Emergency Paths:
  Browser crash / tab close:
    → beforeunload → sendBeacon TX0;        [Layer 6]
    → pagehide → sendCommand TX0;           [Layer 7]
    → WS disconnect → server dead-man switch [Layer 5]
    → Server stops TX audio                 [Layer 8]

  Network loss during TX:
    → WS disconnect → server dead-man switch [Layer 5]
    → Server stops TX audio                 [Layer 8]
    → Radio returns to RX (CAT timeout)
```

## 15.4 Testing the Safety Layers

| Test | Expected Behavior | Layers Tested |
|------|-------------------|---------------|
| Normal PTT press/release | TX → RX within 200ms | 1, 2 |
| Force-close browser during TX | Radio returns to RX | 5, 6, 7 |
| Pull USB cable during TX | Radio returns to RX (no CAT response) | 3 |
| Network packet loss during release | Triple TX0 verify catches it | 3 |
| Tab background on iOS during TX | pagehide sends TX0 | 7 |
| Multiple rapid PTT toggles | Each release properly processed | All |
| Server kill -9 during TX | Radio returns to RX (CAT timeout, no polling) | Hardware |

## 15.5 Safety Design Principles

1. **Release is more important than keying.** Every release path must work even if the keying path is broken.
2. **No single point of failure.** 8 independent layers catch different failure modes.
3. **Fail safe, not fail dangerous.** If in doubt, force RX.
4. **Server has final authority.** Even if the browser is completely gone, the server forces RX (Layer 5).
5. **Verify, don't assume.** Always read back TX state after sending TX0; (Layer 3).
6. **Stop audio before RF.** Audio stream stops before the RF carrier drops, preventing hot-switching noise.
