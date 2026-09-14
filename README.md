# Mac Native Screenshare

An independent, experimental add-on project for using the Mac's built-in Screen Sharing client with an Omarchy desktop: Finder discovery, text clipboard in both directions, Mac keyboard shortcuts, and display sizing.

**Status: source checkpoint. There is no installable package or supported installer yet.** The working prototype has been tested on one Omarchy host and one Mac. The standalone sources need packaging and another machine's acceptance testing before release.

## Repositories

| Repository | Role | Branch |
| --- | --- | --- |
| [mac-native-screenshare](https://github.com/LoFenk/mac-native-screenshare) | Standalone integration, build recipe, tests, and future packaging | `main` |
| [neatvnc-native-screen-sharing](https://github.com/LoFenk/neatvnc-native-screen-sharing) | Modified NeatVNC with opt-in Apple text clipboard support | `native-screen-sharing` |
| [wayvnc-native-screen-sharing](https://github.com/LoFenk/wayvnc-native-screen-sharing) | Modified WayVNC with clipboard teardown, keyboard, pointer, and display-switch fixes | `native-screen-sharing` |
| [omarchy-native-screen-sharing](https://github.com/LoFenk/omarchy-native-screen-sharing) | Historical backup of the original Omarchy integration checkpoint | `native-screen-sharing` |

These repositories are private backups during development. The standalone build needs only the first three repositories. [dependencies.json](dependencies.json) records the exact modified dependency commits and their upstream bases. [docs/RECOVERY.md](docs/RECOVERY.md) explains how to restore the workspace.

This is a community project, independently maintained from Omarchy, WayVNC, NeatVNC, and Apple. AI assistance was used to research and implement the prototype and prepare these repositories. Original upstream authorship and licenses are retained; see [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md).

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

The build does not install software, start sharing, edit desktop configuration, or open firewall ports. Its staged files are inputs for future packaging, not a relocatable release package. It uses `/usr/bin/python3` for integration checks so a Meson virtual environment cannot hide system desktop bindings; `OMARCHY_SHARE_PYTHON` can select another interpreter with those bindings.

## Integration sources

- `run.sh`, `publish.py`, and `probe.py`: prototype server supervision, network-scoped Finder discovery, and authentication checks. `run.sh` now locates helpers beside itself, without an Omarchy source checkout. Its native mode still expects development binaries in the ignored `native-clipboard/` directory.
- `mac-shortcuts.lua` and `mac-shortcuts.sh`: remote-device keyboard mappings and prototype lifecycle control. Service names, runtime markers, and the removable Lua hook still need packaging work.
- `virtual-display.py`: the larger virtual-output trial. It takes explicit output and size inputs and currently assumes one unmirrored physical output at scale 1 and position 0,0.
- `test.py` and `test-mac-shortcuts.lua`: automated checks that do not change the desktop.
- `check-native-frame.py` and `test-output-switch.py`: explicit live-session diagnostics. They are not part of the build and must only be run against an intentionally configured test session.

The existing `OMARCHY_SHARE_*` and `OMARCHY_NATIVE_CLIPBOARD` environment names are retained for source continuity. These prototype scripts are not installation instructions. [docs/ROADMAP.md](docs/ROADMAP.md) records the remaining package and service work.

## Tested behavior and limits

The original host's native-client tests covered Finder discovery, automatic text clipboard both ways, pointer rendering, Option + Up, Command + Shift + workspace digits, other common shortcuts, and full-screen sizing. [VERIFICATION.md](VERIFICATION.md) distinguishes those historical results from standalone source checks.

The native compatibility path currently uses password-authenticated legacy VNC with **unencrypted desktop transport**. Packaging must make that limitation explicit and constrain network access appropriately. Installation, persistent service ownership, reboot recovery, upgrades, removal, other display layouts, and additional Mac versions are unfinished. Neither a working prototype nor passing automated tests establishes production readiness.

## License and provenance

Integration sources are preserved under the [MIT license](LICENSE) from their Omarchy source checkpoint. NeatVNC and WayVNC keep their separate ISC licenses in their own repositories. [docs/checkpoint/extraction.json](docs/checkpoint/extraction.json) records the original integration commit and file hashes; the first commit of this repository preserves those imported files byte for byte.
