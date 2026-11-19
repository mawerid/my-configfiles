import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "setup_agents", ROOT / "script/setup-agents.py"
)
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

    def test_shared_skills_and_repeat_install(self):
        for tool in ("codex", "claude"):
            target = self.target / tool
            personal = target / "skills/personal"
            personal.mkdir(parents=True)
            setup.install(tool, target)
            skill = target / "skills/handoff"
            self.assertTrue(skill.samefile(ROOT / "agents/skills/handoff"))
            inode = skill.lstat().st_ino
            setup.install(tool, target)
            self.assertEqual(skill.lstat().st_ino, inode)
            self.assertTrue(personal.is_dir())

    def test_default_skill_discovery_for_both_tools(self):
        names = set(
            "idea plan work retire-plan close-cycle next handoff wait-what retro "
            "refactor-review create-mr review-mr respond-mr approve-mr release".split()
        )
        for tool in ("codex", "claude"):
            config = self.target / f".{tool}"
            folder = (self.target / ".agents" if tool == "codex" else config) / "skills"
            env = dict(os.environ, HOME=str(self.target))
            env.pop("CODEX_HOME", None)
            env.pop("CLAUDE_CONFIG_DIR", None)
            subprocess.run(
                ["bash", str(ROOT / f"setup-{tool}.sh")],
                env=env,
                check=True,
                capture_output=True,
            )
            for name in names:
                self.assertTrue(
                    (folder / name / "SKILL.md").samefile(
                        ROOT / "agents/skills" / name / "SKILL.md"
                    )
                )
            for resource in (
                "work/tiers.md",
                "create-mr/mr_workflow.py",
                "create-mr/mr-workflow.md",
                "retro/session-digest",
                "refactor-review/scripts/duplicates.py",
            ):
                self.assertTrue((folder / resource).is_file())
            if tool == "claude":
                settings = json.loads((config / "settings.json").read_text())
                self.assertTrue(
                    all(settings["skillOverrides"][name] == "on" for name in names)
                )

    def test_replaces_settings_and_dangling_link_with_backups(self):
        config = self.target / "settings.json"
        config.write_text('{"hooks": {}}')
        instructions = self.target / "CLAUDE.md"
        instructions.symlink_to("missing")
        self.install("claude")
        self.assertTrue(config.samefile(ROOT / "agents/claude/settings.json"))
        self.assertTrue(instructions.samefile(ROOT / "agents/AGENTS.md"))
        (backup,) = self.target.glob(".settings.json.bak.*")
        self.assertEqual(backup.read_text(), '{"hooks": {}}')
        (backup,) = self.target.glob(".CLAUDE.md.bak.*")
        self.assertEqual(backup.readlink(), Path("missing"))

    def test_upgrade_managed_directory(self):
        skill = self.target / "skills/debug"
        shutil.copytree(ROOT / "agents/skills/debug", skill)
        self.install("codex")
        self.assertTrue(skill.is_symlink())
        self.assertTrue(list(skill.parent.glob(".debug.bak.*")))

    def test_moves_legacy_copies_aside(self):
        legacy_skill = self.target / "skills/debug"
        shutil.copytree(ROOT / "agents/skills/debug", legacy_skill)
        personal = self.target / "skills/personal"
        personal.mkdir()
        with contextlib.redirect_stdout(io.StringIO()):
            setup.install(
                "codex", self.target, skills_dir=self.target / "shared-skills"
            )
        self.assertFalse(os.path.lexists(legacy_skill))
        self.assertTrue(list(legacy_skill.parent.glob(".debug.bak.*")))
        self.assertTrue(personal.is_dir())
        manifest = self.target / "repo-managed-permissions.json"
        manifest.write_text("{}")
        self.install("claude")
        self.assertFalse(manifest.exists())
        self.assertTrue(list(self.target.glob(".repo-managed-permissions.json.bak.*")))

    def test_managed_settings_are_private(self):
        for tool, filename in (("codex", "config.toml"), ("claude", "settings.json")):
            self.install(tool)
            mode = (ROOT / "agents" / tool / filename).stat().st_mode & 0o777
            self.assertEqual(mode, 0o600)

    @unittest.skipUnless(shutil.which("codex"), "Codex CLI is not installed")
    def test_codex_cli_loads_installed_configuration(self):
        self.install("codex")
        result = subprocess.run(
            ["codex", "features", "list"],
            env=dict(os.environ, CODEX_HOME=str(self.target)),
            capture_output=True,
            text=True,
            cwd=self.target,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(shutil.which("codex"), "Codex CLI is not installed")
    def test_codex_cli_enforces_installed_command_rules(self):
        self.install("codex")
        cases = [
            (["git", "status", "--short"], "allow"),
            (["git", "diff", "--stat"], "allow"),
            (["git", "push", "origin", "main"], "prompt"),
            (["git", "commit", "-m", "message"], "prompt"),
            (["rm", "example"], "forbidden"),
            (["ssh", "example.invalid"], "forbidden"),
            (["scp", "example", "example.invalid:path"], "forbidden"),
        ]
        for command, expected in cases:
            with self.subTest(command=command):
                result = subprocess.run(
                    [
                        "codex",
                        "execpolicy",
                        "check",
                        "--rules",
                        str(self.target / "rules/repo-default.rules"),
                        "--",
                        *command,
                    ],
                    env=dict(os.environ, CODEX_HOME=str(self.target)),
                    capture_output=True,
                    text=True,
                    cwd=self.target,
                    timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["decision"], expected)

    @unittest.skipIf(os.geteuid() == 0, "User installers deliberately refuse root")
    def test_shell_entrypoints_install_into_explicit_destinations(self):
        for tool, filename in (("codex", "config.toml"), ("claude", "settings.json")):
            destination = self.target / tool
            result = subprocess.run(
                [
                    "bash",
                    str(ROOT / f"setup-{tool}.sh"),
                    "--target-dir",
                    str(destination),
                ],
                capture_output=True,
                text=True,
                cwd=ROOT,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((destination / filename).is_file())


if __name__ == "__main__":
    unittest.main()
