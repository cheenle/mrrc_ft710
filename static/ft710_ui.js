/**
 * FT-710 Web Control — UI Rendering & Event Handlers
 * ===================================================
 * All DOM manipulation, canvas drawing, button logic, and event wiring.
 * Depends on: ft710_main.js (radioState, bands, uiModes, sendCommand, etc.)
 */

// ── Tuning step ─────────────────────────────────────────────────────
let currentTuneStep = 1000;  // Hz
const tuneSteps = [10, 100, 1000, 5000, 10000, 25000];
const DEFAULT_BAND_CYCLE = [
    {name: '160m', start: 1_800_000, end: 2_000_000, default_freq: 1_845_500},
    {name: '80m', start: 3_500_000, end: 4_000_000, default_freq: 3_850_000},
    {name: '60m', start: 5_250_000, end: 5_450_000, default_freq: 5_350_000},
    {name: '40m', start: 7_000_000, end: 7_300_000, default_freq: 7_050_000},
    {name: '30m', start: 10_100_000, end: 10_150_000, default_freq: 10_140_000},
    {name: '20m', start: 14_000_000, end: 14_350_000, default_freq: 14_270_000},
    {name: '17m', start: 18_068_000, end: 18_168_000, default_freq: 18_132_500},
    {name: '15m', start: 21_000_000, end: 21_450_000, default_freq: 21_400_000},
    {name: '12m', start: 24_890_000, end: 24_990_000, default_freq: 24_952_500},
    {name: '10m', start: 28_000_000, end: 29_700_000, default_freq: 28_450_000},
    {name: '6m', start: 50_000_000, end: 54_000_000, default_freq: 50_150_000},
    {name: '4m', start: 70_000_000, end: 70_500_000, default_freq: 70_250_000},
];

function tuneBy(delta) {
    const freq = radioState.active_vfo === 'A' ? radioState.vfo_a_freq : radioState.vfo_b_freq;
    const newFreq = Math.max(30000, Math.min(75000000, freq + delta));
    const field = radioState.active_vfo === 'A' ? 'freq' : 'vfo_b_freq';
    sendCommand(field, newFreq);
    // Optimistic update
    if (radioState.active_vfo === 'A') {
        radioState.vfo_a_freq = newFreq;
    } else {
        radioState.vfo_b_freq = newFreq;
    }
    renderFrequency();
}

// ── Frequency Display ───────────────────────────────────────────────
function formatFrequency(hz) {
    // Split 7.050.000 Hz into display digits:
    //   f10m f1m . f100k f10k f1k . f100h f10h
    //   0    7   .  0     5    0   .  0     0   = 07.050.00 = 7.050 MHz
    const m10 = Math.floor(hz / 10_000_000) % 10;   // tens of MHz
    const m1  = Math.floor(hz / 1_000_000) % 10;    // ones of MHz
    const k100 = Math.floor(hz / 100_000) % 10;     // 100s of kHz
    const k10  = Math.floor(hz / 10_000) % 10;      // 10s of kHz
    const k1   = Math.floor(hz / 1_000) % 10;       // 1s of kHz
    const h100 = Math.floor(hz / 100) % 10;         // 100s of Hz
    const h10  = Math.floor(hz / 10) % 10;          // 10s of Hz
    return { m10: String(m10), m1: String(m1), k100: String(k100), k10: String(k10), k1: String(k1), h100: String(h100), h10: String(h10) };
}

function renderFrequency() {
    const freq = radioState.active_vfo === 'A' ? radioState.vfo_a_freq : radioState.vfo_b_freq;
    const f = formatFrequency(freq);
    setText('f10m', f.m10);
    setText('f1m', f.m1);
    setText('f100k', f.k100);
    setText('f10k', f.k10);
    setText('f1k', f.k1);
    setText('f100h', f.h100);
    // Use f10h if available, otherwise add a trailing 0 span id
    const f10h = document.getElementById('f10h');
    if (f10h) f10h.textContent = f.h10;
}

function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

// ── S-Meter Rendering ───────────────────────────────────────────────
const S_METER_SEGMENTS = [
    { raw: 0, s: 'S0', dbm: -54 },
    { raw: 12, s: 'S1', dbm: -48 },
    { raw: 27, s: 'S2', dbm: -42 },
    { raw: 40, s: 'S3', dbm: -36 },
    { raw: 55, s: 'S4', dbm: -30 },
    { raw: 65, s: 'S5', dbm: -24 },
    { raw: 80, s: 'S6', dbm: -18 },
    { raw: 95, s: 'S7', dbm: -12 },
    { raw: 112, s: 'S8', dbm: -6 },
    { raw: 130, s: 'S9', dbm: 0 },
    { raw: 150, s: '+10', dbm: 10 },
    { raw: 172, s: '+20', dbm: 20 },
    { raw: 190, s: '+30', dbm: 30 },
    { raw: 220, s: '+40', dbm: 40 },
    { raw: 240, s: '+50', dbm: 50 },
    { raw: 255, s: '+60', dbm: 60 },
];

