import importlib.util
import os
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "config/herdr-app/mods/files-preview/html_server.py"
spec = importlib.util.spec_from_file_location("html_server", SCRIPT)
html_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(html_server)


def get(path, url):
    with socket.socket(socket.AF_UNIX) as client:
        client.connect(path)
        client.sendall(f"GET {url} HTTP/1.0\r\n\r\n".encode())
        return b"".join(iter(lambda: client.recv(65536), b""))


def server_pid(path):
    # SO_PEERCRED names the process that called listen(), which has exited;
    # find the daemon that still holds the socket instead.
    with open("/proc/net/unix") as table:
        inode = next(parts[6] for parts in map(str.split, table) if parts[7:] == [path])
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            fds = os.listdir(f"/proc/{pid}/fd")
        except OSError:
            continue
        for fd in fds:
            try:
                if os.readlink(f"/proc/{pid}/fd/{fd}") == f"socket:[{inode}]":
                    return int(pid)
            except OSError:
                pass
    raise LookupError(path)


class HtmlServerTests(unittest.TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        self.root = Path(workspace.name) / "site"
        (self.root / "css").mkdir(parents=True)
        (self.root / "index.html").write_text("<h1>hi</h1>")
        (self.root / "css/x.css").write_text("h1{}")
        self.runtime = Path(workspace.name) / "run"
        self.runtime.mkdir(mode=0o700)

    def start(self):
        # Same invocation as the mod: the script's source passed with -c.
        result = subprocess.run(
            [sys.executable, "-c", SCRIPT.read_text(), str(self.root)],
            env={**os.environ, "XDG_RUNTIME_DIR": str(self.runtime)},
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def test_serves_folder_privately_and_reuses_running_server(self):
        path = self.start()
        pid = server_pid(path)
        self.addCleanup(os.kill, pid, signal.SIGTERM)
        self.assertEqual(os.stat(Path(path).parent).st_mode & 0o777, 0o700)
        self.assertTrue(get(path, "/index.html").endswith(b"<h1>hi</h1>"))
        self.assertTrue(get(path, "/css/x.css").endswith(b"h1{}"))
        self.assertIn(b" 404 ", get(path, "/../../etc/passwd").split(b"\r\n")[0])
        self.assertEqual(self.start(), path)
        self.assertEqual(server_pid(path), pid)

    def test_refuses_socket_folder_open_to_others(self):
        folder = self.runtime / f"herdr-html-{os.getuid()}"
        folder.mkdir(mode=0o755)
        folder.chmod(0o755)
        with mock.patch.dict(os.environ, {"XDG_RUNTIME_DIR": str(self.runtime)}):
            with self.assertRaises(SystemExit):
                html_server.socket_dir()

    def test_exits_and_removes_socket_after_idle_timeout(self):
        path = str(self.runtime / "idle.sock")
        server = html_server.Server(path, html_server.Handler)
        server.timeout = 0.2
        thread = threading.Thread(
            target=html_server.serve, args=(server, path, os.stat(path).st_ino)
        )
        thread.start()
        thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertFalse(os.path.exists(path))


if __name__ == "__main__":
    unittest.main()
