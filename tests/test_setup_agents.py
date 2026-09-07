import contextlib
import datetime
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("setup_agents", ROOT / "script/setup-agents.py")
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory(prefix=".agent-test-", dir=ROOT)
        self.addCleanup(self.workspace.cleanup)
        self.target = Path(self.workspace.name) / "target"
        self.target.mkdir()

    def install(self, tool):
        with contextlib.redirect_stdout(io.StringIO()):
            setup.install(tool, self.target)

    def test_codex_preserves_customization_and_repeat_install_is_unchanged(self):
        config = self.target / "config.toml"
        config.write_text('model = "chosen-model"\ndeveloper_instructions = "Keep my convention."\n'
                          '[mcp_servers.local]\ncommand = "my-server"\n'
                          '[execpolicy]\nuser_rules = ["~/.codex/execpolicy/default.rules"]\n'
                          '[features]\nexec_permission_approvals = true\n')
        for relative in ("skills/personal/SKILL.md", "agents/personal.toml", "rules/default.rules"):
            path = self.target / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("personal content")
        (self.target / "AGENTS.md").write_text("My own instructions.\n")
        self.install("codex")
        data = tomllib.loads(config.read_text())
        self.assertEqual(data["model"], "chosen-model")
        self.assertEqual(data["mcp_servers"]["local"]["command"], "my-server")
        self.assertIn("Keep my convention.", data["developer_instructions"])
        self.assertNotIn("execpolicy", data)
        self.assertNotIn("features", data)
        self.assertIn("My own instructions.", (self.target / "AGENTS.md").read_text())
        for relative in ("skills/personal/SKILL.md", "agents/personal.toml", "rules/default.rules"):
            self.assertEqual((self.target / relative).read_text(), "personal content")
        for path in (self.target / "agents").glob("*.toml"):
            if path.name != "personal.toml":
                agent = tomllib.loads(path.read_text())
                self.assertTrue(all(agent[key] for key in ("name", "description", "developer_instructions")))
        before = {p.relative_to(self.target): p.read_bytes() for p in self.target.rglob("*") if p.is_file()}
        self.install("codex")
        after = {p.relative_to(self.target): p.read_bytes() for p in self.target.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertTrue(list(self.target.glob("config.toml.bak.*")))

    def test_claude_merges_permissions_and_preserves_hooks(self):
        original = {"permissions": {"allow": ["Bash(my-test)"], "deny": ["Read(private/**)"]},
                    "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "my-hook"}]}]}}
        config = self.target / "settings.json"
        config.write_text(json.dumps(original))
        self.install("claude")
        data = json.loads(config.read_text())
        self.assertEqual(data["hooks"], original["hooks"])
        self.assertIn("Bash(my-test)", data["permissions"]["allow"])
        self.assertIn("Read(private/**)", data["permissions"]["deny"])
        self.assertIn("Read(//**/.env)", data["permissions"]["deny"])
        before = config.read_bytes()
        self.install("claude")
        self.assertEqual(config.read_bytes(), before)
        self.assertEqual(len(list(self.target.glob("settings.json.bak.*"))), 1)

    def test_malformed_settings_fail_before_writes(self):
        config = self.target / "settings.json"
        config.write_text("invalid json")
        with self.assertRaises(ValueError):
            self.install("claude")
        self.assertEqual(list(self.target.iterdir()), [config])
        self.assertEqual(config.read_text(), "invalid json")

    def test_symlinked_destination_is_rejected_before_writes(self):
        outside = Path(self.workspace.name) / "elsewhere"
        outside.mkdir()
        (self.target / "agents").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.install("codex")
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse((self.target / "config.toml").exists())

    def test_toml_round_trip_preserves_nested_types(self):
        data = {"quoted.key": {"text": 'line one\n"line two"\\path',
                               "nested": [{"a": True}, {"b": [1, 2.5]}]},
                "date": datetime.date(2026, 9, 6), "time": datetime.time(12, 30),
                "timestamp": datetime.datetime(2026, 9, 6, tzinfo=datetime.timezone.utc)}
        self.assertEqual(tomllib.loads(setup.toml_text(data)), data)

    def test_instruction_update_preserves_surrounding_content(self):
        original = f"Personal prefix\n{setup.BEGIN}\nOld managed text\n{setup.END}\nPersonal suffix\n"
        updated = setup.instructions(original, "New managed text")
        self.assertIn("Personal prefix", updated)
        self.assertIn("Personal suffix", updated)
        self.assertNotIn("Old managed text", updated)
        self.assertEqual(setup.instructions(updated, "New managed text"), updated)

    @unittest.skipIf(os.geteuid() == 0, "User installers deliberately refuse root")
    def test_shell_entrypoints_install_into_explicit_destinations(self):
        for tool, filename in (("codex", "config.toml"), ("claude", "settings.json")):
            destination = self.target / tool
            result = subprocess.run(
                ["bash", str(ROOT / f"setup-{tool}.sh"), "--target-dir", str(destination)],
                capture_output=True, text=True, cwd=ROOT,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((destination / filename).is_file())


if __name__ == "__main__":
    unittest.main()
