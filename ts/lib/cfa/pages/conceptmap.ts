// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

// -----------------------------------------------------------------------------
// Pure engine for the CFA Concept Map — the radial "mastery map" tab.
//
// Matches the approved interactive spec (.lavish/concept-map-spec.html): CFA in
// the centre (biggest), the 10 test sections orbiting it (SIZE ∝ exam weight),
// each section's subsections beyond. Node FILL goes light-gray → turquoise by
// mastery (100% = fully turquoise). The layout is FIXED and deterministic
// (server-precomputable, no randomness) so the map becomes a stable mental map.
//
// No DOM / no Svelte — data → node geometry + fill + templated explanations —
// so the geometry, the honest give-up (abstain) rule, and the AI-off explanation
// fallback are all trivially unit-testable. The Svelte component only draws what
// this module returns; the batched-AI wording (when AI is ON) is layered on top
// of the templated text this file produces, which is ALSO the AI-off fallback.
// -----------------------------------------------------------------------------

import type { TopicRow } from "../types";

// --- viewBox geometry (mirrors the approved spec's 1000×740 stage) -----------
export const VIEW_W = 1000;
export const VIEW_H = 740;
export const CX = 500;
export const CY = 366;
/** Centre CFA node radius. */
export const CFA_R = 60;
/** Empty (0% mastery) fill — the light gray end of the mastery ramp. */
export const EMPTY_FILL = "#E9EDF1";
/** Fully-mastered fill — the turquoise "mastery/progress" semantic (distinct
 * from the orange CTA accent), per the spec footer. */
export const TURQ_FILL = "#14B8B1";

/** SIZE ∝ exam weight. `w` is exam weight as a PERCENT (e.g. 12.5), mirroring
 * the spec's `topicR`/`subR`. Bigger exam weight ⇒ bigger node. */
export function topicRadius(weightPct: number): number {
    return 20 + weightPct * 1.55;
}
export function subRadius(weightPct: number): number {
    return 12 + weightPct * 0.5;
}

// --- fixed, organic layout per canonical topic (keyed by slug) ---------------
// angle (deg) + orbit jitter make the ring organic rather than a rigid wheel,
// but the values are CONSTANT so the map never reshuffles between opens.
interface TopicLayout {
    slug: string;
    /** Angle around the centre, degrees (SVG: 0°=east, grows clockwise). */
    ang: number;
    /** Small orbit-radius jitter so the ring reads organic, not mechanical. */
    r1j: number;
    /** Official CFA Level II exam-weight band, for the tooltip/panel. */
    band: string;
    /** Two subsections; `[name, angleOffsetDeg]`. */
    subs: [string, number][];
}

// Keyed by the canonical slug (cfa/outline/level2_topics.json). Names are
// matched to TopicRow.topic via CANONICAL below so the map is driven by the real
// backend topics, not a hard-coded copy of them.
const TOPIC_LAYOUT: Record<string, TopicLayout> = {
    ethics: { slug: "ethics", ang: 274, r1j: -6, band: "10–15%", subs: [["Standards I–VII", -12], ["GIPS", 12]] },
    quant: { slug: "quant", ang: 306, r1j: 10, band: "5–10%", subs: [["Regression", -11], ["Time-Series", 11]] },
    econ: { slug: "econ", ang: 342, r1j: -4, band: "5–10%", subs: [["Currency", -11], ["Growth", 11]] },
    fra: { slug: "fra", ang: 20, r1j: 8, band: "10–15%", subs: [["Intercorporate", -12], ["Pensions", 12]] },
    corp: { slug: "corp", ang: 58, r1j: -9, band: "5–10%", subs: [["Capital Structure", -11], ["ESG", 11]] },
    equity: { slug: "equity", ang: 96, r1j: 7, band: "10–15%", subs: [["FCFE / FCFF", -12], ["Residual Income", 12]] },
    "fixed-income": { slug: "fixed-income", ang: 140, r1j: -8, band: "10–15%", subs: [["Term Structure", -12], ["Credit", 12]] },
    derivatives: { slug: "derivatives", ang: 176, r1j: 5, band: "5–10%", subs: [["Forwards / Futures", -11], ["Options", 11]] },
    altinv: { slug: "altinv", ang: 212, r1j: 11, band: "5–10%", subs: [["Real Estate", -11], ["Private Equity", 11]] },
    portmgmt: { slug: "portmgmt", ang: 240, r1j: -6, band: "10–15%", subs: [["Active Mgmt", -12], ["Risk", 12]] },
};

// Canonical name → slug (the 10 official Level II areas). The map matches on the
// backend's topic NAME; anything unrecognised is still placed deterministically.
const CANONICAL: Record<string, string> = {
    "Ethics & Professional Standards": "ethics",
    "Quantitative Methods": "quant",
    "Economics": "econ",
    "Financial Reporting & Analysis": "fra",
    "Corporate Issuers": "corp",
    "Equity Investments": "equity",
    "Fixed Income": "fixed-income",
    "Derivatives": "derivatives",
    "Alternative Investments": "altinv",
    "Portfolio Management": "portmgmt",
};
/** Deterministic curriculum order used to place any topic not in TOPIC_LAYOUT. */
const CANONICAL_ORDER = [
    "ethics", "quant", "econ", "fra", "corp",
    "equity", "fixed-income", "derivatives", "altinv", "portmgmt",
];

