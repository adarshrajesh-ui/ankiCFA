---
name: freeze
description: Freeze an approved UI/UX envision session into a pixel-perfect production reference bundle. Use when the user says /freeze, asks to freeze a feature, wants a perfect feature archive, or wants the exact current visual concept preserved for production without degradation.
---

# Freeze Perfect Feature

Use this skill when the user approves a visual concept and wants it preserved exactly for implementation.

## Goal

Create a permanent freeze bundle under:

`/.lavish/perfect features/<Exact Concept Or Feature Name>/`

Never create, edit, or overwrite the repository root `README.md`. The production spec must live only inside the feature freeze folder.

The bundle must preserve:

- The exact source artifact that the user approved.
- Screenshots of how it currently looks.
- A PDF packet for review/sharing.
- A Markdown production spec that captures the feature, design intent, interaction rules, implementation scope, and “no degradation” acceptance bar.

## Workflow

1. Identify the approved source artifact.
   - Prefer the Lavish file currently being discussed.
   - If unclear, ask which `.lavish/*.html` file is the approved concept.

2. Name the freeze folder after the exact concept or feature change.
   - Use Title Case words, not a generic name.
   - Example: `.lavish/perfect features/Concept Map - Mastery Engine Liquid Glass/`

3. Save the frozen source.
   - Copy the approved HTML into the freeze folder as `source.html`.
   - Do not “improve” or restyle the source during freeze.

4. Capture screenshots from the frozen source.
   - Desktop screenshot: `desktop.png`.
   - Mobile screenshot: `mobile.png`.
   - Use Chrome headless where available.

5. Create `<freeze-folder>/FEATURE.md`.
   - Do not create or edit any other `README.md`.
   - Do not touch the repository root `README.md`.
   - Include the feature name.
   - Include the source artifact path.
   - Include all known user decisions from the envision session.
   - Include desktop and Android production scope.
   - Include visual requirements.
   - Include interaction requirements.
   - Include no-degradation acceptance criteria.
   - Include screenshot and PDF paths.

6. Create `packet.html` and `feature.pdf`.
   - The PDF must show the screenshots and include or reference the source code.
   - Keep it practical and reviewable; do not over-polish.

7. Create `manifest.txt`.
   - Include timestamp, source path, generated artifacts, and any caveats.

8. Verify the bundle exists.
   - List generated files and confirm non-zero sizes.

## Production Acceptance Template

Use this acceptance bar in `<freeze-folder>/FEATURE.md`:

```markdown
## Production Acceptance Bar

- Production must match `source.html` visually as closely as platform constraints allow.
- Desktop and Android must preserve the same concept, hierarchy, typography feel, colors, spacing, and interaction model.
- Screenshots must be compared against `desktop.png` and `mobile.png`.
- No stock Anki / AnkiDroid styling may appear on this feature surface.
- Any intentional deviation must be documented with rationale and approved before implementation.
```

## Notes

- The freeze is a contract for implementation, not just a design note.
- Do not replace the frozen file when iterating later. Create a new folder/file for each new approved envision session.
- If the user asks where the freeze went, answer with the exact folder path and key files.
- Be explicit in final responses: say `FEATURE.md` and the full freeze-folder path, never just “README.md”.
