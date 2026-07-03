// capture_mobile.mjs
// Station: MOBILE 390px reference capture of https://www.markmeldrum.com/
// Drives the SYSTEM Google Chrome via Playwright ({ channel: 'chrome' }) so no
// chromium binary download is required. Emulates an iPhone-class mobile device
// (390x844, dSF 3, isMobile, hasTouch, mobile UA), then writes a full-page
// screenshot plus per-section reference crops into ./site/mobile/.
//
// Re-run:  node cfa/ui/reference/capture_mobile.mjs
// (run from the repo root so `playwright` resolves via ./node_modules)
//
// EVIDENCE-ONLY: this script never edits app source. It only reads the live
// public site and writes PNG references. It captures the page as rendered
// (it navigates the hero carousel to the requested slide and pauses autoplay,
// but does not fabricate any content).

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const URL = "https://www.markmeldrum.com/";
const MOBILE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    + "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const outDir = path.join(__dirname, "site", "mobile");
fs.mkdirSync(outDir, { recursive: true });

const errors = [];
const results = [];

function record(name, file, status, selector, note = "") {
    let bytes = 0;
    try {
        bytes = fs.statSync(file).size;
    } catch {
        bytes = 0;
    }
    results.push({ name, file: path.basename(file), status, selector, note, bytes });
    console.log(
        `  [${status.toUpperCase()}] ${path.basename(file)} <- ${selector} (${bytes} bytes) ${
            note ? "// " + note : ""
        }`,
    );
}

// Climb from an anchor's common ancestor up to the widest wrapper still under maxH.
async function containerHandle(texts, maxH) {
    return page.evaluateHandle(
        ({ texts, maxH }) => {
            const norm = (s) => (s || "").replace(/\s+/g, " ").trim();
            const pool = [...document.querySelectorAll("h1,h2,h3,h4,span,div,p,strong,b,a,li")];
            const findFor = (t) =>
                pool.find((e) => norm(e.textContent) === t) || pool.find((e) => norm(e.textContent).startsWith(t));
            const els = texts.map(findFor).filter(Boolean);
            if (!els.length) { return null; }
            let anc = els[0];
            for (let i = 1; i < els.length; i++) {
                while (anc && !anc.contains(els[i])) { anc = anc.parentElement; }
            }
            if (!anc) { return null; }
            let cur = anc;
            while (cur.parentElement) {
                const ph = cur.parentElement.getBoundingClientRect().height;
                if (ph > maxH) { break; }
                cur = cur.parentElement;
            }
            return cur;
        },
        { texts, maxH },
    );
}

async function shotHandle(name, fileName, handle, { selector, status = "exact", note = "", maxH = 3200 }) {
    const file = path.join(outDir, fileName);
    const box = handle ? await handle.boundingBox().catch(() => null) : null;
    if (box && box.width > 40 && box.height > 20 && box.height <= maxH) {
        await handle.scrollIntoViewIfNeeded().catch(() => {});
        await page.waitForTimeout(250);
        await handle.screenshot({ path: file });
        record(name, file, status, selector, `${note} [${Math.round(box.width)}x${Math.round(box.height)}css]`.trim());
        return true;
    }
    return false;
}

async function shotLocator(name, fileName, locator, { selector, status = "exact", note = "" }) {
    const file = path.join(outDir, fileName);
    await locator.scrollIntoViewIfNeeded().catch(() => {});
    await page.waitForTimeout(250);
    const box = await locator.boundingBox().catch(() => null);
    await locator.screenshot({ path: file });
    record(
        name,
        file,
        status,
        selector,
        `${note}${box ? ` [${Math.round(box.width)}x${Math.round(box.height)}css]` : ""}`.trim(),
    );
}

const browser = await chromium.launch({ channel: "chrome", headless: true });
const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 3,
    isMobile: true,
    hasTouch: true,
    userAgent: MOBILE_UA,
});
context.setDefaultTimeout(20000);
const page = await context.newPage();
page.on("pageerror", (e) => errors.push("pageerror: " + e.message));

