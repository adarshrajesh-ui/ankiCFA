// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
// capture_site.mjs
// ---------------------------------------------------------------------------
// Reusable, parameterized reference-capture script for the ankiCFA UI overhaul.
//
// It drives the *system* Google Chrome via Playwright ({ channel: 'chrome' }),
// so NO chromium binary download is required. It captures a full-page
// screenshot plus per-section ELEMENT screenshots of a target site (default:
// https://www.markmeldrum.com/) so that both the DESKTOP and MOBILE capture
// stations can share one code path.
//
// ---------------------------------------------------------------------------
// USAGE
//   node cfa/ui/reference/capture_site.mjs [url] [outDir]
//
// Everything is configurable via env vars (env wins over argv, argv wins over
// defaults):
//   URL      target url             (default https://www.markmeldrum.com/)
//   OUT_DIR  output directory       (default cfa/ui/reference/site/desktop)
//   WIDTH    viewport width  px     (default 1440 desktop / caller sets mobile)
//   HEIGHT   viewport height px     (default 900)
//   SCALE    deviceScaleFactor      (default 2 desktop / 3 mobile)
//   MOBILE   "1"/"true" => mobile   (default false; sets isMobile + hasTouch)
//   HEADLESS "0"/"false" to show    (default headless true)
//
// Examples
//   # Desktop (this station):
//   node cfa/ui/reference/capture_site.mjs
//   # Mobile (sister station), e.g. iPhone 12-ish:
//   MOBILE=1 WIDTH=390 HEIGHT=844 SCALE=3 \
//     OUT_DIR=cfa/ui/reference/site/mobile \
//     node cfa/ui/reference/capture_site.mjs
// ---------------------------------------------------------------------------

import { mkdir } from "node:fs/promises";
import path from "node:path";

// Load Playwright's chromium without requiring a specific install location.
// Tries, in order: PW_MODULE (an absolute entry path or specifier), then the
// "playwright" and "playwright-core" bare specifiers. Using { channel: 'chrome' }
// at launch means NO chromium binary download is ever required.
async function loadChromium() {
    const candidates = [process.env.PW_MODULE, "playwright", "playwright-core"].filter(Boolean);
    const errs = [];
    for (const c of candidates) {
        try {
            const mod = await import(c);
            if (mod.chromium) { return mod.chromium; }
            if (mod.default && mod.default.chromium) { return mod.default.chromium; }
        } catch (e) {
            errs.push(`${c}: ${e.message || e}`);
        }
    }
    throw new Error(
        "Could not load Playwright. Set PW_MODULE to an installed entry, or run "
            + "`npm i playwright-core`. Tried:\n  " + errs.join("\n  "),
    );
}

// ----------------------------- configuration -------------------------------
const argvUrl = process.argv[2];
const argvOut = process.argv[3];

const URL = process.env.URL || argvUrl || "https://www.markmeldrum.com/";
const MOBILE = /^(1|true|yes)$/i.test(process.env.MOBILE || "");
const OUT_DIR = process.env.OUT_DIR
    || argvOut
    || (MOBILE ? "cfa/ui/reference/site/mobile" : "cfa/ui/reference/site/desktop");
const WIDTH = parseInt(process.env.WIDTH || (MOBILE ? "390" : "1440"), 10);
const HEIGHT = parseInt(process.env.HEIGHT || (MOBILE ? "844" : "900"), 10);
const SCALE = parseInt(process.env.SCALE || (MOBILE ? "3" : "2"), 10);
const HEADLESS = !/^(0|false|no)$/i.test(process.env.HEADLESS || "");

// Collected results for the machine-readable summary printed at the end.
const results = [];

