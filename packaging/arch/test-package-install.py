#!/usr/bin/python3
"""Test inert package file installation/removal in a temporary root and database."""
import argparse
from pathlib import Path
import subprocess
import tempfile


def checked(args):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    args = parser.parse_args()
    package = args.package.resolve()
    verify = Path(__file__).with_name('verify-package.py')
    print(checked(['/usr/bin/python3', str(verify), '--package', str(package)]))
    info = checked(['bsdtar', '-xOf', str(package), '.PKGINFO'])
    dependencies = [s.removeprefix('depend = ') for s in info.splitlines() if s.startswith('depend = ')]
    checked(['pacman', '-T', *dependencies])
    with tempfile.TemporaryDirectory(prefix='mac-native-pacman-') as directory:
        base = Path(directory)
        root, db, cache, hooks = [base / s for s in ('root', 'db', 'cache', 'hooks')]
        for path in (root, db, cache, hooks):
            path.mkdir()
        config = base / 'pacman.conf'
        config.write_text('[options]\nArchitecture = x86_64\nSigLevel = Never\nLocalFileSigLevel = Never\n')
        options = ['--config', str(config), '--root', str(root), '--dbpath', str(db),
                   '--cachedir', str(cache), '--logfile', str(base / 'pacman.log'),
                   '--hookdir', str(hooks)]
        # This empty database deliberately has no dependencies. They were checked
        # on the host above; two --nodeps switches suppress names as well as versions.
        transaction = ['fakeroot', '--', 'pacman', *options, '--noconfirm',
                       '--nodeps', '--nodeps', '--noscriptlet']
        checked([*transaction, '-U', str(package)])
        print('Temporary-root install:', checked(['pacman', *options, '-Q', 'mac-native-screenshare']))
        print(checked(['/usr/bin/python3', str(verify), '--root', str(root)]))
        checked([*transaction, '-R', 'mac-native-screenshare'])
        for name in ('usr/lib/mac-native-screenshare', 'usr/share/doc/mac-native-screenshare',
                     'usr/share/licenses/mac-native-screenshare'):
            if (root / name).exists():
                raise RuntimeError('Package removal left files at ' + name)
        if subprocess.run(['pacman', *options, '-Q', 'mac-native-screenshare'], capture_output=True).returncode == 0:
            raise RuntimeError('Package removal left a database entry')
    print('PASS: host dependencies resolve; temporary-root package installation and removal left no package files or database entry. No live-host installation occurred.')


if __name__ == '__main__':
    main()
