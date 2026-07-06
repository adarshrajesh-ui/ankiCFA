# ankiCFA — GNHF Final-Submission Brief

Outcome-driven brief for a GNHF run. It says **what** each feature must do and the bar for
"done," and hands the agent full ownership of **how**. Reviewer feedback from the Early
Submission is folded in (3 items, marked ★).

## How to run it (branch + environment)

Do **not** run on `main`, and do **not** direct-merge (the reviewer flagged this).

- Create a dedicated feature branch, e.g. `cfa/final-submission`, and land it via a **reviewed PR**.
- Run **in the current checkouts** (desktop `/Users/adarshrajesh/AlphaWeek2/ankiCFA`,
  mobile `/Users/adarshrajesh/wed/AnkiDroid`) so the run inherits the real environment that is
  **gitignored and therefore absent from a fresh `--worktree`**: the desktop `.env` (OpenAI key),
  the mobile `local.properties`, the running + sync-logged-in emulator, and existing build outputs.
  (The last worktree run's AI eval fell back to deterministic mode precisely because `.env` wasn't there.)
- If you want to keep using the checkout while it runs, use `--worktree` but first copy the
  gitignored env in: `.env` → the desktop worktree, `AnkiDroid/local.properties` → the mobile worktree.

Suggested: `gnhf --agent claude --max-iterations 400 --prevent-sleep on` on branch `cfa/final-submission`.

---

## GOAL (paste as the goal / termination condition)

```text
ankiCFA is a native, production-grade CFA Level II prep app on BOTH desktop (/Users/adarshrajesh/AlphaWeek2/ankiCFA) and Android (/Users/adarshrajesh/wed/AnkiDroid), sharing the fork's Rust engine. DONE when all hold:
1) Both apps feel natively CFA end-to-end — no stray, un-themed stock-Anki screens; CFA navigation is always present, not hidden behind one tab.
2) The three scores (Memory, Performance, Readiness) show with ranges and honor the give-up/abstain rule on both platforms, and still compute with AI OFF.
3) Both AI features work, each with its own toggle and a source-traceable output: (a) "press Tab to auto-complete the back" card fill, (b) AI ethics grading. A pre-release eval (accuracy + wrong-answer rate on a held-out set, with cutoff) plus a baseline comparison runs before any AI output reaches a student.
4) AI safety: an expanded prompt-injection / adversarial test suite covers every AI surface and shows malicious card or user content cannot override instructions, leak the system prompt, produce unsourced output, or bypass source-tracing; results documented.
5) The two-passage ethics item and the new Concept Map tab work identically on desktop and phone.
6) Two-way sync of the 20-card starter deck, ethics items AND their reviews, and the scores is correct: no lost or double-counted reviews; offline review works then syncs; same-card offline conflicts merge correctly and are documented. A seeded, one-command, step-by-step phone<->desktop round-trip (with on-device screenshots + logs at each step) exists so the demo can be recorded in a single take.
7) Sunday proof exists: memory-model calibration (chart + Brier/log-loss on held-out reviews), performance-model accuracy on held-out exam-style questions, a documented score mapping with a range, a 3-build ablation of the study feature at equal study time, a packaged desktop installer + signed APK, and a results report that honestly includes what didn't work.
8) A UI/UX critique log shows every desktop AND mobile surface passing a final, most-critical review pass at UWorld production grade.
9) Engineering hygiene: all work lands on feature branches via reviewed PRs — no direct-to-main merges.
Verify each increment with a lightweight check (a fast test, script, or screenshot). Commit continuously so work is self-testable. Do NOT run the heavy no-mistakes gate. Keep a living, honest progress + results report.
```

---

## TASK PROMPT (paste as the main instructions)

