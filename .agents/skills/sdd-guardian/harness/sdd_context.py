#!/usr/bin/env python3
"""SDD context harness for the mrrc_ft710 codebase.

Reads harness/constraints.json (machine-readable registry distilled from
SDD/ + AGENTS.md) and provides four commands:

  prime                          Compact session-start digest (golden rules).
  context [PATHS...] [--task T]  SDD refs + applicable constraints for files/topics.
  check [PATHS...] [--staged]    Pattern-scan content; exit 2 if any block-severity hit.
  hook                           PreToolUse hook mode: read event JSON on stdin,
                                 inspect the pending Edit/Write, exit 2 + reason on block.

Stdlib only — hook latency budget is ~5 s including interpreter startup.
"""
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

HARNESS_DIR = Path(__file__).resolve().parent
REGISTRY_PATH = HARNESS_DIR / "constraints.json"
PROJECT_ROOT = HARNESS_DIR.parents[3]


def load_registry() -> dict:
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        return json.load(f)


def norm(path: str) -> str:
    """Normalise a path to project-relative POSIX form for glob matching."""
    p = str(path).replace("\\", "/")
    try:
        p = str(Path(p).resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    except (ValueError, OSError):
        pass
    return p.lstrip("./")


def glob_match(path: str, pattern: str) -> bool:
    """fnmatch with pragmatic '**' handling: 'a/**/b' also matches 'a/b'."""
    if fnmatch.fnmatch(path, pattern):
        return True
    if "**/" in pattern and fnmatch.fnmatch(path, pattern.replace("**/", "")):
        return True
    return False


def matches_any(path: str, patterns: list[str]) -> bool:
    return any(glob_match(path, g) for g in patterns)


def applicable_rules(reg: dict, path: str | None) -> list[dict]:
    """Rules whose scope matches path (path=None → all rules apply)."""
    out = []
    for rule in reg["rules"]:
        if path is not None:
            if rule["scope"] and not matches_any(path, rule["scope"]):
                continue
            if rule.get("exclude_scope") and matches_any(path, rule["exclude_scope"]):
                continue
        out.append(rule)
    return out


def _strip_comment(path: str | None, line: str) -> str:
    """Remove trailing comments so pattern rules don't fire on prose.

    Naive split (strings containing the comment marker can over-strip) —
    acceptable for a lint harness: patterns never match inside comments,
    and a violation hidden by over-stripping is caught at review.
    """
    if path and path.endswith(".py"):
        return line.split("#", 1)[0]
    if path and path.endswith((".js", ".css")):
        return line.split("//", 1)[0]
    return line


def scan_text(reg: dict, path: str | None, text: str) -> list[dict]:
    """Run block/warn pattern rules against text; return violation dicts."""
    violations = []
    rules = applicable_rules(reg, path)
    lines = text.splitlines()
    for rule in rules:
        if rule["severity"] not in ("block", "warn"):
            continue
        for pat in rule.get("patterns", []):
            rx = re.compile(pat)
            for lineno, line in enumerate(lines, 1):
                if rx.search(_strip_comment(path, line)):
                    violations.append({
                        "id": rule["id"],
                        "severity": rule["severity"],
                        "message": rule["message"],
                        "sdd_ref": rule["sdd_ref"],
                        "path": path or "<content>",
                        "line": lineno,
                        "text": line.strip()[:160],
                    })
    return violations


def print_violations(violations: list[dict], stream) -> None:
    for v in violations:
        print(
            f"[{v['severity'].upper()}] {v['id']} ({v['sdd_ref']}) "
            f"{v['path']}:{v['line']}: {v['text']}\n    → {v['message']}",
            file=stream,
        )


# ── Commands ────────────────────────────────────────────────────────

def cmd_prime(reg: dict) -> int:
    blocks = [r for r in reg["rules"] if r["severity"] == "block"]
    print("═══ SDD-GUARDIAN — mrrc_ft710 design harness (SDD " + reg["sdd_version"] + ") ═══")
    print("This repo is documented by SDD/ (IBM TeamSD, 15 chapters). Before changing")
    print("code, load constraints for the files you touch:")
    print("  python3 .agents/skills/sdd-guardian/harness/sdd_context.py context <paths>")
    print("Validate a change before committing:")
    print("  python3 .agents/skills/sdd-guardian/harness/sdd_context.py check --staged")
    print("")
    print("GOLDEN RULES (block-level, SDD-enforced):")
    for r in blocks:
        print(f"  ✗ {r['id']}: {r['title']}  [{r['sdd_ref']}]")
    print("")
    print("Lifecycle: context → design (check ADs/open issues I6,I7) → implement")
    print("(minimal diffs, module conventions) → test (unittest, no hardware, sync")
    print("tests/README) → doc-sync (SDD chapters + 14-version-history + AGENTS.md")
    print("+ README) → commit (imperative, scoped, ask before git mutations).")
    return 0


def cmd_context(reg: dict, paths: list[str], task: str | None) -> int:
    seen_maps: set[int] = set()
    for raw in paths:
        p = norm(raw)
        print(f"── {p} ──")
        matched = False
        for i, entry in enumerate(reg["context_map"]):
            if matches_any(p, entry["globs"]) and i not in seen_maps:
                seen_maps.add(i)
                matched = True
                print("  SDD: " + ", ".join(entry["sdd_refs"]))
                print("  " + entry["notes"])
        rules = [r for r in applicable_rules(reg, p) if r["severity"] != "info" or r["patterns"] == []]
        if rules:
            print("  Constraints:")
            for r in rules:
                tag = {"block": "✗", "warn": "!", "info": "i"}[r["severity"]]
                print(f"    {tag} [{r['severity']}] {r['id']}: {r['message']}")
        if not matched and not rules:
            print("  (no specific SDD mapping — general conventions apply)")
        print("")
    if task:
        kws = {w.lower() for w in re.findall(r"[A-Za-z0-9_\-]{4,}", task)}
        hits = []
        for r in reg["rules"]:
            hay = f"{r['id']} {r['title']} {r['message']}".lower()
            if kws & set(re.findall(r"[a-z0-9_\-]{4,}", hay)):
                hits.append(r)
        if hits:
            print(f"── constraints relevant to: {task!r} ──")
            for r in hits:
                tag = {"block": "✗", "warn": "!", "info": "i"}[r["severity"]]
                print(f"  {tag} [{r['severity']}] {r['id']} ({r['sdd_ref']}): {r['message']}")
    return 0


def cmd_check(reg: dict, paths: list[str], staged: bool) -> int:
    violations: list[dict] = []
    if staged:
        diff = subprocess.run(
            ["git", "diff", "--cached", "-U0", "--no-color"],
            capture_output=True, text=True, cwd=PROJECT_ROOT,
        ).stdout
        cur = None
        for line in diff.splitlines():
            if line.startswith("+++ b/"):
                cur = line[6:]
            elif line.startswith("+") and not line.startswith("+++"):
                violations.extend(scan_text(reg, cur, line[1:]))
    else:
        if not paths:
            print("usage: check <paths...> | --staged", file=sys.stderr)
            return 1
        for raw in paths:
            p = Path(raw)
            if not p.is_file():
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            violations.extend(scan_text(reg, norm(str(p)), text))
    blocks = [v for v in violations if v["severity"] == "block"]
    warns = [v for v in violations if v["severity"] == "warn"]
    if blocks:
        print("SDD-GUARDIAN: blocking violations found:", file=sys.stderr)
        print_violations(blocks, sys.stderr)
    if warns:
        print("SDD-GUARDIAN: warnings:")
        print_violations(warns, sys.stdout)
    if not violations:
        print("SDD-GUARDIAN: clean — no constraint violations.")
    return 2 if blocks else 0


def cmd_hook(reg: dict) -> int:
    """PreToolUse mode: inspect the pending edit; block on violations."""
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # fail-open
    tool = payload.get("tool_name", "")
    ti = payload.get("tool_input", {}) or {}
    path = ti.get("path") or ti.get("file_path")
    content = ti.get("content") if tool == "Write" else ti.get("new_string")
    if content is None and tool == "Bash":
        return 0  # shell commands are out of scope for source-pattern rules
    if content is None:
        return 0
    rel = norm(path) if path else None
    violations = scan_text(reg, rel, content)
    blocks = [v for v in violations if v["severity"] == "block"]
    warns = [v for v in violations if v["severity"] == "warn"]
    if blocks:
        print("SDD-GUARDIAN blocked this edit:", file=sys.stderr)
        print_violations(blocks, sys.stderr)
        return 2
    if warns:
        print("SDD-GUARDIAN warnings (allowed):")
        print_violations(warns, sys.stdout)
    return 0


def main(argv: list[str]) -> int:
    reg = load_registry()
    args = argv[1:]
    if not args:
        print(__doc__)
        return 1
    cmd, rest = args[0], args[1:]
    if cmd == "prime":
        return cmd_prime(reg)
    if cmd == "context":
        task = None
        if "--task" in rest:
            i = rest.index("--task")
            task = " ".join(rest[i + 1:])
            rest = rest[:i]
        return cmd_context(reg, rest, task)
    if cmd == "check":
        staged = "--staged" in rest
        return cmd_check(reg, [a for a in rest if not a.startswith("--")], staged)
    if cmd == "hook":
        return cmd_hook(reg)
    print(f"unknown command: {cmd}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
