# iOS App Opus Integration Guide

**Date**: 2026-07-14  
**Status**: Implementation Ready

---

## 1. Overview
This document guides the integration of `libopus` into the FT710Mobile iOS app to enable Opus encoding/decoding for TX/RX audio.

---

## 2. Files Added
The following files have been created/updated:

- **`Sources/Audio/OpusBridge.h`**: C header for libopus wrapper.
- **`Sources/Audio/OpusBridge.c`**: C implementation linking to `libopus`.
- **`Sources/Audio/OpusDecoder.swift`**: Swift wrapper for decoding RX audio.
- **`Sources/Audio/OpusEncoder.swift`**: Swift wrapper for encoding TX audio.

---

## 3. Xcode Project Setup

### 3.1 Add Files to Project
1. In Xcode, right-click the `FT710Mobile` target.
2. Select **Add Files to "FT710Mobile"**.
3. Navigate to `Sources/Audio/`.
4. Select:
   - `OpusBridge.h`
   - `OpusBridge.c`
5. Ensure **"Copy items if needed"** is checked.
6. Click **Add**.

### 3.2 Link libopus
1. Right-click the `FT710Mobile` target → **Build Phases**.
2. Expand **Link Binary With Libraries**.
3. Click **+**.
4. Search for **`libopus`**.
   - If not found automatically, you must add the `.a` or `.framework` file manually.
   - **Option A (Static Library)**: Download `libopus.a` for iOS (arm64 + armv7) and drag it into the list.
   - **Option B (CocoaPods/SPM)**: Add `pod 'libopus'` or use Swift Package Manager.
   - **Option C (Manual)**: If using XcodeGen, update `project.yml` to include `libopus`.

> **Note**: If `libopus` is not linked, the Opus classes will initialize but return `nil` from encode/decode, falling back to PCM (if available).

---

## 4. Build Settings

Ensure the following in **Build Settings**:
- **Objective-C Bridging Header**: Not required (using `.c`/`.h` directly).
- **Compile Sources**: `OpusBridge.c` must be compiled as Objective-C++ if any C++ libs are used, but pure C is fine here. Set **Compiler Language** to **C**.

---

## 5. Testing

1. **RX Audio**: Connect to server. If server sends Opus, `OpusDecoder` should produce PCM data.
2. **TX Audio**: Press PTT. `OpusEncoder` should encode mic data.
3. **Fallback**: If `libopus` fails, logs will show warnings, and audio may drop if PCM is not supported by the server.

---

## 6. Troubleshooting

- **Undefined symbols for architecture arm64**: `libopus` is not linked properly.
- **Opus decode error -1**: Invalid Opus stream or mismatched sample rate.
- **Silence on TX**: Check if `useOpus` is enabled in `AudioCaptureManager`.

---

**Next Steps**: 
1. Link `libopus` in Xcode.
2. Run app and verify audio.
3. Commit changes.
