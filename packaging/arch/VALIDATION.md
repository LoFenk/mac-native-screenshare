# 0.1.0alpha2-4 display menu and firewall confirmation

Validated September 14, 2026. This experimental prerelease adds a terminal display menu, instructions that can be shown/hidden, and explicit confirmation before applying a scoped UFW rule. Installation remains inert; setup and sharing remain user actions.

## Behavior and sources

`mac-native-screenshare display` offers the normal desktop, three temporary-size presets, and a custom resolution. The guide explains normal Omarchy display settings, Mac viewer scaling, and temporary desktops. Reading or hiding the guide does not change settings or hold the command lock. Display changes require confirmation; an active share is restarted and the Mac briefly disconnects. Stopped sharing stays stopped. Credentials, other settings, and login startup are preserved. Failed restarts restore the prior choice when cleanup succeeds; incomplete cleanup retains recovery state and reports the required actions.

Interactive setup shows the scoped UFW rule and asks before applying it through sudo. The default is no. `firewall --apply` offers the same confirmation for existing installations. Plain `firewall`, noninteractive setup, and `setup --skip-firewall` only print guidance. Confirmation is independent of sudo credential caching, only UFW is elevated, and its terminal is inherited for authentication. Cancelling or failing sudo retains completed setup. UFW enablement, other rules, and administrator rule removal remain separately managed.

Integration source: `f39102f3ccc0bed08a4ebf4c9c3830606012022e`. WayVNC and NeatVNC pins are unchanged from revision 3. `sources.json` records the snapshots and archive hashes; the complete source bundle includes all three and the authoritative outer recipe. The release tag identifies the subsequent packaging commit.

Project contact: Paul Stoica <paul@totallynormal.io>. Project-specific implementation, tests, packaging, and documentation were produced using OpenAI Codex at Paul's direction. His Git identity does not imply manual authorship or independent review. Upstream authors retain credit and the complete bundled license notices remain included.

## Completed checks

- Full two-job build in a fresh workspace within the existing isolated, network-disabled build root, using the generic builder account and `/work` directory.
- Four NeatVNC suites, three WayVNC suites, 13 integration tests, 50 lifecycle tests, five package transaction tests, Lua shortcut/hook checks, and two real detached-WayVNC supervisor tests passed.
- Nine new firewall tests cover confirmation after setup is saved, exact rule preview and invocation, decline/empty input/EOF/interrupt, missing tools, no terminal, explicit skip, sudo failure, changed addresses during consent, and read-only versus apply CLI behavior. Ten new display-menu tests cover guide toggling, presets/custom sizes, normal-mode restoration, cancellation, rejected sizes, active restart ordering, state preservation, failed restart rollback, failed cleanup, and guide access before setup without a terminal.
- A real terminal session exercised opening the menu and showing/hiding the guide with temporary settings. It made no desktop or firewall changes. Display/service operations and sudo execution in the automated tests are simulated.
- Compressed package verification passed for private file layout, permissions, licenses, pinned provenance, disabled startup, transaction hooks, private RUNPATH, bundled library resolution, CLI/binary smoke checks, and stock VNC coexistence. The installed guide and `firewall --help` are checked explicitly.
- A temporary pacman root upgraded revision 3 to revision 4, verified the installed files, and removed the package without residual files or a database entry. Transaction hooks are simulated separately and masked in that temporary root. Declared runtime dependencies resolve on the development host; optional UFW 0.36.2-7 and sudo 1.9.17.p2-6 are available there.
- The complete source bundle passed offline checksum verification, and its outer PKGBUILD hash matches the binary's `.BUILDINFO`. Packaged CLI and guide bytes match both the pinned snapshot and reviewed source. Generic build metadata contains no personal home paths; 173 selected package records are retained.
- Gitleaks scanned reachable integration history and expanded binary/source artifacts including nested archives. The eight findings match the previously reviewed runtime-password concatenation expression and xxHash SIMD variable assignments; none contains a credential. Expanded artifacts contain no personal home-directory paths.

## Environment and remaining acceptance

The reused build root contains selected installed package-owned `/usr` files and generated generic configuration. It had no host home directory, live desktop sockets, credentials, or network access. Meson 1.12.0 and Ninja 1.13.2 are external tools, recorded separately from the package inventory in `build-environment.json`. Build dependency availability and those versions were checked before `makepkg --nodeps`. This is not a fresh-package clean chroot or a bit-identical reproducibility claim. Existing upstream compiler warnings remain.

