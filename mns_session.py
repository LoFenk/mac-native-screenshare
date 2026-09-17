"""Supervise one logged-in desktop; revoke network access before recovery."""
import asyncio
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import time

from mns_common import Error, Paths, ROOT, atomic_write, lock, notify, password, read_private, resolve_network, run, settings, write_json
from mns_desktop import Desktop, verify_hooks
from mns_keyboard import Keyboard
from mns_relay import Relay, reserve
from probe import legacy_probe

GENERATED = ('wayvnc.conf', 'vnc.sock', 'control', 'endpoint.json', 'discovery-ready', 'ready.json', 'keyboard.json')


def session_environment(paths):
    if paths.runtime.parent != Path(f'/run/user/{os.getuid()}'):
        raise Error('This preview requires the standard /run/user/UID graphical runtime directory.')
    for key in ('WAYLAND_DISPLAY', 'HYPRLAND_INSTANCE_SIGNATURE'):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', os.environ.get(key, '')):
            raise Error('Run inside the logged-in Hyprland session.')
    if not (paths.runtime.parent / os.environ['WAYLAND_DISPLAY']).is_socket():
        raise Error('The Wayland display is unavailable.')
    if paths.runtime.parent.stat().st_uid != os.getuid():
        raise Error('The session runtime directory belongs to another user.')


def recover(paths):
    Desktop(paths).restore()
    for name in GENERATED:
        (paths.runtime / name).unlink(missing_ok=True)


async def terminate(child):
    if child and child.returncode is None:
        try:
            child.terminate()
        except ProcessLookupError:
            return
        try:
            await asyncio.wait_for(child.wait(), 5)
        except asyncio.TimeoutError:
            child.kill()
            await child.wait()


async def wait_until(predicate, child, stopping, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if stopping.is_set():
            raise Error('Start was cancelled.')
        if child.returncode is not None:
            raise Error('A screen-sharing component exited during startup.')
        if predicate():
            return
        await asyncio.sleep(.1)
    raise Error('A screen-sharing component did not become ready.')


async def serve(paths):
    stopping = asyncio.Event()
    loop = asyncio.get_running_loop()
    for number in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(number, stopping.set)
    server = discovery = relay = listener = None
    watches = []
    desktop = Desktop(paths)
    try:
        session_environment(paths)
        recover(paths)
        config = settings(paths)
        secret = password(paths)
        verify_hooks(paths)
        for file in ('bin/wayvnc', 'bin/wayvncctl', 'lib/libneatvnc.so.1'):
            if not (ROOT / file).is_file():
                raise Error('Reinstall the package: a required private VNC component is missing.')
        # Login can precede DHCP/Avahi. Wait without changing the desktop or opening a port.
        deadline = time.monotonic() + 45
        while True:
            try:
                address = resolve_network(config)
                run('systemctl', 'is-active', '--quiet', 'avahi-daemon.service', timeout=3)
                break
            except (Error, subprocess.SubprocessError):
                if stopping.is_set() or time.monotonic() >= deadline:
                    print('Selected network or Avahi unavailable; sharing remains stopped.', flush=True)
                    return 0
                await asyncio.sleep(1)
        listener = reserve(address, config['port'])
        before = desktop.begin(config)
        backend = paths.runtime / 'vnc.sock'
        control = paths.runtime / 'control'
        keyboard = Keyboard(paths, desktop)
        atomic_write(paths.runtime / 'wayvnc.conf', '\n'.join([
            'address=unix:' + str(backend), 'enable_auth=true', 'enable_pam=false',
            'password=' + secret, 'relax_encryption=true', 'allow_broken_crypto=true',
            *keyboard.config_lines(), '']))
        environment = dict(os.environ, NVNC_APPLE_CLIPBOARD='1', LD_LIBRARY_PATH=str(ROOT / 'lib'))
        environment.pop('NOTIFY_SOCKET', None)
        server = await asyncio.create_subprocess_exec(str(ROOT / 'bin/wayvnc'), '-r', '-R',
                    '-C', str(paths.runtime / 'wayvnc.conf'), '-S', str(control),
                    '-o', config['output'], '-n', config['name'], '-L', 'warning', env=environment)
        def server_ready():
            return control.is_socket() and run(ROOT / 'bin/wayvncctl', '-S', control, 'version', check=False, timeout=2).returncode == 0
        await wait_until(server_ready, server, stopping, 10)
        keyboard.record()
        # Verify password enforcement before any public peer can reach the backend.
        await asyncio.to_thread(legacy_probe, str(backend), secret.encode(), True)
        del secret
        desktop.activate_virtual(before, control)
        desktop.guard(config)
        resolve_network(config, address)
        relay = Relay(listener, backend, config['subnet'])
        await relay.start()
        write_json(paths.runtime / 'endpoint.json', {'config': config, 'address': address})
        discovery = await asyncio.create_subprocess_exec('/usr/bin/python3', str(ROOT / 'mns_discovery.py'), env=environment)
        await wait_until(lambda: (paths.runtime / 'discovery-ready').is_file(), discovery, stopping, 12)
        resolve_network(config, address)
        write_json(paths.runtime / 'ready.json', {'address': address, 'port': config['port'],
                   'hostname': config['hostname'], 'output': config['output'], 'virtual': config['virtual']})
        notify('READY=1\nSTATUS=Sharing on the selected private LAN; native VNC transport is unencrypted.')
        print(f'Sharing ready: {config["hostname"]}:{config["port"]}; transport is unencrypted.', flush=True)
        version = (ROOT / 'VERSION').read_text()
        def check_state():
            try:
                if not (ROOT / 'VERSION').exists() or (ROOT / 'VERSION').read_text() != version:
                    print('Package changed; sharing stopped. Run start after the upgrade.', flush=True)
                    return False
                resolve_network(config, address)
                verify_hooks(paths)
                desktop.guard(config)
                keyboard.sync()
            except (Error, OSError, ValueError, subprocess.SubprocessError) as error:
                print(str(error), flush=True)
                return False
            return True

        async def guard():
            while await asyncio.to_thread(check_state):
                await asyncio.sleep(1)

        watches = [asyncio.create_task(server.wait()), asyncio.create_task(discovery.wait()),
                   asyncio.create_task(stopping.wait()), asyncio.create_task(guard())]
        done, _ = await asyncio.wait(watches, return_when=asyncio.FIRST_COMPLETED)
        if watches[0] in done and not stopping.is_set():
            raise Error('The private VNC server exited.')
        if watches[1] in done:
            print('Discovery or network changed; sharing stopped. Run start to retry.', flush=True)
        if watches[3] in done:
            watches[3].result()
        return 0
    finally:
        notify('STOPPING=1\nSTATUS=Stopping sharing and restoring desktop changes.')
        (paths.runtime / 'ready.json').unlink(missing_ok=True)
        for watch in watches:
            watch.cancel()
        await asyncio.gather(*watches, return_exceptions=True)
        # Close new/existing TCP streams before touching display or shortcut state.
        if relay:
            await relay.close()
        elif listener:
            listener.close()
        await terminate(discovery)
        await terminate(server)
        recover(paths)


def main():
    paths = Paths()
    with lock(paths, 'session.lock'):
        return asyncio.run(serve(paths))


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (Error, OSError, ValueError, subprocess.SubprocessError) as error:
        print(str(error), flush=True)
        raise SystemExit(1)
