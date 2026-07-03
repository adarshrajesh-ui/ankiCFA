# F7 — Android mobile CFA experience

Bundle the two CFA study decks as an **app asset**, **auto-import them on first
launch**, and prove the one-passage ethics card renders and its **multi-span
highlight + deterministic grading** work **on device** on the fork Rust engine.

This spans two repos (as F6 did):

| Repo | What lives here | Managed by gnhf? |
|------|-----------------|------------------|
| `ankiCFA` (this repo) | the bundled-package **builder** + tests + on-device **proof** + this doc | yes — merged to origin/main |
| `~/wed/AnkiDroid` (fork) | the **asset** + first-launch **auto-import** hook | no — committed on its own branch `cfa/ankidroid-backend-repoint` |

## 1. The bundled package (desktop side)

`tools/cfa/build_mobile_package.py` seeds a fresh collection with both decks and
exports the **whole collection** (`did = None`) to a single `.apkg` so the decks,
their note-types, and the ethics card's HTML/CSS/JS templates all travel together:

* `CFA Level II` — 630 authored notes across 8 topics (`cfa/deck/*.jsonl`)
* `CFA::Ethics Passages` — the 30 F1 one-passage multi-span items

```
just cfa-mobile-package            # -> /tmp/cfa-mobile.apkg
just cfa-mobile-package apkg=out.apkg
just cfa-f7-test                   # builds pylib, then the 3 F7 tests
```

Tests (`tools/cfa/tests/test_build_mobile_package.py`, all green):
1. the package bundles both decks with the expected note counts;
2. the `.apkg` is a valid Anki package (collection db + media manifest);
3. **re-import round-trip** through the **Rust backend** (`import_anki_package`,
   the exact call the phone makes) lands both decks in a fresh collection.

## 2. Auto-import on first launch (AnkiDroid side)

* The built `.apkg` is shipped at
  `AnkiDroid/src/main/assets/cfa/cfa-bootstrap.apkg` (confirmed present inside the
  arm64 APK — see proof log).
* `AnkiDroid/.../CfaBootstrap.kt` adds `DeckPicker.maybeImportCfaBootstrapDeck()`,
  called once from `onFinishedStartup()`. It is **idempotent and non-destructive**:
  * runs at most once (guarded by the `cfa_bootstrap_imported` pref);
  * **only seeds an empty collection**, so it never clobbers a user's own data —
    on a non-empty collection it records the flag and returns;
  * imports **additively** through the shared fork Rust engine
    (`importAnkiPackage` with `withDeckConfigs = true`, no scheduling), then shows
    a confirmation snackbar and refreshes the deck list.
* Build: `~/wed/AnkiDroid/scripts/build_fork_engine_apk.sh` (reuses the prebuilt
  fork `rsdroid-release.aar` — `assembleFullDebug`; incremental Kotlin build ~35s).

## 3. On-device proof (real emulator, fork engine)

Emulator `ankidroid_cfa` (arm64), fork APK carrying `librsdroid.so` (F6). All
screenshots via `adb exec-out screencap -p`.

| Proof | File |
|-------|------|
| First-launch **auto-import** fired (logcat) | `proof/gnhf2/f7-ondevice-autoimport-logcat.txt` |
| Fresh profile → both decks auto-imported, no manual step | `proof/gnhf2/f7-ondevice-autoimport-decklist.png` |
| Ethics card renders after auto-import | `proof/gnhf2/f7-ondevice-autoimport-ethics.png` |
| Manual-import overview (660 notes on the Rust import screen) | `proof/gnhf2/f7-ondevice-import-660.png` |
| Deck list (CFA Level II + Ethics Passages) | `proof/gnhf2/f7-ondevice-decklist.png` |
| Ethics card front | `proof/gnhf2/f7-ondevice-ethics-front.png` |
| One highlighted evidence span | `proof/gnhf2/f7-ondevice-span1.png` |
| **Two non-contiguous** spans (true multi-span) | `proof/gnhf2/f7-ondevice-multispan.png` |
| On-device deterministic grade (AI-off, in-WebView JS) | `proof/gnhf2/f7-ondevice-graded.png` |

The logcat line proving auto-import:

```
CfaBootstrapKt: CFA bootstrap: imported bundled CFA decks from asset
```

The multi-span highlight, add/remove, verdict pick, and the AI-off deterministic
grader (verdict correctness + "N of M spans found") all run in the AnkiDroid
WebView with **no desktop bridge** — exactly the F1 fallback. The F2 AI feedback
block is desktop-only (pycmd) and correctly does not appear on device.

## Honest scope / caveats

* **Decks + ethics cards travel in the bundle; the exam config does not.** An
  `.apkg` (`AnkiPackageExporter`) carries decks, notes, cards, note-types and
  media — but not arbitrary collection config, so the exam date/weights set by
  `cfa.set_exam_config` are **not** in `cfa-bootstrap.apkg` (verified by a
  reimport round-trip returning `None`). The exam config reaches the phone via
  **AnkiWeb sync** from the desktop, which is F8's cross-platform-persistence
  concern; the platform split is formalized in F8's `PLATFORM-MATRIX.md`.
* The auto-import seeds a **fresh, empty** collection. A user who already has a
  collection (or restores one from sync) is never overwritten — they can still
  import the same decks manually (the manual-import proof above uses that path).
* This is a **debug** build against a local fork AAR, run on an emulator, not a
  Play-Store release.