// --------------------------- browser-side helpers --------------------------
// Injected once after load. Provides window.__capture(opts) which locates a
// section by landmark text and tags the "nearest sensible container" with a
// data-cap attribute so Node can screenshot it via a locator.
const HELPERS = `
window.__cap = (function () {
  function visible(el) {
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return false;
    const s = getComputedStyle(el);
    return !(s.visibility === 'hidden' || s.display === 'none' || s.opacity === '0');
  }
  // Smallest visible element whose text contains needle => tight wrapper of the label.
  function deepest(needle) {
    const re = new RegExp(needle, 'i');
    let best = null, bestArea = Infinity;
    for (const el of document.querySelectorAll('body *')) {
      if (!visible(el)) continue;
      const t = el.textContent || '';
      if (!re.test(t)) continue;
      const r = el.getBoundingClientRect();
      const area = r.width * r.height;
      if (area <= bestArea) { best = el; bestArea = area; }
    }
    return best;
  }
  function lca(a, b) {
    const anc = new Set();
    for (let x = a; x; x = x.parentElement) anc.add(x);
    for (let y = b; y; y = y.parentElement) if (anc.has(y)) return y;
    return document.body;
  }
  function nearestSection(el) {
    const docH = document.body.scrollHeight;
    for (let x = el; x && x !== document.body; x = x.parentElement) {
      const tag = x.tagName;
      const cls = (typeof x.className === 'string' ? x.className : '');
      const isSection =
        tag === 'SECTION' || tag === 'HEADER' || tag === 'FOOTER' ||
        tag === 'NAV' || tag === 'ARTICLE' ||
        /(^|[-_\\s])section([-_\\s]|\\d|$)/i.test(cls);
      if (isSection) {
        const r = x.getBoundingClientRect();
        if (r.height <= docH * 0.9) return x; // skip page-spanning wrappers
      }
    }
    return null;
  }
  function rectOf(el) {
    const r = el.getBoundingClientRect();
    return { x: Math.round(r.x), y: Math.round(r.y + window.scrollY),
             w: Math.round(r.width), h: Math.round(r.height) };
  }
  function describe(el) {
    const cls = (typeof el.className === 'string' ? el.className : '')
      .trim().split(/\\s+/).filter(Boolean).slice(0, 2).join('.');
    return el.tagName.toLowerCase() + (cls ? '.' + cls : '');
  }
  return function capture(opts) {
    const needles = opts.needles || [];
    const els = needles.map(deepest).filter(Boolean);
    if (els.length === 0) return { found: false };
    let container;
    let approximated = false;
    if (opts.mode === 'lca') {
      container = els.reduce((acc, el) => (acc ? lca(acc, el) : el), null);
    } else {
      container = els[0];
    }
    if (opts.expandSection) {
      const sec = nearestSection(container);
      if (sec) container = sec;
      else approximated = true; // no landmark ancestor; using tight container
    }
    for (let i = 0; i < (opts.climb || 0); i++) {
      if (container.parentElement && container.parentElement !== document.body)
        container = container.parentElement;
    }
    container.setAttribute('data-cap', opts.tag);
    return { found: true, approximated, tag: opts.tag,
             rect: rectOf(container), desc: describe(container) };
  };
})();
`;

// ------------------------------- utilities ---------------------------------
async function dismissConsent(page) {
    const patterns = [
        /accept all/i,
        /accept/i,
        /agree/i,
        /got it/i,
        /i understand/i,
        /allow all/i,
        /ok/i,
        /continue/i,
        /close/i,
    ];
    for (const re of patterns) {
        try {
            const btn = page.getByRole("button", { name: re }).first();
            if (await btn.isVisible({ timeout: 500 })) {
                await btn.click({ timeout: 1500 });
                await page.waitForTimeout(400);
                return true;
            }
        } catch {
            /* keep trying next pattern */
        }
    }
    // Generic text fallback (non-button consent widgets).
    for (const re of [/accept/i, /agree/i, /got it/i]) {
        try {
            const el = page.getByText(re).first();
            if (await el.isVisible({ timeout: 300 })) {
                await el.click({ timeout: 1000 });
                await page.waitForTimeout(300);
                return true;
            }
        } catch {
            /* ignore */
        }
    }
    return false;
}

// Scroll the whole page to trigger lazy images/content, then return to top.
async function autoScroll(page) {
    await page.evaluate(async () => {
        await new Promise((resolve) => {
            let total = 0;
            let guard = 0;
            const step = Math.max(200, Math.floor(window.innerHeight * 0.8));
            const timer = setInterval(() => {
                window.scrollBy(0, step);
                total += step;
                guard += 1;
                const max = document.body.scrollHeight - window.innerHeight;
                if (total >= max || guard > 400) {
                    clearInterval(timer);
                    resolve();
                }
            }, 80);
        });
    });
    await page.waitForTimeout(900);
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(500);
}

// Screenshot a section located by landmark text via the injected helper.
async function shootSection(page, name, opts) {
    const file = path.join(OUT_DIR, `${name}.png`);
    try {
        const info = await page.evaluate((o) => window.__cap(o), opts);
        if (!info || !info.found) {
            results.push({ name, file, status: "MISSING", note: "landmark not found" });
            console.warn(`[skip] ${name}: landmark not found (${JSON.stringify(opts.needles)})`);
            return false;
        }
        const loc = page.locator(`[data-cap="${opts.tag}"]`).first();
        await loc.scrollIntoViewIfNeeded();
        await page.waitForTimeout(250);
        await loc.screenshot({ path: file });
        results.push({
            name,
            file,
            status: info.approximated ? "APPROX" : "FOUND",
            rect: info.rect,
            desc: info.desc,
        });
        console.log(
            `[ok]   ${name}: ${info.approximated ? "APPROX" : "found"} <${info.desc}> `
                + `css=${info.rect.w}x${info.rect.h}`,
        );
        return true;
    } catch (err) {
        results.push({ name, file, status: "ERROR", note: String(err.message || err) });
        console.warn(`[err]  ${name}: ${err.message || err}`);
        return false;
    }
}

