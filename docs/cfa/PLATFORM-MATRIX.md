# CFA fork — Platform capability matrix (Feature F8)

This document is the honest, single-page answer to _"what runs where?"_ for the
CFA exam-prep fork across the **desktop** app (PyQt + pylib + the Rust engine)
and the **phone** (AnkiDroid running the byte-identical fork `librsdroid.so`,
per [F6](F6-ANDROID-SHARED-ENGINE.md)). The fork's AnkiDroid is now branded
**ankiCFA** and is growing **native CFA screens** — the first shipped one being
the on-device **Exam Readiness** score screen (see the 📱 tier and the mobile
caveat below).

Every capability falls into one of these tiers:

| Tier                  | Meaning                                                                                                                                 | How it gets to the phone                                                                                                  |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| 🟢 **Shared-engine**  | Pure Rust in `rslib`, exposed as a read-only RPC. Runs _identically_ on desktop and device because the same compiled `.so` executes it. | Ships inside the fork APK (F6). Reads whatever content/config is present in the collection.                               |
| 🔵 **Synced-content** | Data (notes, cards, decks, note-types, `col.conf`) that lives in the collection and travels over Anki's native sync protocol.           | AnkiWeb / self-hosted `anki-sync-server` round-trip (F8). Same Rust sync engine on both ends.                             |
| 🟠 **Desktop-only**   | PyQt/pylib features with no on-device counterpart. Deliberately additive and gated so the phone renders cleanly without them.           | Does **not** travel. AI-off / on-device paths fall back to a deterministic equivalent or simply omit the surface.         |
| 📱 **Native mobile**  | A native AnkiDroid (Kotlin) CFA screen in the fork app (branded **ankiCFA**), additive to upstream. Landing on branch `friday/mobile`.  | Ships in the fork APK. Reads the same synced collection/config; computes on-device where a shared RPC is not yet exposed. |

---

## The matrix

