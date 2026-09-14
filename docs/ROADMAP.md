# Path to an independent package

1. Completed: preserve the source checkpoints in private GitHub repositories and extract standalone integration.
2. Completed: define the first release targets and limitations in [RELEASE_SCOPE.md](RELEASE_SCOPE.md).
3. Completed for the inert developer preview: [PACKAGING.md](PACKAGING.md) documents exact source versions, dependency declarations, isolated paths, and validation. This is an inert developer preview; the following lifecycle work is still required.
4. Implement setup, explicit enable/start, stop, and status. Select the network and display, generate fresh credentials, check port use, and manage Finder discovery.
5. Implement service ordering, keyboard hooks, virtual-display restoration, reboot recovery, upgrades, and clean removal. Track and undo only the changes owned by this add-on.
6. Test install, connect, clipboard, shortcuts, pointer, sizing, reconnect, reboot, upgrade, and uninstall on a second Omarchy host with a real Mac client.
7. Publish a clearly experimental release with matching source, build instructions, checksums, known limitations, upstream credits, and AI-assistance disclosure.
8. Consider AUR distribution and optional Omarchy documentation or menu integration. Independently pursue upstream contributions with a human able to understand and verify the code, retiring local patches as upstream releases include equivalent fixes.

Repository preparation and the inert package do not enable services or establish additional runtime acceptance. The original working lab installation remains separate from these source repositories.