function renderSMeter() {
    const canvas = document.getElementById('smeter-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;

    ctx.clearRect(0, 0, w, h);

    const raw = radioState.s_meter;
    // Map raw value to position
    const pos = (raw / 255) * w;

    // Background gradient
    const bgGrad = ctx.createLinearGradient(0, 0, w, 0);
    bgGrad.addColorStop(0, '#22c55e');
    bgGrad.addColorStop(0.3, '#22c55e');
    bgGrad.addColorStop(0.5, '#eab308');
    bgGrad.addColorStop(0.7, '#f59e0b');
    bgGrad.addColorStop(1, '#ef4444');
    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 2, pos, h - 4);

    // Unfilled portion
    ctx.fillStyle = 'rgba(255,255,255,0.05)';
    ctx.fillRect(pos, 2, w - pos, h - 4);

    // S-unit markers
    ctx.fillStyle = 'rgba(255,255,255,0.3)';
    const marks = [0, 12, 27, 40, 55, 65, 80, 95, 112, 130, 150, 172, 190, 220, 240, 255];
    for (const m of marks) {
        const x = (m / 255) * w;
        ctx.fillRect(x, 0, 1, h);
    }

    // Border
    ctx.strokeStyle = 'rgba(255,255,255,0.15)';
    ctx.lineWidth = 1;
    ctx.strokeRect(0.5, 0.5, w - 1, h - 1);

    // Update text values
    setText('smeter-value', radioState.s_unit);
    setText('smeter-dbm', radioState.s_meter_dbm.toFixed(0) + ' dBm');
}

// ── Meter Rendering ─────────────────────────────────────────────────
function renderMeters() {
    // Power meter — watts (calibrated in backend from RM5 raw 0-255).
    // FT-710 is a 100W radio (110W max on the scale).
    const pwrW = radioState.power_watts || 0;
    const pwrPct = Math.min(100, pwrW / 110 * 100);
    setMeterBar('meter-pwr-bar', pwrPct);
    setText('meter-pwr-val', pwrW.toFixed(1));

    // ALC meter — 0-100% deflection (RM4 raw 0-255).
    const alcPct = radioState.alc_pct || 0;
    setMeterBar('meter-alc-bar', alcPct);
    setText('meter-alc-val', alcPct.toFixed(0));

    // SWR meter — ratio 1.0..9.9 (calibrated in backend from RM6 raw).
    const swrVal = radioState.swr_ratio || 1.0;
    const swrPct = Math.min(100, (swrVal - 1) / 4 * 100);  // 1.0->0%, 5.0->100%
    setMeterBar('meter-swr-bar', swrPct);
    setText('meter-swr-val', swrVal.toFixed(1));

    // Id (drain current) — amps (calibrated from RM7 raw).
    const idA = radioState.id_amps || 0;
    const idPct = Math.min(100, idA / 26 * 100);
    setMeterBar('meter-id-bar', idPct);
    setText('meter-id-val', idA.toFixed(1));

    // Vd (drain/supply voltage) — volts (calibrated from RM8 raw).
    const vdV = radioState.vd_volts || 0;
    const vdPct = Math.min(100, vdV / 16 * 100);
    setMeterBar('meter-vd-bar', vdPct);
    setText('meter-vd-val', vdV.toFixed(1));
}

function setMeter(barId, valId, pct, raw) {
    setMeterBar(barId, pct);
    setText(valId, raw);
}

function setMeterBar(barId, pct) {
    const bar = document.getElementById(barId);
    if (bar) {
        bar.style.width = Math.min(100, Math.max(0, pct)) + '%';
    }
}

// ── Status Bar ──────────────────────────────────────────────────────
function renderStatusBar() {
    setText('status-band', radioState.band_name);
    setText('status-mode', radioState.mode_display);

    const txEl = document.getElementById('status-tx');
    if (txEl) {
        if (radioState.tx_status === 1) {
            txEl.textContent = 'TX';
            txEl.classList.add('tx');
        } else if (radioState.tx_status === 2) {
            txEl.textContent = 'TUNE';
            txEl.classList.add('tx');
        } else {
            txEl.textContent = 'RX';
            txEl.classList.remove('tx');
        }
    }

    const dot = document.querySelector('#status-serial .status-dot');
    if (dot) {
        if (radioState.serial_connected) {
            dot.classList.add('connected');
        } else {
            dot.classList.remove('connected');
        }
    }
}

// ── Button Labels ───────────────────────────────────────────────────
const modeCycle = ['LSB', 'USB', 'CW-U', 'AM', 'FM', 'RTTY-L', 'DATA-L'];

function getNextMode(currentMode) {
    const idx = modeCycle.indexOf(currentMode);
    return modeCycle[(idx + 1) % modeCycle.length];
}

function getBandCycle() {
    const serverBandsByName = new Map((bands || []).map(b => [b.name, b]));
    return DEFAULT_BAND_CYCLE.map(function(defaultBand) {
        return Object.assign({}, defaultBand, serverBandsByName.get(defaultBand.name) || {});
    });
}

