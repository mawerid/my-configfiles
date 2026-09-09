#!/usr/bin/env bash
set -euo pipefail
for command in gcc g++ clang cmake ninja gdb lldb clang-format clang-tidy \
    colcon rosdep vcs uv pip pytest jupyter git gh rg fd jq tmux vim git-lfs; do
    command -v "$command" >/dev/null
done
codex --version
claude --version
research-session ros ros2 pkg prefix rclpy
research-session ros /usr/bin/python3 - <<'PY'
import numpy as np
import rclpy
from cv_bridge import CvBridge

assert CvBridge().cv2_to_imgmsg(np.zeros((2, 2, 3), dtype=np.uint8)).height == 2
rclpy.init()
rclpy.shutdown()
PY
python /opt/deep-research-smoke/python-check.py "${1:-}"
build_dir=$(mktemp -d /tmp/deep-research-smoke.XXXXXX)
trap 'rm -rf "$build_dir"' EXIT
cmake -S /opt/deep-research-smoke -B "$build_dir" -G Ninja
cmake --build "$build_dir" --parallel 1
"$build_dir/deep_research_smoke"
printf 'int main(void) { return 0; }\n' > "$build_dir/sanitizer.c"
gcc -fsanitize=address,undefined "$build_dir/sanitizer.c" -o "$build_dir/sanitizer"
"$build_dir/sanitizer"
if [ "${1:-}" = --gpu ]; then
    nvidia-smi
    nvcc --version
fi
