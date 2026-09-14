"""Exercise ownership, recovery, network revocation and the actual byte relay in isolation."""
import argparse
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import mns_cli as cli
import mns_common as common
import mns_desktop as desktop
import mns_relay as relay
import mns_session as session

ORIGINAL = '-- personal config\ndofile("/usr/share/omarchy/default/hypr/bootstrap.lua")\nrequire("default.hypr.omarchy")\nrequire("hypr.monitors")\n'
CONFIG = {'schema': 1, 'interface': 'eth0', 'connection': 'a121d604-57ca-4b6a-ae17-42e1dc257120',
          'address': '192.168.50.10', 'subnet': '192.168.50.0/24', 'output': 'eDP-1', 'port': 5900,
          'name': 'Test desktop', 'hostname': 'mac-share-test.local', 'virtual': None,
          'transport': 'legacy-vnc', 'accepted_unencrypted': True}
MONITOR = {'name': 'eDP-1', 'width': 1280, 'height': 800, 'refreshRate': 60.0, 'scale': 1,
           'x': 0, 'y': 0, 'mirrorOf': 'none', 'transform': 0}


class Workspace(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='mns-lifecycle-test-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.paths = common.Paths(self.base / 'home', self.base / 'runtime')
        common.private_dir(self.paths.config)
        common.private_dir(self.paths.runtime)
        self.paths.hypr.parent.mkdir(parents=True)
        self.paths.hypr.write_text(ORIGINAL)
        self.env = {'HYPRLAND_INSTANCE_SIGNATURE': 'test-instance', 'WAYLAND_DISPLAY': 'wayland-test'}

    def configure(self, **options):
        args = argparse.Namespace(interface='eth0', output='eDP-1', port=None, virtual=None,
                                  physical=False, name=None, accept_unencrypted=True)
        vars(args).update(options)
        with patch.object(cli, 'stopped'), patch.object(cli, 'session_environment'), \
             patch.object(cli, 'networks', return_value=[{k: CONFIG[k] for k in ('interface', 'connection', 'address', 'subnet')}]), \
             patch.object(cli.Desktop, 'reload'), patch.object(cli.Desktop, 'query', return_value=[MONITOR]), \
             patch.object(cli.Desktop, 'physical', return_value=MONITOR), \
             patch.object(cli, 'reserve'), patch.object(cli, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')):
            cli.configure(self.paths, args)

    def journal(self, created=False, instance='test-instance'):
        common.write_json(self.paths.journal, {'schema': 1, 'instance': instance, 'wayland': 'wayland-test',
                          'output': 'eDP-1', 'monitor': MONITOR, 'created': created,
                          'virtual': [1920, 1200] if created else None, 'workspace': 1, 'workspaces': [1, 2]})
        common.atomic_write(self.paths.runtime / 'keyboard', 'enabled\n')
        common.atomic_write(self.paths.runtime / 'display.lua', '-- owned runtime state\n')

    def compositor_socket(self, instance='test-instance'):
        path = self.paths.runtime.parent / 'hypr' / instance / '.socket.sock'
        path.parent.mkdir(parents=True)
        connection = socket.socket(socket.AF_UNIX)
        self.addCleanup(connection.close)
        connection.bind(str(path))


class ConfigurationTests(Workspace):
    def test_setup_then_remove_preserves_personal_config_exactly(self):
        self.configure()
        desktop.verify_hooks(self.paths)
        self.assertEqual(len(common.password(self.paths)), 8)
        self.assertEqual(self.paths.password.stat().st_mode & 0o777, 0o600)
        with patch.dict(os.environ, {}, clear=True):
            cli.remove_configuration(self.paths)
        self.assertEqual(self.paths.hypr.read_text(), ORIGINAL)
        self.assertFalse(self.paths.config.exists())

    def test_setup_is_repeatable_and_preserves_credential(self):
        self.configure()
        secret = common.password(self.paths)
        self.configure(port=5902, virtual='1920x1200')
        self.assertEqual(common.password(self.paths), secret)
        self.assertEqual(common.settings(self.paths)['virtual'], [1920, 1200])
        self.assertEqual(common.settings(self.paths)['port'], 5902)
        self.assertEqual(self.paths.hypr.read_text().count('BEGIN mac-native-screenshare keyboard'), 1)

    def test_explicit_invalid_port_does_not_fall_back_to_default(self):
        with self.assertRaises(common.Error):
            self.configure(port=0)
        self.assertFalse(self.paths.settings.exists())

    def test_unexpected_runtime_path_is_rejected_before_socket_use(self):
        with patch.dict(os.environ, self.env), self.assertRaises(common.Error):
            session.session_environment(self.paths)

    def test_removal_preserves_later_edits_and_unrecognized_files(self):
        self.configure()
        self.paths.hypr.write_text(self.paths.hypr.read_text() + '-- added by user\n')
        (self.paths.config / 'personal-notes').write_text('keep')
        with patch.dict(os.environ, {}, clear=True):
            cli.remove_configuration(self.paths)
        self.assertEqual(self.paths.hypr.read_text(), ORIGINAL + '-- added by user\n')
        self.assertEqual((self.paths.config / 'personal-notes').read_text(), 'keep')

    def test_modified_owned_block_is_not_deleted(self):
        self.configure()
        text = self.paths.hypr.read_text().replace('dofile(path).keyboard(hl,', 'dofile(path).keyboard(other,')
        self.paths.hypr.write_text(text)
        with self.assertRaises(common.Error):
            cli.remove_configuration(self.paths)
        self.assertEqual(self.paths.hypr.read_text(), text)
        self.assertTrue(self.paths.password.exists())

    def test_failed_setup_reload_rolls_back(self):
        calls = 0
        def reload(_self):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise common.Error('Simulated invalid generated hook')
        args = argparse.Namespace(interface='eth0', output='eDP-1', port=None, virtual=None, physical=False, name=None, accept_unencrypted=True)
        with patch.object(cli, 'stopped'), patch.object(cli, 'session_environment'), \
             patch.object(cli, 'networks', return_value=[{k: CONFIG[k] for k in ('interface', 'connection', 'address', 'subnet')}]), \
             patch.object(cli.Desktop, 'reload', reload), patch.object(cli.Desktop, 'query', return_value=[MONITOR]), \
             patch.object(cli.Desktop, 'physical', return_value=MONITOR), patch.object(cli, 'reserve'), \
             patch.object(cli, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')):
            with self.assertRaises(common.Error):
                cli.configure(self.paths, args)
        self.assertEqual(self.paths.hypr.read_text(), ORIGINAL)
        self.assertFalse(self.paths.settings.exists())
        self.assertFalse(self.paths.password.exists())

    def test_partial_setup_is_removable(self):
        self.configure()
        self.paths.settings.unlink()  # Power loss before final settings commit.
        with patch.dict(os.environ, {}, clear=True):
            cli.remove_configuration(self.paths)
        self.assertEqual(self.paths.hypr.read_text(), ORIGINAL)

    def test_prototype_and_nonstandard_config_are_rejected(self):
        for text in (ORIGINAL + '-- mac-shortcuts.lua\n', 'require("hypr.bindings")\n'):
            with self.assertRaises(common.Error):
                desktop.add_hooks(text, desktop.hook_blocks())

    def test_roundtrip_without_final_newline(self):
        self.paths.hypr.write_text(ORIGINAL.rstrip('\n'))
        self.configure()
        with patch.dict(os.environ, {}, clear=True):
            cli.remove_configuration(self.paths)
        self.assertEqual(self.paths.hypr.read_text(), ORIGINAL.rstrip('\n'))

    def test_symlink_and_shared_credential_rejected(self):
        target = self.base / 'secret'
        target.write_text('testpass\n')
        self.paths.password.symlink_to(target)
        with self.assertRaises(OSError):
            common.password(self.paths)
        with self.assertRaises(common.Error):
            common.atomic_write(self.paths.password, 'abcdefgh\n')
        self.paths.password.unlink()
        self.paths.password.write_text('testpass\n')
        self.paths.password.chmod(0o644)
        with self.assertRaises(common.Error):
            common.password(self.paths)

    def test_schema_and_transport_cannot_silently_change(self):
        for update in ({'schema': 2}, {'accepted_unencrypted': False}, {'subnet': '0.0.0.0/0'},
                       {'subnet': '169.254.0.0/16'}, {'interface': 'eth0; touch x'}, {'port': 0},
                       {'virtual': [100, 200]}, {'name': 'name\npassword=x'}):
            with self.assertRaises((common.Error, ValueError)):
                common.validate_settings(dict(CONFIG, **update))

    def test_status_never_contains_credential(self):
        self.configure()
        with patch.object(cli, 'systemctl', return_value=subprocess.CompletedProcess([], 0, 'ActiveState=inactive\n', '')):
            self.assertNotIn(common.password(self.paths), json.dumps(cli.status(self.paths)))

    def test_session_lock_prevents_concurrent_restore(self):
        with common.lock(self.paths, 'session.lock'):
            with self.assertRaises(common.Error):
                with common.lock(self.paths, 'session.lock'):
                    self.fail('Concurrent recovery acquired the session lock')

    def test_exec_stop_recovery_does_not_need_command_lock(self):
        with common.lock(self.paths):
            with patch.object(cli, 'Paths', return_value=self.paths), patch('sys.argv', ['mns', 'recover']):
                cli.main()


class NetworkTests(unittest.TestCase):
    def test_dhcp_rebind_on_same_profile_and_subnet(self):
        with patch.object(common, 'network_state', return_value=(CONFIG['connection'], [ipaddress('192.168.50.22/24')])):
            self.assertEqual(common.resolve_network(CONFIG), '192.168.50.22')
            with self.assertRaises(common.Error):
                common.resolve_network(CONFIG, CONFIG['address'])

    def test_changed_profile_and_prefix_are_rejected(self):
        for connection, address in [('b121d604-57ca-4b6a-ae17-42e1dc257120', '192.168.50.10/24'),
                                    (CONFIG['connection'], '192.168.50.10/16')]:
            with patch.object(common, 'network_state', return_value=(connection, [ipaddress(address)])):
                with self.assertRaises(common.Error):
                    common.resolve_network(CONFIG)

    def test_peers_are_constrained_to_selected_subnet(self):
        self.assertTrue(relay.allowed_peer('192.168.50.20', CONFIG['subnet']))
        for peer in ('192.168.51.20', '10.0.0.2', '192.168.50.0', '192.168.50.255', '::1'):
            self.assertFalse(relay.allowed_peer(peer, CONFIG['subnet']))

    def test_firewall_command_is_scoped_and_reversible(self):
        allow, remove = cli.firewall_commands(CONFIG)
        self.assertIn('in on eth0 proto tcp from 192.168.50.0/24 to 192.168.50.10 port 5900', allow)
        self.assertEqual(remove, allow.replace('ufw allow', 'ufw delete allow', 1))


def ipaddress(value):
    import ipaddress as module
    return module.IPv4Interface(value)


class RecoveryTests(Workspace):
    def test_old_login_journal_does_not_mutate_new_desktop(self):
        self.journal(created=True)
        with patch.object(desktop.Desktop, 'call', side_effect=AssertionError('Must not touch a different compositor')):
            desktop.Desktop(self.paths, self.env).restore()
        self.assertFalse(self.paths.journal.exists())
        self.assertFalse((self.paths.runtime / 'keyboard').exists())

    def test_crash_restores_owned_virtual_and_keeps_unrelated_output(self):
        self.compositor_socket()
        self.journal(created=True)
        monitors = [dict(MONITOR), {'name': desktop.VIRTUAL}, {'name': 'HDMI-A-1'}]
        calls = []
        def call(*args):
            calls.append(args)
            if args == ('output', 'remove', desktop.VIRTUAL):
                monitors[:] = [m for m in monitors if m['name'] != desktop.VIRTUAL]
            return 'ok'
        instance = desktop.Desktop(self.paths, self.env)
        def query(kind):
            return {'id': 2} if kind == 'activeworkspace' else [{'id': 2}] if kind == 'workspaces' else monitors
        with patch.object(instance, 'query', side_effect=query), patch.object(instance, 'call', side_effect=call), \
             patch.object(instance, 'rule'), patch.object(instance, 'reload'), patch.object(desktop.time, 'sleep'):
            instance.restore()
            instance.restore()
        self.assertIn({'name': 'HDMI-A-1'}, monitors)
        self.assertEqual(calls.count(('output', 'remove', desktop.VIRTUAL)), 1)
        self.assertFalse(self.paths.journal.exists())

    def test_missing_physical_display_keeps_recovery_journal(self):
        self.compositor_socket()
        self.journal(created=True)
        instance = desktop.Desktop(self.paths, self.env)
        with patch.object(instance, 'query', side_effect=lambda kind: {'id': 1} if kind == 'activeworkspace' else [{'name': desktop.VIRTUAL}]), \
             patch.object(instance, 'call', side_effect=AssertionError('Do not remove the sole display')):
            with self.assertRaises(common.Error):
                instance.restore()
        self.assertTrue(self.paths.journal.exists())
        self.assertFalse((self.paths.runtime / 'keyboard').exists())

    def test_failed_restore_retains_state_for_retry(self):
        self.compositor_socket()
        self.journal()
        with patch.object(desktop.Desktop, 'query', side_effect=lambda kind: {'id': 1} if kind == 'activeworkspace' else [MONITOR]), \
             patch.object(desktop.Desktop, 'reload', side_effect=common.Error('compositor unavailable')):
            with self.assertRaises(common.Error):
                desktop.Desktop(self.paths, self.env).restore()
        self.assertTrue(self.paths.journal.exists())


class RelayTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='mns-relay-test-')
        self.backend = Path(self.temp.name) / 'vnc.sock'
        self.connections = 0
        self.backend_writers = set()
        async def echo(reader, writer):
            self.connections += 1
            self.backend_writers.add(writer)
            try:
                while data := await reader.read(65536):
                    writer.write(data)
                    await writer.drain()
            finally:
                writer.close()
                self.backend_writers.discard(writer)
        self.server = await asyncio.start_unix_server(echo, str(self.backend))
        listener = relay.reserve('127.0.0.1', 0)
        self.port = listener.getsockname()[1]
        self.relay = relay.Relay(listener, self.backend, '127.0.0.0/8', limit=1)
        await self.relay.start()

    async def asyncTearDown(self):
        await self.relay.close()
        for writer in tuple(self.backend_writers):
            writer.close()
        self.server.close()
        await self.server.wait_closed()
        self.temp.cleanup()

    async def test_bytes_and_revocation_of_established_connection(self):
        reader, writer = await asyncio.open_connection('127.0.0.1', self.port)
        payload = bytes(range(256)) * 400
        writer.write(payload)
        await writer.drain()
        self.assertEqual(await asyncio.wait_for(reader.readexactly(len(payload)), 3), payload)
        await self.relay.close()
        self.assertEqual(await asyncio.wait_for(reader.read(), 2), b'')
        writer.close()
        await writer.wait_closed()
        with self.assertRaises(OSError):
            await asyncio.open_connection('127.0.0.1', self.port)

    async def test_unapproved_peer_never_reaches_backend(self):
        self.relay.subnet = '192.168.50.0/24'
        reader, writer = await asyncio.open_connection('127.0.0.1', self.port)
        self.assertEqual(await asyncio.wait_for(reader.read(), 2), b'')
        self.assertEqual(self.connections, 0)
        writer.close()
        await writer.wait_closed()

    async def test_connection_limit_and_reuse_after_disconnect(self):
        first, writer = await asyncio.open_connection('127.0.0.1', self.port)
        writer.write(b'one')
        await writer.drain()
        self.assertEqual(await first.readexactly(3), b'one')
        second, extra = await asyncio.open_connection('127.0.0.1', self.port)
        self.assertEqual(await asyncio.wait_for(second.read(), 2), b'')
        extra.close()
        writer.close()
        await writer.wait_closed()
        for _ in range(100):
            if not self.relay.tasks:
                break
            await asyncio.sleep(.01)
        third, replacement = await asyncio.open_connection('127.0.0.1', self.port)
        replacement.write(b'two')
        await replacement.drain()
        self.assertEqual(await asyncio.wait_for(third.readexactly(3), 2), b'two')
        replacement.close()
        await replacement.wait_closed()


if __name__ == '__main__':
    unittest.main()