// Dead simple: find current band in the cycle, return the next one.
// Falls off the end → wraps to 160m.  Unknown band → starts at 160m.
function getNextBand(currentBand) {
    const bandList = getBandCycle();
    let idx = bandList.findIndex(b => b.name === currentBand);
    if (idx < 0) idx = 0;   // unknown → 160m is as good a guess as any
    const nextIdx = (idx + 1) % bandList.length;
    return bandList[nextIdx];
}

function getNextFilter(currentIdx, modeName) {
    // Simple: if current is max (23 voice, 21 narrow), cycle back to 1
    const isNarrow = ['CW-U','CW-L','RTTY-L','RTTY-U','DATA-L','DATA-U','PSK'].includes(modeName);
    const maxIdx = isNarrow ? 21 : 23;
    return currentIdx >= maxIdx ? 1 : currentIdx + 1;
}

function getFilterLabel(idx, modeName) {
    const isNarrow = ['CW-U','CW-L','RTTY-L','RTTY-U','DATA-L','DATA-U','PSK'].includes(modeName);
    const voiceWidths = {1:300,2:400,3:600,4:850,5:1100,6:1200,7:1500,8:1650,9:1800,10:1950,11:2100,12:2250,13:2400,14:2450,15:2500,16:2600,17:2700,18:2800,19:2900,20:3000,21:3200,22:3500,23:4000};
    const narrowWidths = {1:50,2:100,3:150,4:200,5:250,6:300,7:350,8:400,9:450,10:500,11:600,12:800,13:1200,14:1400,15:1700,16:2000,17:2400,18:3000,19:3200,20:3500,21:4000};
    const table = isNarrow ? narrowWidths : voiceWidths;
    const hz = table[idx] || 2400;
    if (hz >= 1000) return (hz/1000).toFixed(1) + 'k';
    return hz + 'Hz';
}

function renderButtonLabels() {
    const modeName = radioState.mode_name;
    const nextMode = getNextMode(modeName);
    setText('btn-mode', nextMode);
    document.getElementById('btn-mode').dataset.current = modeName;

    const bandName = radioState.band_name;
    const nextBand = getNextBand(bandName);
    if (nextBand) {
        setText('btn-band', nextBand.name);
        document.getElementById('btn-band').dataset.current = bandName;
    }

    const filterIdx = radioState.filter_width;
    const nextIdx = getNextFilter(filterIdx, modeName);
    setText('btn-filter', getFilterLabel(nextIdx, modeName));
    document.getElementById('btn-filter').dataset.current = filterIdx;

    // ATT cycle: OFF -> 6dB -> 12dB -> 18dB -> OFF
    const attLabels = {0:'OFF', 1:'6dB', 2:'12dB', 3:'18dB'};
    const nextAtt = (radioState.attenuator + 1) % 4;
    setText('btn-att', 'ATT ' + attLabels[nextAtt]);

    // PRE cycle: OFF -> AMP1 -> AMP2 -> OFF
    const preLabels = {0:'OFF', 1:'AMP1', 2:'AMP2'};
    const nextPre = (radioState.preamp + 1) % 3;
    setText('btn-pre', 'PRE ' + preLabels[nextPre]);
}

// ── Toggle States ───────────────────────────────────────────────────
function renderToggles() {
    setToggle('toggle-nr', radioState.noise_reduction);
    setToggle('toggle-nb', radioState.noise_blanker);
    setToggle('toggle-an', radioState.auto_notch);
    setToggle('toggle-comp', radioState.compressor);
    setToggle('toggle-atu', radioState.tuner_status > 0);
}

function setToggle(id, value) {
    const el = document.getElementById(id);
    if (el) el.checked = value;
}

// ── Sliders ─────────────────────────────────────────────────────────
function renderSliders() {
    setSlider('slider-rfpower', 'val-rfpower', radioState.rf_power);
    setSlider('slider-afgain', 'val-afgain', radioState.af_gain);
}

function setSlider(sliderId, valId, value) {
    const slider = document.getElementById(sliderId);
    const val = document.getElementById(valId);
    if (slider) slider.value = value;
    if (val) val.textContent = value;
}

// ── VFO Buttons ─────────────────────────────────────────────────────
function renderVFOButtons() {
    const vfoa = document.getElementById('btn-vfoa');
    const vfob = document.getElementById('btn-vfob');
    if (vfoa) vfoa.classList.toggle('active', radioState.active_vfo === 'A');
    if (vfob) vfob.classList.toggle('active', radioState.active_vfo === 'B');

    const splitBtn = document.getElementById('btn-split');
    if (splitBtn) splitBtn.classList.toggle('split-on', radioState.split);

    const vfoInd = document.getElementById('vfo-indicator');
    if (vfoInd) vfoInd.textContent = 'VFO-' + radioState.active_vfo;
}

// ── Memory Channels ─────────────────────────────────────────────────
function renderMemoryChannels() {
    document.querySelectorAll('.mem-btn').forEach(btn => {
        const idx = parseInt(btn.dataset.mem);
        const ch = memChannels[idx];
        const freqEl = btn.querySelector('.mem-freq');
        if (freqEl) {
            if (ch && ch.freq) {
                freqEl.textContent = (ch.freq / 1e6).toFixed(3);
                btn.title = ch.label || '';
            } else {
                freqEl.textContent = '---';
                btn.title = '';
            }
        }
    });
}