```text
MISSION / FRAMING
Build ankiCFA into a native, production-grade CFA Level II exam-prep app that merely happens to be built on Anki's engine — NOT "Anki with a CFA tab." Every screen, desktop and mobile, must read as a purpose-built CFA product (UWorld-grade). Reuse Anki's scheduler/engine wherever it genuinely helps CFA prep; reskin or replace anything that still looks or behaves like stock Anki.

REPOS
- Desktop: /Users/adarshrajesh/AlphaWeek2/ankiCFA
- Mobile (AnkiDroid fork): /Users/adarshrajesh/wed/AnkiDroid
- They share the fork's Rust engine. The OpenAI API key is already in the desktop .env for the AI proxy; the phone must never hold the key (it calls the proxy).

AGENT ROLES
- Orchestrator = "The Perfectionist": owns the plan and sequencing, spawns subagents, and refuses to mark anything "done" until it is both proven and polished.
- Builder subagents: implement features end-to-end and commit frequently so everything is immediately runnable and testable.
- Critic/Evaluator subagents: adversarial UI/UX reviewers held to a UWorld production bar. They take control of the screen, capture screenshots of every surface, log every defect with a severity, and drive fixes. Each review pass is stricter than the last.

HOW I WANT YOU TO WORK (read this — no micromanagement)
- You own ALL implementation decisions: architecture, file layout, libraries, and sequencing. I'm describing WHAT the product must do and the bar for "done," not HOW to build it. Make the reasonable call and keep moving; don't stop to ask.
- Full permissions. Commit after each increment so you can run and self-test right away.
- Engineering hygiene (★ from review): do all work on feature branches and land via reviewed PRs with a clear description and a reproducible test plan. NO direct-to-main merges.
- After each feature, prove it with a lightweight check — a fast test, a small script, or a captured screenshot. Keep verification light; do NOT run the no-mistakes gate.
- Keep a living, honest progress + results report, explicitly including things that didn't work.
- Do NOT produce screen-recordings/videos; capture screenshots and headless evidence instead (I'll record the final demos myself).

PHASE A — BUILD EVERY FEATURE (commit as you go). Do this before Phase B.

1) Native CFA product shell (desktop + mobile)
   - App opens into a CFA experience (home/today), not a raw deck list. CFA navigation (Home/Today, Study, Concept Map, Readiness, Ethics) is present natively across the whole app.
   - One consistent CFA design system everywhere. No visibly un-themed stock-Anki screens remain.
   - Kill the clunk: fix/replace the confusing logout and "connect" buttons and any dead-ends. Sync setup must be discoverable from an obvious in-app Settings/Connect entry — no hunting through Preferences.

2) The three CFA scores
   - Memory, Performance, and Readiness, each shown with a range and honoring the give-up/abstain rule (a score abstains when evidence is insufficient rather than faking confidence).
   - Displayed consistently on desktop and phone.

3) The two AI features — each with its own toggle, each source-traceable, each with a working AI-off fallback
   - "Tab to complete the back": in the card editor, when the front has content, an affordance invites the user to press Tab to auto-generate the back; pressing Tab calls the LLM (GPT-4o via the key in .env) and fills it in. Works on desktop and phone (phone via the proxy).
   - AI ethics grading: grades the user's ethics answer/highlight with partial-credit tiers and cites the governing Standard/source.
   - Before any AI output reaches a student, run a pre-release eval: accuracy and wrong-answer rate on a held-out set (with a knowledge cutoff), plus a baseline comparison. Every AI output must trace back to a named source.
   - With AI switched OFF, both features degrade gracefully and the app still produces the three scores.

3b) AI safety — expand prompt-injection testing (★ from review)
   - Build/expand an adversarial + prompt-injection test suite covering every AI surface (Tab-fill, ethics grading, concept-map explanations).
   - Prove that hostile card content or user input cannot: override system instructions, exfiltrate or reveal the system/developer prompt, produce output without a traceable source, escape the eval/source-tracing, or coerce unsafe/unsourced answers.
   - Document coverage and results in the report.

4) Flagship Ethics feature (keep the TWO-passage version)
   - The two-passage item — show two passages, mark each ethical/unethical, then highlight the offending text — is the flagship and is preferred over the one-passage version. Keep and polish it, with full parity on desktop and mobile.

5) Concept Map (new tab, identical on phone and desktop) — an approved interactive spec exists at .lavish/concept-map-spec.html; match it.
   - Radial hierarchy: CFA in the center (biggest), the 10 test sections orbiting it, each section's subsections beyond.
   - Node SIZE is proportional to exam weight; node FILL goes light-gray -> turquoise by mastery (100% = fully turquoise, 50% = half turquoise / half gray).
   - Hover a node -> its name + how full it is (%). Click a node -> a casual, plain-English deterministic explanation of how that score came to be, using local templated copy only.
   - Minimalist, clean, organic-but-stable layout; same behavior on both platforms (pinch-zoom on phone).

6) Two-way sync (this is core — make it rock-solid)
   - Full two-way sync of everything that matters: the 20-card starter deck, the ethics items AND their reviews, and the three scores. A review on the phone appears on the desktop and vice-versa.
   - No lost or double-counted reviews.
   - Offline review works and then syncs when the connection returns.
   - If both devices review the same card offline, the merge is correct and documented.
   - (★ from review) Provide a seeded, one-command, step-by-step phone<->desktop round-trip demo with on-device screenshots + logs captured at each step, so the required sync demonstration can be recorded in a single clean take. (You produce the reproducible path + evidence; I record the video.)

7) Sunday "prove it & ship both" deliverables
   - Memory model calibration: a calibration chart + Brier or log-loss on held-out reviews.
   - Performance model: accuracy on held-out exam-style questions.
   - Score mapping documented, with its range/method written down.
   - Study feature evaluated across three builds at equal study time (ablation), reported honestly including negative results.
   - A packaged desktop installer and a packaged signed phone build.
   - A results report + model descriptions + Brainlift, plus evidence both builds install and run clean.

PHASE B — UI/UX CRITIQUE-AND-FIX LOOP (only after Phase A features exist). This is a huge part of the job.
- Treat both apps as if shipping at UWorld production grade. Run it like a science, with a repeatable methodology.
- Enumerate every screen/surface on desktop AND mobile. Capture screenshots. Critic subagents log every UI and UX defect with a severity. Then fix them all.
- Repeat the pass — each round MORE critical than the last, raising the bar every time.
- Known clunk to hunt down: the logout/connect buttons; the CFA tab surfaces; the Readiness screen (clicking Readiness on desktop currently does ~nothing, and the in-app top-bar Exam Readiness is broken while only the menu-bar entry works); and the entire Android UI, which needs a heavy refactor.
- Maintain a living critique log (surface -> issue -> severity -> fix -> after-screenshot). Don't stop until every surface passes a final, most-critical fresh pass.

DEFINITION OF DONE: the GOAL conditions all hold, verified with lightweight checks, landed on feature branches via reviewed PRs, with an honest report of what worked and what didn't.
```
