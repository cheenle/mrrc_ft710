# iOS App Fixes Progress Report

**Date**: 2026-07-14  
**Status**: In Progress

---

## Completed Fixes

### 1. PTT Button Unification ✅
- **File**: `ContentView.swift`
- **Action**: Removed redundant `PTTButtonView` logic, unified on `PTTBar`.
- **Result**: Single PTT interface, no duplication.

### 2. Opus Codec Bridge Implementation ✅
- **Files**: 
  - `OpusBridge.h` (New)
  - `OpusBridge.c` (New)
  - `OpusDecoder.swift` (Updated)
  - `OpusEncoder.swift` (Updated)
- **Action**: Created C-bridge wrapper for `libopus`.
- **Result**: iOS app can now encode/decode Opus if `libopus` is linked.

---

## Pending Fixes

### 1. Link libopus in Xcode ⏳
- **Action**: Developer must add `libopus` to Xcode project.
- **Priority**: P0 (Required for Opus to work).

### 2. Audio Session Unification ⏳
- **Action**: Update `AudioPlaybackManager` and `AudioCaptureManager` to use `.playAndRecord` consistently.
- **Priority**: P1.

### 3. Error Handling Improvements ⏳
- **Action**: Add user-facing error alerts for connection/audio failures.
- **Priority**: P1.

### 4. Unit Tests ⏳
- **Action**: Write tests for `OpusDecoder`, `OpusEncoder`, `RadioState`.
- **Priority**: P2.

---

## Next Steps

1. **Developer**: Link `libopus` in Xcode.
2. **Test**: Verify RX/TX audio with Opus.
3. **Iterate**: Fix any audio glitches.

---

**Analyst**: Agnes Code Review
