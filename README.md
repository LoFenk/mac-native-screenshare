# Native Mac screen sharing source checkpoint

This directory preserves the integration sources for the tested Finder → Network → Omarchy → Share Screen workflow. It accompanies the pinned NeatVNC and WayVNC branches listed in dependencies.json. It is the starting point for a test package; installation and durable service ownership are not implemented yet. Nothing here is enabled by checking out or building this branch.

## Sources

- run.sh supervises the private server and interface-scoped Bonjour publisher. OMARCHY_PATH must point to this integration checkout. Its native branch expects private binaries under this directory's ignored native-clipboard/ directory; build/stage is the package builder's input, not an installed runtime location.
- publish.py advertises the approved interface/address and stops when the chosen network profile or address changes.
- mac-shortcuts.lua and mac-shortcuts.sh preserve the accepted device-scoped Command translations and narrow Option + Up behavior. Installation still needs a managed, removable Lua hook before Omarchy's default bindings load.
- virtual-display.py preserves the runtime larger-output trial, with the physical connector and requested size supplied through OMARCHY_SHARE_PHYSICAL_OUTPUT, OMARCHY_SHARE_WIDTH, and OMARCHY_SHARE_HEIGHT. It requires a single unmirrored physical output at scale 1 and position 0,0. These parameterized inputs have not yet been accepted on a second desktop. Its guardian must be bound to the sharing service, as described below.
- probe.py, test.py, test-mac-shortcuts.lua, check-native-frame.py, and test-output-switch.py preserve protocol, network, shortcut, and real-frame checks. Real desktop tests require explicit invocation; they are not run by build.sh.

The NeatVNC tree owns Apple protocol code and its synthetic wire tests. The WayVNC tree owns clipboard teardown, pointer overlay, held-modifier handling, and output-switch fixes. Existing upstream Nettle 4 prerequisites retain their original authors and cherry-pick provenance.

## Private build

Arrange sibling omarchy/, neatvnc/, and wayvnc/ checkouts at the pinned commits. Use Meson 1.12.0 and Ninja 1.13.2 on PATH, plus the documented system development dependencies: AML, Wayland client, pixman, TurboJPEG, GnuTLS, Nettle/Hogweed 4, GMP, zlib, libdrm, jansson, and xkbcommon. Tests also need Python D-Bus/GObject bindings and Lua. These are the tested Arch/Nettle 4 sources; compatibility with other distributions is not established.

Run `bash omarchy/extras/native-screen-sharing/build.sh "$PWD"` from the parent workspace. The script verifies the dependency commit IDs and clean source trees, builds both libraries/server privately, runs their tests and the portable integration checks, and stages binaries with SHA256 hashes under build/stage/. It does not install packages, edit user configuration, start sharing, or open firewall ports. It does not install missing build dependencies automatically.

The integration checks use /usr/bin/python3 so a virtual environment used for Meson does not hide system D-Bus/GObject bindings. Override OMARCHY_SHARE_PYTHON to choose another interpreter with those bindings.

## Runtime contract to package

The accepted prototype runs under the graphical user session with its imported Wayland and compositor environment. The main service supplies a private systemd password credential and selected interface/address/profile/output arguments to run.sh. The keyboard unit follows the main service and owns its runtime marker. The optional virtual-display guardian follows the main service, stages its output, and activates only after capture is verified. It restores physical capture/workspaces, removes its output, and reloads the unchanged user configuration when stopped.

The previous machine-specific service commands and credentials are deliberately absent. A package must implement fresh credential setup, selected-network access, service ordering, discovery identity, runtime paths, display selection, start/stop/restart, upgrade, and uninstall. The current native compatibility mode uses password-authenticated legacy VNC without encrypted desktop transport; supported network restrictions and that limitation must be explicit. No sample password should become an installed default.

## Verified outcome and limits

On the original Omarchy host, the native Mac user accepted Finder discovery, automatic text clipboard in both directions, normal pointer behavior, Option + Up, Command + Shift + workspace digits, a common-shortcut sweep, and full-screen sizing through a larger virtual output. The old output-switch implementation fails on the first isolated switch; the fix passes 20 alternating switches with full frames at both sizes.

Changing a configuration file can clear runtime display rules. Reboot recovery, installation/removal, additional physical layouts and Mac versions, encrypted native transport, and upstream approval remain unfinished. The Omarchy remote plan favors Sunshine/Moonlight; native built-in Mac access is the separate requirement to discuss before adding a maintained server stack.

Raw logs, personal configuration snapshots, credentials, private addresses, downloaded Apple binaries, and build outputs are excluded from this source checkpoint.
