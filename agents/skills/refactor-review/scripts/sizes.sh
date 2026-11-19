#!/bin/sh
set -eu
git ls-files -- '*.py' '*.js' '*.ts' '*.go' '*.rs' '*.c' '*.cpp' |
while IFS= read -r path; do
    if [ -f "$path" ] && [ ! -L "$path" ]; then wc -l < "$path" | awk -v p="$path" '{print $1, p}'; fi
done | sort -nr
if [ "$#" -gt 0 ]; then git diff --stat "$1" HEAD --; fi
