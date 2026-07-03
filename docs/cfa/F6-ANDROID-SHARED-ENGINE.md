# F6 — Android shared engine (rsdroid repoint)

**Goal.** Rebuild the ankiCFA fork Rust engine into AnkiDroid so the fork-only
backend (containing `BuildExamQueue` + the deadline/retention scheduling) runs
**on device**, not just on desktop. Verified end-to-end on an Android emulator:
the exact fork `librsdroid.so` loads, initializes, and opens a collection under
AnkiDroid.

This feature's build + product-tree changes live in a **separate repo**
(`~/wed/AnkiDroid`, branch `cfa/ankidroid-backend-repoint`) plus its sibling
backend clone (`~/wed/Anki-Android-Backend`). This file and the proof artifacts
under `proof/gnhf2/f6-*` are the desktop-repo record of that work.

## Toolchain (verified on this machine, Apple Silicon macOS)

| Component                | Value                                                       |
| ------------------------ | ----------------------------------------------------------- |
| Android SDK              | `/opt/homebrew/share/android-commandlinetools`              |
| NDK                      | `29.0.14206865`                                             |
| Rust android targets     | `aarch64-linux-android`, `x86_64-linux-android` (installed) |
| `cargo-ndk`              | `~/.cargo/bin/cargo-ndk`                                    |
| JDK for the Gradle build | `/opt/homebrew/opt/openjdk@21`                              |
| Emulator AVD             | `ankidroid_cfa` — android-34 `google_apis` **arm64-v8a**    |
| adb / emulator           | from the homebrew SDK `platform-tools/` and `emulator/`     |

## Build procedure (the proven shortcut)

The full clean cross-compile is multi-hour. The proven shortcut reuses the
fork's already-built web assets and only recompiles the Rust JNI backend:

1. **Backend AAR.** In `~/wed/Anki-Android-Backend`, build the fork engine
   into `rsdroid-release.aar` (cargo-ndk cross-compile of the fork `rslib` for
   `arm64-v8a`, packaged with the reused web assets). Output:
   `rsdroid/build/outputs/aar/rsdroid-release.aar` (~18.8 MB).
2. **Repoint AnkiDroid.** `~/wed/AnkiDroid/local.properties` sets
   `local_backend=true`; `AnkiDroid/build.gradle` then wires the sibling AAR in
   place of the published Maven backend.
3. **Assemble.** `scripts/build_fork_engine_apk.sh` runs
   `./gradlew assembleFullDebug` (skipping the Rust rebuild — the AAR is
   prebuilt), producing 4 per-ABI debug APKs. The arm64-v8a APK bundles
   `lib/arm64-v8a/librsdroid.so` (the fork engine).

One product-tree change was required: AnkiDroid's `Deck.kt` `Order` enum gained
`RELATIVE_OVERDUENESS`, which the fork's newer (26.05) backend protobuf exposes
— see the branch diff.

## The engine that ran on device IS the fork engine (byte-identical)

`proof/gnhf2/f6-fork-rpc-symbols.txt` — the fork `librsdroid.so` contains the
**fork-only** RPC schema absent from stock upstream:

```
BuildExamQueueRequest   days_to_exam   fetch_limit   topic_weights   deadline
```

The `.so` in the fork AAR and the `.so` bundled inside the installed arm64 APK
are byte-for-byte identical:

```
96a3bd381ec992bf7752acebdcd4a38b4cc777045be462645a94e3d6842d09dc  (AAR librsdroid.so)
96a3bd381ec992bf7752acebdcd4a38b4cc777045be462645a94e3d6842d09dc  (APK lib/arm64-v8a/librsdroid.so)
```

## On-device verification (real emulator run — 2026-07-03)

Booted `ankidroid_cfa` headless (`-no-window -no-snapshot -wipe-data`), installed
the arm64-v8a fork APK, launched, and granted storage so the collection opens.
`proof/gnhf2/f6-ondevice-logcat.txt`:

```
AnkiDroidApp: executed makeBackendUsable ...
AnkiDroidApp: executed setupAnkiBackend ...
AnkiDroidApp$onCreate: Backend Version = 0.1.64-anki25.09.2 (26.05b1 d5867e5b5327dc5466b44b589fc1a5c06c386047)
DeckPickerViewModel: handleStartup: Continuing after permission granted
Backend : Opening rust backend with lang=[en-US]
rsdroid : rsdroid::logging: rsdroid logging enabled     <-- the fork .so emitting a Rust log line on device
DeckPicker: onStartupResponse: Success                  <-- collection opened on the fork engine
```

`proof/gnhf2/f6-ondevice-deckpicker.png` — adb screencap of AnkiDroid's
DeckPicker running on the fork engine (empty collection, fresh `wipe-data`).

## Honest scope / caveat

- **Proven:** the _exact_ fork engine `.so` (byte-identical, carrying the
  `BuildExamQueue`/deadline RPC schema) loads, initializes its Rust runtime, and
  services AnkiDroid's collection RPCs on a real Android device. Every scheduling
  call AnkiDroid makes now runs through the fork engine.
- **Not wired yet:** AnkiDroid's stock UI has no button that invokes the
  fork-only `build_exam_queue` RPC, so logcat does not show that _specific_ RPC
  firing from a user tap. Its presence on device is proven by the symbol +
  byte-identical `.so` evidence above; surfacing it in the mobile UI (and
  auto-importing the CFA/ethics decks) is F7's scope.
- The x86_64 APK does **not** bundle `librsdroid.so` (the fork backend was
  cross-compiled for arm64 only); the arm64 emulator is the correct target on
  Apple Silicon.
