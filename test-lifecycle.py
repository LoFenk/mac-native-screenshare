"""Exercise ownership, recovery, network revocation and the actual byte relay in isolation."""
import argparse
import asyncio
import importlib.util
import io
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

    def configure(self, interactive=False, **options):
        args = argparse.Namespace(interface='eth0', output='eDP-1', port=None, virtual=None,
                                  physical=False, name=None, accept_unencrypted=True, skip_firewall=False)
        vars(args).update(options)
        with patch.object(cli, 'stopped'), patch.object(cli, 'session_environment'), \
             patch.object(cli, 'networks', return_value=[{k: CONFIG[k] for k in ('interface', 'connection', 'address', 'subnet')}]), \
             patch.object(cli.Desktop, 'reload'), patch.object(cli.Desktop, 'query', return_value=[MONITOR]), \
             patch.object(cli.Desktop, 'physical', return_value=MONITOR), \
             patch.object(cli, 'resolve_network', return_value=CONFIG['address']), \
             patch.object(cli.sys.stdin, 'isatty', return_value=interactive), \
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
        args = argparse.Namespace(interface='eth0', output='eDP-1', port=None, virtual=None, physical=False, name=None, accept_unencrypted=True, skip_firewall=False)
        with patch.object(cli, 'stopped'), patch.object(cli, 'session_environment'), \
             patch.object(cli, 'networks', return_value=[{k: CONFIG[k] for k in ('interface', 'connection', 'address', 'subnet')}]), \
             patch.object(cli.Desktop, 'reload', reload), patch.object(cli.Desktop, 'query', return_value=[MONITOR]), \
             patch.object(cli.Desktop, 'physical', return_value=MONITOR), patch.object(cli, 'reserve'), \
             patch.object(cli, 'offer_firewall') as firewall, \
             patch.object(cli, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')):
            with self.assertRaises(common.Error):
                cli.configure(self.paths, args)
        firewall.assert_not_called()
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


class FirewallTests(Workspace):
    def setUp(self):
        super().setUp()
        self.output = io.StringIO()
        self.enterContext(patch.object(cli.sys, 'stdout', self.output))
        self.stdin_tty = self.enterContext(patch.object(cli.sys.stdin, 'isatty', return_value=True))
        self.stdout_tty = self.enterContext(patch.object(self.output, 'isatty', return_value=True))
        self.resolve = self.enterContext(patch.object(cli, 'resolve_network', return_value=CONFIG['address']))
        self.available = self.enterContext(patch.object(cli.os, 'access', return_value=True))
        self.confirm = self.enterContext(patch('builtins.input', return_value='no'))
        self.execute = self.enterContext(patch.object(cli.subprocess, 'run'))

    def test_new_and_repeated_setup_prompt_after_saving_and_keep_credentials(self):
        def confirm(question):
            desktop.verify_hooks(self.paths)
            self.assertEqual(common.settings(self.paths)['interface'], 'eth0')
            common.password(self.paths)
            self.assertIn('[y/N]', question)
            self.execute.assert_not_called()
            return 'no'
        self.confirm.side_effect = confirm
        self.configure(interactive=True)
        secret = common.password(self.paths)
        self.configure(interactive=True, port=5902)
        self.assertEqual(self.confirm.call_count, 2)
        self.assertEqual(common.password(self.paths), secret)
        self.assertEqual(common.settings(self.paths)['port'], 5902)
        self.execute.assert_not_called()

    def test_approval_previews_exact_scope_before_only_ufw_is_elevated(self):
        allow, remove = cli.firewall_commands(CONFIG)
        def confirm(question):
            self.assertIn(allow, self.output.getvalue())
            self.assertIn(remove, self.output.getvalue())
            self.execute.assert_not_called()
            return 'YES'
        self.confirm.side_effect = confirm
        cli.offer_firewall(CONFIG)
        self.execute.assert_called_once_with([
            '/usr/bin/sudo', '--', '/usr/bin/ufw', 'allow', 'in', 'on', 'eth0',
            'proto', 'tcp', 'from', '192.168.50.0/24', 'to', '192.168.50.10',
            'port', '5900', 'comment', 'mac-native-screenshare'], check=True)
        self.assertEqual(self.resolve.call_count, 2)

    def test_empty_no_invalid_eof_and_interrupt_never_elevate(self):
        for answer in ('', 'n', 'no', 'sure', EOFError(), KeyboardInterrupt()):
            with self.subTest(answer=type(answer).__name__ if isinstance(answer, BaseException) else answer):
                self.confirm.side_effect = answer if isinstance(answer, BaseException) else None
                self.confirm.return_value = answer
                cli.offer_firewall(CONFIG)
                self.execute.assert_not_called()

    def test_noninteractive_or_explicit_skip_never_prompts_or_elevates(self):
        for stdin, stdout, skip in ((False, True, False), (True, False, False), (True, True, True)):
            with self.subTest(stdin=stdin, stdout=stdout, skip=skip):
                self.stdin_tty.return_value = stdin
                self.stdout_tty.return_value = stdout
                cli.offer_firewall(CONFIG, prompt=not skip)
                self.confirm.assert_not_called()
                self.execute.assert_not_called()
        self.configure(interactive=True, skip_firewall=True)
        self.confirm.assert_not_called()
        self.execute.assert_not_called()

    def test_missing_sudo_or_ufw_leaves_manual_guidance(self):
        self.available.return_value = False
        cli.offer_firewall(CONFIG)
        self.confirm.assert_not_called()
        self.execute.assert_not_called()
        self.assertIn('sudo or UFW is unavailable', self.output.getvalue())

    def test_failed_or_cancelled_sudo_keeps_completed_setup_for_retry(self):
        self.confirm.return_value = 'yes'
        for failure in (subprocess.CalledProcessError(1, ['sudo']), OSError('unavailable'), KeyboardInterrupt()):
            with self.subTest(failure=type(failure).__name__):
                self.execute.side_effect = failure
                with self.assertRaisesRegex(common.Error, 'Sharing settings were kept'):
                    self.configure(interactive=True)
                desktop.verify_hooks(self.paths)
                self.assertTrue(common.password(self.paths))
                self.assertEqual(common.settings(self.paths)['interface'], 'eth0')

    def test_network_change_after_confirmation_never_applies_stale_rule(self):
        self.confirm.return_value = 'yes'
        self.resolve.side_effect = [CONFIG['address'], common.Error('The selected host address changed')]
        with self.assertRaisesRegex(common.Error, 'address changed'):
            cli.offer_firewall(CONFIG)
        self.execute.assert_not_called()

    def test_rule_uses_current_address_without_rewriting_saved_settings(self):
        self.confirm.return_value = 'y'
        self.resolve.return_value = '192.168.50.99'
        config = dict(CONFIG)
        cli.offer_firewall(config)
        argv = self.execute.call_args.args[0]
        self.assertEqual(argv[argv.index('to') + 1], '192.168.50.99')
        self.assertEqual(config, CONFIG)

    def test_firewall_cli_is_read_only_unless_apply_is_explicit_and_interactive(self):
        common.write_json(self.paths.settings, CONFIG)
        with patch.object(cli, 'Paths', return_value=self.paths), \
             patch.object(cli.sys, 'argv', ['mac-native-screenshare', 'firewall']):
            cli.main()
        self.confirm.assert_not_called()
        self.execute.assert_not_called()
        self.stdin_tty.return_value = False
        with patch.object(cli, 'Paths', return_value=self.paths), \
             patch.object(cli.sys, 'argv', ['mac-native-screenshare', 'firewall', '--apply']):
            with self.assertRaisesRegex(common.Error, 'interactive terminal'):
                cli.main()
        self.execute.assert_not_called()
        self.stdin_tty.return_value = True
        self.confirm.return_value = 'yes'
        with patch.object(cli, 'Paths', return_value=self.paths), \
             patch.object(cli.sys, 'argv', ['mac-native-screenshare', 'firewall', '--apply']):
            cli.main()
        self.execute.assert_called_once()


class DisplayMenuTests(Workspace):
    def setUp(self):
        super().setUp()
        self.configure(skip_firewall=True)
        self.output = io.StringIO()
        self.enterContext(patch.object(cli.sys, 'stdout', self.output))
        self.enterContext(patch.object(cli.sys.stdin, 'isatty', return_value=True))
        self.enterContext(patch.object(self.output, 'isatty', return_value=True))
        self.confirm = self.enterContext(patch('builtins.input', return_value='yes'))
        self.enterContext(patch.object(cli, 'session_environment'))
        self.active = self.enterContext(patch.object(cli, 'active', return_value=False))
        self.enterContext(patch.object(cli, 'stopped'))
        self.control = self.enterContext(patch.object(cli, 'systemctl'))
        self.recover = self.enterContext(patch.object(cli, 'recover'))
        self.physical = self.enterContext(patch.object(cli.Desktop, 'physical', return_value=MONITOR))
        self.start = self.enterContext(patch.object(cli, 'start_sharing'))
        self.original = common.settings(self.paths)
        self.secret = common.password(self.paths)
        self.hypr = self.paths.hypr.read_bytes()

    def assert_preserved(self):
        current = common.settings(self.paths)
        self.assertEqual({k: v for k, v in current.items() if k != 'virtual'},
                         {k: v for k, v in self.original.items() if k != 'virtual'})
        self.assertEqual(common.password(self.paths), self.secret)
        self.assertEqual(self.paths.hypr.read_bytes(), self.hypr)
        self.assertFalse(any(call.args[0] in ('enable', 'disable') for call in self.control.call_args_list))

    def test_stopped_toggle_saves_only_display_choice_and_preserves_user_files(self):
        result = cli.change_display(self.paths, [2560, 1600])
        self.assertIn('saved', result)
        self.assertEqual(common.settings(self.paths)['virtual'], [2560, 1600])
        cli.change_display(self.paths, None)
        self.assertEqual(common.settings(self.paths), self.original)
        self.control.assert_not_called()
        self.start.assert_not_called()
        self.assert_preserved()

    def test_active_toggle_confirms_before_stop_and_starts_after_saving(self):
        self.active.return_value = True
        events = []
        def confirm(question):
            self.assertIn('disconnect briefly', self.output.getvalue())
            self.assertIn('laptop will mirror', self.output.getvalue())
            self.control.assert_not_called()
            return 'yes'
        self.confirm.side_effect = confirm
        self.control.side_effect = lambda *args, **kwargs: events.append(args)
        self.recover.side_effect = lambda paths: events.append(('recover',))
        def start(paths):
            self.assertEqual(common.settings(paths)['virtual'], [2560, 1600])
            events.append(('start',))
        self.start.side_effect = start
        self.assertIn('restarted', cli.change_display(self.paths, [2560, 1600]))
        self.assertEqual(events, [('stop', common.UNIT), ('recover',), ('start',)])
        self.assert_preserved()

    def test_cancel_invalid_size_and_same_selection_never_change_state(self):
        for answer in ('', 'no', EOFError(), KeyboardInterrupt()):
            self.confirm.side_effect = answer if isinstance(answer, BaseException) else None
            self.confirm.return_value = answer
            self.assertIn('unchanged', cli.change_display(self.paths, [1920, 1200]))
        with self.assertRaises(common.Error):
            cli.change_display(self.paths, [100, 100])
        self.assertIn('already selected', cli.change_display(self.paths, None))
        self.assertEqual(common.settings(self.paths), self.original)
        self.control.assert_not_called()
        self.recover.assert_not_called()
        self.start.assert_not_called()

    def test_failed_restart_restores_previous_choice_and_keeps_sharing_stopped(self):
        self.active.return_value = True
        self.start.side_effect = common.Error('Cannot capture requested mode')
        with self.assertRaisesRegex(common.Error, 'previous choice was restored'):
            cli.change_display(self.paths, [2560, 1600])
        self.assertEqual(common.settings(self.paths), self.original)
        self.assertEqual(self.control.call_args_list, [unittest.mock.call('stop', common.UNIT)] * 2)
        self.assertEqual(self.start.call_count, 1)
        self.assert_preserved()

    def test_stop_failure_leaves_settings_untouched(self):
        self.active.return_value = True
        self.control.side_effect = common.Error('Cannot stop the service')
        with self.assertRaisesRegex(common.Error, 'Cannot stop'):
            cli.change_display(self.paths, [2560, 1600])
        self.assertEqual(common.settings(self.paths), self.original)
        self.start.assert_not_called()

    def test_failed_cleanup_retains_current_settings_and_reports_recovery(self):
        self.active.return_value = True
        self.start.side_effect = common.Error('Cannot start')
        self.recover.side_effect = [None, common.Error('Display unavailable')]
        with self.assertRaisesRegex(common.Error, 'cleanup needs attention'):
            cli.change_display(self.paths, [2560, 1600])
        self.assertEqual(common.settings(self.paths)['virtual'], [2560, 1600])
        self.assert_preserved()

    def test_help_can_be_shown_and_hidden_without_locks_or_mutations(self):
        self.confirm.side_effect = ['h', 'h', 'q']
        with patch.object(cli, 'lock', side_effect=AssertionError('Reading the guide must not lock controls')):
            cli.display_menu(self.paths)
        output = self.output.getvalue()
        self.assertEqual(output.count('DISPLAY SIZE AND SHARPNESS'), 1)
        self.assertIn('h  Hide display instructions', output)
        self.assertEqual(common.settings(self.paths), self.original)
        self.control.assert_not_called()
        self.recover.assert_not_called()

    def test_menu_dispatches_presets_custom_and_return_to_normal(self):
        self.confirm.side_effect = ['2', '3', '4', '5', '3000x2000', '1', 'q']
        with patch.object(cli, 'change_display', return_value='Saved') as change:
            cli.display_menu(self.paths)
        self.assertEqual([call.args[1] for call in change.call_args_list],
                         [[1920, 1200], [2560, 1600], [3840, 2160], [3000, 2000], None])

    def test_invalid_menu_input_and_custom_cancel_do_not_change_display(self):
        self.confirm.side_effect = ['oops', '5', 'not-a-size', '5', '', 'q']
        with patch.object(cli, 'change_display') as change:
            cli.display_menu(self.paths)
        change.assert_not_called()
        self.assertIn('Use WIDTHxHEIGHT', self.output.getvalue())

    def test_guide_cli_works_without_setup_or_terminal(self):
        self.paths.settings.unlink()
        with patch.object(cli.sys.stdin, 'isatty', return_value=False), \
             patch.object(cli, 'Paths', return_value=self.paths), \
             patch.object(cli.sys, 'argv', ['mac-native-screenshare', 'display', '--guide']):
            cli.main()
        self.assertIn('DISPLAY SIZE AND SHARPNESS', self.output.getvalue())
        self.confirm.assert_not_called()
        self.control.assert_not_called()


class DisplayTests(Workspace):
    def test_physical_start_and_guard_accept_both_scales_without_monitor_rules(self):
        for scale in (1, 2):
            with self.subTest(scale=scale):
                monitor = dict(MONITOR, scale=scale)
                instance = desktop.Desktop(self.paths, self.env)
                def query(kind):
                    return {'id': 1} if kind == 'activeworkspace' else [{'id': 1}] if kind == 'workspaces' else [monitor]
                with patch.object(instance, 'query', side_effect=query), \
                     patch.object(instance, 'call', return_value=''), patch.object(instance, 'reload'), \
                     patch.object(instance, 'evaluate') as evaluate:
                    before = instance.begin(CONFIG)
                    instance.guard(CONFIG)
                self.assertEqual(before['monitor']['scale'], scale)
                self.assertFalse(before['created'])
                self.assertFalse(any('hl.monitor(' in call.args[0] for call in evaluate.call_args_list))
                self.assertFalse((self.paths.runtime / 'display.lua').exists())

    def test_unsupported_layouts_fail_before_start_mutates_files(self):
        for change in ({'scale': 1.5}, {'scale': 3}, {'transform': 1}, {'x': 20},
                       {'y': -20}, {'mirrorOf': 'HDMI-A-1'}, {'name': 'HDMI-A-1'}):
            with self.subTest(change=change):
                instance = desktop.Desktop(self.paths, self.env)
                with patch.object(instance, 'query', return_value=[dict(MONITOR, **change)]), \
                     patch.object(instance, 'call', side_effect=AssertionError('Must reject before mutations')):
                    with self.assertRaises(common.Error):
                        instance.begin(CONFIG)
                self.assertFalse(self.paths.journal.exists())
                self.assertFalse((self.paths.runtime / 'keyboard').exists())

    def test_guard_still_rejects_fractional_scale_and_added_outputs(self):
        instance = desktop.Desktop(self.paths, self.env)
        for monitors in ([dict(MONITOR, scale=1.5)], [dict(MONITOR, scale=2), {'name': 'HDMI-A-1'}]):
            with self.subTest(monitors=monitors), patch.object(instance, 'query', return_value=monitors):
                with self.assertRaises(common.Error):
                    instance.guard(CONFIG)

    def test_virtual_start_reload_and_recovery_preserve_scale(self):
        self.compositor_socket()
        for scale in (1, 2):
            with self.subTest(scale=scale):
                # 4K physical panel at scale 2 occupies 1920 logical pixels.
                panel = dict(MONITOR, width=3840, height=2160, scale=scale)
                monitors = [panel]
                config = dict(CONFIG, virtual=[1920, 1200])
                instance = desktop.Desktop(self.paths, self.env)
                rules = []
                calls = []
                def query(kind):
                    if kind == 'activeworkspace':
                        return {'id': 2}
                    if kind == 'workspaces':
                        return [{'id': n, 'monitor': desktop.VIRTUAL} for n in (1, 2)]
                    return monitors
                def call(*args):
                    calls.append(args)
                    if args == ('configerrors',):
                        return ''
                    if args[:2] == ('output', 'create'):
                        monitors.append(dict(MONITOR, name=desktop.VIRTUAL, width=1920, height=1200))
                    if args == ('output', 'remove', desktop.VIRTUAL):
                        monitors[:] = [panel]
                    if args[0] == 'eval' and args[1].startswith('hl.monitor('):
                        rules.append(args[1])
                    return 'ok'
                with patch.object(instance, 'query', side_effect=query), patch.object(instance, 'call', side_effect=call), \
                     patch.object(desktop.time, 'sleep'), patch.object(desktop, 'run') as control:
                    before = instance.begin(config)
                    instance.activate_virtual(before, self.paths.runtime / 'wayvnc.sock')
                    script = (self.paths.runtime / 'display.lua').read_text()
                    control.assert_called_once_with(common.ROOT / 'bin/wayvncctl', '-S', self.paths.runtime / 'wayvnc.sock', 'output-set', desktop.VIRTUAL)
                    panel['mirrorOf'] = desktop.VIRTUAL
                    instance.guard(config)
                    instance.restore()
                    instance.restore()  # Recovery is also safe to retry.

                # Execute the generated rules as Lua and inspect what Hyprland receives.
                capture = 'hl = {monitor = function(r) print(table.concat({r.output, r.mode, r.position, r.scale, r.mirror}, "|")) end}\n'
                lua = subprocess.check_output(['lua', '-'], input=capture + '\n'.join(rules) + '\n' + script, text=True)
                rows = [row.split('|') for row in lua.splitlines()]
                physical = [r for r in rows if r[0] == 'eDP-1']
                self.assertEqual([float(r[3]) for r in physical], [scale, scale, scale])
                self.assertEqual([r[4] for r in physical], ['', '', desktop.VIRTUAL])
                self.assertTrue(all(r[1:3] == ['3840x2160@60.000', '0x0'] for r in physical))
                virtual = [r for r in rows if r[0] == desktop.VIRTUAL]
                self.assertEqual([r[2] for r in virtual], [f'{3840 // scale}x0', '0x0'])
                self.assertTrue(all(r[1] == '1920x1200@60' and float(r[3]) == 1 for r in virtual))
                self.assertEqual(calls.count(('output', 'remove', desktop.VIRTUAL)), 1)
                self.assertFalse(self.paths.journal.exists())
                self.assertFalse((self.paths.runtime / 'display.lua').exists())
                self.assertFalse((self.paths.runtime / 'keyboard').exists())

    def test_failed_virtual_creation_retains_scale_two_for_recovery(self):
        instance = desktop.Desktop(self.paths, self.env)
        def query(kind):
            return {'id': 1} if kind == 'activeworkspace' else [{'id': 1}] if kind == 'workspaces' else [dict(MONITOR, scale=2)]
        def call(*args):
            return '' if args == ('configerrors',) else 'creation failed' if args[:2] == ('output', 'create') else 'ok'
        with patch.object(instance, 'query', side_effect=query), patch.object(instance, 'call', side_effect=call):
            with self.assertRaisesRegex(common.Error, 'Could not create'):
                instance.begin(dict(CONFIG, virtual=[1920, 1200]))
        before = json.loads(common.read_private(self.paths.journal))
        self.assertEqual(before['monitor']['scale'], 2)
        self.assertTrue(before['created'])


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
