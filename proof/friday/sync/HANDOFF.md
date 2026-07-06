# friday/sync — cross-scope HANDOFF

From **W-sync** (branch `friday/sync`). Items below are OUTSIDE the sync
workstream's edit scope (sync run/config scripts, desktop custom-sync config,
AnkiDroid sync _config_, `card.custom_data` persistence hook, double-count
tests, `proof/friday/sync/**`). They are written here for the owning workstream.

---

## → W-mobile / orchestrator (AnkiDroid CFA app code) — on-device collection diverges from the synced collection

**Severity: blocks device-level sync PERSISTENCE verification (not the sync engine).**

The CFA AnkiDroid build (`com.ichi2.anki.debug`) ships custom activities
(`CfaExamPriorityActivity`, `CfaExamReadinessActivity`, `CfaExamConfigActivity`)
and a first-launch bootstrap. Observed during increment 2:

- The collection AnkiDroid **syncs** to the server is a rich 261-revlog
  collection that at times contains a transient `CFA Exam Priority` deck
  (99 cards). This uploads correctly (verified: server
  `/tmp/cfa-syncserver/cfa/collection.anki2` = 261 revlog; desktop full-download
  matched).
- The **on-disk** collection at `/storage/emulated/0/AnkiDroid/collection.anki2`
  is a 3-revlog collection (WAL empty/checkpointed) that does **not** reflect the
  synced state, and reverts across cold launches. The `CFA Exam Priority` deck
  appears/disappears between launches.
- The custom activities also intercept the launch path: `IntentHandler` routes to
  `CfaExamPriority/Readiness/Config` instead of `DeckPicker`, and pressing Back on
  the DeckPicker exits to the home screen — both make deterministic UI automation
  of the sync flow fragile.

**Impact on W-sync:** the sync _mechanism_ is proven end-to-end (real
`FULL_UPLOAD` from the phone with real content on the server, real
`FULL_DOWNLOAD` to a second device, a clean single-review delta crossing
phone→desktop). But because the phone's persisted collection resets, a
_device-observable_ round-trip (seeing a desktop-made review appear and STICK on
the phone) can't be reliably captured. Reverse-direction correctness is instead
proven by the machine-checked pytest against the real server + real Rust sync
engine.

**Requested fix (mobile app owner):** ensure the CFA custom activities and the
bootstrap operate on the SAME `CollectionManager` collection that AnkiDroid syncs
(do not load/replace a separate enriched collection for Exam Priority/Readiness),
and don't reset `collection.anki2` on launch once `cfa_bootstrap_imported=true`.
Exact files (mobile repo `/Users/adarshrajesh/wed/AnkiDroid`):
`AnkiDroid/src/main/java/com/ichi2/anki/Cfa*Activity.kt` and the CFA bootstrap.

---

## → orchestrator (scores) — apply per-(card,day) dedup in memory_score / compute_cfa_scores

`memory_score()` in `pylib/anki/cfa.py` (~571) counts **raw** revlog rows per card
(`count(*)`). After sync, the same card reviewed on two devices the same day
correctly yields **two** revlog rows (see `test_offline_same_card_dual_review_*`)
but the give-up rule's `graded_reviews` total must use **per-(card, day) dedup**.

**Fix:** use `cfa_sync.deduped_graded_review_count(col)` (or equivalent) instead of
`summ(review_counts.values())` when computing `MemoryScore.graded_reviews` and the
give-up check in `_giveup_reason`.

Flagship regression test: `pylib/tests/test_cfa_sync_dedup.py::
test_offline_same_card_dual_review_revlog_distinct_not_inflated`.

---

## → W3 / ethics — full attempt-detail payload exceeds Anki custom_data limits

Anki enforces **top-level keys ≤ 8 bytes** and **serialized custom_data ≤ 100 bytes**.
The full W3 payload (spans, verdicts, selectionIndices) cannot fit.

**Sync workstream ships:** `cfa_sync.compact_ethics_payload()` + namespace
`cfaEthic` (8 chars) with fields `{id, ok, hl, src, std}`. Desktop hook:
`qt/aqt/cfa_ethics_sync.py` (registered from `qt/aqt/cfa.py`).

**AnkiDroid bridge still needed** to read `localStorage["cfaEthics:pending"]` and
write the same compact shape before sync (out of sync scope).
