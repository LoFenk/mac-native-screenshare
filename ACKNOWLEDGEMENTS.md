# Acknowledgements and authorship

Project owner and contact: **Paul Stoica <paul@totallynormal.io>**.

**The project-specific implementation, tests, packaging, and documentation were produced using OpenAI Codex at Paul Stoica's direction.** Paul provides the project requirements and performs the user acceptance checks recorded in the verification documents. His Git identity identifies the project contact; it is not a claim that he manually wrote or independently reviewed the code. Automated checks are not an independent human security audit.

This independent project builds on the following upstream projects, whose original authors retain credit for their work:

- [Omarchy](https://github.com/omacom/omarchy): integration source checkpoint and desktop environment. Its MIT copyright and permission notice are preserved in [LICENSE](LICENSE).
- [NeatVNC](https://github.com/any1/neatvnc), maintained by Andri Yngvason and contributors: VNC protocol implementation. Its original history and ISC license remain in the NeatVNC repository.
- [WayVNC](https://github.com/any1/wayvnc), maintained by Andri Yngvason and contributors: Wayland capture and input. Its original history and ISC license remain in the WayVNC repository.

The distributed package also includes [third-party notices](packaging/arch/THIRD-PARTY-NOTICES) for bundled headers, protocol definitions, and other upstream source files, including xxHash (BSD-2-Clause) and the BSD queue implementation (BSD-3-Clause). These notices supplement the top-level MIT and ISC license files.

The Nettle/Hogweed 4 prerequisite changes are existing upstream work. Their cherry-pick provenance and original author identities are preserved. They are not original contributions from this project.

No upstream acceptance or endorsement is implied. Any future upstream contribution must satisfy the destination project's contribution policy, including human understanding and independent verification of AI-assisted code.
