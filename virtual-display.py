"""Private, runtime-only larger-display trial for the existing sharing service.

Run `hold` in a user service bound to the sharing service; `activate` switches
the live session only after the new output has passed a capture check. Stop
the trial service to restore the physical output. No user config is written.
"""
import json
import re
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

OUTPUT = 'OMARCHY-SHARE-TEST'
PHYSICAL = os.environ['OMARCHY_SHARE_PHYSICAL_OUTPUT']
WIDTH = int(os.environ['OMARCHY_SHARE_WIDTH'])
HEIGHT = int(os.environ['OMARCHY_SHARE_HEIGHT'])
assert re.fullmatch(r'[A-Za-z0-9._-]+', PHYSICAL)
assert 320 <= WIDTH <= 8192 and 200 <= HEIGHT <= 8192
assert PHYSICAL != OUTPUT
STATE = Path(os.environ['XDG_RUNTIME_DIR']) / 'omarchy-sharing-virtual-test'


def run(*args):
    result = subprocess.run(args, check=True, capture_output=True, text=True, timeout=10)
    return result.stdout.strip()


def query(kind):
    return json.loads(run('hyprctl', '-j', kind))


def evaluate(code):
    result = run('hyprctl', 'eval', code)
    if result != 'ok':
        raise RuntimeError(result)


def control(path, output):
    run('wayvncctl', '-S', path, 'output-set', output)


def monitor_rule(output, mode, position, scale=1, mirror=""):
    # Connector names are validated and json.dumps safely quotes Lua strings.
    evaluate('hl.monitor({output=' + json.dumps(output) + ',mode=' + json.dumps(mode)
             + ',position=' + json.dumps(position) + ',scale=' + str(scale)
             + ',mirror=' + json.dumps(mirror) + '})')


def read_state():
    return json.loads((STATE / 'before.json').read_text())


def restore():
    if not (STATE / 'before.json').exists():
        return
    before = read_state()
    monitors = query('monitors')
    if not any(m['name'] == OUTPUT for m in monitors):
        return
    try:
        active = query('activeworkspace')['id']
    except (ValueError, KeyError):
        active = before['workspace']
    # Remove the mirror relation before the virtual output disappears. The
    # compositor migrates its workspaces onto the sole remaining real output.
    monitor_rule(PHYSICAL, 'preferred', '0x0')
    time.sleep(.3)
    try:
        control(before['control'], PHYSICAL)
    except (subprocess.SubprocessError, OSError) as error:
        print('Sharing control unavailable during restore:', type(error).__name__, flush=True)
    run('hyprctl', 'output', 'remove', OUTPUT)
    # Reload the unchanged user configuration to discard temporary rules.
    run('hyprctl', 'reload')
    time.sleep(.3)
    errors = run('hyprctl', 'configerrors')
    if errors:
        raise RuntimeError(errors)
    if active > 0 and any(w['id'] == active for w in query('workspaces')):
        evaluate('hl.dispatch(hl.dsp.focus({workspace=' + json.dumps(str(active)) + '}))')
    monitors = query('monitors')
    assert len(monitors) == 1 and monitors[0]['name'] == PHYSICAL, 'Unexpected restored output layout'
    assert (monitors[0]['width'], monitors[0]['height']) == (before['monitor']['width'], before['monitor']['height'])
    assert all(w['monitor'] == PHYSICAL for w in query('workspaces'))
    print('Restored physical display and workspaces.', flush=True)


def hold(control_path):
    monitors = query('monitors')
    assert len(monitors) == 1 and monitors[0]['name'] == PHYSICAL
    assert monitors[0]['mirrorOf'] == 'none' and monitors[0]['scale'] == 1
    assert (monitors[0]['x'], monitors[0]['y']) == (0, 0)
    assert not run('hyprctl', 'configerrors')
    STATE.mkdir(mode=0o700, exist_ok=False)
    before = {'control': control_path, 'monitor': monitors[0],
              'workspace': query('activeworkspace')['id'],
              'workspaces': [w['id'] for w in query('workspaces')]}
    (STATE / 'before.json').write_text(json.dumps(before, indent=2) + '\n')
    stopping = False

    def stop(_signum, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        # Pin the auto-positioned physical output before adding a neighbour.
        monitor_rule(PHYSICAL, 'preferred', '0x0')
        result = run('hyprctl', 'output', 'create', 'headless', OUTPUT)
        if result != 'ok':
            raise RuntimeError(result)
        monitor_rule(OUTPUT, f'{WIDTH}x{HEIGHT}@60', f"{before['monitor']['width']}x0")
        time.sleep(.4)
        monitor = next(m for m in query('monitors') if m['name'] == OUTPUT)
        assert (monitor['width'], monitor['height'], monitor['scale']) == (WIDTH, HEIGHT, 1)
        assert 59 <= monitor['refreshRate'] <= 61
        evaluate('hl.dispatch(hl.dsp.focus({workspace=' + json.dumps(str(before['workspace'])) + '}))')
        (STATE / 'ready').write_text('staged\n')
        print(f'Staged virtual {WIDTH}x{HEIGHT}@60 output; sharing still captures {PHYSICAL}.', flush=True)
        while not stopping:
            time.sleep(.5)
    finally:
        restore()
        for name in ('ready', 'active', 'before.json'):
            (STATE / name).unlink(missing_ok=True)
        STATE.rmdir()


def activate():
    before = read_state()
    assert (STATE / 'ready').exists()
    active = query('activeworkspace')['id']
    try:
        control(before['control'], OUTPUT)
        monitor_rule(PHYSICAL, 'preferred', '0x0', mirror=OUTPUT)
        monitor_rule(OUTPUT, f'{WIDTH}x{HEIGHT}@60', '0x0')
        time.sleep(.5)
        evaluate('hl.dispatch(hl.dsp.focus({monitor="' + OUTPUT + '"}))')
        if active > 0:
            evaluate('hl.dispatch(hl.dsp.focus({workspace=' + json.dumps(str(active)) + '}))')
        time.sleep(.5)
        workspaces = query('workspaces')
        assert all(w['monitor'] == OUTPUT for w in workspaces), 'Workspace migration incomplete'
        assert set(before['workspaces']).issubset({w['id'] for w in workspaces})
        assert not run('hyprctl', 'configerrors')
        (STATE / 'active').write_text(f'{WIDTH}x{HEIGHT}\n')
        print(f'Normal sharing now captures {WIDTH}x{HEIGHT}; workspaces retained; physical panel mirrors it.')
    except BaseException:
        restore()
        raise


if __name__ == '__main__':
    os.umask(0o077)
    if sys.argv[1] == 'hold':
        hold(sys.argv[2])
    elif sys.argv[1] == 'activate':
        activate()
    elif sys.argv[1] == 'restore':
        restore()
    else:
        raise SystemExit('Use hold <control-socket>, activate, or restore')
