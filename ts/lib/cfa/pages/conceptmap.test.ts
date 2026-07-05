// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test } from "vitest";

import type { TopicRow } from "../types";
import {
    buildConceptMap,
    CFA_R,
    drillFor,
    EMPTY_FILL,
    fillFor,
    masteryFromTopic,
    masteryLabel,
    masteryPct,
    overallMastery,
    subRadius,
    templatedExplanation,
    topicRadius,
} from "./conceptmap";

const here = dirname(fileURLToPath(import.meta.url));

function topic(over: Partial<TopicRow>): TopicRow {
    return {
        topic: "Equity Investments",
        weight: 0.125,
        reviewedCards: 10,
        gradedReviews: 40,
        recallRange: { low: 0.7, high: 0.86 },
        covered: true,
        ...over,
    };
}

function componentSource(): string {
    return readFileSync(join(here, "CfaConceptMapPage.svelte"), "utf8");
}

// The 10 official Level II areas (weights are single points inside the bands).
function tenTopics(): TopicRow[] {
    const names: [string, number][] = [
        ["Ethics & Professional Standards", 0.125],
        ["Quantitative Methods", 0.075],
        ["Economics", 0.075],
        ["Financial Reporting & Analysis", 0.125],
        ["Corporate Issuers", 0.075],
        ["Equity Investments", 0.125],
        ["Fixed Income", 0.125],
        ["Derivatives", 0.075],
        ["Alternative Investments", 0.075],
        ["Portfolio Management", 0.125],
    ];
    return names.map(([n, w]) => topic({ topic: n, weight: w, recallRange: { low: 0.5, high: 0.6 } }));
}

// --- SIZE ∝ exam weight ------------------------------------------------------

test("topicRadius: node size grows monotonically with exam weight", () => {
    expect(topicRadius(12.5)).toBeGreaterThan(topicRadius(7.5));
    expect(subRadius(12.5)).toBeGreaterThan(subRadius(7.5));
    // A heavy (12.5%) section is meaningfully bigger than a light (7.5%) one.
    expect(topicRadius(12.5) - topicRadius(7.5)).toBeCloseTo(5 * 1.55, 5);
});

// --- FILL: light-gray → turquoise, abstain stays gray ------------------------

test("fillFor: 0% is the empty gray end, null (abstain) is also empty gray", () => {
    // 0% computes to the same colour EMPTY_FILL (#E9EDF1) names.
    expect(fillFor(0)).toBe("rgb(233, 237, 241)");
    expect(fillFor(null)).toBe(EMPTY_FILL);
});

test("fillFor: 100% is full turquoise", () => {
    expect(fillFor(1)).toBe("rgb(20, 184, 177)"); // #14B8B1
});

test("fillFor: 50% is the visual midpoint of the ramp", () => {
    // Halfway between #E9EDF1 and #14B8B1 on each channel.
    expect(fillFor(0.5)).toBe(fillFor(0.5)); // deterministic
    expect(fillFor(0.5)).toBe("rgb(127, 211, 209)");
});

test("fillFor: clamps out-of-range mastery", () => {
    expect(fillFor(2)).toBe(fillFor(1));
    expect(fillFor(-1)).toBe(fillFor(0));
});

// --- mastery + the honest give-up (abstain) rule -----------------------------

test("masteryFromTopic: uses the recall-range midpoint", () => {
    expect(masteryFromTopic(topic({ recallRange: { low: 0.4, high: 0.6 } }))).toBeCloseTo(0.5, 6);
});

test("masteryFromTopic: abstains (null) when there is no recall data", () => {
    expect(masteryFromTopic(topic({ recallRange: null }))).toBeNull();
});

test("masteryFromTopic: abstains (null) when the topic is not covered", () => {
    expect(masteryFromTopic(topic({ covered: false }))).toBeNull();
});

