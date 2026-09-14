"""Verify package transaction behavior without invoking root or a service manager."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('package_lifecycle', Path(__file__).with_name('package-lifecycle.py'))
lifecycle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lifecycle)


class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='mns-transaction-')
        self.addCleanup(self.temp.cleanup)
        (Path(self.temp.name) / '.config/mac-native-screenshare').mkdir(parents=True)
        self.account = SimpleNamespace(pw_uid=1234, pw_name='test-desktop', pw_dir=self.temp.name)

    def test_upgrade_stops_before_files_change_and_preserves_settings(self):
        with patch.object(lifecycle, 'users', return_value=[(self.account, True)]), \
             patch.object(lifecycle.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')) as execute:
            lifecycle.cleanup('upgrade')
        self.assertEqual(execute.call_count, 1)
        self.assertEqual(execute.call_args.args[0][-2:], ['stop', lifecycle.UNIT])

    def test_removal_drops_privileges_before_reading_user_configuration(self):
        with patch.object(lifecycle, 'users', return_value=[(self.account, True)]), \
             patch.object(lifecycle.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')) as execute:
            lifecycle.cleanup('remove')
        calls = [call.args[0] for call in execute.call_args_list]
        self.assertEqual(calls[0][-2:], ['stop', lifecycle.UNIT])
        self.assertEqual(calls[1][:6], ['/usr/bin/runuser', '--user', 'test-desktop', '--', '/usr/bin/env', '-i'])
        self.assertIn('HOME=' + self.temp.name, calls[1])
        self.assertEqual(calls[1][-1], 'remove')

    def test_logged_out_cleanup_never_starts_user_manager(self):
        with patch.object(lifecycle, 'users', return_value=[(self.account, False)]), \
             patch.object(lifecycle.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')) as execute:
            lifecycle.cleanup('remove')
        self.assertEqual(execute.call_count, 1)
        self.assertEqual(execute.call_args.args[0][-2:], ['remove', '--offline'])

    def test_failed_stop_aborts_removal(self):
        with patch.object(lifecycle, 'users', return_value=[(self.account, True)]), \
             patch.object(lifecycle.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '', 'restoration failed')) as execute:
            with self.assertRaises(RuntimeError):
                lifecycle.cleanup('remove')
        self.assertEqual(execute.call_count, 1)

    def test_cleanup_failure_aborts_transaction(self):
        with patch.object(lifecycle, 'users', return_value=[(self.account, False)]), \
             patch.object(lifecycle.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, 'user cleanup')):
            with self.assertRaises(RuntimeError):
                lifecycle.cleanup('remove')


if __name__ == '__main__':
    unittest.main()