// ── PTT Visual ──────────────────────────────────────────────────────
function renderPTTState() {
    const btn = document.getElementById('btn-ptt');
    if (btn) {
        btn.classList.toggle('tx-active', radioState.is_transmitting);
    }
    const tuneBtn = document.getElementById('btn-tune');
    if (tuneBtn) {
        tuneBtn.classList.toggle('tune-active', radioState.tx_status === 2);
    }
}

// ── Waterfall Rendering ─────────────────────────────────────────────
const WF_HISTORY = 120; // rows of waterfall history
let waterfallHistory = [];
let waterfallInitialized = false;
const SCOPE_SPAN_HZ = {
    0: 1000,
    1: 2000,
    2: 5000,
    3: 10000,
    4: 20000,
    5: 50000,
    6: 100000,
    7: 200000,
    8: 500000,
    9: 1000000,
};

function initWaterfall() {
    const canvas = document.getElementById('waterfall-canvas');
    if (!canvas) return;
    const rect = canvas.parentElement.getBoundingClientRect();
    const w = Math.max(100, rect.width - 8); // Minimum 100px wide
    canvas.width = w;
    canvas.height = 67;  // Compact waterfall
    waterfallHistory = [];
    waterfallInitialized = true;
}

function ensureWaterfallInitialized() {
    if (!waterfallInitialized) {
        initWaterfall();
    }
    // Re-check canvas size — layout may have changed
    const canvas = document.getElementById('waterfall-canvas');
    if (canvas && canvas.width < 100) {
        const rect = canvas.parentElement.getBoundingClientRect();
        if (rect.width > 100) {
            canvas.width = rect.width - 8;
            canvas.height = 67;
            waterfallHistory = [];
        }
    }
}

function renderWaterfallRow(wf1) {
    ensureWaterfallInitialized();

    const canvas = document.getElementById('waterfall-canvas');
    if (!canvas) return;
    if (canvas.width < 100 || canvas.height < 10) return;

    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;

    // Scroll canvas content up by 1px
    ctx.drawImage(canvas, 0, 1, w, h - 1, 0, 0, w, h - 1);

    // Draw new row at the bottom (1px high)
    const srcLen = wf1.length;
    for (let x = 0; x < w; x++) {
        // Linear interpolation from source data to canvas width
        const srcPos = (x / w) * srcLen;
        const srcIdx = Math.floor(srcPos);
        const frac = srcPos - srcIdx;
        const v1 = wf1[srcIdx] || 0;
        const v2 = (srcIdx + 1 < srcLen) ? wf1[srcIdx + 1] : v1;
        const val = Math.min(255, v1 + (v2 - v1) * frac);

        // Classic ham waterfall: black→dark blue→blue→cyan→white
        let r, g, b;
        const v = val / 255;
        r = Math.floor(v * v * 180);
        g = Math.floor(v * v * v * 255);
        b = Math.floor(5 + v * 250);

        ctx.fillStyle = 'rgb(' + Math.floor(r) + ',' + Math.floor(g) + ',' + Math.floor(b) + ')';
        ctx.fillRect(x, h - 1, 1, 1);
    }

    // Update frequency scale
    renderFreqScale(w);
}

function renderFreqScale(canvasWidth) {
    const scaleCanvas = document.getElementById('freq-scale-canvas');
    if (!scaleCanvas) return;
    scaleCanvas.width = canvasWidth;
    const ctx = scaleCanvas.getContext('2d');
    const w = scaleCanvas.width;
    ctx.fillStyle = '#1a1a1a';
    ctx.fillRect(0, 0, w, 20);

    const spanHz = SCOPE_SPAN_HZ[radioState.scope_span] || 100000;
    const centerFreq = radioState.active_freq ||
        (radioState.active_vfo === 'B' ? radioState.vfo_b_freq : radioState.vfo_a_freq) ||
        14200000;

    let startFreq = radioState.scope_start_freq;
    if (!startFreq || startFreq <= 0) {
        startFreq = centerFreq - spanHz / 2;
    }

    ctx.fillStyle = '#666';
    ctx.font = '9px monospace';
    ctx.textAlign = 'center';
    const numMarks = 5;
    for (let i = 0; i <= numMarks; i++) {
        const x = (i / numMarks) * w;
        const freq = startFreq + (i / numMarks) * spanHz;
        ctx.fillText((freq / 1e6).toFixed(3), x, 14);
    }
}

function renderScopeSettings() {
    const spanSelect = document.getElementById('scope-span-select');
    if (spanSelect) spanSelect.value = String(radioState.scope_span);
    const speedSelect = document.getElementById('scope-speed-select');
    if (speedSelect) speedSelect.value = String(radioState.scope_speed);
    const canvas = document.getElementById('waterfall-canvas');
    if (canvas && canvas.width > 0) {
        renderFreqScale(canvas.width);
    }
}

