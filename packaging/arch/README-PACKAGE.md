# Mac Native Screenshare developer package

Version 0.1.0alpha1 is an experimental package for x86-64 Omarchy 4.0 / Hyprland 0.56. It is not yet an end-user setup tool or a supported background service.

The package contains the modified WayVNC server and NeatVNC library, the private control client, prototype integration helpers, source-version metadata, licenses, and release-scope documentation. All executable/library files are under `/usr/lib/mac-native-screenshare/`. It does not replace system WayVNC/NeatVNC files or publish an alternative system library.

Installing it does not start screen sharing, enable startup, create credentials, alter a firewall, or change your desktop. Setup/start/stop/status and managed reboot/removal behavior are later milestones. Do not connect the prototype helper scripts to your desktop as an unattended service using these packaging instructions.

## Inspect and install the inert package

On a supported host with the declared dependencies available:

```bash
pacman -Qip ./mac-native-screenshare-0.1.0alpha1-1-x86_64.pkg.tar.zst
pacman -Qlp ./mac-native-screenshare-0.1.0alpha1-1-x86_64.pkg.tar.zst
sudo pacman -U ./mac-native-screenshare-0.1.0alpha1-1-x86_64.pkg.tar.zst
```

These commands are for someone intentionally testing package installation. The packaging build itself never runs them against the live host. The private binaries can be inspected without starting a server:

```bash
/usr/lib/mac-native-screenshare/bin/wayvnc --version
/usr/lib/mac-native-screenshare/bin/wayvncctl --help
```

Normal package removal deletes the installed files:

```bash
sudo pacman -R mac-native-screenshare
```

No runtime configuration is installed by this preview. Configuration created manually is outside this package-file test. The stock `wayvnc` and `neatvnc` packages can coexist with it.

## Native transport limitation

The intended Mac compatibility path uses legacy VNC authentication and unencrypted desktop/input/clipboard transport. It is targeted only at a deliberately selected trusted private IPv4 LAN. It must not be exposed to the internet. A working prototype and package checks do not establish production readiness or a security audit.

See `RELEASE_SCOPE.md` for the exact target and remaining acceptance gates, and `sources.json` for source commits and archive hashes. Retained licenses are installed under `/usr/share/licenses/mac-native-screenshare/`. Substantial AI assistance was used; upstream endorsement and human audit are not implied.
