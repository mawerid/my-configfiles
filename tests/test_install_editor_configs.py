import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("nvim"), "Neovim is not installed")
class EditorConfigInstallerTests(unittest.TestCase):
    def test_zsh_backup_and_editor_state_survive_reinstall(self):
        with tempfile.TemporaryDirectory(prefix=".editor-test-", dir=ROOT) as workspace:
            workspace = Path(workspace)
            env = dict(
                os.environ,
                XDG_CONFIG_HOME=str(workspace / "config"),
                NVIM_APPNAME="editor-review",
                NVIM_LOG_FILE=str(workspace / "nvim.log"),
            )
            tmux = workspace / ".tmux.conf"
            personal_tmux = workspace / "personal.conf"
            personal_tmux.write_text("personal tmux config")
            tmux.symlink_to(personal_tmux)
            zsh = workspace / ".zshrc"
            personal_zsh = workspace / "personal.zsh"
            personal_zsh.write_text("personal zsh config")
            zsh.symlink_to(personal_zsh)
            nvim = workspace / "config/editor-review"
            nvim.mkdir(parents=True)
            personal_nvim = workspace / "personal-init.lua"
            personal_nvim.write_text("-- personal config")
            (nvim / "init.lua").symlink_to(personal_nvim)
            state = {
                "lazy-lock.json": '{"existing":{"commit":"revision"}}',
                "lazyvim.json": '{"extras":["example"]}',
                "personal.lua": "-- personal user file",
            }
            for name, contents in state.items():
                (nvim / name).write_text(contents)

            command = [
                sys.executable,
                str(ROOT / "script/install-editor-configs.py"),
                str(tmux),
                str(zsh),
            ]
            subprocess.run(command, env=env, check=True, capture_output=True)
            self.assertEqual(personal_tmux.read_text(), "personal tmux config")
            self.assertEqual(
                tmux.read_bytes(), (ROOT / "config/tmux/.tmux.conf").read_bytes()
            )
            self.assertFalse(tmux.is_symlink())
            self.assertEqual(personal_zsh.read_text(), "personal zsh config")
            self.assertEqual(
                zsh.read_bytes(), (ROOT / "config/zsh/.zshrc").read_bytes()
            )
            (zsh_backup,) = workspace.glob(".zshrc.bak.*")
            self.assertEqual((zsh_backup / zsh.name).readlink(), personal_zsh)
            self.assertEqual(
                (nvim / "init.lua").read_bytes(),
                (ROOT / "config/nvim/init.lua").read_bytes(),
            )
            self.assertEqual(personal_nvim.read_text(), "-- personal config")
            self.assertFalse((nvim / "init.lua").is_symlink())
            for name, contents in state.items():
                self.assertEqual((nvim / name).read_text(), contents)

            subprocess.run(command, env=env, check=True, capture_output=True)
            self.assertEqual(list(workspace.glob("*.bak.*")), [zsh_backup])
            self.assertFalse(list(nvim.parent.glob("editor-review.bak.*")))
