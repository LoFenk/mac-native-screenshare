# Mac Native Screenshare

An independent, experimental add-on project for using the Mac's built-in Screen Sharing client with an Omarchy desktop: Finder discovery, text clipboard in both directions, Mac keyboard shortcuts, and display sizing.

**Status: experimental developer preview, 0.1.0 alpha 2. Setup, service controls, and recovery/removal are implemented.** The working prototype has been tested on one Omarchy host and one Mac. The packaged lifecycle still needs another machine's acceptance testing before a stable release; automated and detached-server checks are not real-client acceptance.

**Project contact: Paul Stoica <paul@totallynormal.io>. The project-specific implementation, tests, packaging, and documentation were produced using OpenAI Codex at Paul's direction.** His commit identity does not imply manual authorship or independent code review. Upstream authors retain credit for their code; see [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md).

## Download and install

Use the binary package and `SHA256SUMS` from the [alpha 2 revision 2 release](https://github.com/LoFenk/mac-native-screenshare/releases/tag/v0.1.0-alpha.2-r2). While the repository is private, downloads require an account with access. Once public, the same release page permits public downloads. Read the [usage guide](docs/USAGE.md) before configuring sharing.

```bash
sha256sum -c SHA256SUMS --ignore-missing
sudo pacman -U ./mac-native-screenshare-0.1.0alpha2-2-x86_64.pkg.tar.zst
```

The attached `.src.tar.gz` is the complete rebuildable source bundle, including the modified dependencies. It can be rebuilt without access to the separate dependency repositories. GitHub's automatically generated source archives are not that complete bundle. See [packaging instructions](docs/PACKAGING.md).

## Repositories

| Repository | Role | Branch |
| --- | --- | --- |
| [mac-native-screenshare](https://github.com/LoFenk/mac-native-screenshare) | Standalone integration, package recipe, tests, and documentation | `main` |
| [neatvnc-native-screen-sharing](https://github.com/LoFenk/neatvnc-native-screen-sharing) | Modified NeatVNC with opt-in Apple text clipboard support | `native-screen-sharing` |
| [wayvnc-native-screen-sharing](https://github.com/LoFenk/wayvnc-native-screen-sharing) | Modified WayVNC with clipboard teardown, keyboard, pointer, and display-switch fixes | `native-screen-sharing` |
| [omarchy-native-screen-sharing](https://github.com/LoFenk/omarchy-native-screen-sharing) | Historical backup of the original Omarchy integration checkpoint | `native-screen-sharing` |

The dependency and historical backup repositories are currently private. They are optional for users rebuilding the complete release source bundle. A development build from Git checkouts needs the first three repositories. [dependencies.json](dependencies.json) records the exact modified dependency commits and their upstream bases. [docs/RECOVERY.md](docs/RECOVERY.md) explains how to restore the workspace.

This project is independent of Omarchy, WayVNC, NeatVNC, and Apple; none of those projects endorses this package. Report issues with this add-on here, following [CONTRIBUTING.md](CONTRIBUTING.md).

See [the first release scope](docs/RELEASE_SCOPE.md) for the target environment, feature boundaries, network limitations, and release gates.

## Build an Arch package

See [docs/PACKAGING.md](docs/PACKAGING.md) for the checksum-locked recipe and package checks, [the usage guide](docs/USAGE.md) for setup and lifecycle controls, and [the validation record](packaging/arch/VALIDATION.md) for test evidence. Installation leaves sharing disabled; the desktop user explicitly configures and starts it.

## Build the source checkpoint

Arrange the repositories as follows; their local directory names matter to the dependency build recipe:

```text
workspace/
├── mac-native-screenshare/
├── neatvnc/
└── wayvnc/
```

The recorded build environment uses GCC 16.2.1, Meson 1.12.0, and Ninja 1.13.2. Development dependencies include AML, Wayland client, pixman, TurboJPEG, GnuTLS, Nettle/Hogweed 4, GMP, zlib, libdrm, jansson, and xkbcommon. Integration checks need Lua and Python D-Bus/GObject bindings. Meson and Ninja must be on `PATH`. Compatibility with other distributions and dependency versions remains unverified.

From the parent workspace, run:

```bash
bash mac-native-screenshare/build.sh "$PWD"
```

The recipe checks the two dependency commit IDs and clean working trees, builds privately, runs the existing automated checks, and stages binaries with SHA256 hashes under `build/mac-native-screenshare/stage/`. An optional second argument selects a different build directory. Use a fresh build directory when changing source checkout locations; Meson records absolute source paths.

The build does not install software, start sharing, edit desktop configuration, or open firewall ports. Its staged files are development components; use the Arch recipe for a relocatable package. It uses `/usr/bin/python3` for integration checks so a Meson virtual environment cannot hide system desktop bindings; `OMARCHY_SHARE_PYTHON` can select another interpreter with those bindings.

## Integration sources

- `mns_cli.py`, `mns_common.py`, `mns_session.py`: package setup, private settings, user controls, and supervision.
- `mns_desktop.py`, `hyprland-hook.lua`: exact config ownership, keyboard activation, virtual display reload/restoration, and crash recovery.
- `mns_relay.py`, `mns_discovery.py`: private Unix backend, subnet-restricted TCP access, interface-scoped Finder discovery, and network revocation.
- `mac-native-screenshare.service`, `package-lifecycle.py`, and the two pacman hooks: graphical login ordering and cleanup before package replacement/removal.
- `test-lifecycle.py`, `test-supervisor.py`, `test-package-lifecycle.py`, `test-hyprland-hook.lua`: isolated lifecycle tests and real detached-server checks.
- `run.sh`, `publish.py`, and `probe.py`: prototype server supervision, network-scoped Finder discovery, and authentication checks. `run.sh` now locates helpers beside itself, without an Omarchy source checkout. It requires private `bin/` and `lib/` directories beside the helpers, or an explicit `MAC_NATIVE_SCREENSHARE_RUNTIME_DIR` pointing to a development staging directory. It never falls back to a system WayVNC binary.
- `mac-shortcuts.lua` and `mac-shortcuts.sh`: retained keyboard mappings and historical prototype lifecycle control. The package uses the Lua mappings through its dedicated hook.
- `virtual-display.py`: the larger virtual-output trial. It takes explicit output and size inputs and currently assumes one unmirrored physical output at scale 1 and position 0,0.
- `test.py` and `test-mac-shortcuts.lua`: automated checks that do not change the desktop.
- `check-native-frame.py` and `test-output-switch.py`: explicit live-session diagnostics. They are not part of the build and must only be run against an intentionally configured test session.

The existing `OMARCHY_SHARE_*` and `OMARCHY_NATIVE_CLIPBOARD` environment names are retained for source continuity. These prototype scripts are not installation instructions. [docs/ROADMAP.md](docs/ROADMAP.md) records the remaining package and service work.

## Tested behavior and limits

The original host's native-client tests covered Finder discovery, automatic text clipboard both ways, pointer rendering, Option + Up, Command + Shift + workspace digits, other common shortcuts, and full-screen sizing. [VERIFICATION.md](VERIFICATION.md) distinguishes those historical results from standalone source checks.

The native compatibility path uses password-authenticated legacy VNC with **unencrypted desktop transport**. Setup requires acceptance and a selected private LAN; discovery and the relay are restricted to that selection. Real reboot, upgrade, desktop restoration, performance, and Mac-client acceptance remain step 6. Neither a working prototype nor passing automated tests establishes production readiness.

## License and provenance

Integration sources are preserved under the [MIT license](LICENSE) from their Omarchy source checkpoint. NeatVNC and WayVNC keep their separate ISC licenses. The package also includes the [full third-party notices](packaging/arch/THIRD-PARTY-NOTICES), including BSD-2-Clause and BSD-3-Clause terms for bundled code. [docs/checkpoint/extraction.json](docs/checkpoint/extraction.json) records the original integration commit and file hashes; the first commit of this repository preserves those imported files byte for byte.