The user reported a working Mac connection to a second Omarchy host at physical scale 2 after applying the scoped firewall rule. Real virtual-display/menu restarts, the new sudo prompt on that host, clipboard/shortcuts, pointer accuracy, graphical reboot, and active package upgrade/removal acceptance remain pending. These checks do not constitute an independent security audit. The package remains unsigned and uses unencrypted native VNC on the selected trusted private LAN.

No package was installed on the active development desktop. Its existing lab service, desktop settings, firewall, and credentials were not changed.

---

# 0.1.0alpha2-3 scale-2 fix and validation

Validated September 14, 2026. This public experimental prerelease fixes setup/start rejection for a single physical display at scale 2. Physical capture leaves the monitor scale alone. Virtual-display staging and mirror rules retain the physical scale, use its logical width for temporary positioning, and restore the saved scale before removing the virtual output. The optional virtual output remains at scale 1. Fractional scaling remains outside the preview.

## Sources and authorship

Integration source: `2a6c513d69aaa9441f6538d13e9c82a3288ed326`. WayVNC and NeatVNC pins are unchanged from revision 2. The complete source bundle contains all three snapshots and the outer rebuild recipe; `sources.json` records their hashes. The release tag identifies the subsequent packaging commit.

Project contact: Paul Stoica <paul@totallynormal.io>. Project-specific implementation, tests, packaging, and documentation were produced using OpenAI Codex at Paul's direction. The Git identity does not imply manual authorship or independent code review. Upstream authors retain credit. The complete bundled license notices are unchanged and accompany the binary and source bundle.

## Completed checks

- Full two-job build in the network-disabled, isolated build root with a generic builder account and `/work` directory.
- Four NeatVNC suites, three WayVNC suites, 13 integration tests, 31 lifecycle tests, five package transaction tests, Lua shortcut/hook checks, and two real detached-WayVNC supervisor tests passed.
- Five new display tests cover physical start/guard at scales 1 and 2, rejection of unsupported layouts before mutation, continued guard enforcement, virtual staging/mirroring/recovery at both scales, and retaining scale 2 in a failed-start recovery journal. Generated monitor rules execute in Lua and their scale, position, mode, and mirror fields are checked.
- Compressed binary verification passed: private file layout, permissions, complete licenses, pinned provenance, disabled startup, scoped transaction hooks, private RUNPATH, bundled library resolution, CLI/binary smoke checks, and no stock VNC file overlap.
- A temporary pacman root upgraded `0.1.0alpha2-2` to `0.1.0alpha2-3`, verified the installed files, and removed the package without residual files or a database entry. The full declared runtime dependencies resolve on the development host. Transaction hooks are simulated separately; the temporary root masks them because it has no desktop user managers.
- The complete source bundle passed offline input checksum verification. Its outer PKGBUILD hash matches the binary's `.BUILDINFO`. The packaged display code is byte-identical to the pinned integration snapshot and reviewed working source.
- `.BUILDINFO` retains the approved contact, generic build paths, and 173 selected package records. Expanded binary and source artifacts contain no personal home-directory paths.
- Gitleaks scanned reachable integration Git history and the expanded binary/source artifacts, including nested source archives. Its eight findings were reviewed: the VNC configuration expression `password=` concatenated with a runtime variable, and xxHash SIMD variable assignments. None contained a credential.

## Environment and acceptance limits

The existing isolated root was reused with a fresh build workspace. It contains selected installed package-owned `/usr` files, generic configuration, and the package records described in `build-environment.json`. It had no host home directory, live desktop/session sockets, machine credentials, or network access. Meson 1.12.0 and Ninja 1.13.2 were external tools, recorded separately from the package inventory. Build dependencies and those tool versions were checked before `makepkg --nodeps`.

This is an isolated build from selected host package files, not a fresh-package clean chroot or a bit-identical reproducibility claim. Existing upstream compiler warnings remain. Desktop, NetworkManager, Avahi, and transaction operations are simulated in lifecycle tests. Real Mac capture at scale 2, pointer/click alignment, virtual mirroring, clipboard/shortcuts, graphical login/reboot, and active desktop upgrade/removal still need acceptance on the second machine. These automated tests do not constitute an independent security audit.

This remains an unsigned preview with unencrypted native VNC transport confined to the selected trusted private LAN. No package was installed on the active development desktop; its existing lab service and desktop configuration were not changed.

