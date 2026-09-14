# Native screen sharing development workspace

Three isolated Git checkouts preserve the tested source changes. Each uses the `native-screen-sharing` branch. Exact upstream bases, local commit IDs, and changed-file hashes are in [workspace.json](workspace.json). These are local branches, not published GitHub forks or PRs.

- [Omarchy integration and build recipe](omarchy/extras/native-screen-sharing/README.md)
- [NeatVNC Apple protocol source](neatvnc/src/apple-clipboard.c)
- [WayVNC input/capture source](wayvnc/src/main.c)
- [Fresh-build verification](omarchy/extras/native-screen-sharing/VERIFICATION.md)

With the documented build dependencies and Meson/Ninja on PATH, run this from this workspace:

```bash
bash omarchy/extras/native-screen-sharing/build.sh "$PWD"
```

The checked build outputs are under build/stage, with SHA256SUMS. They are package inputs; this is not yet an installable package. The original working desktop still uses the separate lab snapshot. No live configuration was changed for this workspace.

The next milestone is the installer/service/configuration lifecycle, followed by a clean installation and removal test on a second Omarchy computer. Keep runtime acceptance separate from source/build checks. Publishing these branches to forks and opening PRs are later explicit actions.
