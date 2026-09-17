"""Run real private WayVNC detached; simulate only desktop, NM, and Avahi lifecycle."""
import argparse
import asyncio
import importlib.util
import os
from pathlib import Path
import shutil
import socket
import tempfile
import unittest
from unittest.mock import patch

import mns_common as common
import mns_session as session

RUNTIME = None


class SupervisorTests(unittest.IsolatedAsyncioTestCase):
    async def exercise(self, failure, password='Abcd1234'):
        with tempfile.TemporaryDirectory(prefix='mns-supervisor-') as directory:
            base = Path(directory)
            paths = common.Paths(base / 'home', base / 'run')
            common.private_dir(paths.config)
            common.private_dir(paths.runtime)
            root = base / 'package'
            root.mkdir()
            (root / 'bin').symlink_to(RUNTIME / 'bin', target_is_directory=True)
            (root / 'lib').symlink_to(RUNTIME / 'lib', target_is_directory=True)
            (root / 'VERSION').write_text('test-version\n')
            common.atomic_write(paths.password, common.validate_password(password) + '\n')
            with socket.socket() as free:
                free.bind(('127.0.0.1', 0))
                port = free.getsockname()[1]
            config = {'interface': 'test0', 'output': 'test-output', 'virtual': None,
                      'address': '127.0.0.1', 'subnet': '127.0.0.0/8', 'port': port,
                      'name': 'Isolated test', 'hostname': 'isolated-test.local'}
            events, children = [], []
            ready = asyncio.Event()
            spawn = asyncio.create_subprocess_exec
            def recover(_):
                events.append('restore')
                for name in session.GENERATED:
                    (paths.runtime / name).unlink(missing_ok=True)
            class Desktop:
                def __init__(self, _):
                    pass
                def query(self, kind):
                    if kind == 'devices':
                        return {'keyboards': [{'name': 'physical-keyboard', 'layout': 'us', 'variant': 'mac', 'active_layout_index': 0}]}
                    raise AssertionError(kind)
                def begin(self, _):
                    events.append('begin')
                    return {'virtual': None}
                def activate_virtual(self, *_):
                    pass
                def guard(self, *_):
                    pass
            class Relay(session.Relay):
                async def close(self):
                    events.append('revoke')
                    await super().close()
            async def subprocess_exec(*args, **kwargs):
                if args[0] == str(root / 'bin/wayvnc'):
                    # -D guarantees this real VNC process never attaches to any desktop.
                    args = (args[0], '-D', '-C', str(paths.runtime / 'wayvnc.conf'),
                            '-S', str(paths.runtime / 'control'), '-L', 'quiet')
                else:
                    self.assertEqual(args[:2], ('/usr/bin/python3', str(root / 'mns_discovery.py')))
                    # Stand-in for an Avahi publisher that loses its selected network.
                    code = 'from pathlib import Path; import time; Path(' + repr(str(paths.runtime / 'discovery-ready')) + ').write_text("ready"); time.sleep(1); raise SystemExit(3)'
                    args = ('/usr/bin/python3', '-c', code)
                child = await spawn(*args, **kwargs)
                children.append(child)
                return child
            def notification(message):
                if message.startswith('READY=1'):
                    events.append('ready')
                    ready.set()
                    if failure == 'server':
                        children[0].kill()
            def network(*_):
                return '127.0.0.1'
            def command(*args, **kwargs):
                if args[0] == 'systemctl':
                    return ''
                return common.run(*args, **kwargs)
            with patch.object(session, 'ROOT', root), patch.object(session, 'settings', return_value=config), \
                 patch.object(session, 'session_environment'), patch.object(session, 'verify_hooks'), \
                 patch.object(session, 'resolve_network', side_effect=network), patch.object(session, 'Desktop', Desktop), \
                 patch.object(session, 'recover', side_effect=recover), patch.object(session, 'notify', side_effect=notification), \
                 patch.object(session, 'Relay', Relay), patch.object(session, 'run', side_effect=command), \
                 patch.object(session.asyncio, 'create_subprocess_exec', side_effect=subprocess_exec):
                task = asyncio.create_task(session.serve(paths))
                try:
                    await asyncio.wait_for(ready.wait(), 8)
                    if failure == 'network':
                        reader, writer = await asyncio.open_connection('127.0.0.1', port)
                        self.assertTrue((await asyncio.wait_for(reader.readexactly(12), 3)).startswith(b'RFB '))
                        self.assertEqual(await asyncio.wait_for(task, 5), 0)
                        self.assertEqual(await asyncio.wait_for(reader.read(), 2), b'')
                        writer.close()
                        await writer.wait_closed()
                    else:
                        with self.assertRaises(common.Error):
                            await asyncio.wait_for(task, 5)
                finally:
                    if not task.done():
                        task.cancel()
                        await asyncio.gather(task, return_exceptions=True)
            self.assertLess(events.index('revoke'), len(events) - 1)
            self.assertEqual(events[-1], 'restore')
            self.assertTrue(all(child.returncode is not None for child in children))
            self.assertFalse((paths.runtime / 'wayvnc.conf').exists())
            with self.assertRaises(OSError):
                await asyncio.open_connection('127.0.0.1', port)

    async def test_keyboard_control_validates_maps_without_attaching_to_desktop(self):
        with tempfile.TemporaryDirectory(prefix='mns-keyboard-control-') as directory:
            root = Path(directory)
            config, control = root / 'wayvnc.conf', root / 'control'
            config.write_text('address=unix:' + str(root / 'vnc.sock') + '\nxkb_options=lv3:ralt_alt\n')
            child = await asyncio.create_subprocess_exec(str(RUNTIME / 'bin/wayvnc'), '-D',
                        '-C', str(config), '-S', str(control), '-L', 'quiet',
                        env=dict(os.environ, LD_LIBRARY_PATH=str(RUNTIME / 'lib')))
            try:
                for _ in range(50):
                    if control.is_socket(): break
                    await asyncio.sleep(.05)
                self.assertTrue(control.is_socket())
                def call(*args):
                    return common.run(RUNTIME / 'bin/wayvncctl', '-S', control,
                                      'keyboard-set', *args, check=False)
                for args in [('us,us', 'mac,altgr-weur'), ('fr,us', 'oss,altgr-weur'), ('de', '')]:
                    self.assertEqual((await asyncio.to_thread(call, *args)).returncode, 0)
                for args in [('bad_nonexistent_layout', ''), ('us', 'bad_nonexistent_variant'), ('u' * 256, ''), ('us',)]:
                    self.assertNotEqual((await asyncio.to_thread(call, *args)).returncode, 0)
                self.assertEqual((await asyncio.to_thread(call, 'us', '')).returncode, 0)
                self.assertIsNone(child.returncode)
            finally:
                await session.terminate(child)

    async def test_network_loss_revokes_real_client_before_restore(self):
        await self.exercise('network')

    async def test_server_crash_cleans_children_listener_and_credentials(self):
        await self.exercise('server')

    async def test_custom_passwords_authenticate_with_real_detached_server(self):
        for password in ('x', 'a b#=!"', '-secret'):
            with self.subTest(password=password):
                await self.exercise('network', password)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    args, remaining = parser.parse_known_args()
    RUNTIME = args.runtime.resolve()
    unittest.main(argv=[__file__, *remaining])