test("overallMastery: weight-adjusted roll-up, heavier sections dominate", () => {
    const rows = [
        topic({ topic: "Fixed Income", weight: 0.125, recallRange: { low: 0.2, high: 0.2 } }),
        topic({ topic: "Derivatives", weight: 0.075, recallRange: { low: 0.9, high: 0.9 } }),
    ];
    const m = overallMastery(rows)!;
    const expected = (0.2 * 0.125 + 0.9 * 0.075) / (0.125 + 0.075);
    expect(m).toBeCloseTo(expected, 6);
    // The heavy low section pulls the roll-up below the naive mean of 0.55.
    expect(m).toBeLessThan(0.55);
});

test("overallMastery: abstains (null) when NO topic has data yet", () => {
    expect(overallMastery([topic({ recallRange: null }), topic({ recallRange: null })])).toBeNull();
    expect(overallMastery([])).toBeNull();
});

test("masteryPct + masteryLabel: honest 'no data yet' for an abstaining node", () => {
    expect(masteryPct(null)).toBeNull();
    expect(masteryLabel(null)).toBe("no data yet");
    expect(masteryLabel(0.8)).toBe("exam-ready");
    expect(masteryLabel(0.5)).toBe("getting there");
    expect(masteryLabel(0.2)).toBe("needs work");
});

// --- buildConceptMap: hierarchy + geometry -----------------------------------

test("buildConceptMap: one centre + one node per topic + two subs per topic", () => {
    const map = buildConceptMap(tenTopics());
    const centers = map.nodes.filter((n) => n.kind === "cfa");
    const topicNodes = map.nodes.filter((n) => n.kind === "topic");
    const subNodes = map.nodes.filter((n) => n.kind === "sub");
    expect(centers).toHaveLength(1);
    expect(topicNodes).toHaveLength(10);
    expect(subNodes).toHaveLength(20);
    // Centre is drawn last so it paints on top.
    expect(map.nodes[map.nodes.length - 1].kind).toBe("cfa");
});

test("buildConceptMap: centre CFA is the biggest node; subs are the smallest", () => {
    const map = buildConceptMap(tenTopics());
    const maxTopicR = Math.max(...map.nodes.filter((n) => n.kind === "topic").map((n) => n.r));
    const maxSubR = Math.max(...map.nodes.filter((n) => n.kind === "sub").map((n) => n.r));
    expect(map.center.r).toBe(CFA_R);
    expect(map.center.r).toBeGreaterThan(maxTopicR);
    expect(maxTopicR).toBeGreaterThan(maxSubR);
});

test("buildConceptMap: heavier exam section renders a bigger disc than a lighter one", () => {
    const map = buildConceptMap(tenTopics());
    const fra = map.nodes.find((n) => n.name === "Financial Reporting & Analysis")!; // 12.5%
    const econ = map.nodes.find((n) => n.name === "Economics")!; // 7.5%
    expect(fra.r).toBeGreaterThan(econ.r);
});

test("buildConceptMap: an abstaining topic node stays empty-gray (give-up rule)", () => {
    const rows = tenTopics();
    rows[0] = topic({ topic: "Ethics & Professional Standards", weight: 0.125, recallRange: null });
    const map = buildConceptMap(rows);
    const ethics = map.nodes.find((n) => n.name === "Ethics & Professional Standards")!;
    expect(ethics.mastery).toBeNull();
    expect(ethics.pct).toBeNull();
    expect(ethics.fill).toBe(EMPTY_FILL);
});

test("buildConceptMap: subsections inherit the section estimate and are flagged", () => {
    const map = buildConceptMap([topic({ topic: "Equity Investments", weight: 0.125, recallRange: { low: 0.7, high: 0.8 } })]);
    const subs = map.nodes.filter((n) => n.kind === "sub");
    expect(subs.length).toBe(2);
    for (const s of subs) {
        expect(s.inherited).toBe(true);
        expect(s.parent).toBe("Equity Investments");
        expect(s.mastery).toBeCloseTo(0.75, 6);
    }
});

