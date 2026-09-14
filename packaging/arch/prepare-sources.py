#!/usr/bin/python3
"""Export checksum-locked local Git commits into an offline makepkg workspace."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def archive(repo, commit, prefix):
    tar = subprocess.check_output([
        'git', '-C', str(repo), '-c', 'tar.umask=0022', 'archive',
        '--format=tar', '--prefix=' + prefix + '/', commit,
    ])
    return subprocess.check_output(['gzip', '-n', '-9'], input=tar)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True,
                        help='Parent containing mac-native-screenshare/, neatvnc/, wayvnc/')
    parser.add_argument('--output', type=Path, required=True,
                        help='New or empty build directory')
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    spec = json.loads((here / 'sources.json').read_text())
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        parser.error('Output directory must be empty; existing builds are not overwritten.')
    # Validate every export before writing build inputs.
    exports = []
    for item in spec['sources']:
        repo = args.workspace.resolve() / item['directory']
        data = archive(repo, item['commit'], item['prefix'])
        digest = hashlib.sha256(data).hexdigest()
        if digest != item['sha256']:
            raise SystemExit('Archive checksum mismatch: ' + item['name'])
        exports.append((item['archive'], data))
        print('Verified', item['name'], item['commit'])
    output.mkdir(parents=True, exist_ok=True)
    for name, data in exports:
        (output / name).write_bytes(data)
    for name in ['PKGBUILD', 'sources.json', 'wayvnc-private-rpath.patch', 'README-PACKAGE.md', 'verify-package.py', 'THIRD-PARTY-NOTICES']:
        shutil.copy2(here / name, output / name)
    print('Offline package workspace:', output)
    print('Next: run makepkg inside that directory with the declared dependencies installed.')


if __name__ == '__main__':
    main()
