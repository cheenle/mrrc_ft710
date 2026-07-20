---
name: sdd-guardian
description: SDD-driven software-engineering lifecycle guardrails for the mrrc_ft710 FT-710 web-control codebase — enforces SDD architecture decisions, CAT/audio/polling constraints, testing and documentation sync on every code change
type: prompt
whenToUse: When creating, modifying, reviewing, or debugging code in this repository; when planning features or refactors; when the change touches CAT commands, audio, polling, PTT, state, WebSocket protocol, or frontend UI
arguments:
  - task
---

# SDD Guardian — engineering lifecycle for mrrc_ft710

This repository is governed by `SDD/` (IBM TeamSD, 15 chapters, currently **V1.7**).
The SDD is the canonical design record: your job on every change is to keep the
runtime AND the design record consistent. This skill is the enforcement loop;
`${KIMI_SKILL_DIR}/harness/` is the machine-readable backing (constraints.json +
sdd_context.py CLI). ${ARGUMENTS:+Task focus: $ARGUMENTS}

## Phase 0 — Load context (always, before touching code)

```bash
python3 ${KIMI_SKILL_DIR}/harness/sdd_context.py context <files-you-will-touch>
python3 ${KIMI_SKILL_DIR}/harness/sdd_context.py context --task "<one-line task description>"
```

This prints the SDD sections, architecture decisions (AD-001…AD-015), and the
block/warn/info constraints that apply to those files. For anything beyond a
trivial fix, also read the referenced SDD chapter.

## Phase 1 — Design check

- Which ADs does this change touch? Are you about to contradict one? If yes,
  the AD must be amended in `SDD/08` in the same change — never silently.
- Known open issues (SDD §13.4): **I6** no multi-client control arbitration
  (last-writer-wins), **I7** `mem_channels.json` POST has no schema
  validation/backup. Don't design features that assume either is solved.
- Safety review for anything touching PTT/TX: Chapter 15's layered release
  model is load-bearing. TX0 is fire-and-forget; never re-add blocking
  post-release verify loops (removed in V1.2, cost 600 ms).

## Phase 2 — Implement under constraint

Golden rules (block-level; the PreToolUse hook rejects these edits):

- `DN;` is VFO step-DOWN on the FT-710, not DNR — never send or poll it (AD-014).
- Compressor is `PR00`/`PR01` (Yaesu PDF 1/2 mapping is errata; PR02 kills TX audio).
- Tuner mapping is `AC000/AC001/AC003` — deliberately not Hamlib `AC010/AC011`.
- Filter width SET is `SH00NN`; set handlers read `SH0;` back ~150 ms later and
  broadcast the radio's actual index (V1.7).
- Serial I/O only inside `CatController` (`_lock` + `asyncio.to_thread` + 20 ms pacing).
- Audio: 48 kHz codec domain ↔ 44.1 kHz device domain; the ONLY SRC is
  `audio_resample.py` (960↔882). 16 kHz anywhere = the V1.1 crackling bug.
- No inline JS in `index.html`; UI logic in `ft710_ui.js` or `static/modules/`.
- No hardcoded secrets, serial paths, or device assumptions — env vars only.

Warn-level: mutate state via `radio.update(...)` (dirty-field broadcast, AD-003);
new WS endpoints need `?token=` auth; poll loops re-check `_should_skip` /
`_polling_paused()` AFTER every query await (V1.7 stale-read race), and set
handlers call `skip_next_poll` BEFORE the CAT write.

Minimal diffs. Match the module's existing conventions (AGENTS.md style section).

## Phase 3 — Test

```bash
venv/bin/python -m unittest discover -s tests
```

- Every bug fix gets a regression test; every feature gets coverage if the
  logic is hardware-independent (mock at the serial/audio boundary).
- Sync `tests/README.md` module/test counts when tests change.

## Phase 4 — Verify against the harness

```bash
python3 ${KIMI_SKILL_DIR}/harness/sdd_context.py check --staged
```

Must print `clean` (or warnings you can justify) before committing.

## Phase 5 — Documentation sync (part of the change, not an afterthought)

| If you changed… | Then also update |
|---|---|
| CAT command behavior/format | SDD §10.4 table, `FT-710_CAT_Knowledge_Base.md` |
| Polling tasks/intervals/guards | SDD §9.6, AD-009, README polling table |
| Audio rates/codecs/pipeline | SDD §9.3/§9.4, AD-004/AD-011, AGENTS.md module table |
| State fields / WS protocol | SDD §7.2/§9.2/§9.7, README WS section |
| Architecture approach | SDD/08 (new or amended AD) |
| Module responsibilities | AGENTS.md module table |
| Test modules/counts | tests/README.md |
| ANY behavior change | SDD/14-version-history.md new entry + SDD/README Quick Facts version bump |

If the SDD contradicts the runtime you just verified, the SDD is wrong — fix it
in the same commit and say so in the version-history entry.

## Phase 6 — Commit

Short imperative summary, scoped commits (one logical change per commit).
Git mutations only when the user asks. Hardware-dependent changes note the
test environment (radio model, serial port, FT4222, audio device).

## Harness reference

```
sdd_context.py prime                    # session-start digest (SessionStart hook)
sdd_context.py context <paths> [--task] # SDD refs + constraints for files/topics
sdd_context.py check <paths>|--staged   # pattern scan; exit 2 on block violations
sdd_context.py hook                     # PreToolUse mode (stdin JSON), exit 2 blocks
```

Optional automatic enforcement (recommended): install the hooks from
`${KIMI_SKILL_DIR}/harness/hooks.snippet.toml` into `~/.kimi-code/config.toml`
(`python3 ${KIMI_SKILL_DIR}/harness/install_hooks.py` does it idempotently).
That injects `prime` at every session start and runs `hook` before every
Edit/Write so block-level violations are rejected automatically.

Deep reference: `${KIMI_SKILL_DIR}/references/constraint-catalog.md` (full rule
catalog with rationale) and `${KIMI_SKILL_DIR}/references/lifecycle.md`
(phase checklists). Source of truth when they disagree: `SDD/` itself.