test("buildConceptMap: layout is deterministic (stable mental map)", () => {
    const a = buildConceptMap(tenTopics());
    const b = buildConceptMap(tenTopics());
    expect(a.nodes.map((n) => [n.id, n.x, n.y, n.r])).toStrictEqual(
        b.nodes.map((n) => [n.id, n.x, n.y, n.r]),
    );
});

test("buildConceptMap: an unknown topic is still placed without throwing", () => {
    const map = buildConceptMap([topic({ topic: "Some Future Topic", weight: 0.1, recallRange: { low: 0.5, high: 0.5 } })]);
    const node = map.nodes.find((n) => n.name === "Some Future Topic")!;
    expect(Number.isFinite(node.x)).toBe(true);
    expect(Number.isFinite(node.y)).toBe(true);
});

// --- templated explanations: the AI-OFF fallback is always complete ----------

test("templatedExplanation: an abstaining node explains the give-up rule, no fake %", () => {
    const map = buildConceptMap([topic({ recallRange: null })]);
    const t = map.nodes.find((n) => n.kind === "topic")!;
    const text = templatedExplanation(t);
    expect(text).toMatch(/gray/i);
    expect(text).not.toMatch(/\d+%/); // never invents a percentage for no-data
});

test("templatedExplanation: a scored node cites its percent and a next step", () => {
    const map = buildConceptMap([topic({ topic: "Derivatives", weight: 0.075, recallRange: { low: 0.2, high: 0.26 } })]);
    const t = map.nodes.find((n) => n.kind === "topic")!;
    const text = templatedExplanation(t);
    expect(text).toMatch(/23%/); // midpoint of 20–26
    expect(text).toMatch(/Derivatives/);
});

test("templatedExplanation: the centre explains the weight-adjusted roll-up", () => {
    const map = buildConceptMap(tenTopics());
    expect(templatedExplanation(map.center)).toMatch(/overall CFA readiness/i);
});

test("drillFor: centre suggests the dimmest heavy sections; topics get a drill", () => {
    const map = buildConceptMap([topic({ topic: "Fixed Income", weight: 0.125 })]);
    expect(drillFor(map.center)).toMatch(/dimmest heavy sections/i);
    const t = map.nodes.find((n) => n.kind === "topic")!;
    expect(drillFor(t)).toMatch(/Fixed Income near-miss drill/);
});

