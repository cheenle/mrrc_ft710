# FFT Spectrum Line Plot — Design Spec

**Date:** 2026-07-12
**Status:** approved

## Summary

Add a real-time FFT spectrum line chart above the existing waterfall on the FT-710 web dashboard. The FFT plot draws the current scope frame (850-point `wf1` array) as a cyan polyline, giving the operator an instantaneous view of signal peaks that complements the time-history waterfall.

## Motivation

The waterfall alone shows signal history but makes it hard to judge instantaneous peak amplitude. A traditional SDR-style spectrum plot above the waterfall lets the operator see both: the FFT line for "what's happening right now" and the waterfall for "what happened over the last N seconds."

## Design Decisions

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Placement | Above waterfall, same section | Standard SDR layout; frequency scales align vertically |
| Height | 22 px | ~1/3 of waterfall (67 px); tall enough for a readable line, compact enough to not push other UI off-screen |
| Style | Polyline, no fill | Clean, minimal; the waterfall already provides the "fill" context |
| Color | Cyan `#06b6d4` | Contrasts with warm waterfall palettes and the red VFO marker |
| Amplitude mapping | Shared Floor/Ceil from waterfall menu | Single set of controls; consistent visual threshold between FFT and waterfall |
| Data source | Same `wf1` (850 bytes, 0–255) that drives `renderWaterfallRow()` | No new data path needed |

## Implementation Plan

### 1. HTML (`static/index.html`)

Add a new `<canvas id="fft-canvas">` inside `.waterfall-section`, **above** `#waterfall-canvas`:

```html
<section class="waterfall-section">
    <canvas id="fft-canvas" class="fft-canvas"></canvas>
    <canvas id="waterfall-canvas" class="waterfall-canvas"></canvas>
    <canvas id="freq-scale-canvas" class="freq-scale-canvas" height="20"></canvas>
</section>
```

### 2. CSS (`static/ft710.css`)

```css
#fft-canvas {
    width: 100%; height: 22px; display: block;
    border-radius: 4px 4px 0 0;
}
```

Waterfall canvas gets `border-radius: 0` (FFT handles the top rounding).

### 3. JavaScript (`static/ft710_ui.js`)

#### New function: `renderFFTPlot(wf1)`

- Called from `renderWaterfallRow()` each time a new spectrum frame arrives
- Clear the FFT canvas
- Map each of the 850 wf1 points to (x, y):
  - `x = (i / 850) * canvasWidth`
  - `y = canvasHeight - ((raw - floor) / (ceil - floor)) * canvasHeight`
  - Clamp y to [0, canvasHeight]
- Draw as a single polyline path using `ctx.strokeStyle = '#06b6d4'`
- Use 1px line width; add subtle glow via `ctx.shadowBlur = 2` + `ctx.shadowColor`

#### Modified function: `renderWaterfallRow(wf1)`

Add one line at the top:
```js
renderFFTPlot(wf1);
```

#### Modified function: `initWaterfall()`

Also initialize the FFT canvas dimensions during layout.

### 4. No changes to

- Server-side Python (data path unchanged)
- WebSocket spectrum protocol
- Floor/Ceil controls (shared)
- Color theme selector (FFT color is fixed, not theme-dependent)

## Edge Cases

- **Canvas too narrow** (< 100px): skip FFT render (same guard as waterfall)
- **Floor ≥ Ceil**: use `dynRange = 1` fallback (same as waterfall)
- **First frame before init**: `ensureWaterfallInitialized()` handles initialization
- **Window resize**: FFT canvas width is recalculated alongside waterfall canvas

## Testing

- Verify FFT line appears above waterfall on page load
- Change Floor/Ceil sliders → FFT line amplitude scaling updates immediately
- Tune VFO → frequency scale and FFT data alignment preserved
- Resize browser window → FFT canvas resizes correctly
- Mobile Safari / Chrome → renders without artifacts
