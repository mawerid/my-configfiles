import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "setup_herdr", ROOT / "script/setup-herdr.py"
)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class HerdrInstallerTests(unittest.TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory(prefix=".herdr-test-", dir=ROOT)
        self.addCleanup(workspace.cleanup)
        self.root = Path(workspace.name)
        self.target = self.root / "herdr"
        self.target.mkdir()

    def install(self):
        with contextlib.redirect_stdout(io.StringIO()):
            installer.install(self.target)

    def test_uses_current_main_layout_and_backs_up_only_changed_files(self):
        self.install()
        layouts = self.target / "layouts"
        self.assertFalse(layouts.exists())
        layouts.mkdir()
        main = layouts / "main.json"
        source = {
            "id": "root",
            "type": "row",
            "children": [
                {"id": "files", "type": "block", "content": {"mod": "files"}},
                {"id": "extra", "type": "block", "content": {"mod": "changes"}},
            ],
        }
        main.write_text(json.dumps(source))
        self.install()
        preview = layouts / "files-preview.json"
        generated = json.loads(preview.read_text())
        self.assertEqual(json.loads(main.read_text()), source)
        self.assertEqual(generated["children"][0]["content"]["mod"], "files-preview")
        self.assertEqual(generated["children"][1], source["children"][1])
        self.assertFalse((self.target / ".setup-backups").exists())

        preview.write_text("{}")
        self.install()
        (backup,) = (self.target / ".setup-backups").glob(
            "*/layouts/files-preview.json"
        )
        self.assertEqual(backup.read_text(), "{}")
        inode = preview.stat().st_ino
        self.install()
        self.assertEqual(preview.stat().st_ino, inode)

    def test_refuses_symlinked_backup_directory_before_replacement(self):
        personal = self.root / "personal"
        personal.mkdir()
        (self.target / ".setup-backups").symlink_to(personal)
        settings = self.target / "settings.json"
        settings.write_text('{"zoom": 2}')

        with self.assertRaisesRegex(ValueError, "Invalid backup directory"):
            self.install()

        self.assertEqual(settings.read_text(), '{"zoom": 2}')
        self.assertFalse((self.target / "mods").exists())
        self.assertEqual(list(personal.iterdir()), [])
