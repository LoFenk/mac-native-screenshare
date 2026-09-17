# Verification record

## Revision 7 keyboard defaults — September 17, 2026

Revision 6 was installed after administrator authentication. With the personal service keyboard override and shortcut snippet removed, accents and Option+Up passed in both Foot and Omarchy agent terminals. A live system-layout change from US Macintosh to French exposed stale input-method state: `é` became `2`, even though WayVNC had received the new map. The original system layout was restored after the test.

Hyprland 0.56.2's input-method grab caches keyboard data by device identity ([source](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/protocols/InputMethodV2.cpp#L27)). WayVNC now recreates the idle virtual keyboard resource when applying a prepared map. It retains the RFB connection, pointer, and keyboard lock state. The private control command still waits for held keys to be released and prepares all maps before changing devices.

The opt-in `python test-keyboard-live.py --live-desktop --runtime /path/to/runtime` regression check reproduces the input-method case using a private authenticated Unix socket and a scratch Foot terminal. It changes no desktop configuration. The development build passed US→French→US accent and Option+Up checks through the same connection, with Fcitx5 active, and correctly deferred an update while Option was held. All three WayVNC suites passed. Revision 7 package build and installed-package acceptance follow below when completed. Nothing has been published.

## Revision 6 build checks

Built `0.1.0alpha2-6` from integration `f8040ba712b55c403b35f1cf8d4102c9a962f829`, WayVNC `9f754d0b5b3886ac124013bcdd113bc76aaba24e`, and the unchanged NeatVNC pin. All four NeatVNC and three WayVNC suites; 13 protocol, 56 lifecycle, seven keyboard-policy, five package-transaction, and four supervisor tests; Lua/hook/shell checks; archive verification; temporary-root upgrade/removal; and offline source verification passed. Those isolated checks did not expose the live input-method issue described above. Revision 7 supersedes this build.

## Custom-password release, package revision 5

The current package supports `reset-password [PASSWORD]`, with explicit 1–8-character printable ASCII passwords or automatic generation when omitted. [Package validation](packaging/arch/VALIDATION.md) records the full rebuild, custom-password authentication against real detached VNC servers, final archive checks, and temporary-root revision upgrade/removal. A local revision 5 build was installed through pacman and its packaged service restarted successfully with the existing credential preserved. The public artifact was rebuilt from the same pinned implementation in the generic isolated build environment. Separate second-machine/Mac acceptance remains pending.

## Original source checkpoint

The [original verification record](docs/checkpoint/VERIFICATION.md) reports a fresh build of the pinned NeatVNC and WayVNC sources with all four NeatVNC suites, three WayVNC suites, 13 integration unit checks, Lua shortcut checks, and shell syntax checks passing. It separately records the original host's Mac-client acceptance.

Those results describe the checkpoint before standalone extraction. They do not establish installer, reboot, removal, or second-machine support.

## Standalone extraction

The first repository commit preserves all 15 integration files byte for byte from Omarchy commit `b807f14b8ec03d95cc141df3fe160d7e863f47c6`. Original SHA256 hashes are recorded in [docs/checkpoint/extraction.json](docs/checkpoint/extraction.json). The Omarchy MIT license and original workspace manifest are also retained.

The standalone adaptation changes only source-directory lookup in `build.sh` and `run.sh`, the default build-output directory, dependency repository URLs, ignore rules, and documentation. The VNC source commits and other runtime scripts retain their checkpoint contents. A build no longer requires an Omarchy source checkout.

On September 13, 2026, a fresh temporary workspace containing only this standalone integration and local clones of the two pinned dependencies completed the entire build recipe. There was no Omarchy source checkout in that workspace. All four NeatVNC suites, three WayVNC suites, 13 integration unit checks, Lua shortcut checks, and shell syntax checks passed. Python source syntax, initial-import hashes, dependency pins, preserved license content, and local documentation links were also checked.

The build used the existing Meson/Ninja tools on this development host and staged server, control client, and library outputs with SHA256 hashes. It is a clean source build, not a hermetic build or a relocatable package. The compiler reported warnings in unchanged upstream authentication and coordinate-transform code; this check does not constitute a security audit.

Live desktop diagnostics were excluded. No service was started against the active desktop and no user configuration, firewall, or installed package was changed.

## Arch package preview

Steps 2 and 3 are recorded in [the release scope](docs/RELEASE_SCOPE.md), [packaging instructions](docs/PACKAGING.md), and [package validation](packaging/arch/VALIDATION.md). The latter covers the makepkg build, final archive, dependency isolation, and temporary-root installation/removal. It does not extend the original Mac-client runtime acceptance to the packaged deployment.

## Setup and service lifecycle

Steps 4 and 5 are implemented in version 0.1.0alpha2. [USAGE.md](docs/USAGE.md) documents explicit setup, controls, login ordering, owned keyboard/virtual-display changes, recovery, upgrade, and removal. Twenty-six isolated lifecycle tests, five package transaction tests, Lua hook checks, and two real detached-WayVNC supervisor checks cover configuration ownership, interrupted setup, credentials, network restrictions, stream revocation, crash cleanup, and preservation of unrelated files. The systemd unit passed read-only validation.

Desktop, NetworkManager, Avahi, and root transaction operations are simulated in those tests. No package was installed on the active host, and the existing lab service/configuration was left unchanged. Real Mac connection, virtual display behavior, graphical login/reboot, upgrade, and uninstall acceptance remain roadmap step 6.

## Publication preparation, package revision 2

Revision `0.1.0alpha2-2` adds bundled-code notices and explicit Codex authorship disclosure, records Paul Stoica <paul@totallynormal.io> as the contact, and rebuilds in a namespace with a generic account/path and selected build packages. The source trees and runtime behavior remain unchanged apart from documentation and packaging. The full rebuild, automatic checks, archive verification, offline source verification, and temporary-root revision upgrade/removal passed. See the leading section of [package validation](packaging/arch/VALIDATION.md) for the exact environment and remaining acceptance limits.
