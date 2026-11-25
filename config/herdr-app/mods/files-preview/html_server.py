"""Serve one folder over a private Unix socket; exit after IDLE seconds without requests.

Prints the socket path. Reuses a server already listening for the same folder.
Herdr runs this on a remote machine as `python3 -c <this file> <folder>`.
"""

import hashlib
import http.server
import os
import socket
import socketserver
import stat
import sys
import tempfile
from functools import partial

IDLE = 300


def socket_dir():
    base = os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir()
    path = os.path.join(base, f"herdr-html-{os.getuid()}")
    try:
        os.mkdir(path, 0o700)
    except FileExistsError:
        pass
    info = os.lstat(path)
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_mode & 0o077
    ):
        sys.exit(f"Unsafe socket folder: {path}")
    return path


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class Server(socketserver.UnixStreamServer):
    timeout = IDLE
    idle = False

    def handle_timeout(self):
        self.idle = True


def alive(path):
    with socket.socket(socket.AF_UNIX) as probe:
        try:
            probe.connect(path)
            return True
        except OSError:
            return False


def serve(server, path, inode):
    try:
        while not server.idle:
            server.handle_request()
    finally:
        server.server_close()
        # A newer server may own the path by now; remove only our own socket.
        try:
            if os.stat(path).st_ino == inode:
                os.unlink(path)
        except FileNotFoundError:
            pass


def main(root):
    root = os.path.realpath(root)
    if not os.path.isdir(root):
        sys.exit(f"Not a folder: {root}")
    name = hashlib.sha256(root.encode()).hexdigest()[:16] + ".sock"
    path = os.path.join(socket_dir(), name)
    if not alive(path):
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass
        server = Server(path, partial(Handler, directory=root))
        inode = os.stat(path).st_ino
        if os.fork() == 0:
            try:
                os.setsid()
                if os.fork() == 0:
                    null = os.open(os.devnull, os.O_RDWR)
                    for fd in (0, 1, 2):
                        os.dup2(null, fd)
                    serve(server, path, inode)
            finally:
                os._exit(0)
        os.wait()
        server.server_close()
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
