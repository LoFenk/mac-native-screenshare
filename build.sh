#!/bin/bash
# Build the pinned source checkpoint privately; no installation or service start.
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1

workspace="${1:?Usage: bash build.sh <workspace-with-neatvnc-and-wayvnc> [build-directory]}"
workspace="$(realpath -- "$workspace")"
build_root="${2:-$workspace/build/mac-native-screenshare}"
build_root="$(realpath -m -- "$build_root")"
source_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
integration_python="${OMARCHY_SHARE_PYTHON:-/usr/bin/python3}"
"$integration_python" -c 'import dbus; from gi.repository import GLib, GLibUnix'

"$integration_python" - "$workspace" "$source_root/dependencies.json" <<'PY'
import json
from pathlib import Path
import subprocess
import sys

workspace = Path(sys.argv[1])
lock = json.loads(Path(sys.argv[2]).read_text())
for name, source in lock['repositories'].items():
    repo = workspace / name
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    if head != source['commit']:
        raise SystemExit(f'{name}: checkout differs from dependencies.json')
    dirty = subprocess.check_output(['git', 'status', '--porcelain'], cwd=repo, text=True)
    if dirty.strip():
        raise SystemExit(f'{name}: commit or remove uncommitted build inputs first')
print('Both dependency checkouts match their pinned commits.')
PY

mkdir -p -- "$build_root"
if [[ ! -f $build_root/neatvnc/build.ninja ]]; then
  meson setup "$build_root/neatvnc" "$workspace/neatvnc" --buildtype=debugoptimized \
    -Dtests=true -Dexamples=true -Dh264=disabled -Dgbm=disabled -Dnettle=enabled -Dtls=enabled
fi
ninja -C "$build_root/neatvnc" -j2
meson test -C "$build_root/neatvnc" --print-errorlogs

if [[ ! -f $build_root/wayvnc/build.ninja ]]; then
  PKG_CONFIG_PATH="$build_root/neatvnc/meson-uninstalled${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}" \
    meson setup "$build_root/wayvnc" "$workspace/wayvnc" --buildtype=debugoptimized \
      -Dtests=true -Dman-pages=disabled -Dscreencopy-dmabuf=disabled
fi
ninja -C "$build_root/wayvnc" -j2
LD_LIBRARY_PATH="$build_root/neatvnc${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
  meson test -C "$build_root/wayvnc" --print-errorlogs

"$integration_python" "$source_root/test.py"
lua "$source_root/test-mac-shortcuts.lua" "$source_root/mac-shortcuts.lua"
bash -n "$source_root/run.sh" "$source_root/mac-shortcuts.sh" "$source_root/build.sh"

stage="$build_root/stage"
mkdir -p "$stage/bin" "$stage/lib"
install -m755 "$build_root/wayvnc/wayvnc" "$stage/bin/wayvnc"
install -m755 "$build_root/wayvnc/wayvncctl" "$stage/bin/wayvncctl"
install -m755 "$build_root/neatvnc/libneatvnc.so.1.0.1" "$stage/lib/libneatvnc.so.1.0.1"
ln -sfn libneatvnc.so.1.0.1 "$stage/lib/libneatvnc.so.1"
"$integration_python" - "$stage" <<'PY'
import hashlib
from pathlib import Path
import sys

stage = Path(sys.argv[1])
names = ['bin/wayvnc', 'bin/wayvncctl', 'lib/libneatvnc.so.1.0.1']
(stage / 'SHA256SUMS').write_text(''.join(
    hashlib.sha256((stage / name).read_bytes()).hexdigest() + '  ' + name + '\n'
    for name in names))
print(f'Private build and tests passed. Artifacts: {stage}')
PY