// Return the first *visible* element (non-null, non-trivial bounding box) from a
// locator that may match several nodes — skips hidden matches (e.g. the site's
// display:none schedule <table>s) instead of hanging on scrollIntoView.
async function firstVisible(locator) {
    const n = await locator.count();
    for (let i = 0; i < n; i++) {
        const el = locator.nth(i);
        const box = await el.boundingBox().catch(() => null);
        if (box && box.width > 2 && box.height > 2) { return { el, box }; }
    }
    return null;
}

// Temporarily hide position:fixed/sticky nodes (via visibility, so layout does
// NOT shift) while `fn` runs, then restore. Prevents a sticky nav from bleeding
// into element screenshots taller than the viewport (e.g. the pricing table).
async function withFixedHidden(page, fn) {
    await page.evaluate(() => {
        window.__hidden = [];
        for (const el of document.querySelectorAll("body *")) {
            const p = getComputedStyle(el).position;
            if (p === "fixed" || p === "sticky") {
                window.__hidden.push([el, el.style.visibility]);
                el.style.visibility = "hidden";
            }
        }
    });
    try {
        return await fn();
    } finally {
        await page.evaluate(() => {
            for (const [el, v] of window.__hidden || []) { el.style.visibility = v; }
            window.__hidden = [];
        });
    }
}

// Screenshot the first visible node matching a CSS selector (or comma list).
// `approx` marks the shot as a nearest-region approximation for the handoff.
// `hideFixed` neutralizes sticky/fixed overlays for the duration of the shot.
async function shootSelector(page, name, selector, { approx = false, hideFixed = false } = {}) {
    const file = path.join(OUT_DIR, `${name}.png`);
    const hit = await firstVisible(page.locator(selector));
    if (!hit) { return false; }
    try {
        await hit.el.scrollIntoViewIfNeeded({ timeout: 5000 });
        await page.waitForTimeout(250);
        const box = (await hit.el.boundingBox()) || hit.box;
        if (hideFixed) { await withFixedHidden(page, () => hit.el.screenshot({ path: file })); }
        else { await hit.el.screenshot({ path: file }); }
        results.push({
            name,
            file,
            status: approx ? "APPROX" : "FOUND",
            rect: { w: Math.round(box.width), h: Math.round(box.height) },
            via: selector,
        });
        console.log(
            `[ok]   ${name}: ${approx ? "APPROX" : "found"} <${selector}> `
                + `css=${Math.round(box.width)}x${Math.round(box.height)}`,
        );
        return true;
    } catch (err) {
        console.warn(`[err]  ${name}: ${err.message || err}`);
        return false;
    }
}

// Selector-first capture with heuristic (landmark-text) fallback, so the script
// stays reusable across sites even though we know exact classes for this one.
async function capture(page, name, { selectors = [], approx = false, hideFixed = false, preAction, ...heuristic }) {
    if (preAction) {
        try {
            await preAction(page);
        } catch (e) {
            console.warn(`[warn] ${name} preAction: ${e.message || e}`);
        }
    }
    for (const sel of selectors) {
        if (await shootSelector(page, name, sel, { approx, hideFixed })) { return true; }
    }
    if (heuristic.needles) { return shootSection(page, name, { tag: name, ...heuristic }); }
    results.push({ name, file: path.join(OUT_DIR, `${name}.png`), status: "MISSING" });
    console.warn(`[skip] ${name}: no selector matched and no heuristic given`);
    return false;
}

