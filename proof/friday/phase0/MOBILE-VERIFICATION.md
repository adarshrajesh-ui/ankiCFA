# Mobile verification — what I drove + captured (emulator `emulator-5554`)

I drove the live `ankidroid_cfa` emulator (AnkiDroid `com.ichi2.anki.debug`) to
verify the mobile side directly. Screenshots in this dir.

## Confirmed: the mobile app is a NATIVE CFA product

- **Branding** — title bar reads **"ankiCFA / 40 cards due"**; custom app icon
  (dark tile, red star) in the launcher (`mobile-01…04`).
- **CFA content** — decks `CFA` ▸ `Ethics Pairs` + `CFA Level II`; the Ethics
  deck's cards are **"Contrastive Pair"** notes (`MISREP-01…`, `PRIORITY-01…`)
  = the minimal-pairs flagship (`mobile-02/03`).
- **Native nav** — the drawer's top entry is **"Exam Readiness"** (above Decks /
  Browser / Statistics) — a CFA-first information architecture (`mobile-06`).

## D6 evidence — phone shows the 3 scores with give-up (`mobile-09-readiness.png`)

`CfaExamReadinessActivity` renders:

- Header **"ANKICFA · CFA LEVEL II — Exam Readiness"**.
- **Three scores** — READINESS / MEMORY / PERFORMANCE — each with its state
  ("N/A — abstaining") and the give-up reason.
- Give-up thresholds + wording **match my engine byte-for-byte**:
  "not enough data: 1 graded reviews (need **200**), 0% topic coverage (need
  **50%**)"; "1 first-seen questions (need **30**)". These are exactly
  `cfa.py`'s `MIN_GRADED_REVIEWS=200`, `MIN_TOPIC_COVERAGE=0.50`,
  `MIN_FIRST_EXPOSURES=30` and reason strings.
- **Per-topic recall** for all **8 canonical topics** (Alt Investments, Corporate
  Issuers, Economics, Equity, Ethics, FRA, Portfolio Mgmt, Quant).
- Evidence line: "1 graded reviews · 0/8 topics covered (0%) · 1 first exposures".

⇒ D6's "phone shows 3 scores w/ **give-up**" is demonstrated. Ranges (vs give-up)
render once the profile has ≥200 graded reviews / ≥50% coverage (this demo
profile has 1 review, so it's honestly in give-up state).

## Honest gaps (why this isn't yet full "desktop == mobile parity")

- The screen says **"Source: on-device (deterministic)"** — the app is built
  from the pre-RPC AAR (21:03) and `CfaScoresProvider` is on its **fallback**
  path (`SOURCE_FALLBACK`), a _second_ Kotlin implementation. The fallback was
  clearly written to mirror the engine (identical thresholds/wording/topics),
  but true single-engine parity needs the RPC.
- **To close it (mobile worker's integration step):** now that the RPC is on
  `main`, rebuild the AAR (`Anki-Android-Backend/cfa_build_fork_engine.sh` →
  regenerates `computeCfaScores` binding), wire `CfaScoresProvider.scores()` to
  `col.backend.computeCfaScores(...)` (map to `CfaScores`, `SOURCE_RPC`),
  reinstall, and this same screen reads "Source: shared engine". Then a
  populated profile shows the ranges and the desktop parity holds by
  construction.
- **D4/D5 (sync round-trip recording):** the harness (`just cfa-syncserver`) +
  the emulator are ready; recording a review→sync→desktop round-trip is the
  final device step, best done with the mobile worker's finished build to avoid
  driving their in-progress app (it went briefly unstable under external
  automation, a sign it's actively owned).
