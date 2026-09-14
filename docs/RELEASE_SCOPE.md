# First release scope: 0.1.0 alpha 2

This is an experimental developer preview. Setup, service enablement, reboot ordering, and removal/recovery are implemented and covered by isolated tests. Installation leaves sharing disabled. This public prerelease is available for testing; a stable release remains gated on a second machine's real desktop and Mac acceptance tests. See [USAGE.md](USAGE.md) for the controls and lifecycle limits.

## Target environment

| Area | Initial target and evidence |
| --- | --- |
| Host | Arch Linux x86-64 running Omarchy 4.0.x; development baseline Omarchy 4.0.3-1 |
| Desktop | Logged-in Hyprland session using the Omarchy Lua configuration; baseline Hyprland 0.56.2-2, initial target 0.56.x |
| Client | Apple's built-in Screen Sharing on macOS Tahoe 26.x; the prototype user's reported version was 26.6.2, not independently inspected |
| Network | One explicitly selected NetworkManager IPv4 connection on the same trusted private LAN as the Mac; local mDNS discovery must be available |
| Displays | One physical output, initially unmirrored, at scale 1 or 2 and position 0,0; optional single scale-1 virtual output for viewer sizing |
| Users | One Mac controlling the host user's existing desktop; no separate remote login or independent multiuser desktop |

Package revision 3 adds scale-2 setup, physical capture guards, and scale preservation through virtual staging, mirroring, and recovery. The regression tests simulate the compositor and execute generated monitor rules in Lua; a successful Mac connection at scale 2 has since been reported after applying the scoped firewall rule; pointer accuracy and virtual-display acceptance remain pending.

These are release targets, not claims that every version in a range has been tested. Package dependencies bound the Omarchy and Hyprland versions to the initial target families. New host versions, other Macs, and other layouts need explicit compatibility testing.

## Intended user-visible behavior

The completed first release should discover the host in Finder's Network view and connect through Share Screen using a newly generated sharing password. It should support text clipboard in both directions, visible pointer rendering, the tested Command/Option shortcuts, and an optional larger virtual display with restoration when sharing stops.

The original host's prototype demonstrated these behaviors. The packaged installation must repeat those tests before they become supported package behavior. The release does not include audio, file/image clipboard, drag-and-drop transfer, remote disk unlock, access before desktop login, unattended headless boot, multiple physical displays, fractional scaling, or a replacement Mac client.

## Transport and access limits

The native compatibility mode uses legacy VNC password authentication. Desktop, input, and clipboard traffic are **not encrypted by VNC**; the password mechanism only uses eight bytes. Setup generates a fresh random eight-character credential, stores it privately, and requires acceptance of the transport limitation. Starting and login enablement are explicit commands.

Initial use is confined to a deliberately selected trusted private LAN, with access and discovery restricted to that selection. It must not automatically listen on every interface, enable router forwarding, expose the service publicly, or assume that password authentication encrypts the connection. Network/profile changes should stop discovery and sharing. A VPN or SSH tunnel could protect transport, but automatic tunnel setup and cross-subnet Finder discovery are outside the first release scope.

## Package milestone

The package owns a private software tree, documentation/licenses, one CLI launcher, a disabled user unit, and two pre-transaction cleanup hooks. It does not replace Arch's `wayvnc` or `neatvnc` or claim to provide their system libraries. Installing it does not modify Hyprland configuration, enable startup, create credentials, or open firewall ports. Explicit setup owns two marked user config blocks and private settings; removal preserves unrelated edits. Interactive setup can offer a scoped UFW rule with explicit confirmation and sudo authentication. Global Avahi enablement, UFW enablement, and removal of administrator-confirmed firewall rules remain separately managed. A terminal display menu offers temporary sizing and toggleable instructions; normal monitor changes remain Omarchy settings. Real desktop and client lifecycle acceptance remains unfinished.

## Release gates

1. Build the pinned sources and pass protocol, keyboard, and packaging checks.
2. Verify the installed server resolves its bundled NeatVNC library with no build-directory dependency and coexists with the stock package files.
3. Complete explicit setup/start/stop/status and managed service, keyboard, network, and display lifecycles.
4. On a second Omarchy host with a Mac client, test install, Finder discovery, authentication, clipboard, shortcuts, sizing, reconnect, reboot, upgrade, stop, and uninstall.
5. Document tested versions and remaining limitations before inviting outside testers.