| Capability                                                                            | Feature    | Tier                                 | On desktop                                             | On phone                                                                                                                                                                                          | Evidence                                                                                                                              |
| ------------------------------------------------------------------------------------- | ---------- | ------------------------------------ | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Exam-priority queue (`BuildExamQueue`)                                                | F0b / F8   | 🟢 Shared-engine                     | ✅                                                     | ✅ runs on synced content                                                                                                                                                                         | [f8-persistence-report.txt](../../proof/gnhf2/f8-persistence-report.txt) step 6; [F6](F6-ANDROID-SHARED-ENGINE.md)                    |
| Deadline retention (`DeadlineRetention`)                                              | F2/DOK-4   | 🟢 Shared-engine                     | ✅                                                     | ✅ (same RPC on device)                                                                                                                                                                           | [F6](F6-ANDROID-SHARED-ENGINE.md), fork RPC symbols                                                                                   |
| Content-type weighting (`type::` multipliers)                                         | F8-legacy  | 🟢 Shared-engine                     | ✅                                                     | ✅ (part of queue RPC)                                                                                                                                                                            | queue scores in the F8 report                                                                                                         |
| CFA Level II study deck                                                               | deck-build | 🔵 Synced-content                    | ✅                                                     | ✅ (sync **and** bundled apkg)                                                                                                                                                                    | F8 report step 5; [F7](F7-ANDROID-MOBILE-EXPERIENCE.md)                                                                               |
| Ethics one-passage deck + note-type                                                   | F1         | 🔵 Synced-content                    | ✅                                                     | ✅ (card renders + multi-span highlight)                                                                                                                                                          | [F7](F7-ANDROID-MOBILE-EXPERIENCE.md) screencaps; F8 report                                                                           |
| Multi-span deterministic grader (in-card JS)                                          | F1         | 🔵 Synced-content                    | ✅                                                     | ✅ (runs in the WebView, AI-off)                                                                                                                                                                  | [F7](F7-ANDROID-MOBILE-EXPERIENCE.md) `f7-ondevice-graded.png`                                                                        |
| **Exam config** (`cfa_exam_config` in `col.conf`)                                     | F0b / F8   | 🔵 Synced-content                    | ✅                                                     | ✅ **over sync only**                                                                                                                                                                             | F8 report step 5 — the piece the apkg could **not** carry                                                                             |
| Review history / FSRS scheduling state                                                | core       | 🔵 Synced-content                    | ✅                                                     | ✅ (more-recent-review-wins)                                                                                                                                                                      | [test_cfa_sync.py](../../pylib/tests/test_cfa_sync.py)                                                                                |
| AI tab-to-fill card backs                                                             | F3         | 🟠 Desktop-only                      | ✅ (editor, AI-off → disabled button)                  | ❌ (no editor surface on device)                                                                                                                                                                  | [F3 notes]; button gated on `ai_enabled()`                                                                                            |
| Semantic LLM grading of highlights                                                    | F2         | 🟠 Desktop-only                      | ✅ (pycmd → Python → LLM)                              | ❌ (AI-off deterministic grader runs instead)                                                                                                                                                     | on-device grade uses the F1 fallback                                                                                                  |
| Exam-readiness scores: Memory / Performance / Readiness (+ranges, abstain, per-topic) | F4 / D6    | 🟢 desktop RPC + 📱 native mobile    | ✅ `ExamReadinessDialog` (shared `compute_cfa_scores`) | ✅ native **Exam Readiness** screen (3 scores + ranges + give-up/abstain + per-topic recall) on fork `friday/mobile` — **deterministic on-device scorer** (shared `computeCfaScores` RPC pending) | desktop [f4-readiness-*.png](../../proof/gnhf2/); mobile [Anki-Android PR #1](https://github.com/adarshrajesh-ui/Anki-Android/pull/1) |
| Deadline / exam-date picker dialog                                                    | F0b/F5     | 🟠 Desktop-only                      | ✅ (`DeadlineDialog`, sets `col.conf`)                 | ❌ dialog — but the **config it writes syncs** (🔵)                                                                                                                                               | [f0b-deadline-*.png](../../proof/gnhf2/)                                                                                              |
| CFA design system (Qt QSS + card `:root` tokens)                                      | F5         | 🟠 Desktop-only (Qt) / 🔵 (card CSS) | ✅                                                     | ✅ card styling only                                                                                                                                                                              | [DESIGN-SYSTEM.md](DESIGN-SYSTEM.md)                                                                                                  |

---

## Why the split is what it is

- **The Rust engine is the same binary on both platforms.** F6 proved the
  installed `lib/arm64-v8a/librsdroid.so` is byte-identical (sha256) to the
  fork AAR and carries the fork-only `BuildExamQueueRequest` symbols. So any
  read-only RPC we add to `rslib` is automatically a 🟢 shared-engine feature —
  it needs no per-platform UI to _execute_, only content + config to read.

- **`col.conf` travels over sync but not in an `.apkg`.** F7 discovered that an
  `AnkiPackageExporter` bundle (even whole-collection) carries decks, notes,
  cards, note-types, and media, but **not** arbitrary `col.conf` keys — a
  reimport returned `None` for `cfa_exam_config`. F8 confirms the sync path
  _does_ carry it: seeding the config on the desktop and syncing lands it
  verbatim on a fresh phone collection (F8 report step 5). Practical
  consequence: **the bundled deck bootstraps a phone offline, but the exam date
  and topic weights only appear after the first AnkiWeb/self-hosted sync.**

- **Desktop-only features are additive and fail safe.** The AI features (F2
  grading, F3 tab-fill) are gated on `cfa.ai.llm_client.ai_enabled()`; with no
  key they disable/omit the surface and the deterministic F1 grader runs
  instead — this is exactly what happens on device, where there is no editor
  and no key. The scoring/deadline dialogs are Qt surfaces with no AnkiDroid
  port, but the _data they write_ (`col.conf`) is 🔵 synced-content, so a
  desktop-set exam date still reaches the phone.

## Reproducing the persistence proof

```
just cfa-f8-test          # 3 tests: decks+ethics deck, exam config, shared-engine queue over a real sync server
PYTHONPATH=out/pylib:pylib:. out/pyenv/bin/python tools/cfa/f8_persistence_proof.py   # narrated round-trip
```

Both stand up a real local `anki-sync-server` (a subprocess running Anki's own
`run_sync_server`) and drive a genuine desktop → server → fresh-phone full
sync; the phone side is a Rust-backed `Collection`, the identical engine F6
proved loads under AnkiDroid. Output: [proof/gnhf2/f8-persistence-report.txt](../../proof/gnhf2/f8-persistence-report.txt).

## Honest caveats

- The F8 automated proof exercises the sync **protocol** with two collections
  driven by the same Rust engine that runs on device; it does not, by itself,
  drive the AnkiDroid UI through a login+sync. The on-device deck rendering and
  ethics-card behaviour are proven separately by F7's real emulator screencaps.
  Together they cover the claim end-to-end (content renders on device + the
  same content/config travels over the shared sync engine), which is the honest
  scope of this feature.
- Media sync is disabled in the round-trip (`sync_media=False`); the CFA decks
  and ethics cards carry no external media, so this does not affect the result.
- **Native mobile surfaces — honest status.** The fork's AnkiDroid work lives on
  branch `friday/mobile` ([Anki-Android PR #1](https://github.com/adarshrajesh-ui/Anki-Android/pull/1)),
  not yet merged to AnkiDroid `main`. Only the **Exam Readiness** screen (the
  three scores + ranges + abstain + per-topic recall) is done and proven on a
  real arm64 emulator; its scores come from a **deterministic on-device scorer**
  (the screen is labeled "Source: on-device (deterministic)") because the shared
  `computeCfaScores` RPC is not yet exposed in the engine. The native
  Study-by-Exam-Priority action, the on-device exam-config editor, and
  minimal-pairs on device are **in progress** on the same branch and are
  deliberately **not** claimed as shipped here. The exam-priority queue and the
  exam-config _data_ already reach the phone today via the 🟢 shared RPC and 🔵
  sync respectively (rows above); what is landing is their native mobile _UI_.