// ── Render All ──────────────────────────────────────────────────────
function renderAll() {
    initWaterfall();
    renderFrequency();
    renderSMeter();
    renderMeters();
    renderStatusBar();
    renderButtonLabels();
    renderToggles();
    renderSliders();
    renderScopeSettings();
    renderVFOButtons();
    renderMemoryChannels();
    renderPTTState();
}

// ── Render Updates (partial, from dirty field list) ─────────────────
function renderUpdates(dirtyFields) {
    const freqFields = ['vfo_a_freq', 'vfo_b_freq', 'active_vfo'];
    const meterFields = ['s_meter', 's_meter_dbm', 's_unit'];
    const txMeters = ['power_meter', 'alc_meter', 'swr_meter', 'id_meter', 'vd_meter'];
    const settingsFields = [
        'mode', 'mode_name', 'mode_display', 'band_name', 'tx_status',
        'is_transmitting', 'filter_width', 'filter_hz', 'preamp', 'preamp_label',
        'attenuator', 'attenuator_label', 'noise_blanker', 'noise_reduction',
        'auto_notch', 'compressor', 'tuner_status', 'rf_power',
        'split', 'serial_connected', 'scope_span', 'scope_speed', 'scope_mode',
        'scope_start_freq',
    ];

    let needFreq = false, needSMeter = false, needMeters = false;
    let needStatus = false, needButtons = false, needToggles = false;
    let needSliders = false, needVFO = false, needPTT = false, needScope = false;

    for (const f of dirtyFields) {
        if (freqFields.includes(f)) needFreq = true;
        if (meterFields.includes(f)) needSMeter = true;
        if (txMeters.includes(f)) needMeters = true;
        if (settingsFields.includes(f)) {
            if (['mode','mode_name','mode_display'].includes(f)) needButtons = true;
            if (['band_name'].includes(f)) needButtons = needStatus = true;
            if (['tx_status','is_transmitting'].includes(f)) needStatus = needPTT = true;
            if (['filter_width','filter_hz','preamp','preamp_label','attenuator','attenuator_label'].includes(f)) needButtons = true;
            if (['noise_blanker','noise_reduction','auto_notch','compressor','tuner_status'].includes(f)) needToggles = true;
            if (['rf_power','af_gain'].includes(f)) needSliders = true;
            if (['scope_span','scope_speed','scope_mode','scope_start_freq'].includes(f)) needScope = true;
            if (['split'].includes(f)) needVFO = true;
            if (['serial_connected'].includes(f)) needStatus = true;
            needStatus = true; // Most settings affect status bar
            needButtons = true; // Most settings affect button labels
        }
    }

    if (needFreq) renderFrequency();
    if (needSMeter) renderSMeter();
    if (needMeters) renderMeters();
    if (needStatus) renderStatusBar();
    if (needButtons) renderButtonLabels();
    if (needToggles) renderToggles();
    if (needSliders) renderSliders();
    if (needScope || needFreq) renderScopeSettings();
    if (needVFO || needFreq) renderVFOButtons();
    if (needPTT) renderPTTState();
}

function renderField(field) {
    renderUpdates([field]);
}

// ── PTT Handlers (called from ptt_manager.js) ───────────────────────
function handlePTTStart() {
    sendCommand('ptt', true);
    radioState.tx_status = 1;
    radioState.is_transmitting = true;
    renderPTTState();
    renderStatusBar();
    // Start TX audio capture
    if (typeof startTXAudio === 'function') startTXAudio();
}

function handlePTTEnd() {
    sendCommand('ptt', false);
    radioState.tx_status = 0;
    radioState.is_transmitting = false;
    renderPTTState();
    renderStatusBar();
    // Stop TX audio capture
    if (typeof stopTXAudio === 'function') stopTXAudio();
}

function handleTuneStart() {
    sendCommand('tune', true);
    radioState.tx_status = 2;
    renderPTTState();
    renderStatusBar();
}

function handleTuneEnd() {
    sendCommand('tune', false);
    radioState.tx_status = 0;
    renderPTTState();
    renderStatusBar();
}

