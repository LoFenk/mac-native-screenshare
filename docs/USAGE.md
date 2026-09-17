# Using the 0.1.0 alpha 2 developer preview

This package implements setup and service lifecycle. The user reported a successful Mac connection to a second Omarchy host at physical scale 2 after applying the scoped firewall rule. The remaining acceptance checks in roadmap step 6 are still pending. The lifecycle tests use temporary user files, simulated desktop/network services, and a real WayVNC server detached from any desktop. They do not establish real reboot behavior or complete Mac/display acceptance.

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

This preview requires one unrotated, unmirrored physical output at scale 1 or 2 and position 0,0, the standard Omarchy Lua bootstrap/default loader, a regular desktop account with UID at least 1000, and a systemd-managed graphical session. It uses fixed `~/.config/hypr` and `~/.config/mac-native-screenshare` locations so package removal can find configured accounts. Custom XDG configuration locations are outside this preview. It refuses the old prototype keyboard hook; retire the lab installation deliberately before switching the development host to this package. Concurrent VNC desktop sessions are outside scope.

Package revision `0.1.0alpha2-3` adds physical display scale 2. Keep your existing monitor scale: physical capture does not change it. The optional virtual output remains at scale 1 with the requested pixel dimensions; its mirroring rules preserve the physical panel's scale, including during recovery. Fractional scales remain outside this preview. A real scale-2 Mac connection has been reported; pointer accuracy, clipboard, shortcuts, and virtual-display lifecycle still need acceptance testing.

Avahi must already be running. Setup reports if `avahi-daemon.service` needs an administrator to enable it. Installation leaves firewall rules alone. After saving the sharing configuration, interactive setup shows the exact UFW allow rule for the selected interface, private subnet, current host address, and port, then asks whether to apply it. The default is no. If you confirm, only UFW runs through `sudo`; it can ask for your login password. Existing identical rules are reused. UFW's enabled state and other rules are unchanged.

To review and apply the rule later, including while sharing is running:

```bash
mac-native-screenshare firewall --apply
```

`firewall` without `--apply` only prints the allow and deletion commands. `setup --skip-firewall` and noninteractive setup print guidance without prompting or elevating privileges. Explicit `firewall --apply` requires a terminal. Cancelling or failing sudo keeps the completed sharing settings and credentials so you can retry. A network/address change during the confirmation requires a fresh review. If UFW or sudo is unavailable, configure access with your administrator.

The confirmed rule remains administrator-managed: changing the selected address, network, or port can require a new rule and removal of the old one. The printed deletion command reverses that exact rule. Uninstall does not delete administrator firewall rules. Existing mDNS access must also be available. Finder can discover the host even when its VNC port is blocked; `doctor` now points to this firewall command when local checks pass but the Mac cannot connect.

## Connect and control

On the Mac, use Finder → Network → the configured desktop name → Share Screen. Use the sharing password; no username is required. The hostname and current address are available through `status`; direct connections can use `vnc://HOST:PORT` in Finder's Connect to Server.

| Command | Effect |
| --- | --- |
| `start` | Start now in the existing graphical session; return when the server, authentication check, and discovery are ready |
| `stop` | Disconnect clients, stop discovery/server, restore desktop changes; preserve login-start preference |
| `enable` | Start at future graphical logins on the selected network; does not start now |
| `disable` | Stop now and remove login startup |
| `status [--json]` | Report configuration, service state, endpoint, and pending recovery without credentials |
| `display` | Open the display menu; press `h` to show/hide instructions and choose normal or temporary desktop sizing |
| `display --guide` | Print the same instructions without changing settings; available before setup |
| `firewall [--apply]` | Print the scoped rule, or ask for confirmation before applying it through sudo |
| `doctor` | Check configuration, credential permissions, network, port when stopped, display, hooks, and Avahi |
| `reset-password [PASSWORD]` | Set the supplied password, or generate one when omitted, while stopped; use `password` to view it |
| `recover` | Retry journaled cleanup after an interrupted session; refuses while the supervisor owns the session lock |
| `remove` | Stop, disable, remove owned config blocks and credentials; keep unrelated edits and unrecognized files |

For logs, use `journalctl --user -u mac-native-screenshare.service`. Do not publish credential files or the runtime VNC configuration.

To choose a password after setup:

```bash
mac-native-screenshare stop
mac-native-screenshare reset-password 'my-pass'
mac-native-screenshare start
```

Omit the argument to generate a fresh eight-character password. Custom passwords accept 1–8 printable ASCII characters, including punctuation and internal spaces, but no leading or trailing spaces. Longer values are rejected because legacy VNC uses at most eight bytes. Quote passwords containing shell characters; use `reset-password -- '-secret'` for a password beginning with a hyphen. Command-line passwords can appear in shell history and process listings. The command never prints the chosen value. Setup still generates a password initially and preserves it on subsequent setup runs.

## Display menu and instructions

```bash
mac-native-screenshare display
```

Press **h** to show or hide the instructions. They explain Mac viewer zoom, normal Omarchy monitor scaling/resolution, and temporary virtual desktops. Reading the guide changes nothing and does not block other start/stop commands. **q** closes the menu.

Choose **1** for the normal laptop desktop; **2–4** for temporary 1920×1200, 2560×1600, or 3840×2160 desktops; or **5** for a custom size. The selected mode is shown at the top. A change requires confirmation. If sharing is active, the app stops it, saves the choice, and starts it again; the Mac briefly disconnects and may need reconnecting. If sharing is stopped, only the preference is saved for next start. Credentials, network selection, firewall rules, and login startup are preserved.

Temporary desktops use scale 1. The laptop mirrors that same desktop while sharing is active; stopping restores its normal layout. The temporary preference remains selected for future starts until you choose **1**. The menu does not edit normal Omarchy monitor settings. If restart fails and cleanup succeeds, it restores the previous selection and leaves sharing stopped. If cleanup fails, it retains the recovery state and reports the recovery commands.

For the instructions alone, including before initial setup, run `mac-native-screenshare display --guide`. The packaged guide is also readable at `/usr/lib/mac-native-screenshare/display-guide.txt`.

If text is also too large locally, follow the guide's normal Omarchy scaling instructions with sharing stopped. If only the Mac view needs adjustment, first consider its View → scaling controls; these fit the existing image without changing Linux resolution. Temporary sizing provides another desktop size when that is useful. More pixels can provide more workspace when fitted to the Mac, but do not guarantee sharper text; scaling, aspect ratio, and client quality settings also matter.

## Virtual sizing and keyboard behavior

The original explicit commands remain available. Stop sharing before using setup to change its settings:

```bash
mac-native-screenshare stop
mac-native-screenshare setup --virtual 1920x1200 --skip-firewall
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
