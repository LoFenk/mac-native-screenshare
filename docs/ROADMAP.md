# Path to an independent package

1. Completed: preserve the source checkpoints in private GitHub repositories and extract standalone integration.
2. Completed: define the first release targets and limitations in [RELEASE_SCOPE.md](RELEASE_SCOPE.md).
3. Completed: [PACKAGING.md](PACKAGING.md) documents exact source versions, dependency declarations, isolated paths, and validation.
4. Implemented: setup, explicit enable/start, stop, status, network/display selection, fresh credentials, port checks, and Finder discovery. See [USAGE.md](USAGE.md).
5. Implemented: graphical session ordering, owned keyboard/display hooks, crash and virtual-display recovery, package upgrade/removal cleanup. Covered by isolated tests; real desktop/reboot acceptance is step 6.
6. Test install, connect, clipboard, shortcuts, pointer, sizing, reconnect, reboot, upgrade, and uninstall on a second Omarchy host with a real Mac client.
7. Publish a clearly experimental release with matching source, build instructions, checksums, known limitations, upstream credits, and AI-assistance disclosure.
8. Consider AUR distribution and optional Omarchy documentation or menu integration. Independently pursue upstream contributions with a human able to understand and verify the code, retiring local patches as upstream releases include equivalent fixes.

Installing the package does not enable sharing or establish additional real-client acceptance. The original working lab installation remains separate from these source repositories.
