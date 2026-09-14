#!/usr/bin/python3
"""Check a staged or packaged private runtime without opening a desktop session."""
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile

PACKAGE = 'mac-native-screenshare'
PREFIX = Path('usr/lib') / PACKAGE
DOCS = Path('usr/share/doc') / PACKAGE
LICENSES = Path('usr/share/licenses') / PACKAGE


def run(*args):
    env = os.environ.copy()
    for key in ('LD_LIBRARY_PATH', 'LD_PRELOAD', 'LD_AUDIT'):
        env.pop(key, None)
    return subprocess.check_output(args, env=env, text=True, stderr=subprocess.STDOUT)


def verify_root(root):
    root = root.resolve()
    expected = [PREFIX / 'bin/wayvnc', PREFIX / 'bin/wayvncctl',
                PREFIX / 'lib/libneatvnc.so.1', PREFIX / 'run.sh',
                PREFIX / 'publish.py', PREFIX / 'probe.py',
                PREFIX / 'mac-shortcuts.lua', PREFIX / 'mac-shortcuts.sh',
                PREFIX / 'virtual-display.py', DOCS / 'README.md',
                DOCS / 'RELEASE_SCOPE.md', DOCS / 'sources.json',
                LICENSES / 'LICENSE', LICENSES / 'neatvnc-COPYING',
                LICENSES / 'wayvnc-COPYING']
    for name in expected:
        if not (root / name).is_file():
            raise ValueError('Missing package file: ' + str(name))
    files = []
    for path in root.rglob('*'):
        relative = path.relative_to(root)
        if relative.as_posix() in ('.PKGINFO', '.BUILDINFO', '.MTREE'):
            continue
        if path.is_dir() and not path.is_symlink():
            continue
        if not any(relative.is_relative_to(prefix) for prefix in (PREFIX, DOCS, LICENSES)):
            raise ValueError('Unexpected file outside private package paths: ' + str(relative))
        if path.is_symlink() and not path.resolve().is_relative_to(root / PREFIX):
            raise ValueError('Symlink escapes private runtime: ' + str(relative))
        if not path.is_symlink() and path.stat().st_mode & 0o6022:
            raise ValueError('Unsafe file permissions: ' + str(relative))
        files.append('/' + relative.as_posix())
    server = root / PREFIX / 'bin/wayvnc'
    control = root / PREFIX / 'bin/wayvncctl'
    for binary in (server, control):
        dynamic = run('readelf', '-d', str(binary))
        paths = re.findall(r'\((?:RUNPATH|RPATH)\).*?\[(.*?)\]', dynamic)
        if paths != ['$ORIGIN/../lib']:
            raise ValueError('Unexpected runtime library search path: ' + str(binary) + ': ' + repr(paths))
    library = (root / PREFIX / 'lib/libneatvnc.so.1').resolve()
    if re.search(r'\((?:RUNPATH|RPATH)\)', run('readelf', '-d', str(library))):
        raise ValueError('Bundled NeatVNC contains an unexpected runtime search path')
    loaded = run('/usr/lib/ld-linux-x86-64.so.2', '--list', str(server))
    match = re.search(r'libneatvnc\.so\.1 => (.*?) \(', loaded)
    if not match or Path(match.group(1)).resolve() != library:
        raise ValueError('Server did not load the bundled NeatVNC: ' + loaded)
    run(str(server), '--version')
    run(str(control), '--help')
    # Compare file ownership, not shared directory entries.
    installed = subprocess.run(['pacman', '-Qlq', 'wayvnc', 'neatvnc'], capture_output=True, text=True)
    stock_files = {line for line in installed.stdout.splitlines() if not line.endswith('/')}
    if stock_files.intersection(files):
        raise ValueError('Package overlaps stock WayVNC/NeatVNC files')
    spec = json.loads((root / DOCS / 'sources.json').read_text())
    assert spec['package'] == PACKAGE
    assert {s['name'] for s in spec['sources']} == {'integration', 'wayvnc', 'neatvnc'}
    print('PASS: private file layout, permissions, licenses, pinned provenance, bundled library resolution, binary smoke checks, and no stock file overlap.')


def verify_archive(package):
    info = run('bsdtar', '-xOf', str(package), '.PKGINFO')
    assert 'pkgname = ' + PACKAGE + '\n' in info
    assert 'arch = x86_64\n' in info
    for line in info.splitlines():
        if line.startswith(('provides = ', 'replaces = ', 'conflict = ')):
            raise ValueError('Package must not replace or provide system VNC packages')
        if line.startswith('depend = ') and re.match(r'(?:wayvnc|neatvnc|libneatvnc\.so)(?:[<>=]|$)', line[9:]):
            raise ValueError('Package must not depend on stock VNC components')
    members = run('bsdtar', '-tf', str(package)).splitlines()
    for member in members:
        path = PurePosixPath(member)
        if path.is_absolute() or '..' in path.parts or path.name == '.INSTALL':
            raise ValueError('Unsafe or active installation member: ' + member)
    with tempfile.TemporaryDirectory(prefix='mac-native-package-check-') as directory:
        subprocess.run(['bsdtar', '--no-same-owner', '-xf', str(package), '-C', directory], check=True)
        verify_root(Path(directory))
    print('PASS: package metadata and inert installation contents.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--root', type=Path)
    group.add_argument('--package', type=Path)
    args = parser.parse_args()
    if args.root:
        verify_root(args.root)
    else:
        verify_archive(args.package.resolve())


if __name__ == '__main__':
    main()