try {
    console.log(`Navigating (mobile 390x844 dSF3) -> ${URL}`);
    let navMode = "networkidle";
    try {
        await page.goto(URL, { waitUntil: "networkidle", timeout: 30000 });
    } catch (e) {
        navMode = "domcontentloaded+settle";
        errors.push("goto networkidle not reached in 30s: " + String(e.message).split("\n")[0]);
        await page.waitForLoadState("domcontentloaded").catch(() => {});
        await page.waitForLoadState("load").catch(() => {});
    }
    console.log("  navMode:", navMode);

    // fonts + settle
    await page.evaluate(() => (document.fonts ? document.fonts.ready : Promise.resolve())).catch(() => {});
    await page.waitForTimeout(1500);
    await page.waitForSelector("#masthead, h1", { timeout: 15000 }).catch(() => {});

    // Dismiss cookie/consent + promo overlays (best effort; records which fired).
    const dismissers = [
        "#onetrust-accept-btn-handler",
        "#accept-recommended-btn-handler",
        "button:has-text(\"Accept All Cookies\")",
        "button:has-text(\"Accept All\")",
        "button:has-text(\"Accept Cookies\")",
        "button:has-text(\"I Accept\")",
        "button:has-text(\"I Agree\")",
        "button:has-text(\"Got it\")",
        ".pum-close",
        ".popmake-close",
        "button.mfp-close",
        ".mm-modal-close",
        "[aria-label=\"Close\"]",
        ".modal.show button.close",
    ];
    for (const sel of dismissers) {
        try {
            const el = page.locator(sel).first();
            if (await el.isVisible({ timeout: 500 })) {
                await el.click({ timeout: 2000 });
                await page.waitForTimeout(500);
                console.log("  dismissed overlay via", sel);
            }
        } catch {
            /* ignore */
        }
    }

    // Scroll full page to trigger lazy images, then return to top.
    await page.evaluate(async () => {
        await new Promise((resolve) => {
            let total = 0;
            const step = 600;
            const timer = setInterval(() => {
                window.scrollBy(0, step);
                total += step;
                if (total >= document.documentElement.scrollHeight + 1500) {
                    clearInterval(timer);
                    resolve();
                }
            }, 80);
        });
    });
    await page.waitForTimeout(1000);
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(800);

    const headerPos = await page.evaluate(() => {
        const h = document.querySelector("#masthead");
        return h ? getComputedStyle(h).position : "none";
    });
    console.log("  #masthead position:", headerPos);

    // 1) FULL PAGE (natural state, before any carousel manipulation)
    {
        const file = path.join(outDir, "fullpage.png");
        await page.screenshot({ path: file, fullPage: true });
        record("fullpage", file, "exact", "page.screenshot(fullPage)", "entire mobile page");
    }

    // 2) NAV — mobile top bar / brand / side-panel (hamburger) toggle
    await shotLocator("nav", "nav.png", page.locator("#masthead").first(), {
        selector: "#masthead",
        status: "exact",
        note: "mobile top bar: brand + toggle",
    });

    // 3) HERO — navigate slick carousel to the "Master the CFA Exam with Confidence" slide
    {
        const carousel = page.locator(".mm-homepage-carousel").first();
        const wanted = /Master the CFA/i;
        const activeText = async () =>
            page.evaluate(() => {
                const cur = document.querySelector(".mm-homepage-carousel .slick-current");
                return cur ? (cur.innerText || "").replace(/\s+/g, " ").trim() : "";
            });
        // Pause autoplay + jump straight to the target slide via slick API if present.
        await page
            .evaluate(() => {
                try {
                    const $ = window.jQuery || window.$;
                    if ($ && $(".mm-homepage-carousel").slick) {
                        const $c = $(".mm-homepage-carousel");
                        $c.slick("slickPause");
                        let idx = -1;
                        $c.find(".slick-slide:not(.slick-cloned)").each(function(i) {
                            if (/Master the CFA/i.test(this.innerText || "")) { idx = i; }
                        });
                        if (idx >= 0) { $c.slick("slickGoTo", idx); }
                    }
                } catch {
                    /* ignore */
                }
            })
            .catch(() => {});
        await page.waitForTimeout(900);
        let txt = await activeText();
        if (!wanted.test(txt)) {
            const next = page.locator(".mm-homepage-carousel .slick-next").first();
            for (let i = 0; i < 5 && !wanted.test(txt); i++) {
                await next.click({ timeout: 3000 }).catch(() => {});
                await page.waitForTimeout(700);
                txt = await activeText();
            }
        }
        // Re-pause so autoplay can't advance before the screenshot.
        await page
            .evaluate(() => {
                try {
                    const $ = window.jQuery || window.$;
                    if ($ && $(".mm-homepage-carousel").slick) { $(".mm-homepage-carousel").slick("slickPause"); }
                } catch {
                    /* ignore */
                }
            })
            .catch(() => {});
        await carousel.scrollIntoViewIfNeeded().catch(() => {});
        await page.waitForTimeout(300);
        const file = path.join(outDir, "hero.png");
        await carousel.screenshot({ path: file });
        const ok = wanted.test(txt);
        record(
            "hero",
            file,
            ok ? "exact" : "approx",
            ".mm-homepage-carousel",
            ok
                ? `active slide = "${txt.slice(0, 48)}" (autoplay paused)`
                : `could not activate target slide; active = "${txt.slice(0, 48)}"`,
        );
    }

    // 4) STATS BAND — 250,000+ / 180+ / Top-rated strip (div-based; use common ancestor)
    {
        const h = await containerHandle(["250,000+", "180+", "Top-rated"], 900);
        const done = await shotHandle("stats-band", "stats-band.png", h, {
            selector: "container of ['250,000+','180+','Top-rated']",
            status: "exact",
            note: "stats strip (stacks vertically on mobile)",
            maxH: 1200,
        });
        if (!done) {
            // fallback: wider net incl. the "Study smarter" intro heading
            const h2 = await containerHandle(["Study smarter and pass the first time.", "Top-rated"], 1200);
            const ok2 = await shotHandle("stats-band", "stats-band.png", h2, {
                selector: "container of ['Study smarter...','Top-rated']",
                status: "approx",
                note: "approximated: primary stats container was degenerate",
                maxH: 1600,
            });
            if (!ok2) { errors.push("stats-band: no suitable container element found"); }
        }
    }

    // 5) FEATURE CARDS — Lecture Videos / Question Bank / Study Planner / Archive / Performance
    {
        const h = await containerHandle(
            ["Lecture Videos", "Question Bank", "Study Planner", "Archive", "Performance"],
            1700,
        );
        const done = await shotHandle("feature-cards", "feature-cards.png", h, {
            selector: "container of feature card labels",
            status: "exact",
            note: "Lecture Videos / Question Bank / Study Planner / Archive / Performance (mobile stack)",
            maxH: 2000,
        });
        if (!done) {
            const h2 = await containerHandle(["Start preparing for a successful career", "Performance"], 2000);
            const ok2 = await shotHandle("feature-cards", "feature-cards.png", h2, {
                selector: "container of ['Start preparing...','Performance']",
                status: "approx",
                note: "approximated: primary feature grid container was degenerate",
                maxH: 2400,
            });
            if (!ok2) { errors.push("feature-cards: no suitable container element found"); }
        }
    }

    // 6) TABLE — prefer a live/visible <table>; else the visible Pricing region
    {
        const realTable = await page.evaluateHandle(() => {
            const t = [...document.querySelectorAll("table")].find((tb) => {
                const r = tb.getBoundingClientRect();
                const s = getComputedStyle(tb);
                return r.width > 0 && r.height > 0 && s.display !== "none" && s.visibility !== "hidden";
            });
            return t || null;
        });
        const box = await realTable.boundingBox().catch(() => null);
        if (box && box.height > 20) {
            await shotHandle("table", "table.png", realTable, {
                selector: "first visible <table>",
                status: "exact",
                note: "live schedule/pricing table",
                maxH: 3200,
            });
        } else {
            const h = await containerHandle(["Pricing & Subscriptions"], 1500);
            const ok = await shotHandle("table", "table.png", h, {
                selector: "container of 'Pricing & Subscriptions'",
                status: "approx",
                note:
                    "approximated: only <table>s on page are the schedule tables inside hidden .discord-bootcamp-schedules (display:none); captured the visible Pricing & Subscriptions packages region instead",
                maxH: 2200,
            });
            if (!ok) { errors.push("table: no visible table and no pricing container found"); }
        }
    }

    // 7) TESTIMONIALS — "Why choose Meldrum?" + review carousel
    {
        const loc = page.locator(".mm-testimonials-container").first();
        if (await loc.count()) {
            await shotLocator("testimonials", "testimonials.png", loc, {
                selector: ".mm-testimonials-container",
                status: "exact",
                note: "\"Why choose Meldrum?\" heading + testimonial carousel",
            });
        } else {
            const h = await containerHandle(["Why choose Meldrum?"], 1400);
            const ok = await shotHandle("testimonials", "testimonials.png", h, {
                selector: "container of 'Why choose Meldrum?'",
                status: "approx",
                note: "approximated via heading container",
                maxH: 1800,
            });
            if (!ok) { errors.push("testimonials: not found"); }
        }
    }

    // 8) FOOTER
    {
        await shotLocator("footer", "footer.png", page.locator("footer").first(), {
            selector: "footer",
            status: "exact",
            note: "site footer",
        });
    }

    console.log("\n=== SUMMARY ===");
    console.log(JSON.stringify({ url: URL, viewport: "390x844@3x", outDir, headerPos, results, errors }, null, 2));
} catch (e) {
    errors.push("FATAL: " + e.message);
    console.error("FATAL", e);
} finally {
    await browser.close();
}

if (errors.length) {
    console.log("\nNON-FATAL/LOAD ERRORS:");
    for (const e of errors) { console.log("  - " + e); }
}