---

# 0.1.0alpha2-2 publication preparation and validation

Validated September 14, 2026. This package revision preserves alpha 2 runtime behavior, adds the complete bundled-code notices, uses the approved project contact, and removes personal workstation metadata from the build artifacts. It remains an unsigned experimental preview. Installation leaves sharing disabled; second-machine/Mac and live desktop acceptance remain pending.

## Authorship and source

Project contact: Paul Stoica <paul@totallynormal.io>. The project-specific implementation, tests, packaging, and documentation were produced using OpenAI Codex at Paul's direction. The Git identity identifies the contact and does not imply manual authorship or independent code review. Upstream authors retain credit for their work.

Integration source: `08ebb7eafe816b58dc4461a77e8a8e17f5ef1b8c`. The WayVNC and NeatVNC pins are unchanged. `sources.json` records all three commits and source checksums; the complete `.src.tar.gz` contains those source snapshots and the recipe. The outer recipe is authoritative when rebuilding the bundle.

The binary includes the MIT/ISC license files and 62 distinct upstream notice blocks covering bundled source, headers, and protocol definitions, including xxHash (BSD-2-Clause) and BSD queues (BSD-3-Clause). Package license metadata includes the BSD licenses. Verification checks the complete packaged notice file against the recipe and rejects incomplete notices.

## Completed validation

- Full two-job build in an isolated, network-disabled namespace using a generic builder account and `/work` directory.
- Four NeatVNC suites, three WayVNC suites, 13 integration checks, 26 lifecycle checks, five package transaction checks, Mac shortcut/Lua hook checks, and two real detached-WayVNC supervisor checks passed.
- Compressed package checks passed for file layout, permissions, licenses, disabled startup, transaction hooks, private RUNPATH, bundled-library resolution, CLI/binary smoke checks, and stock VNC file coexistence.
- A temporary pacman root passed installation, upgrade from `0.1.0alpha2-1`, and removal without residual package files or a database record. Lifecycle hooks are tested separately; the temporary root masks them because it has no desktop user managers.
- The complete source bundle verified all inputs offline. Its PKGBUILD hash matches the binary's `.BUILDINFO`.
- `.BUILDINFO` records the approved contact, generic `/work` paths, and the 173 selected package records from the build environment. It does not contain the personal workstation's complete package inventory.

## Build environment and limits

The isolated root was assembled from selected installed package-owned `/usr` files and package records, with generic configuration generated separately. Factory configuration and an unreadable privileged D-Bus launcher were omitted. It had no host home directory, desktop/session sockets, machine credentials, or network access. Meson 1.12.0 and Ninja 1.13.2 were included as external tools and are explicitly recorded outside pacman's package inventory in `build-environment.json`.

Build dependencies available in the root and external tool versions were checked before `makepkg --nodeps`. The full declared runtime dependencies were checked separately on the target host, including Omarchy 4.0.3 / Hyprland 0.56.2 and the Nettle 4 ABIs. The root intentionally omits the full desktop runtime. This is an isolated build from selected host package files, not a clean chroot installed from freshly downloaded packages or a bit-identical reproducible-build claim.

Desktop, NetworkManager, Avahi, and root transaction operations are simulated in the automated lifecycle tests. Real Mac connection, virtual displays, graphical login/reboot, active desktop upgrades/removal, and an independent security audit remain outstanding. Unchanged upstream compiler warnings remain. Native VNC desktop, input, and clipboard transport is unencrypted and limited to the selected trusted private LAN.

No package was installed on the active desktop. Its existing lab service, credentials, configuration, and firewall were not changed.

---

# 0.1.0alpha2-1 packaging and lifecycle validation

Validated on September 13, 2026. This unsigned private developer preview implements roadmap steps 4 and 5. Installation leaves sharing disabled; real desktop/Mac acceptance is still step 6.

## Completed checks

