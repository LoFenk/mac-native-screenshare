"""Shared configuration and ownership rules for the standalone add-on."""
import contextlib
import fcntl
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import tempfile
import uuid

NAME = 'mac-native-screenshare'
UNIT = NAME + '.service'
ROOT = Path(__file__).resolve().parent
SCHEMA = 1
PRIVATE_NETWORKS = tuple(map(ipaddress.IPv4Network, ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')))


class Error(RuntimeError):
    pass


def run(*args, check=True, env=None, timeout=10):
    result = subprocess.run([str(a) for a in args], capture_output=True, text=True,
                            timeout=timeout, env=env)
    if check and result.returncode:
        raise Error(f'{args[0]} failed: {(result.stderr or result.stdout).strip()}')
    return result.stdout.strip() if check else result


class Paths:
    def __init__(self, home=None, runtime=None):
        self.home = Path(home or Path.home())
        # Fixed per-user locations make offline package removal discoverable.
        self.config = self.home / '.config' / NAME
        self.hypr = self.home / '.config/hypr/hyprland.lua'
        self.runtime = Path(runtime or os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}')) / NAME
        self.settings = self.config / 'settings.json'
        self.ownership = self.config / 'ownership.json'
        self.password = self.config / 'password'
        self.journal = self.runtime / 'session.json'


def private_dir(path):
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise Error(f'Expected a private directory owned by this user: {path}')


def read_private(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'r') as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise Error(f'Expected a private regular file owned by this user: {path}')
        return source.read()


def atomic_write(path, text, mode=0o600):
    if path.is_symlink():
        raise Error(f'Refusing to replace a symlink: {path}')
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as out:
            os.fchmod(out.fileno(), mode)
            out.write(text)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        Path(temporary).unlink(missing_ok=True)


def write_json(path, data):
    atomic_write(path, json.dumps(data, indent=2) + '\n')


@contextlib.contextmanager
def lock(paths, name='command.lock'):
    private_dir(paths.runtime)
    fd = os.open(paths.runtime / name, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise Error('Another screen-sharing operation is running.') from error
        yield
    finally:
        os.close(fd)


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}', value):
        raise Error('Invalid interface or output name.')
    return value


def validate_settings(data):
    if data.get('schema') != SCHEMA:
        raise Error('Unsupported settings version. Keep your files and use a compatible package.')
    identifier(data['interface'])
    identifier(data['output'])
    uuid.UUID(data['connection'])
    network = ipaddress.IPv4Network(data['subnet'])
    if not any(network.subnet_of(n) for n in PRIVATE_NETWORKS) or network.prefixlen > 30:
        raise Error('Choose an RFC1918 private LAN subnet with usable host addresses.')
    if type(data['port']) is not int or not 1024 <= data['port'] <= 65535:
        raise Error('Port must be between 1024 and 65535.')
    if data.get('transport') != 'legacy-vnc' or data.get('accepted_unencrypted') is not True:
        raise Error('Setup must explicitly accept unencrypted native VNC transport.')
    if not re.fullmatch(r'[a-z0-9-]{1,50}\.local', data['hostname']):
        raise Error('Invalid discovery hostname.')
    if not isinstance(data['name'], str) or not 1 <= len(data['name'].encode()) <= 63 or any(ord(c) < 32 for c in data['name']):
        raise Error('Discovery name must be 1–63 UTF-8 bytes without control characters.')
    size = data.get('virtual')
    if size is not None and (not isinstance(size, list) or len(size) != 2 or
                            any(type(n) is not int for n in size) or
                            not 320 <= size[0] <= 8192 or not 200 <= size[1] <= 8192):
        raise Error('Virtual display size must be between 320x200 and 8192x8192.')
    return data


def settings(paths):
    return validate_settings(json.loads(read_private(paths.settings)))


def password(paths):
    value = read_private(paths.password).strip()
    if not re.fullmatch(r'[A-Za-z0-9+/]{8}', value):
        raise Error('Invalid saved credential. Run reset-password while sharing is stopped.')
    return value


def new_password():
    import base64
    return base64.b64encode(secrets.token_bytes(6)).decode()


def network_state(interface):
    identifier(interface)
    lines = run('nmcli', '--escape', 'no', '-g', 'GENERAL.CON-UUID,IP4.ADDRESS',
                'device', 'show', interface, timeout=3).splitlines()
    if not lines:
        raise Error('The selected network is not connected.')
    addresses = []
    for line in lines[1:]:
        try:
            addresses.append(ipaddress.IPv4Interface(line))
        except ValueError:
            continue
    return lines[0], addresses


def resolve_network(config, expected=None):
    connection, addresses = network_state(config['interface'])
    network = ipaddress.IPv4Network(config['subnet'])
    matches = [a for a in addresses if a.network == network and a.ip not in
               (network.network_address, network.broadcast_address)]
    if connection != config['connection'] or len(matches) != 1:
        raise Error('The selected network profile or subnet is unavailable or ambiguous.')
    address = str(matches[0].ip)
    if expected is not None and address != expected:
        raise Error('The selected host address changed. Start sharing again after checking the network.')
    return address


def notify(message):
    import socket
    address = os.environ.get('NOTIFY_SOCKET')
    if address:
        if address.startswith('@'):
            address = '\0' + address[1:]
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as connection:
            try:
                connection.connect(address)
                connection.sendall(message.encode())
            except OSError:
                # A disappearing service manager must not prevent cleanup.
                pass
