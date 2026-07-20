# Lifecycle Checklists — mrrc_ft710

Phase-by-phase checklists referenced from `SKILL.md`. Tick every item or
consciously justify skipping it.

## 0. Context

- [ ] Ran `sdd_context.py context <paths>` for every file I expect to touch
- [ ] Ran `sdd_context.py context --task "<description>"` for topical rules
- [ ] Read the SDD chapters the harness pointed at (non-trivial changes)

## 1. Design

- [ ] Identified affected ADs (AD-001…AD-015); contradictions get an AD amendment in the same change
- [ ] Checked open issues I6/I7 don't undermine the design
- [ ] PTT/TX-adjacent work reviewed against Chapter 15 layered release model
- [ ] Non-trivial work went through plan mode with concrete file/step lists

## 2. Implementation

- [ ] No block-level constraint violations (golden rules in SKILL.md Phase 2)
- [ ] Set handlers: `skip_next_poll` BEFORE the CAT write; `radio.update` after
- [ ] Poll-side changes keep the post-await stale-read guard and 0.25 s timeouts
- [ ] Minimal diff; module conventions matched; no drive-by refactors

## 3. Test

- [ ] `venv/bin/python -m unittest discover -s tests` passes
- [ ] Regression test added for the bug / coverage for new logic
- [ ] Tests are hardware-free (mocked serial/audio/scope boundaries)
- [ ] `tests/README.md` counts updated

## 4. Harness verify

- [ ] `sdd_context.py check --staged` → clean (or warnings justified in commit/PR text)

## 5. Documentation sync

- [ ] Affected SDD chapters updated (see trigger table in SKILL.md Phase 5)
- [ ] `SDD/14-version-history.md` new entry (behavior changes)
- [ ] `SDD/README.md` Quick Facts version bumped
- [ ] `AGENTS.md` module table / conventions current
- [ ] `README.md` user-visible behavior current

## 6. Commit

- [ ] Short imperative summary; one logical change per commit
- [ ] User asked for the git mutation (never commit unprompted)
- [ ] Hardware-dependent changes document the verification environment
