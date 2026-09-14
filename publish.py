"""Interface-scoped temporary Bonjour publication; no system config writes."""

import ipaddress
import signal
import socket
import subprocess
import sys

import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib, GLibUnix


def check_network(interface, address, connection):
    ipaddress.IPv4Address(address)
    state = subprocess.check_output(
        ["nmcli", "-g", "GENERAL.CON-UUID,IP4.ADDRESS", "device", "show", interface],
        text=True, timeout=3,
    ).splitlines()
    if not state or state[0] != connection or not any(
        entry.split("/")[0] == address for entry in state[1:]
    ):
        raise RuntimeError("The selected network profile or host address changed")


def main():
    check_only = sys.argv[1:2] == ["--check"]
    args = sys.argv[2:] if check_only else sys.argv[1:]
    if len(args) != 3:
        raise ValueError("Expected interface, host IPv4, and approved network UUID")
    interface, address, connection = args
    check_network(interface, address, connection)
    if check_only:
        return

    DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus(private=True)
    server = dbus.Interface(bus.get_object("org.freedesktop.Avahi", "/"), "org.freedesktop.Avahi.Server")
    group = dbus.Interface(bus.get_object("org.freedesktop.Avahi", server.EntryGroupNew()), "org.freedesktop.Avahi.EntryGroup")
    loop = GLib.MainLoop()
    failure = []

    def stop():
        loop.quit()
        return False

    def changed(state, error):
        if int(state) == 2:
            print("Bonjour ready: Omarchy / _rfb._tcp / omarchy-screen.local:5900", flush=True)
        elif int(state) in (3, 4):
            failure.append(f"Avahi publication failed: {error or 'name collision'}")
            loop.quit()

    def guard():
        try:
            check_network(interface, address, connection)
            if int(group.GetState()) != 2:
                raise RuntimeError("Bonjour registration is no longer established")
        except Exception as error:
            failure.append(str(error))
            loop.quit()
            return False
        return True

    group.connect_to_signal("StateChanged", changed)
    index = socket.if_nametoindex(interface)
    # Protocol 0 is IPv4. A dedicated A-only name avoids advertising an IPv6
    # endpoint when this prototype has no IPv6 desktop listener.
    group.AddAddress(index, 0, dbus.UInt32(16), "omarchy-screen.local", address)
    group.AddService(index, 0, dbus.UInt32(0), "Omarchy", "_rfb._tcp", "local", "omarchy-screen.local", dbus.UInt16(5900), dbus.Array([], signature="ay"))
    try:
        group.Commit()
        GLibUnix.signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, stop)
        GLibUnix.signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, stop)
        # Bounded polling is intentionally prototype-only, not the production
        # network lifecycle proposed for upstream integration.
        GLib.timeout_add_seconds(2, guard)
        loop.run()
    finally:
        try:
            group.Reset()
        finally:
            bus.close()
    if failure:
        raise RuntimeError(failure[0])


if __name__ == "__main__":
    main()
