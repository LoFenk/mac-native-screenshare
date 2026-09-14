# Source checkpoint verification — September 13, 2026

The NeatVNC and WayVNC branches were reconstructed from the accepted split patches and subsequent keyboard/display deltas. Every changed source file matches the running prototype's source byte for byte: 16 NeatVNC files and six WayVNC files. The existing Nettle 4 prerequisite commits were cherry-picked with their original authors and source commit references.

A new build directory compiled both branches successfully with GCC 16.2.1, Meson 1.12.0, and Ninja 1.13.2. The complete build.sh path then passed all four NeatVNC suites, all three WayVNC suites, 13 integration unit checks, Lua Command/Option-Up checks, and shell syntax checks. Staged server, control client, and library artifacts have SHA256 hashes. This is a source recipe with recorded dependencies, not a hermetic or bit-identical build claim.

The integration copy was checked for Python syntax and known private host identifiers. Explicit environment inputs replace the original physical connector, dimensions, test credential path, and fixed user runtime directory. run.sh uses OMARCHY_PATH for its source directory. Those parameterized runtime paths and the eventual installer still need a separate desktop acceptance test; the source-preparation step did not run them against the active session.

The build initially exposed the Meson virtual environment hiding system Python D-Bus bindings. The recipe now explicitly selects the system interpreter for integration checks and verifies those bindings before compiling. The successful final run exercised that correction.

Original-host native acceptance remains documented separately from the fresh build: Finder discovery, automatic text clipboard both ways, visible pointer, tested Mac shortcuts, and full-screen sizing through a virtual output. No new sharing service, firewall rule, user configuration, or installation was activated by this source-preparation step. Nothing has been pushed or submitted upstream.