// ── Event Wiring ────────────────────────────────────────────────────
function initUI() {
    // Mode button: cycles to next mode
    document.getElementById('btn-mode').addEventListener('click', function() {
        const nextMode = getNextMode(radioState.mode_name);
        sendCommand('mode', nextMode);
        radioState.mode_name = nextMode;
        renderButtonLabels();
        renderStatusBar();
    });

    // Band button: cycles to next band
    document.getElementById('btn-band').addEventListener('click', function() {
        const nextBand = getNextBand(radioState.band_name);
        if (nextBand) {
            console.log('[Band] click', {
                current: radioState.band_name,
                next: nextBand.name,
                bsr: nextBand.bsr,
                default_freq: nextBand.default_freq,
                bands: bands.map(b => b.name),
            });
            sendCommand('band', nextBand.name);
            radioState.band_name = nextBand.name;
            radioState.active_vfo = 'A';
            radioState.vfo_a_freq = nextBand.default_freq;
            renderFrequency();
            renderButtonLabels();
            renderStatusBar();
        }
    });

    // Filter button: cycles filter width
    document.getElementById('btn-filter').addEventListener('click', function() {
        const nextIdx = getNextFilter(radioState.filter_width, radioState.mode_name);
        sendCommand('filter', nextIdx);
        radioState.filter_width = nextIdx;
        renderButtonLabels();
    });

    // ATT button: cycles attenuator
    document.getElementById('btn-att').addEventListener('click', function() {
        const nextAtt = (radioState.attenuator + 1) % 4;
        sendCommand('att', nextAtt);
        radioState.attenuator = nextAtt;
        renderButtonLabels();
    });

    // PRE button: cycles preamp
    document.getElementById('btn-pre').addEventListener('click', function() {
        const nextPre = (radioState.preamp + 1) % 3;
        sendCommand('preamp', nextPre);
        radioState.preamp = nextPre;
        renderButtonLabels();
    });

    // Tuning buttons — resolve step dynamically from currentTuneStep
    document.querySelectorAll('.tune-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const action = this.dataset.action;
            let delta = 0;
            if (action === 'slow-left')  delta = -currentTuneStep;
            if (action === 'slow-right') delta = currentTuneStep;
            if (action === 'fast-left')  delta = -(currentTuneStep * 5);
            if (action === 'fast-right') delta = currentTuneStep * 5;
            if (delta !== 0) tuneBy(delta);
        });
    });

    // Step button — cycle through preset step sizes
    document.getElementById('btn-step').addEventListener('click', function() {
        const idx = tuneSteps.indexOf(currentTuneStep);
        const nextIdx = (idx + 1) % tuneSteps.length;
        currentTuneStep = tuneSteps[nextIdx];
        const labels = {10:'10Hz', 100:'100Hz', 1000:'1kHz', 5000:'5kHz', 10000:'10kHz', 25000:'25kHz'};
        const stepLabel = labels[currentTuneStep] || currentTuneStep + 'Hz';
        this.textContent = stepLabel;
        // Update tune button tooltips so the user knows what each does
        document.querySelectorAll('.tune-btn').forEach(btn => {
            const action = btn.dataset.action;
            if (action === 'slow-left' || action === 'slow-right') {
                btn.title = 'Step ' + stepLabel;
            } else if (action === 'fast-left' || action === 'fast-right') {
                btn.title = 'Step ' + (currentTuneStep * 5 / 1000) + 'kHz';
            }
        });
    });

    // Toggle switches
    document.getElementById('toggle-nr').addEventListener('change', function() {
        sendCommand('nr', this.checked);
        radioState.noise_reduction = this.checked;
    });
    document.getElementById('toggle-nb').addEventListener('change', function() {
        sendCommand('nb', this.checked);
        radioState.noise_blanker = this.checked;
    });
    document.getElementById('toggle-an').addEventListener('change', function() {
        sendCommand('an', this.checked);
        radioState.auto_notch = this.checked;
    });
    document.getElementById('toggle-comp').addEventListener('change', function() {
        sendCommand('comp', this.checked);
        radioState.compressor = this.checked;
    });
    document.getElementById('toggle-atu').addEventListener('change', function() {
        const val = this.checked ? 1 : 0;
        sendCommand('tuner', val);
        radioState.tuner_status = val;
    });

    // Scope span selector
    document.getElementById('scope-span-select').addEventListener('change', function() {
        const v = parseInt(this.value);
        sendCommand('scope_span', v);
        radioState.scope_span = v;
        renderScopeSettings();
    });
    // Scope speed selector
    document.getElementById('scope-speed-select').addEventListener('change', function() {
        const v = parseInt(this.value);
        sendCommand('scope_speed', v);
        radioState.scope_speed = v;
        renderScopeSettings();
    });

    // NR/NB level sliders
    document.getElementById('slider-nrlevel').addEventListener('input', function() {
        setText('val-nrlevel', this.value);
    });
    document.getElementById('slider-nrlevel').addEventListener('change', function() {
        sendCommand('nr_level', parseInt(this.value));
    });
    document.getElementById('slider-nblevel').addEventListener('input', function() {
        setText('val-nblevel', this.value);
    });
    document.getElementById('slider-nblevel').addEventListener('change', function() {
        sendCommand('nb_level', parseInt(this.value));
    });

    // Sliders
    document.getElementById('slider-rfpower').addEventListener('input', function() {
        setText('val-rfpower', this.value);
    });
    document.getElementById('slider-rfpower').addEventListener('change', function() {
        const v = parseInt(this.value);
        sendCommand('rf_power', v);
        radioState.rf_power = v;
    });
    document.getElementById('slider-afgain').addEventListener('input', function() {
        setText('val-afgain', this.value);
        // Control browser audio volume (gain 0.0–1.0 from slider 0–255)
        var g = parseInt(this.value) / 255.0;
        if (typeof AudioRX_gain_node !== 'undefined' && AudioRX_gain_node) {
            AudioRX_gain_node.gain.value = g;
        }
        radioState.af_gain = parseInt(this.value);
    });
    document.getElementById('slider-afgain').addEventListener('change', function() {
        // No-op: browser-side volume only, don't send CAT command
    });
    document.getElementById('slider-micgain').addEventListener('input', function() {
        setText('val-micgain', this.value);
    });
    document.getElementById('slider-micgain').addEventListener('change', function() {
        const v = parseInt(this.value);
        sendCommand('mic_gain', v);
        radioState.mic_gain = v;
    });

    // VFO buttons
    document.getElementById('btn-vfoa').addEventListener('click', function() {
        if (radioState.active_vfo !== 'A') {
            sendCommand('vfo', 'A');
            radioState.active_vfo = 'A';
            renderVFOButtons();
            renderFrequency();
        }
    });
    document.getElementById('btn-vfob').addEventListener('click', function() {
        if (radioState.active_vfo !== 'B') {
            sendCommand('vfo', 'B');
            radioState.active_vfo = 'B';
            renderVFOButtons();
            renderFrequency();
        }
    });
    document.getElementById('btn-ab').addEventListener('click', function() {
        sendCommand('vfo_equal', true);
        radioState.vfo_a_freq = radioState.vfo_b_freq;
        renderFrequency();
    });
    document.getElementById('btn-split').addEventListener('click', function() {
        const newSplit = !radioState.split;
        sendCommand('split', newSplit);
        radioState.split = newSplit;
        renderVFOButtons();
    });

    // PTT button
    const pttBtn = document.getElementById('btn-ptt');
    pttBtn.addEventListener('mousedown', handlePTTStart);
    pttBtn.addEventListener('touchstart', function(e) { e.preventDefault(); handlePTTStart(); });
    pttBtn.addEventListener('mouseup', handlePTTEnd);
    pttBtn.addEventListener('touchend', function(e) { e.preventDefault(); handlePTTEnd(); });
    pttBtn.addEventListener('mouseleave', handlePTTEnd);
    pttBtn.addEventListener('touchcancel', handlePTTEnd);

    // TUNE button
    const tuneBtn = document.getElementById('btn-tune');
    tuneBtn.addEventListener('click', function() {
        if (radioState.tx_status === 2) {
            handleTuneEnd();
        } else {
            handleTuneStart();
        }
    });

    // Memory buttons
    document.querySelectorAll('.mem-btn').forEach(btn => {
        let pressTimer;
        let longPressHandled = false;
        const idx = parseInt(btn.dataset.mem);

        btn.addEventListener('click', function() {
            if (longPressHandled) {
                longPressHandled = false;
                return;
            }
            // Tap: recall
            const ch = memChannels[idx];
            if (ch && ch.freq) {
                sendMsg({
                    type: 'memRecall',
                    freq: ch.freq,
                    mode: ch.mode || undefined,
                });
                if (radioState.active_vfo === 'B') {
                    radioState.vfo_b_freq = ch.freq;
                } else {
                    radioState.vfo_a_freq = ch.freq;
                }
                if (ch.mode) {
                    radioState.mode_name = ch.mode;
                }
                renderFrequency();
                renderVFOButtons();
            }
        });

        function saveMemoryChannel() {
            longPressHandled = true;
            var saveFreq = radioState.active_vfo === 'A' ? radioState.vfo_a_freq : radioState.vfo_b_freq;
            const ch = {
                freq: saveFreq,
                mode: radioState.mode_name,
                label: radioState.band_name + ' ' + (saveFreq / 1e6).toFixed(3),
            };
            memChannels[idx] = ch;
            // Persist locally so channels survive page refresh
            try { sessionStorage.setItem('ft710_memChannels', JSON.stringify(memChannels)); } catch(e) {}
            sendMsg({
                type: 'memSave',
                channels: memChannels,
            });
            renderMemoryChannels();
        }

        // Long press: save (uses active VFO)
        btn.addEventListener('touchstart', function(e) {
            pressTimer = setTimeout(function() {
                saveMemoryChannel();
                hapticFeedback('medium');
            }, 800);
        });
        btn.addEventListener('touchend', function() { clearTimeout(pressTimer); });
        btn.addEventListener('touchcancel', function() { clearTimeout(pressTimer); });
        // Desktop long press (uses active VFO)
        btn.addEventListener('mousedown', function(e) {
            pressTimer = setTimeout(function() {
                saveMemoryChannel();
            }, 800);
        });
        btn.addEventListener('mouseup', function() { clearTimeout(pressTimer); });
        btn.addEventListener('mouseleave', function() { clearTimeout(pressTimer); });
    });

    // Menu
    document.getElementById('menu-toggle').addEventListener('click', function() {
        document.getElementById('main-menu').classList.add('open');
        document.getElementById('menu-overlay').classList.add('open');
    });
    document.getElementById('menu-close').addEventListener('click', closeMenu);
    document.getElementById('menu-overlay').addEventListener('click', closeMenu);
    document.querySelectorAll('.menu-item[data-action]').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const action = this.dataset.action;
            handleMenuAction(action);
            closeMenu();
        });
    });
}

