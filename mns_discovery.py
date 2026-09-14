"""Interface-scoped Avahi registration with NetworkManager change detection."""
import json
import signal
import socket
import sys
import time

import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib, GLibUnix

from mns_common import Paths, atomic_write, read_private, resolve_network


def main():
    paths = Paths()
    active = json.loads(read_private(paths.runtime / 'endpoint.json'))
    config, address = active['config'], active['address']
    DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus(private=True)
    loop = GLib.MainLoop()
    failure = []
    started = time.monotonic()
    ready = paths.runtime / 'discovery-ready'
    server = dbus.Interface(bus.get_object('org.freedesktop.Avahi', '/'), 'org.freedesktop.Avahi.Server')
    group = dbus.Interface(bus.get_object('org.freedesktop.Avahi', server.EntryGroupNew()), 'org.freedesktop.Avahi.EntryGroup')
    nm = dbus.Interface(bus.get_object('org.freedesktop.NetworkManager', '/org/freedesktop/NetworkManager'), 'org.freedesktop.NetworkManager')
    device = str(nm.GetDeviceByIpIface(config['interface']))

    def stop():
        loop.quit()
        return False

    def fail(message):
        failure.append(message)
        ready.unlink(missing_ok=True)
        loop.quit()
        return False

    def guard(*_):
        try:
            resolve_network(config, address)
            state = int(group.GetState())
            if state in (3, 4) or (state != 2 and time.monotonic() - started > 10):
                return fail('Finder discovery registration was lost.')
        except Exception as error:
            return fail(str(error))
        return True

    def changed(state, error):
        if int(state) == 2:
            atomic_write(ready, 'ready\n')
        elif int(state) in (3, 4):
            fail('Finder discovery failed: ' + str(error or 'name collision'))

    def device_changed(state, *_):
        if int(state) != 100:
            fail('The selected network disconnected.')
        else:
            guard()

    group.connect_to_signal('StateChanged', changed)
    bus.add_signal_receiver(device_changed, signal_name='StateChanged',
                            dbus_interface='org.freedesktop.NetworkManager.Device', path=device)
    bus.add_signal_receiver(guard, signal_name='PropertiesChanged',
                            dbus_interface='org.freedesktop.DBus.Properties', path=device)
    bus.add_signal_receiver(lambda *_: fail('NetworkManager or Avahi restarted.'),
                            signal_name='NameOwnerChanged', dbus_interface='org.freedesktop.DBus',
                            arg0='org.freedesktop.NetworkManager')
    bus.add_signal_receiver(lambda *_: fail('Avahi restarted.'),
                            signal_name='NameOwnerChanged', dbus_interface='org.freedesktop.DBus',
                            arg0='org.freedesktop.Avahi')
    try:
        resolve_network(config, address)
        index = socket.if_nametoindex(config['interface'])
        group.AddAddress(index, 0, dbus.UInt32(16), config['hostname'], address)
        group.AddService(index, 0, dbus.UInt32(0), config['name'], '_rfb._tcp', 'local',
                         config['hostname'], dbus.UInt16(config['port']), dbus.Array([], signature='ay'))
        group.Commit()
        GLibUnix.signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, stop)
        GLibUnix.signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, stop)
        # Also covers address-object changes and missed D-Bus notifications.
        GLib.timeout_add_seconds(1, guard)
        loop.run()
    finally:
        ready.unlink(missing_ok=True)
        try:
            group.Reset()
        finally:
            bus.close()
    if failure:
        print(failure[0], file=sys.stderr)
        return 3
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
