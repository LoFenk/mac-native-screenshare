# Verification record

## Original source checkpoint

The [original verification record](docs/checkpoint/VERIFICATION.md) reports a fresh build of the pinned NeatVNC and WayVNC sources with all four NeatVNC suites, three WayVNC suites, 13 integration unit checks, Lua shortcut checks, and shell syntax checks passing. It separately records the original host's Mac-client acceptance.

Those results describe the checkpoint before standalone extraction. They do not establish installer, reboot, removal, or second-machine support.

## Standalone extraction

The first repository commit preserves all 15 integration files byte for byte from Omarchy commit `b807f14b8ec03d95cc141df3fe160d7e863f47c6`. Original SHA256 hashes are recorded in [docs/checkpoint/extraction.json](docs/checkpoint/extraction.json). The Omarchy MIT license and original workspace manifest are also retained.

The standalone adaptation changes only source-directory lookup in `build.sh` and `run.sh`, the default build-output directory, dependency repository URLs, ignore rules, and documentation. The VNC source commits and other runtime scripts retain their checkpoint contents. A build no longer requires an Omarchy source checkout.

On September 13, 2026, a fresh temporary workspace containing only this standalone integration and local clones of the two pinned dependencies completed the entire build recipe. There was no Omarchy source checkout in that workspace. All four NeatVNC suites, three WayVNC suites, 13 integration unit checks, Lua shortcut checks, and shell syntax checks passed. Python source syntax, initial-import hashes, dependency pins, preserved license content, and local documentation links were also checked.

The build used the existing Meson/Ninja tools on this development host and staged server, control client, and library outputs with SHA256 hashes. It is a clean source build, not a hermetic build or a relocatable package. The compiler reported warnings in unchanged upstream authentication and coordinate-transform code; this check does not constitute a security audit.

Live desktop diagnostics were excluded. No service was started against the active desktop and no user configuration, firewall, or installed package was changed.