function closeMenu() {
    document.getElementById('main-menu').classList.remove('open');
    document.getElementById('menu-overlay').classList.remove('open');
}

function handleMenuAction(action) {
    switch (action) {
        case 'band-select':
            showBandSelector();
            break;
        case 'mode-select':
            showModeSelector();
            break;
        case 'memory-manage':
            showMemoryManager();
            break;
        case 'settings':
            // Scroll to settings
            document.getElementById('settings-panel').scrollIntoView({behavior:'smooth'});
            break;
        case 'logout':
            fetch('/api/auth/logout', {method:'POST'}).then(function() {
                window.location.replace('/login');
            });
            break;
    }
}

// ── Modal Dialogs ───────────────────────────────────────────────────
function showModal(title, items, onSelect, currentValue) {
    // Remove any existing modal
    const existing = document.querySelector('.modal-overlay');
    if (existing) existing.remove();

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';

    const content = document.createElement('div');
    content.className = 'modal-content';

    const titleEl = document.createElement('div');
    titleEl.className = 'modal-title';
    titleEl.textContent = title;

    const grid = document.createElement('div');
    grid.className = 'modal-grid';

    items.forEach(function(item) {
        const btn = document.createElement('button');
        btn.className = 'modal-btn';
        btn.textContent = item.label || item.name || item;
        if (item === currentValue || item.name === currentValue) {
            btn.classList.add('selected');
        }
        btn.addEventListener('click', function() {
            onSelect(item);
            overlay.remove();
        });
        grid.appendChild(btn);
    });

    const closeBtn = document.createElement('button');
    closeBtn.className = 'modal-close';
    closeBtn.textContent = 'Cancel';
    closeBtn.addEventListener('click', function() { overlay.remove(); });

    content.appendChild(titleEl);
    content.appendChild(grid);
    content.appendChild(closeBtn);
    overlay.appendChild(content);
    document.body.appendChild(overlay);

    overlay.addEventListener('click', function(e) {
        if (e.target === overlay) overlay.remove();
    });
}

