# Licensing brief - Rack Designer (open source, AGPL-3.0)

## Context (owner decision, 2026-11-08)
Rack Designer bundles **PyQt6** (GPL-3.0 only, or commercial) since at least v0.1.19 and **PyMuPDF** (AGPL-3.0, or commercial) since v0.1.20. A closed-source exe with these libraries does not comply with their licences. The owner chose to **publish Rack Designer as open source**. Because of PyMuPDF the combined work must be under the **GNU AGPL v3** (compatible with PyQt6's GPL v3, see section 13 of both licences).
Rack Designer does **not** use the Stage Tools EULA: the AGPL itself contains the disclaimer of warranty and limitation of liability (sections 15-16). Portable builds are removed from distribution.

## Tasks
1. **Licence files**: add `LICENSE` with the full GNU AGPL v3 text (https://www.gnu.org/licenses/agpl-3.0.txt). Owner to confirm "AGPL-3.0-only" or "AGPL-3.0-or-later" (proposal: or-later, the FSF default). Add a short licence header to the source files: "Copyright (C) 2026 Riccardo Nessi" + AGPL notice. README: "Licence" section.
2. **Repository**: make it public under the `Stage-Tools` organisation. Check that every released version (0.1.17, 0.1.18, 0.1.19, 0.1.20) has a git tag on the exact commit it was built from; where missing, create the tag or attach a source zip to that GitHub release (the GPL/AGPL requires the corresponding source of every distributed binary).
3. **Appropriate Legal Notices in the UI** (GPL/AGPL section 5d): About shows the copyright, "This program comes with ABSOLUTELY NO WARRANTY", that it is free software under the GNU AGPL v3, and a link to the source repository.
4. **Clean build**: the v0.1.20 exe also contains numpy, psutil, charset_normalizer (not needed?). Build from a dedicated venv with only the real requirements (PyQt6, reportlab, PyMuPDF, Pillow if used).
5. **THIRD-PARTY-NOTICES.txt**: after the clean build, report the bundled packages and versions so the notices can be generated (PyQt6/Qt, PyMuPDF/MuPDF, reportlab, Pillow, Python ...). Install it in the program folder.
6. **Installer (rack_designer_installer.iss)**: `LicenseFile=LICENSE` (shows the AGPL); install `LICENSE` and `THIRD-PARTY-NOTICES.txt` into `{app}`. Release only the Setup (no portable zip).

## Done when
- The repo is public with LICENSE, tags/source for every release, and the About shows the legal notices.

