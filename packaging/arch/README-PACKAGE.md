# Mac Native Screenshare developer package

Version 0.1.0alpha2-4 is an experimental add-on for x86-64 Omarchy 4.0 / Hyprland 0.56. Setup and service lifecycle are implemented. A second-host Mac connection at scale 2 has been reported; full acceptance remains pending.

Revision 4 adds a terminal display menu and a guide that can be shown/hidden, plus confirmation before applying a scoped UFW rule during setup. Run `mac-native-screenshare display` to choose normal or temporary desktop sizing, or `display --guide` to read the instructions. Physical scale 1 or 2 remains supported; optional virtual outputs use scale 1.

The package contains private modified WayVNC/NeatVNC components, a `mac-native-screenshare` command, a disabled user unit, and scoped cleanup hooks for upgrade/removal. It coexists with stock WayVNC/NeatVNC. Installing it does not start sharing, enable startup, create credentials, change desktop configuration, or alter firewall rules.

## Install and configure

On a supported host with the declared dependencies available:

```bash
pacman -Qip ./mac-native-screenshare-0.1.0alpha2-4-x86_64.pkg.tar.zst
sudo pacman -U ./mac-native-screenshare-0.1.0alpha2-4-x86_64.pkg.tar.zst
mac-native-screenshare setup
mac-native-screenshare password
mac-native-screenshare start
mac-native-screenshare status
```

Run the add-on commands as the logged-in desktop user, without sudo. Setup requires an explicitly selected trusted private LAN and acknowledgement that native VNC desktop/input/clipboard transport is unencrypted. Avahi must already be active. Interactive setup offers the scoped UFW rule after showing it and receiving confirmation; sudo may ask for your login password. `firewall --apply` repeats that prompt later. `--skip-firewall` or noninteractive setup prints guidance only. Confirmed firewall rules remain administrator-managed, and mDNS access must be available. Do not expose this preview to the internet.

Read **USAGE.md** before configuration. It covers startup, larger virtual displays, recovery, password rotation, firewall guidance, upgrades, and removal. It also explains why the original lab hook must be retired before adopting this package on the development host. The package does not migrate that working lab automatically.

For deliberate removal:

```bash
mac-native-screenshare remove
sudo pacman -R mac-native-screenshare
```

Upgrade hooks stop sharing before replacing files and retain settings/startup preference. Removal hooks clean configured regular users after dropping privileges. Cleanup failures abort the transaction so the recovery tools remain available. Unrelated edits and unrecognized files are preserved. Administrator-created firewall rules remain separately managed.

See RELEASE_SCOPE.md for targets and acceptance gates, and sources.json for exact commits/archive hashes. Licenses are under `/usr/share/licenses/mac-native-screenshare/`. Project contact: Paul Stoica <paul@totallynormal.io>. The project-specific implementation, tests, packaging, and documentation were produced using OpenAI Codex at Paul's direction. His commit identity is not a claim of manual authorship or independent code review. Upstream authors retain credit for their code. Endorsement and production readiness are not implied.
