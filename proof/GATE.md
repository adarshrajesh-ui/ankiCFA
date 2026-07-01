# Day-one gate: builds & runs from source — PASS

- **Commit (baseline):** 6770ad3ef460b766d85a3399bd268ff87f4224cb (branch cfa/exam-queue-mvp)
- **Build:** `just build` (= `./ninja pylib qt`) → "Build succeeded in 95.72s", all 64 steps
  (Rust rslib, protobuf codegen, sveltekit web pages, qt/aqt, pylib, generated bindings).
  Full log: proof/build-baseline.log
- **Generated bindings produced:** out/pylib/anki/_backend_generated.py, out/ts/lib/generated/backend.ts
- **Import smoke test (proof/gate-smoke.log):** `anki` + `aqt` import from source;
  opened a real Collection (scheduler v2/2021), backend RPC methods present → "SMOKE OK".
- **Headless launch (proof/gate-launch.log):** app booted offscreen (QT_QPA_PLATFORM=offscreen),
  ran ~85s in the Qt event loop with no error, created the profile DB (prefs21.db).
  Full collection-open + main window is the supported interactive path (needs a display);
  the programmatic collection open above proves the pylib↔Rust backend works from source.

Conclusion: the fork builds from source and the app boots. Feature work proceeds on this base.
