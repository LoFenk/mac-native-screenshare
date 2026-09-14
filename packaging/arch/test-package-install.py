#!/usr/bin/python3
"""Test package files in a temporary root; test transaction behavior separately."""
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
    parser.add_argument('--upgrade-from', type=Path, help='Also install an older package before upgrading to this one')
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
        # This root has no user managers or Python. Transaction behavior is
        # checked separately by test-package-lifecycle.py without live calls.
        for name in ('mac-native-screenshare-upgrade.hook', 'mac-native-screenshare-remove.hook'):
            (hooks / name).symlink_to('/dev/null')
        config = base / 'pacman.conf'
        config.write_text('[options]\nArchitecture = x86_64\nSigLevel = Never\nLocalFileSigLevel = Never\n')
        options = ['--config', str(config), '--root', str(root), '--dbpath', str(db),
                   '--cachedir', str(cache), '--logfile', str(base / 'pacman.log'),
                   '--hookdir', str(hooks)]
        # This empty database deliberately has no dependencies. They were checked
        # on the host above; two --nodeps switches suppress names as well as versions.
        transaction = ['fakeroot', '--', 'pacman', *options, '--noconfirm',
                       '--nodeps', '--nodeps', '--noscriptlet']
        if args.upgrade_from:
            checked([*transaction, '-U', str(args.upgrade_from.resolve())])
            print('Temporary-root previous version:', checked(['pacman', *options, '-Q', 'mac-native-screenshare']))
        checked([*transaction, '-U', str(package)])
        print('Temporary-root install:', checked(['pacman', *options, '-Q', 'mac-native-screenshare']))
        print(checked(['/usr/bin/python3', str(verify), '--root', str(root)]))
        if args.upgrade_from:
            for name in ('run.sh', 'publish.py', 'mac-shortcuts.sh', 'virtual-display.py'):
                if (root / 'usr/lib/mac-native-screenshare' / name).exists():
                    raise RuntimeError('Upgrade retained obsolete prototype helper: ' + name)
            print('PASS: package upgrade replaced the previous version and removed obsolete prototype helpers.')
        checked([*transaction, '-R', 'mac-native-screenshare'])
        for name in ('usr/lib/mac-native-screenshare', 'usr/share/doc/mac-native-screenshare',
                     'usr/share/licenses/mac-native-screenshare', 'usr/bin/mac-native-screenshare',
                     'usr/lib/systemd/user/mac-native-screenshare.service',
                     'usr/share/libalpm/hooks/mac-native-screenshare-upgrade.hook',
                     'usr/share/libalpm/hooks/mac-native-screenshare-remove.hook'):
            if (root / name).exists():
                raise RuntimeError('Package removal left files at ' + name)
        if subprocess.run(['pacman', *options, '-Q', 'mac-native-screenshare'], capture_output=True).returncode == 0:
            raise RuntimeError('Package removal left a database entry')
    print('PASS: host dependencies resolve; temporary-root package installation and removal left no package files or database entry. No live-host installation occurred.')


if __name__ == '__main__':
    main()
