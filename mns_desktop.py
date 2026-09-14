"""Own only marked config blocks and journaled, session-local desktop changes."""
import json
import os
from pathlib import Path
import re
import stat
import time

from mns_common import Error, ROOT, atomic_write, identifier, read_private, run, write_json

VIRTUAL = 'MAC-NATIVE-SHARE'
ANCHOR = 'require("default.hypr.omarchy")'


def hook_blocks(root=ROOT):
    # A removed package leaves these guards inert even before explicit cleanup.
    def block(kind):
        return (f'-- BEGIN mac-native-screenshare {kind} v1\n'
                'do\n'
                f'  local path = {json.dumps(str(root / "hyprland-hook.lua"))}\n'
                '  local file = io.open(path, "r")\n'
                f'  if file then file:close(); dofile(path).{kind}(hl, path:match("(.+)/[^/]+$")) end\n'
                'end\n'
                f'-- END mac-native-screenshare {kind} v1\n')
    return {'keyboard': block('keyboard'), 'display': block('display')}


def add_hooks(text, blocks):
    if 'mac-native-screenshare' in text:
        raise Error('Existing add-on hook needs recovery or removal before setup.')
    if 'mac-shortcuts.lua' in text or 'omarchy-screen-sharing-keyboard' in text:
        raise Error('A prototype keyboard hook is present. Retire that installation before setting up this package.')
    lines = text.splitlines(keepends=True)
    matches = [i for i, line in enumerate(lines) if line.strip() == ANCHOR]
    if len(matches) != 1 or not any('bootstrap.lua' in line and not line.lstrip().startswith('--') for line in lines[:matches[0]]):
        raise Error('Expected the standard Omarchy Lua bootstrap and defaults loader. No config was changed.')
    lines.insert(matches[0], blocks['keyboard'])
    result = ''.join(lines)
    if not result.endswith('\n'):
        result += '\n'
    return result + blocks['display']


def remove_hooks(text, owned):
    # Preserve all edits outside our exact blocks. Modified blocks require review.
    for block in owned['blocks'].values():
        if text.count(block) > 1:
            raise Error('Duplicate managed hook blocks need manual review.')
        if block in text:
            text = text.replace(block, '', 1)
    if 'BEGIN mac-native-screenshare' in text or 'END mac-native-screenshare' in text:
        raise Error('A managed hook was edited. Remove those marked blocks manually, then retry remove.')
    if not owned['had_final_newline'] and text.endswith('\n'):
        # Restore the original byte layout only if the remainder is unmodified.
        import hashlib
        candidate = text[:-1]
        if hashlib.sha256(candidate.encode()).hexdigest() == owned['original_sha256']:
            text = candidate
    return text


def config_text(paths):
    info = paths.hypr.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
        raise Error('The main Hyprland config must be a regular file owned by this user.')
    return paths.hypr.read_text(), stat.S_IMODE(info.st_mode)


def verify_hooks(paths):
    owned = json.loads(read_private(paths.ownership))
    text, _ = config_text(paths)
    if owned.get('schema') != 1 or any(text.count(b) != 1 for b in owned['blocks'].values()):
        raise Error('Managed Hyprland hooks are missing or changed. Run doctor; sharing stays stopped.')
    if text.index(owned['blocks']['keyboard']) > text.index(ANCHOR):
        raise Error('The keyboard hook must precede Omarchy defaults.')
    return owned


