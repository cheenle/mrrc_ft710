# Status Bar: Bandwidth & Latency Display

**Date:** 2026-07-12
**Status:** Approved

## Overview

Add real-time network bandwidth (all 4 WebSocket channels) and latency (control RTT + audio jitter buffer) to the existing status bar in `static/index.html`.

## Design

### HTML (`static/index.html`)

Append two `<span>` items to `.status-bar`:

```html
<span class="status-item" id="status-bitrate">↓0 ↑0</span>
<span class="status-item" id="status-latency">RTT -- J--</span>
```

### Bandwidth Tracking (`static/ft710_main.js`)

Replace the existing bandwidth IIFE (lines 966-977) with unified 4-channel tracking:

- `window.__netBytes` object: `{ rxCtrl, rxSpec, rxAudio, txCtrl, txAudio }`
- Accumulate bytes in each WS `onmessage` handler (and `sendMsg` for TX)
- Every 1 second: compute `(bytes * 8) / 1000` → kbps, reset counters, update `#status-bitrate` as `↓XXK ↑XXK`

### Latency (`static/ft710_main.js`)

**Control RTT:**
- Record `performance.now()` when ping is sent (`window.__pingSent`)
- On pong, compute RTT = `performance.now() - window.__pingSent`, store in `window.__lastRtt`
- Update `#status-latency` in the same 1-second timer

**Audio Jitter Buffer:**
- Worklet (`static/rx_worklet_processor.js`) reports buffer depth via `postMessage({type:'stats', bufferMs})` every ~2s
- Main thread stores in `window.__jitterMs`
- Display as `RTT XXms JXXms` in `#status-latency`

### CSS

No new CSS required — `.status-item` already handles flex layout with gap.

## Files Changed

| File | Change |
|------|--------|
| `static/index.html` | Add 2 `<span>` to `.status-bar` |
| `static/ft710_main.js` | Unified 4-channel bandwidth + RTT measurement + latency display |
| `static/rx_worklet_processor.js` | Add periodic jitter buffer stats reporting |

## Error Handling

- If `#status-bitrate` or `#status-latency` elements are missing, silently skip (graceful degradation)
- If ping was sent but no pong received before next ping, RTT stays at last known value
- If worklet stats never arrive, jitter shows `J--`

## Testing

- Manual: open browser, verify bandwidth numbers change during audio RX/TX
- Manual: verify RTT updates after each ping/pong cycle (~15s)
- Manual: verify jitter buffer display when audio is streaming