function rad(deg: number): number {
    return (deg * Math.PI) / 180;
}

/**
 * The exact light-gray → turquoise interpolation from the spec (`mix`): 0 = the
 * empty gray, 1 = full turquoise. A null mastery (abstaining) renders as the
 * empty gray so an unearned node is honestly dim, never faked bright.
 */
export function fillFor(mastery: number | null): string {
    if (mastery === null) {
        return EMPTY_FILL;
    }
    const m = Math.max(0, Math.min(1, mastery));
    const g = [0xe9, 0xed, 0xf1];
    const t = [0x14, 0xb8, 0xb1];
    const c = g.map((gv, i) => Math.round(gv + (t[i] - gv) * m));
    return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
}

/**
 * A topic's mastery for the map: the midpoint of its recall range, clamped to
 * 0..1. Honest give-up (abstain) rule: a topic with no recall data yet — or one
 * not marked covered — returns null so its node stays gray until brightness is
 * actually earned. Mirrors the desktop honest-score model (never fabricate
 * confidence from thin evidence).
 */
export function masteryFromTopic(row: TopicRow): number | null {
    if (!row.covered || row.recallRange === null) {
        return null;
    }
    const mid = (row.recallRange.low + row.recallRange.high) / 2;
    return Math.max(0, Math.min(1, mid));
}

/**
 * The centre CFA node's fill: an exam-WEIGHT-adjusted roll-up of every topic
 * that has data. Heavier sections move the centre more (matches the spec's "the
 * biggest nodes move it most"). Abstains (null) when NO topic has data yet, so
 * the centre is gray on a fresh deck rather than a fake overall score.
 */
export function overallMastery(topics: TopicRow[]): number | null {
    let wsum = 0;
    let msum = 0;
    for (const t of topics) {
        const m = masteryFromTopic(t);
        if (m === null) {
            continue;
        }
        const w = t.weight > 0 ? t.weight : 0.1;
        wsum += w;
        msum += m * w;
    }
    return wsum === 0 ? null : msum / wsum;
}

/** Whole-percent for a mastery, or null when abstaining. */
export function masteryPct(mastery: number | null): number | null {
    return mastery === null ? null : Math.round(mastery * 100);
}

/** Calm one-word readiness label for a node's fill (spec's panel wording). */
export function masteryLabel(mastery: number | null): string {
    if (mastery === null) {
        return "no data yet";
    }
    const pct = mastery * 100;
    if (pct >= 70) {
        return "exam-ready";
    }
    if (pct >= 45) {
        return "getting there";
    }
    return "needs work";
}

export type NodeKind = "cfa" | "topic" | "sub";

/** One drawable node the Svelte layer renders verbatim. */
export interface ConceptNode {
    id: string;
    kind: NodeKind;
    /** Short label shown on/near the node. */
    name: string;
    /** Full topic name (for the tooltip + panel title). */
    full: string;
    /** Parent section's full name for a subsection, else null. */
    parent: string | null;
    x: number;
    y: number;
    r: number;
    /** 0..1, or null when abstaining (renders gray). */
    mastery: number | null;
    /** round(mastery*100), or null. */
    pct: number | null;
    /** Rest fill colour for the node (already resolved via `fillFor`). */
    fill: string;
    /** Official exam-weight band text (topics only). */
    band: string | null;
    /** Radians angle for placing a topic's persistent label outside its disc. */
    labelAngle: number;
    /** Whether the node carries an always-on label (centre + topics). */
    persistentLabel: boolean;
    /**
     * True for a subsection whose fill INHERITS the section estimate — the
     * engine tracks recall at the section level, not per subsection yet, so the
     * honest thing is to show the section's mastery, clearly flagged, rather than
     * invent a divergent per-subsection number.
     */
    inherited: boolean;
}

/** A connector line from a parent node to a child node. */
export interface ConceptEdge {
    x1: number;
    y1: number;
    x2: number;
    y2: number;
    width: number;
}

export interface ConceptMap {
    nodes: ConceptNode[];
    edges: ConceptEdge[];
    /** The centre CFA node (also present in `nodes`). */
    center: ConceptNode;
}

/**
 * Build the full, deterministic concept map from the real per-topic rows. Draw
 * order in `nodes` is subsections → topics → centre so the centre renders on top
 * (matches the spec). Any topic missing from the fixed layout is still placed
 * deterministically around the ring by canonical order, so the map never crashes
 * on an unexpected topic set.
 */
