# Using the 0.1.0 alpha 2 developer preview

This package now implements setup and service lifecycle. It still needs the second-host/Mac acceptance in roadmap step 6. The lifecycle tests use temporary user files, simulated desktop/network services, and a real WayVNC server detached from any desktop. They do not establish that this packaged deployment works across a real reboot or with a real Mac.

## Set up

Install the Arch package on the target Omarchy host, then run these commands as the logged-in desktop user, without sudo:

```bash
mac-native-screenshare setup
mac-native-screenshare password
mac-native-screenshare start
mac-native-screenshare status
```

Setup asks you to choose a connected Ethernet/Wi-Fi interface and physical display and to accept the unencrypted native VNC transport. It generates a fresh eight-character password and installs two guarded, marked blocks in `~/.config/hypr/hyprland.lua`. It checks Hyprland configuration errors before and after the change. Setup does not start sharing or enable startup. The password command displays the credential only in an interactive terminal; status and service logs omit it.

For explicit noninteractive selection, first use `networks` and `displays`, then, substituting your actual interface and output:

```bash
mac-native-screenshare setup --interface enp1s0 --output eDP-1 --accept-unencrypted
```

This preview requires one unrotated, unmirrored physical output at scale 1 and position 0,0, the standard Omarchy Lua bootstrap/default loader, a regular desktop account with UID at least 1000, and a systemd-managed graphical session. It uses fixed `~/.config/hypr` and `~/.config/mac-native-screenshare` locations so package removal can find configured accounts. Custom XDG configuration locations are outside this preview. It refuses the old prototype keyboard hook; retire the lab installation deliberately before switching the development host to this package. Concurrent VNC desktop sessions are outside scope.

Avahi must already be running. Setup reports if `avahi-daemon.service` needs an administrator to enable it. The package does not change global service settings or firewall rules. If UFW blocks incoming VNC, `mac-native-screenshare firewall` prints an optional allow rule scoped to the chosen interface, subnet, current host address, and port, plus its exact deletion command. An administrator manages that rule separately. Existing local mDNS access must also be available. A changed DHCP address can require updating that administrator-owned firewall rule.

## Connect and control

On the Mac, use Finder → Network → the configured desktop name → Share Screen. Use the sharing password; no username is required. The hostname and current address are available through `status`; direct connections can use `vnc://HOST:PORT` in Finder's Connect to Server.

| Command | Effect |
| --- | --- |
| `start` | Start now in the existing graphical session; return when the server, authentication check, and discovery are ready |
| `stop` | Disconnect clients, stop discovery/server, restore desktop changes; preserve login-start preference |
| `enable` | Start at future graphical logins on the selected network; does not start now |
| `disable` | Stop now and remove login startup |
| `status [--json]` | Report configuration, service state, endpoint, and pending recovery without credentials |
| `doctor` | Check configuration, credential permissions, network, port when stopped, display, hooks, and Avahi |
| `reset-password` | Generate a new password while stopped; use `password` to view it |
| `recover` | Retry journaled cleanup after an interrupted session; refuses while the supervisor owns the session lock |
| `remove` | Stop, disable, remove owned config blocks and credentials; keep unrelated edits and unrecognized files |

For logs, use `journalctl --user -u mac-native-screenshare.service`. Do not publish credential files or the runtime VNC configuration.

## Virtual sizing and keyboard behavior

Stop sharing before updating its settings. For a larger display:

```bash
mac-native-screenshare stop
mac-native-screenshare setup --virtual 1920x1200
mac-native-screenshare start
```

Setup reuses the selected network/display and preserves the password. Use `setup --physical` to return to physical capture. `--port` and `--name` can also update stopped settings. Supported virtual dimensions are 320×200 through 8192×8192; practical performance limits still need client testing.

The supervisor stages one reserved `MAC-NATIVE-SHARE` output, switches capture, and mirrors the physical panel to it. A runtime tail hook reapplies the virtual rules when Hyprland reloads. On stop, the panel is unmirrored, the owned virtual output is removed, and the current user configuration is reloaded; workspaces migrate back through the compositor. The keyboard hook translates the tested remote keyboard names while sharing is active. It leaves physical bindings and pointer bindings with their original behavior. Both hooks are inactive when their runtime markers are absent.

If the physical display disappears during virtual sharing, access stops and recovery retains the virtual output instead of removing the only remaining desktop. Reconnect the physical display and run `recover`. The journal stays available if restoration fails. Removal refuses edited managed blocks rather than deleting text it can no longer identify; inspect the two marked blocks and retry after resolving the edits.

## Network, reboot, upgrade, and removal

The private VNC backend listens on a user-private Unix socket. A bounded relay listens only on the selected IPv4 address and admits peers from the selected private subnet. Eight simultaneous connections are allowed to accommodate protocol/clipboard connections; this is still a one-user/one-Mac release target. NetworkManager events and a one-second fallback check stop discovery when the selected profile, subnet, or current address changes. The supervisor closes the listener and established relays before desktop cleanup. This is an application-level subnet restriction, not a firewall replacement or encrypted transport.

`enable` is tied to `graphical-session.target`, after the Wayland session environment is ready. It does not provide access before login. Startup waits up to 45 seconds for the approved network and Avahi. At a later login, a new DHCP address is accepted only on the same interface/profile/subnet. A network/display change during sharing stops it until another explicit start or graphical login. Server crashes get at most three start attempts in two minutes, with journaled cleanup between attempts. A journal from a dead compositor is discarded without applying its snapshot to a new login.

Pacman pre-transaction hooks stop this add-on in active user managers before upgrades or removal. Upgrades preserve settings, credentials, and the startup preference; run `start` after the transaction to resume sharing now. Unknown configuration schema versions fail without silently rewriting settings.

For deliberate removal:

```bash
mac-native-screenshare remove
sudo pacman -R mac-native-screenshare
```

The package's removal hook also invokes cleanup as each configured regular local user, dropping privileges before reading user configuration. Logged-out accounts are cleaned without starting a user manager. If cleanup fails, the package transaction aborts so the restoration tools remain installed. A pre-setup backup and ownership journal allow exact removal of the managed blocks while preserving later personal edits. Encrypted/unmounted homes, external account databases, custom configuration roots, and bypassing pacman hooks require running `remove` as each affected user before package removal. Any firewall rule installed by an administrator remains theirs to remove with the command shown by `firewall`.

The existing lab installation is independent of this package and is never automatically migrated or removed.
