#!/usr/bin/python3
"""Opt-in keyboard/IME regression check using a private VNC server and scratch Foot.

Requires the installed Hyprland shortcut hook. Changes no desktop configuration.
Run with --live-desktop while the input method (for example Fcitx5) is running.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import struct
import subprocess
import sys
import tempfile
import time

from probe import read_exact, vnc_response


def capture(path):
    import select
    import termios
    import tty
    previous = termios.tcgetattr(0)
    try:
        tty.setraw(0)
        path.write_bytes(b'')
        path.with_suffix('.ready').touch()
        deadline = time.monotonic() + 30
        with path.open('ab', buffering=0) as output:
            while time.monotonic() < deadline:
                if select.select([0], [], [], .1)[0]:
                    data = os.read(0, 4096)
                    if not data:
                        break
                    output.write(data)
    finally:
        termios.tcsetattr(0, termios.TCSANOW, previous)


def stop(child):
    child.terminate()
    try:
        child.wait(timeout=3)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait()


def check(runtime):
    def active():
        return json.loads(subprocess.check_output(['hyprctl', '-j', 'activewindow']))

    with tempfile.TemporaryDirectory(prefix='mns-keyboard-', dir=os.environ['XDG_RUNTIME_DIR']) as directory:
        scratch = Path(directory)
        secret = secrets.token_hex(4)
        config = scratch / 'wayvnc.conf'
        config.write_text('\n'.join([
            'address=unix:' + str(scratch / 'vnc.sock'),
            'enable_auth=true', 'enable_pam=false', 'password=' + secret,
            'relax_encryption=true', 'allow_broken_crypto=true',
            'xkb_layout=us,us', 'xkb_variant=mac,altgr-weur',
            'xkb_model=pc105', 'xkb_rules=evdev', 'xkb_options=lv3:ralt_alt', '',
        ]))
        config.chmod(0o600)
        server = subprocess.Popen([
            str(runtime / 'bin/wayvnc'), '-R', '-C', str(config),
            '-S', str(scratch / 'control'), '-L', 'error',
        ], env=dict(os.environ, LD_LIBRARY_PATH=str(runtime / 'lib')))
        terminal = connection = None
        try:
            for _ in range(50):
                if (scratch / 'control').is_socket():
                    break
                assert server.poll() is None, 'Test server exited'
                time.sleep(.1)
            output = scratch / 'input.bin'
            terminal = subprocess.Popen([
                'foot', '--app-id=foot', '--title=Temporary keyboard check',
                sys.executable, str(Path(__file__).resolve()), '--capture', str(output),
            ])
            for _ in range(50):
                if output.with_suffix('.ready').exists() and active().get('pid') == terminal.pid:
                    break
                time.sleep(.1)
            assert active().get('pid') == terminal.pid, 'Scratch terminal not focused'
            connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            connection.settimeout(3)
            connection.connect(str(scratch / 'vnc.sock'))
            assert read_exact(connection, 12).startswith(b'RFB 003.')
            connection.sendall(b'RFB 003.003\n')
            assert struct.unpack('!I', read_exact(connection, 4))[0] == 2
            connection.sendall(vnc_response(secret.encode(), read_exact(connection, 16)))
            assert struct.unpack('!I', read_exact(connection, 4))[0] == 0
            connection.sendall(b'\x01')
            initial = read_exact(connection, 24)
            read_exact(connection, struct.unpack('!I', initial[20:24])[0])

            def key(symbol, down):
                assert active().get('pid') == terminal.pid, 'Focus changed; aborting input'
                connection.sendall(struct.pack('!BBHI', 4, down, 0, symbol))
                time.sleep(.075)

            samples = {}

            def sample(name, events, expected):
                start = len(output.read_bytes())
                for symbol, down in events:
                    key(symbol, down)
                time.sleep(.2)
                samples[name] = output.read_bytes()[start:].hex()
                assert samples[name] == expected, samples

            accent = [(0xe9, 1), (0xe9, 0)]
            option_up = [(0xffe7, 1), (0xff52, 1), (0xff52, 0), (0xffe7, 0)]
            sample('eacute', accent, 'c3a9')
            sample('plain_up', [(0xff52, 1), (0xff52, 0)], '1b5b41')
            sample('option_up', option_up, '1b5b313b3341')
            ctl = [str(runtime / 'bin/wayvncctl'), '-S', str(scratch / 'control'), 'keyboard-set']
            key(0xffe7, 1)
            busy = subprocess.run(ctl + ['fr,us', 'oss,altgr-weur'], capture_output=True, text=True)
            assert busy.returncode and 'busy' in busy.stdout + busy.stderr, busy
            key(0xffe7, 0)
            for layout, variant, label in [('fr,us', 'oss,altgr-weur', 'french'),
                                            ('us,us', 'mac,altgr-weur', 'restored')]:
                subprocess.run(ctl + [layout, variant], check=True, capture_output=True)
                time.sleep(.3)
                sample(label + '_eacute', accent, 'c3a9')
                sample(label + '_option_up', option_up, '1b5b313b3341')
            print(json.dumps({'same_vnc_connection': True, 'busy_update_deferred': True, **samples}, indent=2))
        finally:
            if connection:
                connection.close()
            if terminal:
                stop(terminal)
            stop(server)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live-desktop', action='store_true')
    parser.add_argument('--runtime', type=Path, default=Path('/usr/lib/mac-native-screenshare'))
    parser.add_argument('--capture', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.capture:
        capture(args.capture)
    elif args.live_desktop:
        check(args.runtime.resolve())
    else:
        parser.error('--live-desktop is required: this check opens and types into a scratch terminal')