class Desktop:
    def __init__(self, paths, environment=None):
        self.paths = paths
        self.env = dict(os.environ if environment is None else environment)

    def call(self, *args):
        return run('hyprctl', *args, env=self.env, timeout=5)

    def query(self, kind):
        return json.loads(self.call('-j', kind))

    def evaluate(self, code):
        result = self.call('eval', code)
        if result != 'ok':
            raise Error('Hyprland rejected a runtime change: ' + result)

    def reload(self):
        self.call('reload')
        errors = self.call('configerrors')
        if errors:
            raise Error('Hyprland configuration errors: ' + errors)

    def physical(self, output):
        monitors = self.query('monitors')
        if len(monitors) != 1 or monitors[0]['name'] != output:
            raise Error('This preview requires exactly the selected physical output.')
        monitor = monitors[0]
        if (monitor['scale'], monitor['x'], monitor['y']) != (1, 0, 0) or monitor.get('mirrorOf', 'none') != 'none' or monitor.get('transform', 0) != 0:
            raise Error('The physical output must be unmirrored, unrotated, at scale 1 and position 0,0.')
        if output == VIRTUAL or output.startswith(('HEADLESS', 'WL-', 'WAYLAND-')):
            raise Error('Choose a physical display.')
        if self.call('configerrors'):
            raise Error('Fix existing Hyprland configuration errors before sharing.')
        return monitor

    def rule(self, output, mode, position='0x0', mirror=''):
        identifier(output)
        self.evaluate('hl.monitor({output=' + json.dumps(output) + ',mode=' + json.dumps(mode) +
                      ',position=' + json.dumps(position) + ',scale=1,mirror=' + json.dumps(mirror) + '})')

    def begin(self, config):
        monitor = self.physical(config['output'])
        before = {'schema': 1, 'instance': self.env['HYPRLAND_INSTANCE_SIGNATURE'],
                  'wayland': self.env['WAYLAND_DISPLAY'], 'output': config['output'],
                  'monitor': monitor, 'virtual': config['virtual'], 'created': False,
                  'workspace': self.query('activeworkspace')['id'],
                  'workspaces': [w['id'] for w in self.query('workspaces')]}
        # Journal intent before the first mutation, including virtual creation.
        write_json(self.paths.journal, before)
        atomic_write(self.paths.runtime / 'keyboard', 'enabled\n')
        self.reload()
        self.evaluate('assert(hl.omarchy_mac_shortcuts and hl.omarchy_mac_shortcuts.translated > 0)')
        if config['virtual']:
            width, height = config['virtual']
            if any(m['name'] == VIRTUAL for m in self.query('monitors all')):
                raise Error('The add-on virtual output name is already in use.')
            before['created'] = True
            write_json(self.paths.journal, before)
            self.rule(config['output'], self.mode(monitor))
            if self.call('output', 'create', 'headless', VIRTUAL) != 'ok':
                raise Error('Could not create the virtual output.')
            self.rule(VIRTUAL, f'{width}x{height}@60', f'{monitor["width"]}x0')
            time.sleep(.3)
            virtual = next((m for m in self.query('monitors') if m['name'] == VIRTUAL), {})
            if (virtual.get('width'), virtual.get('height'), virtual.get('scale')) != (width, height, 1):
                raise Error('The virtual output did not reach its requested size.')
        return before

    @staticmethod
    def mode(monitor):
        return f'{monitor["width"]}x{monitor["height"]}@{monitor["refreshRate"]:.3f}'

    def activate_virtual(self, before, control):
        if not before['virtual']:
            return
        width, height = before['virtual']
        output = before['output']
        mode = self.mode(before['monitor'])
        # The tail hook reapplies only these runtime rules on config reload.
        script = ('hl.monitor({output=' + json.dumps(VIRTUAL) + ',mode=' + json.dumps(f'{width}x{height}@60') + ',position="0x0",scale=1})\n' +
                  'hl.monitor({output=' + json.dumps(output) + ',mode=' + json.dumps(mode) + ',position="0x0",scale=1,mirror=' + json.dumps(VIRTUAL) + '})\n')
        atomic_write(self.paths.runtime / 'display.lua', script)
        run(ROOT / 'bin/wayvncctl', '-S', control, 'output-set', VIRTUAL)
        self.reload()
        time.sleep(.3)
        self.evaluate('hl.dispatch(hl.dsp.focus({monitor=' + json.dumps(VIRTUAL) + '}))')
        if before['workspace'] > 0:
            self.evaluate('hl.dispatch(hl.dsp.focus({workspace=' + json.dumps(str(before['workspace'])) + '}))')
        workspaces = self.query('workspaces')
        if not all(w['monitor'] == VIRTUAL for w in workspaces) or not set(before['workspaces']).issubset({w['id'] for w in workspaces}):
            raise Error('Virtual display workspace migration was incomplete.')

    def guard(self, config):
        monitors = self.query('monitors all')
        names = {m['name'] for m in monitors}
        expected = {config['output'], VIRTUAL} if config['virtual'] else {config['output']}
        if names != expected:
            raise Error('Display layout changed. Sharing has stopped.')
        if config['virtual']:
            virtual = next(m for m in monitors if m['name'] == VIRTUAL)
            physical = next(m for m in monitors if m['name'] == config['output'])
            if (virtual['width'], virtual['height'], virtual['scale'], virtual['x'], virtual['y']) != (*config['virtual'], 1, 0, 0) or physical.get('mirrorOf') != VIRTUAL:
                raise Error('Virtual display configuration changed. Sharing has stopped.')
        else:
            self.physical(config['output'])
        self.evaluate('assert(hl.omarchy_mac_shortcuts and hl.omarchy_mac_shortcuts.translated > 0)')

    def restore(self):
        if not self.paths.journal.exists():
            return
        before = json.loads(read_private(self.paths.journal))
        if before.get('schema') != 1:
            raise Error('Unknown recovery journal version; keeping it for review.')
        identifier(before['output'])
        instance = before['instance']
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', instance):
            raise Error('Invalid compositor in recovery journal.')
        # Never replay an old desktop snapshot into a different login session.
        socket = self.paths.runtime.parent / 'hypr' / instance / '.socket.sock'
        same_session = socket.is_socket()
        self.env['HYPRLAND_INSTANCE_SIGNATURE'] = instance
        self.env['WAYLAND_DISPLAY'] = before['wayland']
        for name in ('keyboard', 'display.lua'):
            (self.paths.runtime / name).unlink(missing_ok=True)
        if same_session:
            active_workspace = self.query('activeworkspace')['id']
            monitors = self.query('monitors all')
            if before['created'] and any(m['name'] == VIRTUAL for m in monitors):
                if not any(m['name'] == before['output'] for m in monitors):
                    raise Error('Reconnect the physical display and run recover; the virtual output is retained to avoid losing the only display.')
                self.rule(before['output'], self.mode(before['monitor']))
                time.sleep(.2)
                if self.call('output', 'remove', VIRTUAL) != 'ok':
                    raise Error('Could not remove the owned virtual display; recovery journal retained.')
            self.reload()
            if before['created'] and any(m['name'] == VIRTUAL for m in self.query('monitors all')):
                raise Error('The virtual display still exists; recovery journal retained.')
            if before['created'] and active_workspace > 0 and any(w['id'] == active_workspace for w in self.query('workspaces')):
                self.evaluate('hl.dispatch(hl.dsp.focus({workspace=' + json.dumps(str(active_workspace)) + '}))')
        self.paths.journal.unlink()
