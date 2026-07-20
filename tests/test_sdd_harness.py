"""
Tests for the SDD-Guardian context harness (.agents/skills/sdd-guardian).

Validates the constraint registry is well-formed, the context map covers the
core modules, and the CLI enforces block-level rules (check + PreToolUse hook
modes). Runs without hardware — the harness is stdlib-only Python.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HARNESS = REPO_ROOT / ".agents" / "skills" / "sdd-guardian" / "harness"
CLI = HARNESS / "sdd_context.py"
REGISTRY = HARNESS / "constraints.json"


def run_cli(*args, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        input=stdin, capture_output=True, text=True, cwd=REPO_ROOT,
    )


class ConstraintRegistryTests(unittest.TestCase):
    """constraints.json must stay well-formed — the hook depends on it."""

    @classmethod
    def setUpClass(cls):
        cls.reg = json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_required_fields_and_unique_ids(self):
        ids = set()
        for rule in self.reg["rules"]:
            for field in ("id", "title", "severity", "sdd_ref", "scope", "message"):
                self.assertIn(field, rule, f"rule missing {field}: {rule.get('id')}")
            self.assertNotIn(rule["id"], ids, f"duplicate rule id {rule['id']}")
            ids.add(rule["id"])

    def test_severities_valid(self):
        for rule in self.reg["rules"]:
            self.assertIn(rule["severity"], ("block", "warn", "info"))

    def test_patterns_compile(self):
        import re
        for rule in self.reg["rules"]:
            for pat in rule.get("patterns", []):
                re.compile(pat)  # raises on invalid regex

    def test_context_map_covers_core_modules(self):
        globs = [g for entry in self.reg["context_map"] for g in entry["globs"]]
        for core in ("server.py", "cat_controller.py", "poll_scheduler.py",
                     "radio_state.py", "config.py", "audio_handler.py"):
            self.assertIn(core, globs, f"context map missing {core}")

    def test_every_rule_has_sdd_traceability(self):
        for rule in self.reg["rules"]:
            ref = rule["sdd_ref"]
            self.assertTrue(
                any(t in ref for t in ("AD-", "§", "Ch", "AGENTS", "V1.", "README")),
                f"{rule['id']} has no SDD trace: {ref!r}",
            )


class HarnessCliTests(unittest.TestCase):
    """CLI behavior: context lookup, check enforcement, hook blocking."""

    def test_prime_prints_golden_rules(self):
        r = run_cli("prime")
        self.assertEqual(r.returncode, 0)
        self.assertIn("GOLDEN RULES", r.stdout)
        self.assertIn("cat-no-dn", r.stdout)

    def test_context_for_server_py(self):
        r = run_cli("context", "server.py")
        self.assertEqual(r.returncode, 0)
        self.assertIn("AD-001", r.stdout)
        self.assertIn("ws-endpoint-auth", r.stdout)

    def test_context_for_cat_controller(self):
        r = run_cli("context", "cat_controller.py")
        self.assertIn("AD-014", r.stdout)
        self.assertIn("cat-sh-format", r.stdout)

    def test_check_blocks_dn_command(self):
        with tempfile_named("query(ser, \"DN\")\n") as p:
            r = run_cli("check", p)
        self.assertEqual(r.returncode, 2)
        self.assertIn("cat-no-dn", r.stderr)

    def test_check_blocks_sh0nn_format(self):
        with tempfile_named('cmd = f"SH0{idx:02d}"\n') as p:
            r = run_cli("check", p)
        self.assertEqual(r.returncode, 2)
        self.assertIn("cat-sh-format", r.stderr)

    def test_check_passes_clean_code(self):
        with tempfile_named('cmd = f"SH00{idx:02d}"\nawait cat.set(cmd)\n') as p:
            r = run_cli("check", p)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("clean", r.stdout)

    def test_hook_blocks_dn_edit(self):
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Edit",
            "tool_input": {
                "path": str(REPO_ROOT / "cat_controller.py"),
                "new_string": 'resp = await self.query("DN", timeout=timeout)',
            },
        }
        r = run_cli("hook", stdin=json.dumps(payload))
        self.assertEqual(r.returncode, 2)
        self.assertIn("cat-no-dn", r.stderr)

    def test_hook_allows_clean_edit(self):
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Edit",
            "tool_input": {
                "path": str(REPO_ROOT / "cat_controller.py"),
                "new_string": 'cmd = f"SH00{index:02d}"',
            },
        }
        r = run_cli("hook", stdin=json.dumps(payload))
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_hook_fail_open_on_garbage_stdin(self):
        r = run_cli("hook", stdin="not json")
        self.assertEqual(r.returncode, 0)

    def test_repo_core_files_are_clean(self):
        """The harness must not cry wolf: shipped core modules pass block rules."""
        core = ["server.py", "cat_controller.py", "poll_scheduler.py",
                "radio_state.py", "config.py", "audio_handler.py",
                "audio_resample.py", "opus_rx.py"]
        r = run_cli("check", *core)
        self.assertEqual(r.returncode, 0,
                         f"core files trip block rules:\n{r.stderr}")


from contextlib import contextmanager

@contextmanager
def tempfile_named(content: str):
    """Write content to a temp .py file inside the repo (glob scope applies)."""
    p = REPO_ROOT / "_sdd_harness_test_tmp.py"
    try:
        p.write_text(content, encoding="utf-8")
        yield str(p)
    finally:
        p.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
