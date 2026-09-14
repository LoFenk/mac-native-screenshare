# Mac Native Screenshare developer package

Version 0.1.0alpha2-3 is an experimental add-on for x86-64 Omarchy 4.0 / Hyprland 0.56. Setup and service lifecycle are implemented; real second-host/Mac acceptance remains pending.

Revision 3 accepts physical monitor scale 1 or 2 and preserves it through virtual-display setup and recovery. Optional virtual outputs remain at scale 1. Keep your existing monitor scale and rerun `setup` if the previous revision rejected it.

The package contains private modified WayVNC/NeatVNC components, a `mac-native-screenshare` command, a disabled user unit, and scoped cleanup hooks for upgrade/removal. It coexists with stock WayVNC/NeatVNC. Installing it does not start sharing, enable startup, create credentials, change desktop configuration, or alter firewall rules.

## Install and configure

On a supported host with the declared dependencies available:

```bash
pacman -Qip ./mac-native-screenshare-0.1.0alpha2-3-x86_64.pkg.tar.zst
sudo pacman -U ./mac-native-screenshare-0.1.0alpha2-3-x86_64.pkg.tar.zst
mac-native-screenshare setup
mac-native-screenshare password
mac-native-screenshare start
mac-native-screenshare status
```

Run the add-on commands as the logged-in desktop user, without sudo. Setup requires an explicitly selected trusted private LAN and acknowledgement that native VNC desktop/input/clipboard transport is unencrypted. Avahi must already be active, and firewall/mDNS access is separately managed. Do not expose this preview to the internet.

Read **USAGE.md** before configuration. It covers startup, larger virtual displays, recovery, password rotation, firewall guidance, upgrades, and removal. It also explains why the original lab hook must be retired before adopting this package on the development host. The package does not migrate that working lab automatically.

For deliberate removal:

```bash
mac-native-screenshare remove
sudo pacman -R mac-native-screenshare
```

Upgrade hooks stop sharing before replacing files and retain settings/startup preference. Removal hooks clean configured regular users after dropping privileges. Cleanup failures abort the transaction so the recovery tools remain available. Unrelated edits and unrecognized files are preserved. Administrator-created firewall rules remain separately managed.

See RELEASE_SCOPE.md for targets and acceptance gates, and sources.json for exact commits/archive hashes. Licenses are under `/usr/share/licenses/mac-native-screenshare/`. Project contact: Paul Stoica <paul@totallynormal.io>. The project-specific implementation, tests, packaging, and documentation were produced using OpenAI Codex at Paul's direction. His commit identity is not a claim of manual authorship or independent code review. Upstream authors retain credit for their code. Endorsement and production readiness are not implied.
