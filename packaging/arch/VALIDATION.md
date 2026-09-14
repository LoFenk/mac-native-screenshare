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
