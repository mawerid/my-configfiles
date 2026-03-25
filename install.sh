#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/script"

run_script() {
    local script="$1"
    if [[ ! -f "$script" ]]; then
        echo "Missing script: $script" >&2
        exit 1
    fi
    bash "$script"
}

case "$(uname -s)" in
    Darwin)
        echo "Detected macOS"
        run_script "$SCRIPT_DIR/setup-macos.sh"
        ;;
    Linux)
        if [[ -r /etc/os-release ]]; then
            # shellcheck disable=SC1091
            . /etc/os-release
            if [[ "${ID:-}" == "ubuntu" || "${ID_LIKE:-}" == *"ubuntu"* ]]; then
                echo "Detected Ubuntu"
                run_script "$SCRIPT_DIR/setup-ubuntu.sh"
            else
                echo "Unsupported Linux distro: ${ID:-unknown}" >&2
                exit 1
            fi
        else
            echo "Cannot detect Linux distribution" >&2
            exit 1
        fi
        ;;
    *)
        echo "Unsupported platform: $(uname -s)" >&2
        exit 1
        ;;
esac