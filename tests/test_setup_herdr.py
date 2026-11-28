import base64
import contextlib
import hashlib
import importlib.util
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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
                {
                    "id": "sidebar",
                    "type": "column",
                    "children": [
                        {"id": "spaces", "type": "block", "content": {"mod": "spaces"}},
                        {"id": "agents", "type": "block", "content": {"mod": "agents"}},
                    ],
                },
            ],
        }
        main.write_text(json.dumps(source))
        self.install()
        preview = layouts / "files-preview.json"
        generated = json.loads(preview.read_text())
        self.assertEqual(json.loads(main.read_text()), source)
        self.assertEqual(generated["children"][0]["content"]["mod"], "files-preview")
        self.assertEqual(generated["children"][1]["content"]["mod"], "changes-diff")
        sidebar = generated["children"][2]["children"]
        self.assertEqual(sidebar[0]["content"]["mod"], "spaces-icons")
        self.assertEqual(sidebar[1], source["children"][2]["children"][1])
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


def icon_package(version, tamper=False):
    manifest = {
        "iconDefinitions": {
            "file": {"iconPath": "./../icons/file.svg"},
            "folder": {"iconPath": "./../icons/folder.svg"},
            "folder-open": {"iconPath": "./../icons/folder-open.svg"},
            "latex": {"iconPath": "./../icons/tex.svg"},
            "python": {"iconPath": "./../icons/python.svg"},
            "python_light": {"iconPath": "./../icons/python_light.svg"},
            "ghost": {"iconPath": "./../icons/ghost.svg"},
        },
        "file": "file",
        "folder": "folder",
        "folderExpanded": "folder-open",
        "fileExtensions": {"py": "python", "tex": "latex", "boo": "ghost"},
        "fileNames": {"Makefile": "python", "makefile": "latex"},
        "folderNames": {"src": "python"},
        "folderNamesExpanded": {"src": "python"},
        "light": {"fileExtensions": {"py": "python_light"}},
    }
    files = {"package/dist/material-icons.json": json.dumps(manifest).encode()}
    files["package/LICENSE"] = b"MIT"
    for name in ("file", "folder", "folder-open", "tex", "python", "python_light"):
        files[f"package/icons/{name}.svg"] = b"<svg/>"
    files["package/icons/../../evil.svg"] = b"<svg/>"
    files["package/icons/Bad Name.svg"] = b"<svg/>"
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    archive = buffer.getvalue()
    digest = hashlib.sha512(b"other" if tamper else archive).digest()
    meta = {
        "version": version,
        "dist": {
            "tarball": "archive",
            "integrity": "sha512-" + base64.b64encode(digest).decode(),
        },
    }
    return {installer.ICON_PACKAGE: json.dumps(meta).encode(), "archive": archive}


class MaterialIconTests(unittest.TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        self.target = Path(workspace.name)
        self.icons = self.target / installer.ICONS

    def install(self, package):
        fetched = []

        def fetch(url):
            fetched.append(url)
            return package[url]

        with mock.patch.object(installer, "fetch", fetch):
            with contextlib.redirect_stdout(io.StringIO()):
                installer.install_icons(self.target)
        return fetched

    def test_installs_safe_icons_and_resolved_lowercase_table(self):
        self.install(icon_package("1.0.0"))
        table = json.loads((self.icons / "icons.json").read_text())
        self.assertEqual(table["version"], "1.0.0")
        self.assertEqual(
            table["fileExtensions"], {"py": "python.svg", "tex": "tex.svg"}
        )
        self.assertEqual(table["fileNames"], {"makefile": "python.svg"})
        self.assertEqual(table["folderExpanded"], "folder-open.svg")
        self.assertEqual(table["light"]["fileExtensions"], {"py": "python_light.svg"})
        self.assertEqual(
            sorted(path.name for path in self.icons.iterdir()),
            [
                "LICENSE",
                "file.svg",
                "folder-open.svg",
                "folder.svg",
                "icons.json",
                "python.svg",
                "python_light.svg",
                "tex.svg",
            ],
        )
        self.assertFalse((self.target / "evil.svg").exists())

    def test_skips_current_version_and_replaces_older_one(self):
        self.install(icon_package("1.0.0"))
        self.assertEqual(self.install(icon_package("1.0.0")), [installer.ICON_PACKAGE])
        (self.icons / "stale.svg").write_text("old")
        self.install(icon_package("1.1.0"))
        self.assertFalse((self.icons / "stale.svg").exists())
        self.assertEqual(
            json.loads((self.icons / "icons.json").read_text())["version"], "1.1.0"
        )
        self.assertEqual(
            [p.name for p in self.icons.parent.iterdir() if p.name != "icons"], []
        )

    def test_checksum_mismatch_keeps_installed_icons(self):
        self.install(icon_package("1.0.0"))
        with self.assertRaisesRegex(ValueError, "checksum"):
            self.install(icon_package("1.1.0", tamper=True))
        self.assertEqual(
            json.loads((self.icons / "icons.json").read_text())["version"], "1.0.0"
        )
        self.assertEqual(
            [p.name for p in self.icons.parent.iterdir() if p.name != "icons"], []
        )
