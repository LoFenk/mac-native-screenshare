# Build the experimental Arch package

The package name is `mac-native-screenshare`, version `0.1.0alpha2-1`, for `x86_64`. It targets the environment in [RELEASE_SCOPE.md](RELEASE_SCOPE.md). Installation leaves sharing disabled. The package installs a user unit and upgrade/removal hooks, but does not enable startup, create credentials, change firewall rules, or edit desktop configuration. Explicit setup and controls are documented in [USAGE.md](USAGE.md).

## Source and recipe layout

The recipe lives in [packaging/arch/PKGBUILD](../packaging/arch/PKGBUILD), with package metadata in `.SRCINFO`. [sources.json](../packaging/arch/sources.json) pins the integration, NeatVNC, and WayVNC Git commits and the SHA256 of each deterministic source archive. All `source` entries have real SHA256 checksums; none use `SKIP`.

The integration source is pinned to the commit implementing setup, service controls, recovery, and transaction cleanup. Later packaging/documentation commits do not silently change that source snapshot. The two VNC branches remain at their original tested commits. The recipe applies a small, checksum-verified Meson patch to WayVNC solely to set the installed binaries' private library search path.

Sources are exported locally because the repositories are private. Authentication tokens are not put in download URLs or a `PKGBUILD`. The export helper reads the named Git commits, not uncommitted working-tree contents, and verifies their archive hashes before writing a new build directory. It refuses to overwrite a nonempty directory.

## Build

Restore the three-repository workspace using [RECOVERY.md](RECOVERY.md). From its parent directory, run:

```bash
/usr/bin/python3 mac-native-screenshare/packaging/arch/prepare-sources.py \
  --workspace "$PWD" \
  --output "$PWD/package-build/0.1.0alpha2"
cd package-build/0.1.0alpha2
makepkg
/usr/bin/python3 verify-package.py \
  --package ./mac-native-screenshare-0.1.0alpha2-1-x86_64.pkg.tar.zst
```

Use a new output directory for a fresh build. The builder needs Arch's `base-devel` and the runtime/build/check dependencies declared in the recipe, including Meson 1.12 or newer and Ninja. `makepkg` does not install anything unless explicitly invoked with install/dependency-install options, which the commands above omit.

`makepkg` verifies the archives, builds the private sources, runs their existing tests and integration checks, stages the selected runtime files, validates that tree, and creates the binary package. The post-build check inspects the actual compressed artifact after stripping. Build concurrency is limited to two jobs for this preview.

To create a self-contained source package containing the exact archives and recipe:

```bash
makepkg --allsource
```

That source package can be rebuilt without access to the private repositories once the required build dependencies are available. It must be kept private until a public release is authorized. These steps do not claim a hermetic or bit-identical binary build: system libraries and toolchains are recorded by `.BUILDINFO`, not vendored into the package.

## Installed files and dependency isolation

```text
/usr/lib/mac-native-screenshare/
  bin/wayvnc
  bin/wayvncctl
  lib/libneatvnc.so.1 -> libneatvnc.so.1.0.1
  lib/libneatvnc.so.1.0.1
  mns_*.py, package-lifecycle.py, probe.py, VERSION
  mac-shortcuts.lua, hyprland-hook.lua
/usr/bin/mac-native-screenshare
/usr/lib/systemd/user/mac-native-screenshare.service
/usr/share/libalpm/hooks/
  mac-native-screenshare-upgrade.hook
  mac-native-screenshare-remove.hook
/usr/share/doc/mac-native-screenshare/
  README.md, USAGE.md, RELEASE_SCOPE.md, ACKNOWLEDGEMENTS.md, sources.json
/usr/share/licenses/mac-native-screenshare/
  LICENSE, neatvnc-COPYING, wayvnc-COPYING
```

The installed WayVNC binaries use `$ORIGIN/../lib` as their runtime library search path. Meson's install step removes the absolute build-library path. The package does not install `/usr/bin/wayvnc`, a global `libneatvnc`, pkg-config files, or development headers, and does not declare `provides`, `conflicts`, or `replaces` for the stock packages. The runtime scripts choose the private control client as well as the private server; a missing private runtime is an error rather than a fallback to stock software.

System dependencies such as AML, Nettle, GnuTLS, Wayland, Python, NetworkManager, Avahi, systemd, util-linux, and Hyprland stay managed by pacman. Nettle library ABI requirements are recorded in the built package; the initial Omarchy/Hyprland version families are constrained. Dependency declarations do not start the corresponding services.

JPEG, TLS support, and the existing protocol tests are enabled. H.264/GPU capture, PAM login, man-page generation, and example binaries are disabled for this package. This does not enable encrypted native Mac transport: the tested Mac compatibility path still uses legacy unencrypted VNC.

## Validation boundaries

The package checks verify private paths and file modes, required licenses and source metadata, absence of installation activation, exact service/transaction-hook paths and directives, `$ORIGIN` library lookup, use of the bundled NeatVNC, executable smoke checks, and non-overlap with installed stock VNC package files. They do not start a desktop server. Lifecycle checks exercise temporary user configuration, subnet rejection, live relay revocation, recovery, and cleanup failure handling. Two supervisor checks use the real private WayVNC in detached mode with simulated desktop/NetworkManager/Avahi operations. The service unit is also checked with systemd-analyze verify.

Run `packaging/arch/test-package-install.py <package-file>` (optionally with `--upgrade-from <older-package>` to check replacement of older files) from the repository with Python to exercise file installation/removal in an isolated package database/root without installing this preview on the development desktop. This check also needs `fakeroot` and the declared runtime dependencies available on the host. Such a test uses the host libraries for executable checks and does not establish a clean-machine deployment. The temporary-root pacman check masks the two lifecycle hooks because that root has no user managers or Python installation; their behavior is tested separately with mocked subprocesses. This does not replace real upgrade/removal and second-host/Mac acceptance in step 6.

## Updating source pins

Commit and test the intended integration/dependency changes first. Update `sources.json` with those exact commits, regenerate the gzip archives with `git -c tar.umask=0022 archive` and `gzip -n -9`, update the recipe's SHA256 values, and regenerate `.SRCINFO` from the recipe. Build from a new empty output directory. Never rewrite an existing package version to contain different source code; increment the appropriate version or package release.

Reference: [Arch PKGBUILD manual](https://man.archlinux.org/man/PKGBUILD.5.en), [makepkg manual](https://man.archlinux.org/man/makepkg.8.en), and [Meson installation documentation](https://mesonbuild.com/Installing.html).

The completed validation and the use of existing Meson/Ninja tools outside the package database are recorded in [packaging/arch/VALIDATION.md](../packaging/arch/VALIDATION.md).
