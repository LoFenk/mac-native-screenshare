# Path to an independent package

1. Preserve the source checkpoints in private GitHub repositories and extract standalone integration. This is the scope of the initial repository preparation.
2. Define a first release's supported Omarchy/Mac versions, display layouts, network use, and documented transport limitations.
3. Create an Arch package with exact source versions, dependency declarations, and isolated server/library paths.
4. Implement setup, explicit enable/start, stop, and status. Select the network and display, generate fresh credentials, check port use, and manage Finder discovery.
5. Implement service ordering, keyboard hooks, virtual-display restoration, reboot recovery, upgrades, and clean removal. Track and undo only the changes owned by this add-on.
6. Test install, connect, clipboard, shortcuts, pointer, sizing, reconnect, reboot, upgrade, and uninstall on a second Omarchy host with a real Mac client.
7. Publish a clearly experimental release with matching source, build instructions, checksums, known limitations, upstream credits, and AI-assistance disclosure.
8. Consider AUR distribution and optional Omarchy documentation or menu integration. Independently pursue upstream contributions with a human able to understand and verify the code, retiring local patches as upstream releases include equivalent fixes.

The repository extraction does not implement a package installer, enable services, or establish additional runtime acceptance. The original working lab installation remains separate from these source repositories.
