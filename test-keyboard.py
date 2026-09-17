"""Keyboard selection and live-update policy; no desktop or input access."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace
import subprocess

import mns_keyboard as keyboard


def device(layout='us', variant='mac', index=0, name='internal-keyboard', main=False):
    return dict(layout=layout, variant=variant, active_layout_index=index, name=name, main=main)


def desktop(*devices, layout='us', variant=''):
    data = {'devices': {'keyboards': list(devices)},
            'getoption input:kb_layout': {'str': layout},
            'getoption input:kb_variant': {'str': variant}}
    return SimpleNamespace(query=lambda kind: data[kind])


class KeyboardTests(unittest.TestCase):
    def test_selects_physical_instead_of_virtual_main(self):
        host = desktop(device(name='hl-virtual-keyboard-wayvnc', main=True, variant='altgr-weur'),
                       device(name='hl-virtual-keyboard-fcitx5', main=True),
                       device(name='power-button', variant=''), device())
        self.assertEqual(keyboard.selected_layout(host), ('us', 'mac'))

    def test_multilayout_tracks_active_group_and_empty_variant(self):
        for index, expected in [(0, ('us', 'mac')), (1, ('fr', 'oss')), (2, ('de', ''))]:
            self.assertEqual(keyboard.selected_layout(desktop(device('us,fr,de', 'mac,oss,', index))), expected)
        self.assertEqual(keyboard.selected_layout(desktop(device(variant=''), variant='mac')), ('us', ''))

    def test_physical_main_and_headless_fallback(self):
        self.assertEqual(keyboard.selected_layout(desktop(device(), device('de', '', main=True))), ('de', ''))
        self.assertEqual(keyboard.selected_layout(desktop(layout='fr', variant='oss')), ('fr', 'oss'))

    def test_invalid_configuration(self):
        for bad in [device(index=5), device(layout='us\nxkb_options=broken')]:
            with self.assertRaises(keyboard.Error):
                keyboard.selected_layout(desktop(bad))

    def test_composed_fallback_keeps_system_variant(self):
        self.assertEqual(keyboard.transport_layout('us', 'mac'), ('us,us', 'mac,altgr-weur'))
        self.assertEqual(keyboard.transport_layout('fr', 'oss'), ('fr,us', 'oss,altgr-weur'))
        self.assertEqual(keyboard.transport_layout('us', 'altgr-weur'), ('us', 'altgr-weur'))

    def test_live_update_retries_busy_and_preserves_previous_map_on_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            host = Mock()
            host.query.side_effect = desktop(device()).query
            sync = keyboard.Keyboard(SimpleNamespace(runtime=Path(directory)), host)
            self.assertIn('xkb_variant=mac,altgr-weur', sync.config_lines())
            self.assertIn('xkb_options=lv3:ralt_alt', sync.config_lines())
            with patch.object(keyboard, 'run') as run:
                sync.sync()
                run.assert_not_called()
                host.query.side_effect = desktop(device('fr', 'oss')).query
                run.return_value = subprocess.CompletedProcess([], 1, '', 'Keyboard busy; retry after keys are released')
                sync.sync()
                self.assertEqual(sync.selected, ('us', 'mac'))
                run.return_value = subprocess.CompletedProcess([], 1, '', 'Invalid map')
                sync.sync()
                self.assertEqual(sync.selected, ('us', 'mac'))
                run.return_value = subprocess.CompletedProcess([], 0, 'Ok', '')
                sync.sync()
                self.assertEqual(sync.selected, ('fr', 'oss'))
                self.assertEqual(run.call_args.args[-3:], ('keyboard-set', 'fr,us', 'oss,altgr-weur'))
                self.assertIn('"system_variant": "oss"', (Path(directory) / 'keyboard.json').read_text())
                count = run.call_count
                sync.sync()
                self.assertEqual(run.call_count, count)

    def test_transient_query_failure_keeps_working_map(self):
        with tempfile.TemporaryDirectory() as directory:
            host = Mock()
            host.query.side_effect = desktop(device()).query
            sync = keyboard.Keyboard(SimpleNamespace(runtime=Path(directory)), host)
            host.query.side_effect = keyboard.Error('Compositor unavailable')
            sync.sync()
            self.assertEqual(sync.selected, ('us', 'mac'))


if __name__ == '__main__':
    unittest.main()
