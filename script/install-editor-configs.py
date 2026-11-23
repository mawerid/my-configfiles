import os
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile, mkdtemp

CONFIG = Path(__file__).resolve().parents[1] / "config"


def install_file(source, target, *, backup=False):
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.is_symlink() and target.exists():
        if not target.is_file():
            raise ValueError(f"Expected a file at {target}")
        if source.read_bytes() == target.read_bytes():
            return
    with NamedTemporaryFile(dir=target.parent, delete=False) as staged:
        temporary = Path(staged.name)
    try:
        shutil.copy2(source, temporary)
        if backup and os.path.lexists(target):
            folder = Path(mkdtemp(prefix=f"{target.name}.bak.", dir=target.parent))
            destination = folder / target.name
            shutil.copy2(target, destination, follow_symlinks=False)
            print(f"Backed up {target} to {destination}")
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    tmux = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / ".tmux.conf"
    zsh = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    nvim = Path(
        subprocess.check_output(
            [
                "nvim",
                "--headless",
                "-u",
                "NONE",
                "-i",
                "NONE",
                '+lua io.write(vim.fn.stdpath("config"))',
                "+qa",
            ],
            text=True,
        )
    )
    if not nvim.is_absolute():
        raise ValueError("Could not determine the active Neovim config directory.")

    nvim_source = CONFIG / "nvim"
    targets = [
        (source, nvim / source.relative_to(nvim_source))
        for source in sorted(nvim_source.rglob("*"))
        if source.is_file()
    ]
    for _, target in targets:
        for parent in target.parents:
            if parent == nvim.parent:
                break
            if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
                raise ValueError(f"Expected a Neovim config directory at {parent}")
        if not target.is_symlink() and target.exists() and not target.is_file():
            raise ValueError(f"Expected a file at {target}")

    if zsh is not None:
        install_file(CONFIG / "zsh/.zshrc", zsh, backup=True)
    install_file(CONFIG / "tmux/.tmux.conf", tmux)
    for source, target in targets:
        install_file(source, target)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        sys.exit(f"Configuration setup failed: {error}")