// --------------------------------- main ------------------------------------
async function run() {
    await mkdir(OUT_DIR, { recursive: true });
    console.log(
        `capture_site: url=${URL} out=${OUT_DIR} viewport=${WIDTH}x${HEIGHT} `
            + `scale=${SCALE} mobile=${MOBILE} headless=${HEADLESS}`,
    );

    const chromium = await loadChromium();
    const browser = await chromium.launch({ channel: "chrome", headless: HEADLESS });
    const context = await browser.newContext({
        viewport: { width: WIDTH, height: HEIGHT },
        deviceScaleFactor: SCALE,
        isMobile: MOBILE,
        hasTouch: MOBILE,
    });
    const page = await context.newPage();

    // --- navigate (robust: don't die if networkidle never settles) ---
    try {
        await page.goto(URL, { waitUntil: "domcontentloaded", timeout: 60000 });
    } catch (err) {
        console.error(`FATAL: initial navigation failed: ${err.message || err}`);
        await browser.close();
        process.exitCode = 2;
        return;
    }
    await page.waitForLoadState("networkidle", { timeout: 25000 }).catch(() => {
        console.warn("networkidle not reached within 25s; continuing.");
    });

    // fonts + lazy content settle
    await page.evaluate(() => document.fonts && document.fonts.ready).catch(() => {});
    await page.waitForTimeout(1500);

    await dismissConsent(page);
    await autoScroll(page);
    await page.evaluate(HELPERS);

    // --- full page ---
    const fullFile = path.join(OUT_DIR, "fullpage.png");
    await page.screenshot({ path: fullFile, fullPage: true });
    results.push({ name: "fullpage", file: fullFile, status: "FOUND" });
    console.log(`[ok]   fullpage`);

    // --- nav / brand header ---
    await capture(page, "nav", {
        selectors: ["header.site-header", "header", "nav"],
        needles: ["Mark Meldrum"],
        climb: 2,
        expandSection: true,
    });

    // --- hero: the "Master the CFA Exam with Confidence" carousel slide ---
    // The hero is a slick carousel that auto-rotates and clones slides. Drive it
    // (jQuery + slick are on the page) to the "Master the CFA" slide, pause, then
    // screenshot the carousel container so the intended slide is shown.
    await capture(page, "hero", {
        selectors: [".mm-homepage-carousel", ".mm-homepage-carousel .slick-list"],
        needles: ["Master the CFA.{0,8}Exam with Confidence"],
        expandSection: true,
        preAction: async (pg) => {
            await pg.evaluate(() => {
                const $ = window.jQuery;
                const slider = ".mm-homepage-carousel";
                const slides = [...document.querySelectorAll(`${slider} .slick-slide:not(.slick-cloned)`)];
                const target = slides.find((s) => /Master the CFA/i.test(s.textContent || ""));
                const idx = target ? parseInt(target.getAttribute("data-slick-index") || "0", 10) : 0;
                if ($ && $(slider).length && $(slider).slick) {
                    try {
                        $(slider).slick("slickPause");
                    } catch {}
                    try {
                        $(slider).slick("slickGoTo", idx, true);
                    } catch {}
                }
            });
            await pg.waitForTimeout(1300); // let the slide transition settle
        },
    });

    // --- feature cards: Lecture Videos ... Performance Stats grid ---
    await capture(page, "feature-cards", {
        selectors: [".mm-feature-section-1"],
        needles: [
            "Structured, in-depth lessons taught by", // Lecture Videos card (unique)
            "Visualize your strengths and weaknesses", // Performance Stats card (unique)
        ],
        mode: "lca",
        expandSection: true,
    });

    // --- stats band: 250,000+ / 180+ / Top-rated ---
    await capture(page, "stats-band", {
        selectors: [".mm-stats-section"],
        needles: ["250,000", "Top-rated"],
        mode: "lca",
        expandSection: true,
    });

    // --- table: pricing/schedule table. Real <table>s exist but are hidden on the
    //     homepage, so capture the visible Pricing & Subscriptions package grid. ---
    if (!(await shootSelector(page, "table", "table:visible", { hideFixed: true }))) {
        await capture(page, "table", {
            selectors: [".mm-pricing-table-section"],
            approx: true,
            hideFixed: true,
            needles: ["Pricing & Subscriptions"],
            climb: 1,
            expandSection: true,
        });
    }

    // --- testimonials: "Why choose Meldrum?" ---
    await capture(page, "testimonials", {
        selectors: [".mm-testimonials-section"],
        needles: ["Why choose Meldrum"],
        expandSection: true,
    });

    // --- footer ---
    await capture(page, "footer", {
        selectors: ["footer.bb-footer", "footer"],
        needles: ["powered by the best brands"],
        climb: 1,
        expandSection: true,
    });

    await browser.close();

    // --- machine-readable summary for the orchestrator ---
    console.log("\n===CAPTURE_SUMMARY_JSON===");
    console.log(
        JSON.stringify(
            { url: URL, outDir: OUT_DIR, viewport: { WIDTH, HEIGHT, SCALE }, mobile: MOBILE, results },
            null,
            2,
        ),
    );
}

run().catch((err) => {
    console.error("UNCAUGHT:", err);
    process.exitCode = 1;
});
