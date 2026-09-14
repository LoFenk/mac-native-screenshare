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
