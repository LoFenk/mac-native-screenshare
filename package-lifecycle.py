#!/usr/bin/python3
"""Pacman pre-transaction cleanup. Execute user cleanup only after dropping uid."""
import os
from pathlib import Path
import pwd
import subprocess
import sys

NAME = 'mac-native-screenshare'
UNIT = NAME + '.service'
ROOT = '/usr/lib/' + NAME


def users(accounts=None):
    for account in accounts if accounts is not None else pwd.getpwall():
        if account.pw_uid < 1000 or account.pw_uid == 65534:
            continue
        config = Path(account.pw_dir) / '.config' / NAME
        startup = Path(account.pw_dir) / '.config/systemd/user/graphical-session.target.wants' / UNIT
        bus = Path('/run/user') / str(account.pw_uid) / 'bus'
        if config.exists() or startup.is_symlink() or bus.is_socket():
            yield account, bus.is_socket()


def cleanup(operation, accounts=None):
    failures = []
    for account, online in users(accounts):
        try:
            if online:
                # This talks to the user's manager; it does not read or execute user files as root.
                result = subprocess.run(['/usr/bin/systemctl', '--user', '--machine=' + account.pw_name + '@.host',
                                         'stop', UNIT], capture_output=True, text=True, timeout=100)
                if result.returncode and 'not loaded' not in result.stderr:
                    raise RuntimeError(result.stderr.strip())
            if operation == 'remove':
                config = Path(account.pw_dir) / '.config' / NAME
                startup = Path(account.pw_dir) / '.config/systemd/user/graphical-session.target.wants' / UNIT
                if not config.exists() and not startup.is_symlink():
                    continue
                # HOME is the account database value; inherited Python/shell paths are discarded.
                environment = {'HOME': account.pw_dir, 'USER': account.pw_name, 'LOGNAME': account.pw_name,
                               'PATH': '/usr/bin', 'LC_ALL': 'C', 'PYTHONDONTWRITEBYTECODE': '1'}
                if online:
                    environment['XDG_RUNTIME_DIR'] = f'/run/user/{account.pw_uid}'
                    environment['DBUS_SESSION_BUS_ADDRESS'] = f'unix:path=/run/user/{account.pw_uid}/bus'
                command = ['/usr/bin/runuser', '--user', account.pw_name, '--', '/usr/bin/env', '-i',
                           *[key + '=' + value for key, value in environment.items()],
                           '/usr/bin/python3', ROOT + '/mns_cli.py', 'remove']
                if not online:
                    command.append('--offline')
                subprocess.run(command, check=True, timeout=150)
        except (OSError, RuntimeError, subprocess.SubprocessError) as error:
            failures.append(account.pw_name + ': ' + str(error))
    if failures:
        raise RuntimeError('Cleanup incomplete; package transaction must wait:\n' + '\n'.join(failures))


if __name__ == '__main__':
    if os.getuid() != 0 or sys.argv[1:] not in (['upgrade'], ['remove']):
        raise SystemExit('Use only as the root pacman pre-transaction upgrade/remove helper.')
    try:
        cleanup(sys.argv[1])
    except RuntimeError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