function showBandSelector() {
    const items = bands.map(function(b) { return {name: b.name, label: b.name + ' (' + (b.start/1e6).toFixed(1) + '-' + (b.end/1e6).toFixed(1) + ' MHz)'}; });
    showModal('Select Band', items, function(band) {
        sendCommand('band', band.name);
        radioState.band_name = band.name;
        if (band.default_freq) {
            radioState.vfo_a_freq = band.default_freq;
            renderFrequency();
        }
        renderButtonLabels();
        renderStatusBar();
    }, radioState.band_name);
}

function showModeSelector() {
    const items = uiModes.map(function(m) { return {name: m, label: m}; });
    showModal('Select Mode', items, function(mode) {
        sendCommand('mode', mode.name);
        radioState.mode_name = mode.name;
        radioState.mode = (mode.name === 'LSB' ? 1 : mode.name === 'USB' ? 2 : mode.name === 'CW-U' ? 3 : mode.name === 'AM' ? 5 : mode.name === 'FM' ? 4 : mode.name === 'RTTY-L' ? 6 : mode.name === 'DATA-L' ? 8 : 1);
        renderButtonLabels();
        renderStatusBar();
    }, radioState.mode_name);
}

function showMemoryManager() {
    let html = '<div class="modal-title">Memory Manager</div>';
    for (let i = 0; i < 6; i++) {
        const ch = memChannels[i];
        const freqStr = ch ? (ch.freq / 1e6).toFixed(3) + ' MHz' : 'Empty';
        const label = ch ? (ch.label || '') : '';
        html += '<div style="display:flex;justify-content:space-between;align-items:center;padding:8px;border-bottom:1px solid #444;">';
        html += '<span style="font-weight:700;color:#f59e0b;">M' + (i+1) + '</span>';
        html += '<span>' + freqStr + '</span>';
        html += '<span style="font-size:11px;color:#999;">' + label + '</span>';
        html += '<button data-clear="' + i + '" style="background:#ef4444;color:#fff;border:none;border-radius:4px;padding:4px 8px;font-size:11px;">Clear</button>';
        html += '</div>';
    }
    html += '<button class="modal-close" id="mem-close">Close</button>';

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    const content = document.createElement('div');
    content.className = 'modal-content';
    content.innerHTML = html;
    overlay.appendChild(content);
    document.body.appendChild(overlay);

    content.querySelectorAll('[data-clear]').forEach(btn => {
        btn.addEventListener('click', function() {
            const idx = parseInt(this.dataset.clear);
            memChannels[idx] = null;
            // Persist locally so channels survive page refresh
            try { sessionStorage.setItem('ft710_memChannels', JSON.stringify(memChannels)); } catch(e) {}
            sendMsg({type: 'memSave', channels: memChannels});
            renderMemoryChannels();
            overlay.remove();
        });
    });
    document.getElementById('mem-close').addEventListener('click', function() { overlay.remove(); });
    overlay.addEventListener('click', function(e) { if (e.target === overlay) overlay.remove(); });
}

// ── Haptic Feedback ─────────────────────────────────────────────────
function hapticFeedback(pattern) {
    if ('vibrate' in navigator) {
        if (pattern === 'medium') navigator.vibrate(15);
        else navigator.vibrate(8);
    }
}

// ── Initialize ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
    initUI();
});
