# F7 — Android mobile CFA experience

Bundle the CFA study content as an **importable phone package** and document the
boundary between this repo and native AnkiDroid UI. In this repo, "phone support"
means the `.apkg` carries the same CFA decks, phone-friendly card templates, and
machine-readable feature manifest that AnkiDroid/AnkiMobile can import or sync.
The native Android shell/asset hook lives outside this repository.

This spans two repos (as F6 did):

| Repo                    | What lives here                                                                                     | Managed here? |
| ----------------------- | --------------------------------------------------------------------------------------------------- | ------------- |
| `ankiCFA` (this repo)   | bundled-package **builder**, tests, shared card templates, package manifest, proof/docs             | yes           |
| AnkiDroid fork/external | native Android screens, APK asset placement, first-launch **auto-import** hook, Kotlin/Gradle build | no            |

## 1. The bundled package (desktop side)

`tools/cfa/build_mobile_package.py` seeds a fresh collection and exports the
**whole collection** (`did = None`) to a single `.apkg` so the decks, note-types,
card HTML/CSS/JS, bundled media, and internal CFA feature manifest all travel
together:

- `CFA Level II` — authored CFA knowledge cards from `cfa/deck/*.jsonl`, using
  the `CFA Knowledge` phone-friendly note type and named-source footer.
- `CFA::Ethics Pairs` — the 30 current minimal-pair ethics flagship cards, using
  tap/drag multi-span highlighting and deterministic offline grading in card JS.
- `CFA::_Internal` — a suspended app-state deck containing
  `cfa.mobile.package_manifest`, a compact manifest that declares which packaged
  phone behaviours are present and which require a native client.

```
just cfa-mobile-package            # -> /tmp/cfa-mobile.apkg
just cfa-mobile-package out.apkg
just cfa-f7-test                   # builds pylib, then the F7 package tests
```

Tests (`tools/cfa/tests/test_build_mobile_package.py`, all green):

1. the package bundles both decks with the expected note counts;
2. the `.apkg` is a valid Anki package (collection db + media manifest);
3. **re-import round-trip** through the **Rust backend** (`import_anki_package`,
   the exact call the phone makes) lands both decks in a fresh collection;
4. the `CFA::_Internal` manifest note survives import and names the packaged
   phone-supported behaviours plus native-client-only features.

## 2. Auto-import on first launch (native AnkiDroid side)

- In the external AnkiDroid fork, the built `.apkg` can be shipped at
  `AnkiDroid/src/main/assets/cfa/cfa-bootstrap.apkg` (confirmed present inside the
  arm64 APK — see proof log).
- `AnkiDroid/.../CfaBootstrap.kt` adds `DeckPicker.maybeImportCfaBootstrapDeck()`,
  called once from `onFinishedStartup()`. It is **idempotent and non-destructive**:
  - runs at most once (guarded by the `cfa_bootstrap_imported` pref);
  - **only seeds an empty collection**, so it never clobbers a user's own data —
    on a non-empty collection it records the flag and returns;
  - imports **additively** through the shared fork Rust engine
    (`importAnkiPackage` with `withDeckConfigs = true`, no scheduling), then shows
    a confirmation snackbar and refreshes the deck list.
- Build and native UI work are external to this repo. There is no
  `AndroidManifest.xml`, Gradle project, Kotlin, or Java source in `ankiCFA`.

## 3. On-device proof (real emulator, fork engine)

Emulator `ankidroid_cfa` (arm64), fork APK carrying `librsdroid.so` (F6). All
screenshots via `adb exec-out screencap -p`.

| Proof                                                        | File                                              |
| ------------------------------------------------------------ | ------------------------------------------------- |
| First-launch **auto-import** fired (logcat)                  | `proof/gnhf2/f7-ondevice-autoimport-logcat.txt`   |
| Fresh profile → both decks auto-imported, no manual step     | `proof/gnhf2/f7-ondevice-autoimport-decklist.png` |
| Ethics card renders after auto-import                        | `proof/gnhf2/f7-ondevice-autoimport-ethics.png`   |
| Manual-import overview (660 notes on the Rust import screen) | `proof/gnhf2/f7-ondevice-import-660.png`          |
| Deck list (CFA Level II + Ethics Pairs)                      | `proof/gnhf2/f7-ondevice-decklist.png`            |
| Ethics card front                                            | `proof/gnhf2/f7-ondevice-ethics-front.png`        |
| One highlighted evidence span                                | `proof/gnhf2/f7-ondevice-span1.png`               |
| **Two non-contiguous** spans (true multi-span)               | `proof/gnhf2/f7-ondevice-multispan.png`           |
| On-device deterministic grade (AI-off, in-WebView JS)        | `proof/gnhf2/f7-ondevice-graded.png`              |

The logcat line proving auto-import:

```
CfaBootstrapKt: CFA bootstrap: imported bundled CFA decks from asset
```

The multi-span highlight, add/remove, verdict pick, and AI-off deterministic
grader all run inside the card template in a mobile WebView with no desktop
bridge. Android builds that inject `window.CFA_AI_GRADING_ENABLED` and a
`CFA_AI_PROXY_URL` can additionally use the server-side AI proxy; otherwise the
offline deterministic grade remains the honest fallback.

## Honest scope / caveats

- **This repo does not contain native Android UI.** It can update the package,
  shared templates, sync-facing state, and docs/tests. It cannot directly port
  the desktop Home/Study/Concept Map/Readiness shell into AnkiDroid Kotlin UI.
- The `.apkg` carries decks, notes, cards, note-types, media, and the internal
  CFA package manifest. Normal Anki sync remains the canonical path for live
  collection config/user state such as exam settings and AI toggles across
  devices.
- The auto-import seeds a **fresh, empty** collection. A user who already has a
  collection (or restores one from sync) is never overwritten — they can still
  import the same decks manually (the manual-import proof above uses that path).
- Historical proof screenshots may predate the current `CFA::Ethics Pairs`
  naming; the package builder/tests are the source of truth for the current
  shipped phone content.