export function buildConceptMap(topics: TopicRow[], cfaMastery?: number | null): ConceptMap {
    const edges: ConceptEdge[] = [];
    const topicNodes: ConceptNode[] = [];
    const subNodes: ConceptNode[] = [];

    topics.forEach((row, i) => {
        const slug = CANONICAL[row.topic] ?? CANONICAL_ORDER[i % CANONICAL_ORDER.length];
        const lay = TOPIC_LAYOUT[slug] ?? {
            slug,
            ang: (360 / Math.max(topics.length, 1)) * i,
            r1j: 0,
            band: `${Math.round(row.weight * 100)}%`,
            subs: [] as [string, number][],
        };
        const weightPct = row.weight * 100;
        const a = rad(lay.ang);
        const R1 = 196 + lay.r1j;
        const tx = CX + Math.cos(a) * R1;
        const ty = CY + Math.sin(a) * R1;
        const tr = topicRadius(weightPct);
        const mastery = masteryFromTopic(row);

        edges.push({ x1: CX, y1: CY, x2: tx, y2: ty, width: +(1.1 + weightPct * 0.12).toFixed(2) });

        topicNodes.push({
            id: `topic:${slug}`,
            kind: "topic",
            name: row.topic,
            full: row.topic,
            parent: null,
            x: tx,
            y: ty,
            r: tr,
            mastery,
            pct: masteryPct(mastery),
            fill: fillFor(mastery),
            band: lay.band,
            labelAngle: a,
            persistentLabel: true,
            inherited: false,
        });

        for (const [subName, off] of lay.subs) {
            const sa = rad(lay.ang + off);
            const R2 = 306 + (off < 0 ? -8 : 8);
            const sx = CX + Math.cos(sa) * R2;
            const sy = CY + Math.sin(sa) * R2;
            edges.push({ x1: tx, y1: ty, x2: sx, y2: sy, width: 1.4 });
            subNodes.push({
                id: `sub:${slug}:${subName}`,
                kind: "sub",
                name: subName,
                full: subName,
                parent: row.topic,
                x: sx,
                y: sy,
                r: subRadius(weightPct),
                // Subsections inherit the section estimate (see `inherited`).
                mastery,
                pct: masteryPct(mastery),
                fill: fillFor(mastery),
                band: null,
                labelAngle: sa,
                persistentLabel: false,
                inherited: true,
            });
        }
    });

    const centerM = cfaMastery === undefined ? overallMastery(topics) : cfaMastery;
    const center: ConceptNode = {
        id: "cfa",
        kind: "cfa",
        name: "CFA",
        full: "Overall CFA readiness",
        parent: null,
        x: CX,
        y: CY,
        r: CFA_R,
        mastery: centerM,
        pct: masteryPct(centerM),
        fill: fillFor(centerM),
        band: null,
        labelAngle: 0,
        persistentLabel: true,
        inherited: false,
    };

    return { nodes: [...subNodes, ...topicNodes, center], edges, center };
}

/**
 * The templated, plain-English "why" for a node. This is BOTH the AI-off
 * fallback AND the ~80% templated base the batched AI call warms when AI is on,
 * so the map is always fully explanatory offline (the give-up rule is honoured
 * verbatim here). Deterministic, but written casually — not a rigid one-liner.
 */
export function templatedExplanation(node: ConceptNode): string {
    const { kind, full, pct, mastery, parent } = node;

    if (mastery === null || pct === null) {
        if (kind === "cfa") {
            return "Your overall readiness is still gray — there aren't enough graded "
                + "reviews yet to roll up an honest number. Study a few sections and "
                + "this centre node starts to fill. (The give-up rule: no evidence, no "
                + "fake confidence.)";
        }
        const what = kind === "sub" ? `${full} (under ${parent})` : full;
        return `${what} is gray because there isn't enough evidence yet to score it — `
            + "it stays dim until you've logged enough graded reviews here. Brightness "
            + "is earned, never faked.";
    }

    const recall = pct >= 70 ? "solid" : pct >= 45 ? "decent" : "shaky";

    if (kind === "cfa") {
        return `This is your overall CFA readiness — about ${pct}%. It's the `
            + "weight-adjusted roll-up of every section below, so your biggest, "
            + "dimmest sections move it the most. Filling a heavy gray section lifts "
            + "the centre far more than topping up one that's already turquoise.";
    }
    if (kind === "sub") {
        return `You're at about ${pct}% on ${full} (under ${parent}). This reflects the `
            + `${parent} section estimate — recall there is ${recall}, but it tends to `
            + "bend under exam-style wording. A few targeted near-miss drills fill it "
            + "fastest. (Per-subsection tracking arrives as you log more reviews.)";
    }
    // topic
    return `You're at about ${pct}% on ${full}. Recall is ${recall}, but ${full} still `
        + "slips on reworded vignettes — that's what keeps it from filling. A short set "
        + `of ${full} near-miss drills is the quickest way to more turquoise.`;
}

/** The panel's "next best action" chip text for a node. */
export function drillFor(node: ConceptNode): string {
    if (node.kind === "cfa") {
        return "▶ Study your two dimmest heavy sections first";
    }
    const name = node.kind === "sub" ? node.full : node.full;
    return `▶ Start a ${name} near-miss drill`;
}
