# ankiCFA Lane 4 Final Proof Log

## Summary

Lane 4 scope: package and prove desktop/mobile installs, tighten premium CFA UI/UX, and document the final visual audit. Final acceptance bar: no unresolved Critical/High defects in final screenshots; Medium defects require explicit rationale; Low defects are logged.

## Package And Launch Evidence

| ID  | Platform      | Artifact                                                                             | Signing                                                                                                                                                     | Evidence                                       | Status  |
| --- | ------------- | ------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- | ------- |
| I01 | Desktop macOS | TBD DMG, expected `out/installer/dist/anki-26.05-mac-apple.dmg` via release workflow | Prefer `just release::sign --ref cfa/lane4-package-ui`; fallback `just release::build --ref cfa/lane4-package-ui` or local `just` wrapper if CI unavailable | `logs/desktop/`, `screenshots/install-launch/` | Pending |
| I02 | Android       | TBD `AnkiDroid-full-arm64-v8a-release.apk`                                           | Repo fallback release keystore unless production env vars are supplied                                                                                      | `logs/android/`, `screenshots/install-launch/` | Pending |

Desktop packaging rule: do not invoke `tools/build-installer` directly because it shells through `./ninja`; use the existing release `just` workflow or add/use an explicit `just` wrapper if local installer building is required.

Android packaging rule: build `:AnkiDroid:assembleFullRelease`; phrase signing as "signed with repo fallback release keystore" when `KEYSTOREPATH`, `KEYSTOREPWD`/`KSTOREPWD`, `KEYALIAS`, and `KEYPWD` are absent.

## Surface Proof Log

| ID  | Platform | Surface                | Severity | Evidence                                                                                     | Issue                                                                  | Fix / Action                                                                                                            | After Screenshot                                           | Result             |
| --- | -------- | ---------------------- | -------- | -------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- | ------------------ |
| M01 | Android  | CFA Home / Today       | High     | Audit finding: old mobile CFA pages read as light navy/orange islands inside stock AnkiDroid | Product identity split; not the requested premium black/gold direction | Retoned native CFA shell and Home WebView to night/gold tokens; added persistent CFA bottom shell                       | `screenshots/android/01-android-cfa-home-after.png`        | Pending screenshot |
| M02 | Android  | Exam Readiness         | High     | Audit finding: mixed CFA web/shell identity                                                  | Readiness did not share the premium mobile shell                       | Retoned readiness asset and native frame; added bottom shell                                                            | `screenshots/android/02-android-readiness-after.png`       | Pending screenshot |
| M03 | Android  | Concept Map            | High     | Audit finding: mobile map still referenced turquoise/light UI language                       | Palette and copy clashed with black/gold direction                     | Retoned map to charcoal->gold mastery fill, dark panels, gold copy                                                      | `screenshots/android/03-android-concept-map-after.png`     | Pending screenshot |
| M04 | Android  | AI Settings / More     | Medium   | Audit finding: settings/sync more surfaces can read as bolted-on                             | AI settings was light and lacked persistent shell                      | Retoned asset/native frame and selected More tab                                                                        | `screenshots/android/04-android-ai-settings-after.png`     | Pending screenshot |
| M05 | Android  | Study Hub              | High     | Audit finding: spinner trampoline feels sparse/sub-premium                                   | Study by Exam Priority had only a progress spinner                     | Retoned native study trampoline and added bottom shell; richer empty-state copy still pending final screenshot pass     | `screenshots/android/05-android-study-after.png`           | Pending screenshot |
| M06 | Android  | Reviewer front/answer  | High     | Audit finding: reviewer is the highest-priority stock-Anki surface                           | Reviewer frame and Show Answer CTA could still read as stock AnkiDroid | Retoned reviewer root/card/answer area to CFA night cockpit and promoted Show Answer to gold primary CTA with dark text | `screenshots/android/06-android-reviewer-answer-after.png` | Pending screenshot |
| D01 | Desktop  | Final desktop surfaces | Pending  | Desktop audit inventory                                                                      | Need final pass screenshots across CFA pages and escape hatches        | Use existing CFA-themed surfaces and targeted `just cfa-*` capture/check recipes                                        | `screenshots/desktop/`                                     | Pending            |

## Reproduction Commands

Desktop:

```bash
just cfa-desktop-shell-test
just cfa-chrome-test
just cfa-graphs-test
just cfa-congrats-test
just cfa-card-info-test
just cfa-deck-options-theme-test
just cfa-change-notetype-theme-test
just cfa-import-theme-test
just cfa-conceptmap-test
just cfa-installer-test
just cfa-installer-verify app="--dmg <dmg>"
```

Android:

```bash
./gradlew --no-daemon --max-workers=1 :AnkiDroid:testFullDebugUnitTest --tests '*Cfa*'
./gradlew --no-daemon --max-workers=1 :AnkiDroid:assembleFullRelease
shasum -a 256 AnkiDroid/build/outputs/apk/full/release/AnkiDroid-full-arm64-v8a-release.apk
```

PDF generation:

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --headless=new --print-to-pdf="proof/final-submission/proof-packet.pdf" "file://$PWD/proof/final-submission/proof-packet.html"
```

## Missing Or Blocked Evidence

- Desktop DMG is pending release workflow/local wrapper decision and build output.
- Android release APK is pending Gradle build, signing verification, install, launch, and screenshot proof.
- Targeted desktop `just cfa-desktop-shell-test cfa-chrome-test cfa-graphs-test cfa-conceptmap-test` failed during the shared web build before test assertions: the `congrats` bundle hit missing `.woff2` loader errors from `ts/lib/cfa/theme.scss`. Treat as a desktop verification blocker to resolve or route around with narrower recipes before final sign-off.
- Final statement is pending the last visual pass across screenshots.
