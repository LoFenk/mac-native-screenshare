"""Set up and control the independent Mac Native Screenshare add-on."""
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import socket
import subprocess
import sys
import tempfile

from mns_common import Error, NAME, Paths, ROOT, SCHEMA, UNIT, atomic_write, lock, network_state, new_password, password, private_dir, read_private, resolve_network, run, settings, validate_settings, write_json
from mns_desktop import Desktop, add_hooks, config_text, hook_blocks, remove_hooks, verify_hooks
from mns_relay import reserve
from mns_session import recover, session_environment


def systemctl(*args, check=True):
    return run('systemctl', '--user', *args, check=check, timeout=100)


def active():
    result = systemctl('show', UNIT, '--property=ActiveState', '--value', check=False)
    if result.returncode:
        raise Error('Cannot reach the user service manager.')
    return result.stdout.strip() in ('active', 'activating', 'deactivating', 'reloading')


def stopped():
    if active():
        raise Error('Stop sharing before changing or removing its configuration.')


def networks():
    found = []
    for line in run('nmcli', '--escape', 'no', '-t', '-f', 'DEVICE,TYPE,STATE', 'device', 'status').splitlines():
        parts = line.split(':')
        if len(parts) != 3 or parts[1] not in ('ethernet', 'wifi') or parts[2] != 'connected':
            continue
        connection, addresses = network_state(parts[0])
        for address in addresses:
            if any(address.network.subnet_of(ipaddress.IPv4Network(n)) for n in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')):
                found.append({'interface': parts[0], 'connection': connection,
                              'address': str(address.ip), 'subnet': str(address.network)})
    return found


def choose(items, description):
    if not items:
        raise Error('No eligible ' + description + ' found.')
    if not sys.stdin.isatty():
        raise Error('Select ' + description + ' explicitly for noninteractive setup.')
    for index, item in enumerate(items, 1):
        print(f'{index}: {item}')
    try:
        index = int(input('Choose ' + description + ' number: ')) - 1
        if not 0 <= index < len(items):
            raise ValueError
        return items[index]
    except ValueError as error:
        raise Error('Invalid selection.') from error


def configure(paths, args):
    stopped()
    session_environment(paths)
    desktop = Desktop(paths)
    desktop.reload()
    old = settings(paths) if paths.settings.exists() else None
    if old:
        verify_hooks(paths)
        password(paths)
    if not old and not args.accept_unencrypted:
        if not sys.stdin.isatty():
            raise Error('Native VNC is unencrypted. Deliberately select a trusted private LAN and pass --accept-unencrypted to continue.')
        print('Native Mac VNC leaves desktop, input, and clipboard traffic unencrypted. Use only a trusted private LAN.')
        if input('Type yes to accept and configure sharing (it stays stopped): ').strip().lower() != 'yes':
            raise Error('Setup cancelled.')
    choices = networks()
    selected = [n for n in choices if n['interface'] == (args.interface or (old and old['interface']))]
    if args.interface and len(selected) != 1:
        raise Error('The selected Ethernet/Wi-Fi interface needs exactly one private IPv4 subnet.')
    network = selected[0] if len(selected) == 1 else choose(choices, 'network')
    monitors = desktop.query('monitors')
    output = args.output or (old and old['output'])
    if not output:
        output = choose([m['name'] for m in monitors], 'display')
    desktop.physical(output)
    virtual = old['virtual'] if old else None
    if args.virtual:
        match = re.fullmatch(r'(\d+)x(\d+)', args.virtual)
        if not match:
            raise Error('Use --virtual WIDTHxHEIGHT, for example 1920x1200.')
        virtual = list(map(int, match.groups()))
    if args.physical:
        virtual = None
    name = args.name or (old and old['name']) or ('Mac Screenshare - ' + socket.gethostname().split('.')[0])[:63]
    config = validate_settings({'schema': SCHEMA, **network, 'output': output,
              'port': args.port or (old and old['port']) or 5900,
              'virtual': virtual, 'name': name,
              'hostname': old['hostname'] if old else 'mac-share-' + secrets.token_hex(5) + '.local',
              'transport': 'legacy-vnc', 'accepted_unencrypted': True})
    with reserve(network['address'], config['port']):
        pass
    if run('systemctl', 'is-active', '--quiet', 'avahi-daemon.service', check=False).returncode:
        raise Error('Finder discovery needs avahi-daemon.service. Have your administrator enable it, then retry setup.')
    private_dir(paths.config)
    if old:
        write_json(paths.settings, config)
        print('Settings updated. Existing password and login-start preference retained; sharing is stopped.')
        return
    if paths.ownership.exists() or paths.password.exists():
        raise Error('An incomplete setup exists. Run remove to recover its owned files, then retry.')
    original, mode = config_text(paths)
    blocks = hook_blocks()
    changed = add_hooks(original, blocks)
    owned = {'schema': 1, 'blocks': blocks, 'had_final_newline': original.endswith('\n'),
             'original_sha256': hashlib.sha256(original.encode()).hexdigest()}
    # Journal exact ownership and backup before touching the user's file.
    atomic_write(paths.config / 'hyprland.lua.before', original)
    write_json(paths.ownership, owned)
    atomic_write(paths.password, new_password() + '\n')
    try:
        atomic_write(paths.hypr, changed, mode)
        desktop.reload()
        write_json(paths.settings, config)
    except BaseException:
        current, current_mode = config_text(paths)
        atomic_write(paths.hypr, remove_hooks(current, owned), current_mode)
        desktop.reload()
        for name in ('password', 'ownership.json', 'hyprland.lua.before'):
            (paths.config / name).unlink(missing_ok=True)
        raise
    print(f'Setup complete: {network["interface"]}, {network["subnet"]}, {output}, TCP {config["port"]}. Sharing is stopped.')
    print('Run mac-native-screenshare password to view the fresh credential, then start to share.')


def remove_configuration(paths):
    recover(paths)
    if paths.ownership.exists():
        owned = json.loads(read_private(paths.ownership))
        if owned.get('schema') != 1:
            raise Error('Unknown ownership format; keeping files for review.')
        if paths.hypr.exists():
            current, mode = config_text(paths)
            remaining = remove_hooks(current, owned)
            if remaining != current:
                atomic_write(paths.hypr, remaining, mode)
            # Offline removal has no compositor to reload; next login reads clean config.
            if os.environ.get('HYPRLAND_INSTANCE_SIGNATURE'):
                Desktop(paths).reload()
    elif paths.settings.exists():
        raise Error('Ownership record is missing. Keep your files and inspect the marked Hyprland blocks before removal.')
    for name in ('settings.json', 'password', 'ownership.json', 'hyprland.lua.before'):
        (paths.config / name).unlink(missing_ok=True)
    if paths.config.exists():
        try:
            paths.config.rmdir()
        except OSError:
            print('Unrecognized files retained in ' + str(paths.config))


def status(paths):
    result = systemctl('show', UNIT, '--property=ActiveState,SubState,UnitFileState,Result', check=False)
    state = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    state['configured'] = paths.settings.is_file()
    state['recovery_needed'] = paths.journal.is_file() and state.get('ActiveState') not in ('active', 'activating')
    if result.returncode:
        state['manager'] = 'unavailable'
    if paths.settings.is_file():
        config = settings(paths)
        state['selection'] = {k: config[k] for k in ('interface', 'subnet', 'output', 'port', 'virtual', 'hostname')}
    if state.get('ActiveState') == 'active' and (paths.runtime / 'ready.json').exists():
        state['endpoint'] = json.loads(read_private(paths.runtime / 'ready.json'))
    return state


def import_session():
    systemctl('import-environment', 'WAYLAND_DISPLAY', 'HYPRLAND_INSTANCE_SIGNATURE', 'XDG_RUNTIME_DIR')


def disable(paths, offline=False):
    if not offline:
        if not os.environ.get('HYPRLAND_INSTANCE_SIGNATURE'):
            environment = systemctl('show-environment', check=False)
            for line in environment.stdout.splitlines():
                key, separator, value = line.partition('=')
                if separator and key in ('HYPRLAND_INSTANCE_SIGNATURE', 'WAYLAND_DISPLAY') and re.fullmatch(r'[A-Za-z0-9_.-]+', value):
                    os.environ[key] = value
        systemctl('stop', UNIT)
        systemctl('disable', UNIT)
        systemctl('reset-failed', UNIT, check=False)
    else:
        # A logged-out user has no running service. Remove only our known enable link.
        link = paths.home / '.config/systemd/user/graphical-session.target.wants' / UNIT
        if link.is_symlink():
            if os.readlink(link) != '/usr/lib/systemd/user/' + UNIT:
                raise Error('Unexpected startup link target; keeping it for review.')
            link.unlink()
        elif link.exists():
            raise Error('The startup path is not an owned symlink.')
    recover(paths)


def firewall_commands(config):
    # Administrator action stays explicit; no privileged/global firewall edits.
    base = ['allow', 'in', 'on', config['interface'], 'proto', 'tcp', 'from', config['subnet'],
            'to', config['address'], 'port', str(config['port']), 'comment', NAME]
    return shlex.join(['sudo', 'ufw', *base]), shlex.join(['sudo', 'ufw', 'delete', *base])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', action='version', version=(ROOT / 'VERSION').read_text().strip())
    subs = parser.add_subparsers(dest='command', required=True)
    setup = subs.add_parser('setup', help='Choose or update settings; does not start sharing')
    setup.add_argument('--interface')
    setup.add_argument('--output')
    setup.add_argument('--port', type=int)
    setup.add_argument('--name')
    display = setup.add_mutually_exclusive_group()
    display.add_argument('--virtual', metavar='WIDTHxHEIGHT')
    display.add_argument('--physical', action='store_true')
    setup.add_argument('--accept-unencrypted', action='store_true')
    for command, help_text in (
        ('networks', 'List eligible connected private networks'), ('displays', 'List displays'),
        ('start', 'Start sharing in this desktop session'), ('stop', 'Stop and restore the desktop'),
        ('enable', 'Enable sharing at future graphical logins'), ('disable', 'Stop and disable login startup'),
        ('password', 'Show the password in this terminal'), ('reset-password', 'Rotate the password while stopped'),
        ('recover', 'Retry restoration after an interrupted session'), ('doctor', 'Check setup without starting sharing'),
        ('firewall', 'Print optional scoped UFW allow and removal commands')):
        subs.add_parser(command, help=help_text)
    subs.add_parser('status', help='Report state without credentials').add_argument('--json', action='store_true')
    subs.add_parser('remove', help='Stop, disable, and remove owned user configuration').add_argument('--offline', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    paths = Paths()
    temporary = None
    if args.command == 'remove' and args.offline and not paths.runtime.parent.exists():
        temporary = tempfile.TemporaryDirectory(prefix=NAME + '-offline-')
        paths = Paths(runtime=temporary.name)
    if os.getuid() < 1000 or os.getuid() == 65534:
        raise Error('Run this command as a regular desktop user (UID 1000 or higher), without sudo.')
    if args.command == 'networks':
        print(json.dumps(networks(), indent=2))
        return
    if args.command == 'displays':
        print(json.dumps(Desktop(paths).query('monitors'), indent=2))
        return
    if args.command == 'status':
        state = status(paths)
        print(json.dumps(state, indent=2) if args.json else '\n'.join(f'{k}: {v}' for k, v in state.items()))
        return
    if args.command == 'recover':
        # ExecStopPost must not contend with the CLI waiting in systemctl stop.
        with lock(paths, 'session.lock'):
            recover(paths)
        print('Recovery complete.')
        return
    with lock(paths):
        if args.command == 'setup':
            configure(paths, args)
        elif args.command == 'start':
            session_environment(paths)
            settings(paths)
            password(paths)
            verify_hooks(paths)
            if systemctl('is-active', '--quiet', 'graphical-session.target', check=False).returncode:
                raise Error('A systemd-managed graphical session is required.')
            import_session()
            systemctl('daemon-reload')
            systemctl('reset-failed', UNIT, check=False)
            systemctl('start', UNIT)
            if not active() or not (paths.runtime / 'ready.json').is_file():
                raise Error('Sharing did not become ready. Run status and journalctl --user -u ' + UNIT)
            print('Sharing started. Use Finder → Network → Share Screen, or the address shown by status.')
        elif args.command == 'enable':
            settings(paths)
            verify_hooks(paths)
            systemctl('enable', UNIT)
            print('Sharing will start after future graphical logins on the selected network. Run start to share now.')
        elif args.command == 'stop':
            systemctl('stop', UNIT)
            recover(paths)
            print('Sharing stopped and owned desktop changes restored. Login-start preference retained.')
        elif args.command == 'disable':
            disable(paths)
            print('Sharing stopped; login startup disabled.')
        elif args.command == 'remove':
            disable(paths, args.offline)
            remove_configuration(paths)
            print('Owned configuration and credentials removed. You can now remove the package with pacman.')
        elif args.command == 'password':
            if not sys.stdout.isatty():
                raise Error('Run password in an interactive terminal; credentials are never written to status or logs.')
            print(password(paths))
        elif args.command == 'reset-password':
            stopped()
            settings(paths)
            atomic_write(paths.password, new_password() + '\n')
            print('Fresh password saved. Run password to view it.')
        elif args.command == 'doctor':
            config = settings(paths)
            password(paths)
            verify_hooks(paths)
            session_environment(paths)
            print('Selected network address:', resolve_network(config))
            if not active():
                Desktop(paths).physical(config['output'])
                with reserve(resolve_network(config), config['port']):
                    pass
            run('systemctl', 'is-active', '--quiet', 'avahi-daemon.service')
            print('Setup, credential permissions, hooks, network, desktop, and Avahi checks passed. Real Mac connectivity is a separate check.')
        elif args.command == 'firewall':
            config = settings(paths)
            config['address'] = resolve_network(config)
            allow, remove = firewall_commands(config)
            print('If UFW blocks this connection, an administrator can use:\n' + allow + '\nRemove that exact rule with:\n' + remove)
            print('The add-on does not change firewall rules. Existing mDNS access must also be available.')


if __name__ == '__main__':
    os.umask(0o077)
    os.environ['LC_ALL'] = 'C'
    try:
        main()
    except (Error, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
