# Native Mac screen sharing: package preparation

The requirement is Finder → Network → Omarchy → Share Screen using the Mac's built-in client, including automatic text clipboard, normal pointer behavior, Mac shortcuts, and a desktop that fills the viewer. These behaviors were accepted on the development host. The existing remote.md plan favors Sunshine/Moonlight; adding a native Mac compatibility path needs maintainer discussion.

The isolated native-screen-sharing branches separate NeatVNC protocol changes, WayVNC input/capture fixes, and Omarchy integration. extras/native-screen-sharing contains the integration source checkpoint and pinned dependency build recipe. It is deliberately not wired into installation, menus, user configuration, or startup yet.

The next milestone is a versioned test package with install, explicit enable/start, stop, diagnostics, and uninstall. It must detect or request the target interface and output, create a fresh credential, constrain discovery/network access, manage virtual-display and keyboard lifecycle, and survive logout/reboot/configuration reload without private lab paths. The supported legacy transport limitation must be documented.

On a second Omarchy computer, validate installation, native Finder discovery and authentication, clipboard both ways, shortcuts, pointer, full-screen sizing, disconnect/reconnect, reboot, stop, and removal. Compare the cleaned-up system against its pre-install state. Keep original-machine acceptance distinct from parameterized integration code that has not yet run on a second host.

Prepare atomic upstream changes and portable regressions for the library/server fixes independently of Omarchy's installation decisions. Do not resubmit the existing Nettle 4 prerequisites as original contributions. No upstream PR or fork has been published by this source-preparation step.