- Full makepkg build from integration commit `6136589c61daaad32b83b19a1679d0f6d648e353` and the unchanged, checksum-pinned NeatVNC/WayVNC commits.
- Four NeatVNC suites, three WayVNC suites, and thirteen existing integration checks passed.
- Twenty-six lifecycle tests passed: setup/rollback, fresh private credentials, repeat setup, invalid input, network/profile/subnet changes, exact hook removal, preservation of personal edits, crash journals, virtual-display recovery, lock coordination, and actual bounded relay connections/revocation.
- Five package transaction tests passed: stop before upgrade/removal, preservation on upgrade, privilege drop before reading user configuration, offline cleanup, and abort on failure.
- Mac keyboard and runtime Lua hook checks passed. The user unit passed `systemd-analyze --user verify` without installation or activation.
- Two supervisor tests used the real private WayVNC in detached mode on temporary Unix sockets and localhost. Wrong passwords were rejected and the correct password accepted before readiness; simulated network loss closed an established relay client before desktop cleanup; server termination cleaned up children, the listener, and generated credentials. No compositor was attached and no desktop content was requested.
- The final compressed package passed file-layout, mode, license, metadata, private RUNPATH, bundled-library, CLI/binary smoke, disabled startup, transaction-hook, and stock-file coexistence checks.
- Temporary-root pacman installation/removal passed. An alpha 1 → alpha 2 package upgrade also passed and removed obsolete packaged prototype helpers.
- The complete source bundle verified all inputs offline; its PKGBUILD SHA256 matches the binary package's `.BUILDINFO`.

## Environment and limits

Host baseline: x86-64 Omarchy 4.0.3-1, Hyprland 0.56.2-2, GCC 16.2.1, Nettle 4.0. Existing Meson 1.12.0 and Ninja 1.13.2 tools were used outside pacman's database. All other declared dependencies passed `pacman -T` before `makepkg --nodeps`; both external tool versions were independently checked and recorded in `external-build-tools.json`.

Desktop, NetworkManager, Avahi, and root transaction operations are simulated in lifecycle tests. The temporary pacman root masks the two transaction hooks because it has no user managers or Python installation; hook behavior is tested separately, not against real user homes. This was not a clean-chroot build, real graphical-login/reboot test, actual pacman cleanup of an active desktop, real virtual-display/client acceptance test, or security audit. Unchanged upstream compiler warnings remain in authentication and coordinate-transform code.

Native VNC transport is unencrypted. Avahi enablement and administrator firewall rules are separately managed. The new package has not been installed on this development host, and its existing lab service, desktop configuration, credentials, firewall, and installed packages were not changed. Public release and second-host/Mac acceptance remain pending.

---

# 0.1.0alpha1-1 packaging validation

Validated on September 13, 2026. This is an unsigned, private developer preview. It installs inert files, not a configured sharing service.

## Results

- Built with makepkg from three commit-pinned, SHA256-verified source archives.
- Four NeatVNC suites and three WayVNC suites passed.
- Thirteen integration unit checks, Lua shortcut checks, and source syntax checks passed.
- The staged tree and final compressed binary package passed private-path, file-mode, license, metadata, and binary smoke checks.
- The installed server resolves the bundled NeatVNC through `$ORIGIN/../lib` after relocation, without relying on a build-directory path or inherited `LD_LIBRARY_PATH`.
- No package files overlap installed stock WayVNC/NeatVNC files; no global VNC replacement/provision/conflict is declared.
- All built runtime dependencies, including Nettle ABI requirements, resolve against the development host's package database.
- A separate temporary root and database passed pacman package installation, executable checks, and removal with no remaining package files or package record. The empty test database bypassed dependency installation; dependency availability was checked separately on the host.
- Source checksum tampering, a nonempty export destination, and substitution of the bundled library with a system-library symlink were rejected.
- The complete source package was extracted separately and all its source checksums verified without GitHub access. Its recipe matches the binary package's recorded PKGBUILD hash.

## Environment and limits

Host baseline: x86-64 Omarchy 4.0.3-1, Hyprland 0.56.2-2, GCC 16.2.1, Nettle 4.0. The existing Meson 1.12.0 and Ninja 1.13.2 virtual-environment tools were used; these two tools are not registered in pacman's database. Before makepkg --nodeps, all other declared build/runtime/check dependencies were verified using pacman -T and both tool versions were checked independently. The artifact directory contains external-build-tools.json; the package contains .BUILDINFO.

This was not a clean-chroot build, an independent security audit, or a second-machine/Mac acceptance test. The compiler still reports warnings in unchanged upstream authentication and coordinate-transform code. Native Mac transport remains unencrypted legacy VNC, with the network limitations described in the release scope.

Setup/start/stop/status, managed desktop/network/service configuration, reboot and upgrade recovery, and real-client acceptance remain steps 4 through 6. No package was installed into the active host, and its running sharing service, desktop, firewall, credentials, and system packages were not changed.
