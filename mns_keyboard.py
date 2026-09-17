"""Follow the physical keyboard's language, with a composed-text VNC fallback."""
import subprocess

from mns_common import Error, ROOT, run, write_json


def selected_layout(desktop):
    # Virtual input can become Hyprland's "main" keyboard. Never feed our own
    # map (or an input method's copy of it) back into the system-layout choice.
    keyboards = [k for k in desktop.query('devices')['keyboards']
                 if not any(part in k['name'].lower() for part in
                            ('virtual', 'passthrough', 'power-button', 'sleep-button',
                             'video-bus', 'ir-receiver'))]
    keyboards.sort(key=lambda k: (not k.get('main'), 'keyboard' not in k['name'].lower()))
    keyboard = keyboards[0] if keyboards else {}
    layouts = (keyboard.get('layout') or desktop.query('getoption input:kb_layout')['str'] or 'us').split(',')
    variants = (keyboard['variant'] if keyboard else desktop.query('getoption input:kb_variant')['str']).split(',')
    index = keyboard.get('active_layout_index', 0)
    if not isinstance(index, int) or not 0 <= index < len(layouts):
        raise Error('Cannot determine the selected system keyboard layout')
    layout = layouts[index].strip()
    variant = variants[index].strip() if index < len(variants) else ''
    # XKB names, including custom names, are passed as argument values, never
    # shell code. Reject control characters before writing the WayVNC config.
    if not layout or any(c in layout + variant for c in '\n\r\0') or len(layout + variant) > 200:
        raise Error('Invalid system keyboard layout name')
    return layout, variant


def transport_layout(layout, variant):
    # Mac dead-key composition arrives as the final character. us(mac), for
    # example, has dead_acute but no eacute. Keep the system layout first and
    # add completed Western European letters as an inverse-lookup fallback.
    if (layout, variant) == ('us', 'altgr-weur'):
        return layout, variant
    return layout + ',us', variant + ',altgr-weur'


class Keyboard:
    def __init__(self, paths, desktop):
        self.paths, self.desktop = paths, desktop
        self.selected = selected_layout(desktop)
        self.warning = None

    def config_lines(self):
        layout, variant = transport_layout(*self.selected)
        # VNC sends semantic modifier keysyms, not physical Option keycodes.
        # Physical lv3:alt_switch/altwin options must not remap Command twice.
        return ['xkb_layout=' + layout, 'xkb_variant=' + variant,
                'xkb_model=pc105', 'xkb_rules=evdev', 'xkb_options=lv3:ralt_alt']

    def record(self):
        write_json(self.paths.runtime / 'keyboard.json', {
            'system_layout': self.selected[0], 'system_variant': self.selected[1],
            'remote_layout': transport_layout(*self.selected)[0],
            'remote_variant': transport_layout(*self.selected)[1],
        })

    def sync(self):
        try:
            selected = selected_layout(self.desktop)
            if selected == self.selected:
                self.warning = None
                return
            layout, variant = transport_layout(*selected)
            result = run(ROOT / 'bin/wayvncctl', '-S', self.paths.runtime / 'control',
                         'keyboard-set', layout, variant, check=False, timeout=5)
            if result.returncode:
                if 'Keyboard busy' in result.stdout + result.stderr:
                    return  # Keep held keys intact; the next check retries.
                raise Error('Remote keyboard update failed: ' + (result.stderr or result.stdout).strip())
            self.selected = selected
            self.record()
            self.warning = None
            print(f'Remote keyboard follows system layout: {selected[0]} ({selected[1] or "default"}).', flush=True)
        except (Error, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
            # A bad/transient keyboard setting must not tear down a working
            # display connection. Network and desktop guards still run.
            warning = str(error)
            if warning != self.warning:
                print('Keeping previous remote keyboard: ' + warning, flush=True)
                self.warning = warning
