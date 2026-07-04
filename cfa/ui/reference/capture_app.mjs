// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
// capture_app.mjs
// ---------------------------------------------------------------------------
// Screenshot the LIVE CFA SvelteKit pages exactly as the desktop app serves
// them, via the *system* Google Chrome ({ channel: 'chrome' }) — no chromium
// download required, same harness style as capture_site.mjs.
//
// Point it at a running tools/cfa/serve_cfa_pages.py instance (the real
// aqt.mediasrv bound to ANKI_API_PORT against a richly-seeded collection):
//
//   PORT=40000 DECK_ID=<deckId> node cfa/ui/reference/capture_app.mjs
//
// Each page is captured at the width of its real Qt host dialog
// (ExamReadinessDialog 640px, DeadlineDialog 560px) so the shot reflects what
// the learner actually sees, then full-page so nothing is clipped. Console
// errors and failed sub-requests (e.g. a missing font/chunk) are collected and
// printed so the capture can be trusted (or honestly flagged).
// ---------------------------------------------------------------------------

import { mkdir } from "node:fs/promises";
import path from "node:path";

async function loadChromium() {
    const candidates = [process.env.PW_MODULE, "playwright", "playwright-core"].filter(Boolean);
    const errs = [];
    for (const c of candidates) {
        try {
            const mod = await import(c);
            if (mod.chromium) return mod.chromium;
            if (mod.default && mod.default.chromium) return mod.default.chromium;
        } catch (e) {
            errs.push(`${c}: ${e.message || e}`);
        }
    }
    throw new Error("Could not load Playwright. Tried:\n  " + errs.join("\n  "));
}

const PORT = process.env.PORT || "40000";
const DECK_ID = process.env.DECK_ID;
const OUT_DIR = process.env.OUT_DIR || "cfa/ui/reference/app";
const SCALE = parseInt(process.env.SCALE || "2", 10);

if (!DECK_ID) {
    console.error("FATAL: set DECK_ID=<deckId> (from serve_cfa_pages.py READY line)");
    process.exit(2);
}

const SHOTS = [
    {
        name: "readiness",
        url: `http://127.0.0.1:${PORT}/cfa-readiness/${DECK_ID}`,
        file: "verify-readiness-desktop.png",
        width: 800, // ExamReadinessDialog.resize(800, 600)
        height: 600,
    },
    {
        name: "deadline",
        url: `http://127.0.0.1:${PORT}/cfa-deadline/${DECK_ID}`,
        file: "verify-deadline-desktop.png",
        width: 560, // DeadlineDialog.resize(560, 500)
        height: 500,
    },
];

async function run() {
    await mkdir(OUT_DIR, { recursive: true });
    const chromium = await loadChromium();
    const browser = await chromium.launch({ channel: "chrome", headless: true });

    const results = [];
    for (const shot of SHOTS) {
        const context = await browser.newContext({
            viewport: { width: shot.width, height: shot.height },
            deviceScaleFactor: SCALE,
        });
        const page = await context.newPage();
        const consoleErrors = [];
        const failed = [];
        page.on("console", (m) => {
            if (m.type() === "error") consoleErrors.push(m.text());
        });
        page.on("requestfailed", (r) => {
            failed.push(`${r.url()} :: ${r.failure()?.errorText || "failed"}`);
        });
        page.on("response", (r) => {
            if (r.status() >= 400) failed.push(`${r.url()} :: HTTP ${r.status()}`);
        });

        let navError = null;
        try {
            await page.goto(shot.url, { waitUntil: "networkidle", timeout: 60000 });
        } catch (e) {
            navError = e.message || String(e);
        }
        // Fonts + hydration settle.
        await page.evaluate(() => document.fonts && document.fonts.ready).catch(() => {});
        await page.waitForTimeout(1000);

        // Probe: read the rendered fonts + a couple of on-page numbers so the
        // capture can PROVE the bundled fonts + real data are present.
        const probe = await page.evaluate(() => {
            const bodyText = document.body.innerText || "";
            const heading = document.querySelector("h1, h2, [class*='heading']");
            const serifEl = document.querySelector("[class*='hero'], [class*='Hero'], h1, h2");
            const cs = serifEl ? getComputedStyle(serifEl) : null;
            const bodyCs = getComputedStyle(document.body);
            const fonts = document.fonts ? [...document.fonts].map((f) => `${f.family}:${f.status}`) : [];
            return {
                title: document.title,
                headingText: heading ? heading.textContent.trim().slice(0, 80) : null,
                serifFont: cs ? cs.fontFamily : null,
                bodyFont: bodyCs.fontFamily,
                loadedFonts: [...new Set(fonts)],
                textLen: bodyText.length,
                textSnippet: bodyText.replace(/\s+/g, " ").trim().slice(0, 240),
                scrollHeight: document.body.scrollHeight,
            };
        }).catch((e) => ({ error: String(e) }));

        const file = path.join(OUT_DIR, shot.file);
        await page.screenshot({ path: file, fullPage: true });

        results.push({ name: shot.name, url: shot.url, file, navError, consoleErrors, failed, probe });
        console.log(`\n[${shot.name}] -> ${file}`);
        console.log(JSON.stringify({ navError, consoleErrors, failed, probe }, null, 2));
        await context.close();
    }

    await browser.close();
    console.log("\n===CAPTURE_APP_SUMMARY_JSON===");
    console.log(JSON.stringify(results, null, 2));
}

run().catch((err) => {
    console.error("UNCAUGHT:", err);
    process.exitCode = 1;
});