// --- Phase B regression guard (D-P4-1) ----------------------------------
// The side-panel mastery gauge must NOT fake a 0% fill for an abstaining
// node (pct === null) — that conflates "no evidence yet" with a genuine 0%
// score and breaks the give-up rule. Lock the fix in the Svelte source so a
// revert to `width: {active.pct ?? 0}%` is caught.
test("D-P4-1: panel gauge distinguishes abstain from a genuine 0%", () => {
    const src = componentSource();
    // The abstain-conflating fallback must be gone…
    expect(src).not.toContain("active.pct ?? 0}%");
    // …the fill is only drawn when there IS a measured pct…
    expect(src).toMatch(/#if active\.pct !== null/);
    // …and the abstaining track gets its own honest treatment.
    expect(src).toMatch(/is-nodata=\{active\.pct === null\}/);
    expect(src).toMatch(/&\.is-nodata\s*\{/);
});

// --- Phase B regression guard (D-P4-3) ----------------------------------
// The desktop map must carry the same on-node HOVER TOOLTIP the approved spec
// and the mobile asset have: hovering a node shows its name + "% mastered"
// right at the node (the only name cue for the unlabelled subsection nodes),
// honouring the give-up rule ("no data yet"). Lock it in the source so the
// tooltip can't silently regress back to panel-only.
test("D-P4-3: hover tooltip renders name + % at the node (spec parity)", () => {
    const src = componentSource();
    // The tooltip is driven by hover/focus (hotId), never by a pinned select…
    expect(src).toMatch(/tipNode = hotId !== null/);
    // …it emits both the name and a "% mastered"/"no data yet" line…
    expect(src).toContain("cfa-tip__name");
    expect(src).toContain("cfa-tip__pct");
    expect(src).toContain("% mastered");
    expect(src).toContain("no data yet");
    // …and the tooltip group is aria-hidden (the node aria-label already speaks).
    expect(src).toMatch(/class="cfa-tip"[\s\S]*?aria-hidden="true"/);
});

// --- Phase B regression guard (D-P4-4) ----------------------------------
// The map SVG must expose its focusable node buttons to screen readers. The
// desktop made every node a focusable role="button" (tabindex=0), so the SVG
// container must NOT be role="img" (which flattens the SVG to one image and
// prunes the a11y subtree, orphaning those focusable buttons — WCAG 4.1.2 /
// 1.3.1). It must be role="group" so the map keeps its accessible name AND the
// interactive nodes stay reachable. Lock it in the source.
test("D-P4-4: map SVG is a named group, not an a11y-pruning role=img", () => {
    const src = componentSource();
    // The <svg ...> attributes (up to the first '>') carry role="group",
    // never role="img", while keeping the accessible name.
    const svgOpen = src.slice(src.indexOf("<svg"), src.indexOf(">", src.indexOf("<svg")) + 1);
    expect(svgOpen).toContain('role="group"');
    expect(svgOpen).not.toContain('role="img"');
    expect(svgOpen).toContain('aria-label="Interactive CFA concept mastery map"');
    // The nodes are still focusable buttons (the reason role=img is wrong here).
    expect(src).toMatch(/role="button"\s*\n\s*tabindex="0"/);
});

// --- Phase B regression guard (D-P4-5) ----------------------------------
// Clicking a node pins its explanation, but the user must always be able to get
// BACK to the calm overview — no dead-end where a pinned node is stuck open with
// no exit (Nielsen #3, user control & freedom). Lock in the toggle-off click,
// the Escape-to-unpin key handling (both on-node and window-level), and the
// discoverability hint so the exits can't silently regress.
test("D-P4-5: a pinned node can always be unpinned (toggle + Escape)", () => {
    const src = componentSource();
    // Clicking the same pinned node toggles the selection off (not a one-way set).
    expect(src).toMatch(/selId = selId === n\.id \? null : n\.id/);
    // Escape clears the pin from anywhere via a window keydown listener…
    expect(src).toContain("svelte:window on:keydown={onWindowKey}");
    expect(src).toMatch(/function onWindowKey[\s\S]*?e\.key === "Escape"[\s\S]*?selId = null/);
    // …and also when a node itself has focus (the on-node key handler).
    expect(src).toMatch(/e\.key === "Escape" && selId !== null/);
    // The exit is discoverable in the lede copy.
    expect(src).toContain("to unpin");
});

test("frozen liquid-glass surface keeps the key production selectors", () => {
    const src = componentSource();

    expect(src).toContain("Exact build target · liquid glass · same on phone &amp; desktop");
    expect(src).toContain('class="cfa-map__appbar"');
    expect(src).toContain('class="cfa-map__hero"');
    expect(src).toContain('class="cfa-map__stage"');
    expect(src).toContain('class="cfa-map__mapbox"');
    expect(src).toContain('class="cfa-map__panel"');
    expect(src).toContain('class="cfa-map__section-card"');
    expect(src).toContain("pearl");
    expect(src).toContain("liquid glass");
});

test("batched explanation bridge fires once on mount and never per node tap", () => {
    const src = componentSource();

    expect(src).toMatch(/onMount\(\(\) => \{[\s\S]*?bridgeCommand<string>\(\s*"cfaExplainMap:"/);
    expect(src.match(/cfaExplainMap:/g)).toHaveLength(1);
    expect(src).toMatch(/on:click=\{\(\) => onSelect\(n\)\}/);
    expect(src).not.toMatch(/on:click=\{\(\) => bridgeCommand<string>\(\s*"cfaExplainMap:/);
});

test("AI-off fallback copy and priority drill routing remain available", () => {
    const src = componentSource();

    expect(src).toContain("AI is off — these explanations are the deterministic templated fallback");
    expect(src).toContain('on:click={() => go("cfa:priority")}');
    expect(src).toContain("{drillFor(active)}");
});
