# Restore the development workspace

The repositories are private. Authenticate to GitHub using an account with access before cloning. Run these commands in a new, empty parent directory; they create the local dependency names expected by `build.sh`:

```bash
gh repo clone LoFenk/mac-native-screenshare mac-native-screenshare -- --branch main
gh repo clone LoFenk/neatvnc-native-screen-sharing neatvnc -- --branch native-screen-sharing
gh repo clone LoFenk/wayvnc-native-screen-sharing wayvnc -- --branch native-screen-sharing
```

The checkpoint pins are:

| Dependency | Commit |
| --- | --- |
| NeatVNC | `458553ce35b8828f9973b20f36fe3fc8460b45ab` |
| WayVNC | `5c2fc1356d84c192d23481fa526fee30ca749ac8` |

For a historical checkout, select the matching dependency commits from that version's `dependencies.json` before building. New commits on the dependency branches do not automatically change these pins. Preserve any local changes before switching commits.

With the build dependencies in the README available, run:

```bash
bash mac-native-screenshare/build.sh "$PWD"
```

## Original Omarchy checkpoint

The original repository is preserved separately for historical recovery:

```bash
gh repo clone LoFenk/omarchy-native-screen-sharing omarchy-checkpoint -- --branch native-screen-sharing
```

Its source checkpoint is `b807f14b8ec03d95cc141df3fe160d7e863f47c6`, based on upstream `31bd80daa4613ffdee995ac27467fce5a2990806`. The original integration is in `extras/native-screen-sharing/`. It is not a dependency of the standalone project.

The files in [checkpoint/](checkpoint/) are historical records. Statements there about local-only sources or the old directory layout describe the checkpoint before these private backups and standalone extraction. Use the current README for the active layout.

## What the backup contains

The repositories preserve source code, commits, upstream authorship, licenses, dependency pins, and verification records. They do not contain host credentials, raw private logs, personal desktop configuration, downloaded Apple binaries, or build outputs. Recreating an enabled sharing service still requires the planned setup and lifecycle work; cloning these sources does not enable sharing.
