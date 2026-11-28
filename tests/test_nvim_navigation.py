import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("nvim"), "nvim is not installed")
class NvimNavigationTests(unittest.TestCase):
    def test_edge_handoff_to_tmux_and_herdr(self):
        with tempfile.TemporaryDirectory() as home:
            env = {
                **os.environ,
                **{
                    k: home
                    for k in ("XDG_STATE_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME")
                },
                "NVIM_LOG_FILE": os.path.join(home, "nvim.log"),
            }
            result = subprocess.run(
                [
                    "nvim",
                    "--headless",
                    "--clean",
                    "-l",
                    str(ROOT / "tests/nvim_navigation.lua"),
                    str(ROOT / "config/nvim/lua/config/keymaps.lua"),
                ],
                cwd=home,
                capture_output=True,
                text=True,
                env=env,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("navigation self-check passed", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
