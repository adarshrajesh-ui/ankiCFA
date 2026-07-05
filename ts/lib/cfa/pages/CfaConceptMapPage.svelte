<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

CfaConceptMapPage — the CFA Concept Map tab: a radial "mastery map" built from
the approved interactive spec (.lavish/concept-map-spec.html). CFA sits at the
centre (biggest), the 10 test sections orbit it (SIZE ∝ exam weight), each
section's subsections beyond. Node FILL goes light-gray → turquoise by mastery;
a node with no evidence yet stays gray (the honest give-up rule).

Thin by design: all geometry, fill, the abstain rule and the (AI-off) templated
explanations come from the pure `./conceptmap` engine; this component only draws
what it returns and wires hover (name + %) / click (pin the plain-English why).
The batched-AI wording, when AI is on, warms these same templated strings.
-->
<script lang="ts">
    import { onMount } from "svelte";

    import { bridgeCommand, bridgeCommandsAvailable } from "@tslib/bridgecommand";

    import { Eyebrow, PageHeading } from "$lib/cfa";
    import type { CfaHomePayload } from "$lib/cfa";

    import {
        buildConceptMap,
        type ConceptNode,
        drillFor,
        EMPTY_FILL,
        masteryLabel,
        templatedExplanation,
        TURQ_FILL,
        VIEW_H,
        VIEW_W,
    } from "./conceptmap";

    /** The CFA payload (carries the per-topic rows the map is built from). */
    export let data: CfaHomePayload;

    $: map = buildConceptMap(data.topics);

    let hotId: string | null = null;
    let selId: string | null = null;

    // --- batched AI explanation (one call on load) ---------------------------
    // The map draws instantly from the templated (deterministic) explanations;
    // when AI is on we ALSO fire ONE batched call for casual per-node wording and
    // merge whatever comes back over the templates, honestly flagging provenance.
    type AiResp = {
        ok: boolean;
        aiOn: boolean;
        explanations: Record<string, string>;
        error: string | null;
    };
    let aiExpl: Record<string, string> = {};
    // off = AI toggled off · loading = batched call in flight · ai = at least one
    // node came back · failed = call ran but yielded nothing usable.
    let aiStatus: "off" | "loading" | "ai" | "failed" = data.aiEnabled ? "loading" : "off";

    onMount(() => {
        if (!data.aiEnabled || !bridgeCommandsAvailable()) {
            aiStatus = data.aiEnabled ? "failed" : "off";
            return;
        }
        const nodes = map.nodes.map((n) => ({
            id: n.id,
            full: n.full,
            kind: n.kind,
            pct: n.pct,
            band: n.band,
            parent: n.parent,
        }));
        bridgeCommand<string>(
            "cfaExplainMap:" + JSON.stringify({ nodes }),
            (raw) => {
                try {
                    const resp = JSON.parse(raw) as AiResp;
                    if (!resp.aiOn) {
                        aiStatus = "off";
                        return;
                    }
                    aiExpl = resp.explanations ?? {};
                    aiStatus = resp.ok && Object.keys(aiExpl).length > 0
                        ? "ai"
                        : "failed";
                } catch {
                    aiStatus = "failed";
                }
            },
        );
    });

    // The node currently driving the side panel: the pinned selection wins,
    // otherwise the hovered node, otherwise the centre (a calm default).
    $: activeId = selId ?? hotId ?? map.center.id;
    $: active = map.nodes.find((n) => n.id === activeId) ?? map.center;

    // On-node hover tooltip (name + % mastered), matching the approved spec's
    // `showTip` and the mobile asset — so hovering a node (especially an
    // UNLABELLED subsection) shows its name + fill RIGHT THERE, not only in the
    // far-away side panel. Driven by hover/focus (hotId), never by a pinned
    // selection, exactly like the spec. Honours the give-up rule ("no data
    // yet"). aria-hidden: the node's own aria-label already announces this.
    interface TipGeom {
        name: string;
        pct: string;
        x: number;
        nameY: number;
        pctY: number;
        bgX: number;
        bgY: number;
        w: number;
    }
    function computeTip(n: ConceptNode): TipGeom {
        // Prefer above the disc; drop below if it would clip the top edge.
        const above = n.y - n.r - 42 > 6;
        const ty = above ? n.y - n.r - 8 : n.y + n.r + 42;
        const w = Math.max(n.name.length * 8.6, 96) + 26;
        return {
            name: n.name,
            pct: n.pct === null ? "no data yet" : `${n.pct}% mastered`,
            x: n.x,
            nameY: ty - 16,
            pctY: ty + 7,
            bgX: n.x - w / 2,
            bgY: ty - 35,
            w,
        };
    }
    $: tipNode = hotId !== null ? map.nodes.find((n) => n.id === hotId) ?? null : null;
    $: tip = tipNode ? computeTip(tipNode) : null;

    function pctText(n: ConceptNode): string {
        return n.pct === null ? "No data yet" : `${n.pct}% mastered`;
    }
    function eyebrowFor(n: ConceptNode): string {
        if (selId === n.id) {
            return "Explanation";
        }
        if (n.kind === "cfa") {
            return "Overall";
        }
        if (n.kind === "sub") {
            return `Subsection · ${n.parent}`;
        }
        return "Test section";
    }
    function metaFor(n: ConceptNode): string {
        if (n.kind === "cfa") {
            return "Weight-adjusted across all 10 sections";
        }
        if (n.kind === "sub") {
            return `Subsection of ${n.parent} · reflects the section estimate`;
        }
        return n.band ? `Exam weight ${n.band} of your grade` : "Test section";
    }

    function labelAnchor(n: ConceptNode): "start" | "end" | "middle" {
        const cx = Math.cos(n.labelAngle);
        return cx > 0.25 ? "start" : cx < -0.25 ? "end" : "middle";
    }
    function labelX(n: ConceptNode): number {
        return n.x + Math.cos(n.labelAngle) * (n.r + 13);
    }
    function labelY(n: ConceptNode): number {
        return n.y + Math.sin(n.labelAngle) * (n.r + 13) + 4;
    }

    function onEnter(n: ConceptNode): void {
        hotId = n.id;
    }
    function onLeave(): void {
        hotId = null;
    }
    // Clicking a node pins its explanation; clicking the SAME pinned node again
    // UNPINS it (toggle) so there is always a way back to the calm hover/centre
    // default — no dead-end where one node's explanation is stuck open with no
    // exit (Nielsen #3, user control & freedom).
    function onSelect(n: ConceptNode): void {
        selId = selId === n.id ? null : n.id;
    }
    function onKey(e: KeyboardEvent, n: ConceptNode): void {
        if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onSelect(n);
        } else if (e.key === "Escape" && selId !== null) {
            e.preventDefault();
            selId = null;
        }
    }
    // Escape unpins from anywhere (the keyboard "emergency exit"), even if focus
    // has moved off the pinned node — so a keyboard user is never trapped.
    function onWindowKey(e: KeyboardEvent): void {
        if (e.key === "Escape" && selId !== null) {
            selId = null;
        }
    }

    // The explanation shown for the active node: the batched-AI wording when it
    // came back for THIS node, otherwise the deterministic templated fallback.
    $: activeExpl = aiExpl[active.id] ?? templatedExplanation(active);
    $: activeIsAi = aiExpl[active.id] !== undefined;

    // AI provenance line — always honest about what's actually on screen:
    // an explicit AI-off / AI-failed / AI-generated state, never a vague promise.
    $: aiTag =
        aiStatus === "off"
            ? "AI is off — these explanations are the deterministic templated fallback, built from your performance data."
            : aiStatus === "loading"
              ? "Generating plain-English explanations with AI (one batched call)…"
              : aiStatus === "failed"
                ? "AI explanation failed — showing the deterministic templated fallback, built from your performance data."
                : activeIsAi
                  ? "AI-generated from your performance data, in one batched call when the tab opened."
                  : "AI is on, but this node fell back to its deterministic templated explanation.";
</script>

<svelte:window on:keydown={onWindowKey} />

<div class="cfa-app cfa-map">
    <div class="cfa-map__inner">
        <PageHeading
            eyebrow="ankiCFA · Level II"
            title="Concept Map"
            eyebrowTone="green"
        />
        <p class="cfa-map__lede">
            One node per CFA concept in an organic hierarchy: <b>CFA</b> at the
            centre, the <b>10 test sections</b> orbiting it, each section's
            <b>subsections</b> beyond. Node <b>size = exam weight</b>; node
            <b>fill = your mastery</b>, light gray → turquoise. Hover for a
            node's name and fill; click to pin a plain-English why (click it
            again or press <kbd>Esc</kbd> to unpin).
        </p>

        <div class="cfa-map__stage">
            <div class="cfa-map__mapbox">
                <!-- role="group", NOT "img": every node below is a focusable
                role="button" (tabindex=0). role="img" would flatten the SVG to a
                single presentational image and PRUNE the accessibility subtree,
                leaving those focusable node buttons unreachable by screen
                readers (focusable-but-not-in-a11y-tree — WCAG 4.1.2 / 1.3.1).
                "group" gives the map its accessible name AND exposes the
                interactive nodes. (The approved spec/mobile use "img" because
                their nodes are NOT focusable; only the desktop made them so.) -->
                <svg
                    viewBox="0 0 {VIEW_W} {VIEW_H}"
                    role="group"
                    aria-label="Interactive CFA concept mastery map"
                >
                    <defs>
                        <linearGradient id="cfa-turqfill" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0" stop-color="#31CFC7" />
                            <stop offset="1" stop-color="#0E9C97" />
                        </linearGradient>
                        <radialGradient id="cfa-centerglow" cx="50%" cy="50%" r="50%">
                            <stop offset="0" stop-color={TURQ_FILL} stop-opacity="0.14" />
                            <stop offset="1" stop-color={TURQ_FILL} stop-opacity="0" />
                        </radialGradient>
                        {#each map.nodes as n (n.id)}
                            <clipPath id="cfa-clip-{n.id}">
                                <circle cx={n.x} cy={n.y} r={n.r} />
                            </clipPath>
                        {/each}
                    </defs>

                    <circle cx={map.center.x} cy={map.center.y} r="170" fill="url(#cfa-centerglow)" />

                    <g fill="none" stroke-linecap="round">
                        {#each map.edges as e}
                            <line
                                x1={e.x1}
                                y1={e.y1}
                                x2={e.x2}
                                y2={e.y2}
                                stroke="#D3DBE1"
                                stroke-width={e.width}
                            />
                        {/each}
                    </g>

                    {#each map.nodes as n (n.id)}
                        {@const on = hotId === n.id || selId === n.id}
                        <g
                            class="cfa-node"
                            class:on
                            role="button"
                            tabindex="0"
                            aria-label="{n.full}: {pctText(n)}"
                            on:mouseenter={() => onEnter(n)}
                            on:mouseleave={onLeave}
                            on:focus={() => onEnter(n)}
                            on:blur={onLeave}
                            on:click={() => onSelect(n)}
                            on:keydown={(e) => onKey(e, n)}
                        >
                            <!-- rest disc: one colour on the mastery ramp -->
                            <circle
                                class="cfa-node__rest"
                                cx={n.x}
                                cy={n.y}
                                r={n.r}
                                fill={n.fill}
                                stroke={n.kind === "cfa" ? "#BFE4E1" : "#D7DEE4"}
                                stroke-width={n.kind === "cfa" ? 2 : 1}
                            />
                            <!-- precise fill gauge, revealed on hover/select -->
                            {#if on && n.pct !== null}
                                <g clip-path="url(#cfa-clip-{n.id})">
                                    <rect x={n.x - n.r} y={n.y - n.r} width={2 * n.r} height={2 * n.r} fill={EMPTY_FILL} />
                                    <rect
                                        x={n.x - n.r}
                                        y={n.y + n.r - 2 * n.r * (n.mastery ?? 0)}
                                        width={2 * n.r}
                                        height={2 * n.r * (n.mastery ?? 0)}
                                        fill="url(#cfa-turqfill)"
                                    />
                                </g>
                                <circle class="cfa-node__ring" cx={n.x} cy={n.y} r={n.r + 3} fill="none" stroke="#0E9C97" stroke-width="3" />
                            {/if}

                            {#if n.kind === "cfa"}
                                <text class="cfa-node__clabel" x={n.x} y={n.y + 7} text-anchor="middle" font-size="21">CFA</text>
                            {:else if n.persistentLabel}
                                <text
                                    class="cfa-node__tlabel"
                                    x={labelX(n)}
                                    y={labelY(n)}
                                    text-anchor={labelAnchor(n)}
                                >{n.name}</text>
                            {/if}
                        </g>
                    {/each}

                    <!-- Hover tooltip: name + % right at the node (spec parity;
                    the only name cue for the unlabelled subsection nodes). -->
                    {#if tip}
                        <g class="cfa-tip" pointer-events="none" aria-hidden="true">
                            <rect
                                class="cfa-tip__bg"
                                x={tip.bgX}
                                y={tip.bgY}
                                width={tip.w}
                                height="48"
                                rx="8"
                                ry="8"
                            />
                            <text
                                class="cfa-tip__name"
                                x={tip.x}
                                y={tip.nameY}
                                text-anchor="middle">{tip.name}</text>
                            <text
                                class="cfa-tip__pct"
                                x={tip.x}
                                y={tip.pctY}
                                text-anchor="middle">{tip.pct}</text>
                        </g>
                    {/if}
                </svg>

                <div class="cfa-map__legend">
                    <span class="cfa-map__legend-end">0%</span>
                    <div class="cfa-map__legend-bar"></div>
                    <span class="cfa-map__legend-end">100% mastered</span>
                </div>
                <p class="cfa-map__cap">
                    Size = exam weight · fill = your mastery · the layout is fixed
                    so the map stays a memorable mental picture.
                </p>
            </div>

            <aside class="cfa-map__panel">
                <Eyebrow tone="muted">{eyebrowFor(active)}</Eyebrow>
                <h3 class="cfa-map__ptitle">{active.full}</h3>
                <div class="cfa-map__ppct">
                    {pctText(active)}{active.pct !== null ? ` · ${masteryLabel(active.mastery)}` : ""}
                </div>
                <div class="cfa-map__pmeta">{metaFor(active)}</div>
                <!-- Mastery gauge. When the node is abstaining (no evidence
                yet) we do NOT draw a 0%-width fill — that would read as a real
                "you scored zero", conflating no-data with true-0% and breaking
                the give-up rule. Instead the track shows an "awaiting evidence"
                hatch, honestly distinct from both empty-0% and a partial fill. -->
                <div
                    class="cfa-map__gauge"
                    class:is-nodata={active.pct === null}
                    role="progressbar"
                    aria-valuemin="0"
                    aria-valuemax="100"
                    aria-valuenow={active.pct ?? undefined}
                    aria-valuetext={active.pct === null
                        ? "No data yet — awaiting evidence"
                        : `${active.pct}% mastered`}
                >
                    {#if active.pct !== null}
                        <i style="width: {active.pct}%"></i>
                    {/if}
                </div>
                <p class="cfa-map__expl" class:is-placeholder={active.pct === null && selId === null}>
                    {activeExpl}
                </p>
                {#if selId !== null}
                    <div class="cfa-map__drill">
                        <span class="cfa-map__drillchip">{drillFor(active)}</span>
                    </div>
                {/if}
                <div class="cfa-map__aitag">{aiTag}</div>
            </aside>
        </div>
    </div>
</div>

<style lang="scss">
    @use "../tokens" as cfa;

    // The mastery turquoise is a concept-map-specific "progress" semantic
    // (distinct from the orange CTA accent), per the approved spec footer.
    $turq: #14b8b1;
    $turq-deep: #0e9c97;
    $turq-soft: #e4f6f5;
    $empty: #e9edf1;

    .cfa-map {
        box-sizing: border-box;
        width: 100%;
        padding: cfa.space(7) cfa.space(6);
        background: cfa.$cfa-page;
        color: cfa.$cfa-ink;
        font-family: cfa.$cfa-font-body;
        font-size: cfa.$cfa-fs-body;
        font-weight: cfa.$cfa-weight-regular;
        line-height: cfa.$cfa-lh-body;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;

        :global(*),
        :global(*::before),
        :global(*::after) {
            box-sizing: border-box;
        }

        &__inner {
            display: flex;
            flex-direction: column;
            gap: cfa.space(5);
            max-width: 1160px;
            margin: 0 auto;
        }

        &__lede {
            margin: 0;
            max-width: 770px;
            color: cfa.$cfa-muted;
            font-size: cfa.$cfa-fs-lead;
            line-height: cfa.$cfa-lh-body;

            b {
                color: cfa.$cfa-ink;
                font-weight: cfa.$cfa-weight-semibold;
            }

            // A small "key cap" for the Esc hint — quiet, hairline, body font
            // (the design system bans monospace), matching the chip affordance.
            kbd {
                display: inline-block;
                padding: 0 cfa.space(1);
                font-family: inherit;
                font-size: cfa.$cfa-fs-meta;
                font-weight: cfa.$cfa-weight-semibold;
                color: cfa.$cfa-ink;
                background: cfa.$cfa-bg;
                border: 1px solid cfa.$cfa-control-border;
                border-radius: cfa.$cfa-radius-pill;
            }
        }

        // Map + explanation panel side by side; stacks on narrow widths.
        &__stage {
            display: grid;
            grid-template-columns: minmax(0, 1.7fr) minmax(0, 1fr);
            gap: cfa.space(4);
            align-items: stretch;

            @media (max-width: 940px) {
                grid-template-columns: minmax(0, 1fr);
            }
        }

        &__mapbox {
            background: linear-gradient(180deg, #ffffff, #fbfdfd);
            border: 1px solid cfa.$cfa-line;
            border-radius: cfa.$cfa-radius-block;
            padding: cfa.space(1);
            overflow: hidden;

            svg {
                display: block;
                width: 100%;
                height: auto;
                touch-action: manipulation;
            }
        }

        &__legend {
            display: flex;
            align-items: center;
            gap: cfa.space(3);
            padding: cfa.space(2) cfa.space(3) 0;
        }
        &__legend-bar {
            flex: 1;
            height: 12px;
            border-radius: cfa.$cfa-radius-pill;
            background: linear-gradient(90deg, $empty, $turq);
            border: 1px solid cfa.$cfa-line;
        }
        &__legend-end {
            font-size: cfa.$cfa-fs-meta;
            color: cfa.$cfa-faint-ink;
        }
        &__cap {
            margin: cfa.space(1) 0 cfa.space(2);
            padding: 0 cfa.space(3);
            text-align: center;
            font-size: cfa.$cfa-fs-meta;
            color: cfa.$cfa-faint-ink;
        }

        &__panel {
            display: flex;
            flex-direction: column;
            min-width: 0;
            background: cfa.$cfa-bg;
            border: 1px solid cfa.$cfa-line;
            border-radius: cfa.$cfa-radius-block;
            padding: cfa.space(4);
        }
        &__ptitle {
            margin: cfa.space(1) 0 0;
            font-family: cfa.$cfa-font-heading;
            font-size: cfa.$cfa-fs-subtitle;
            font-weight: cfa.$cfa-weight-semibold;
            line-height: cfa.$cfa-lh-heading;
        }
        &__ppct {
            margin-top: cfa.space(1);
            font-size: cfa.$cfa-fs-small;
            font-weight: cfa.$cfa-weight-semibold;
            color: $turq-deep;
        }
        &__pmeta {
            margin-top: 2px;
            font-size: cfa.$cfa-fs-meta;
            color: cfa.$cfa-faint-ink;
        }
        &__gauge {
            height: 10px;
            border-radius: cfa.$cfa-radius-pill;
            background: $empty;
            overflow: hidden;
            margin: cfa.space(3) 0 cfa.space(1);

            > i {
                display: block;
                height: 100%;
                background: linear-gradient(90deg, $turq, $turq-deep);
                transition: width 0.35s ease;
            }

            // Abstaining node: a neutral diagonal hatch reads as "awaiting
            // evidence / not applicable", never as a measured 0% fill.
            &.is-nodata {
                background: repeating-linear-gradient(
                    -45deg,
                    $empty,
                    $empty 4px,
                    cfa.$cfa-bg 4px,
                    cfa.$cfa-bg 8px
                );
                border: 1px solid cfa.$cfa-line;
            }
        }
        &__expl {
            margin: cfa.space(3) 0 0;
            font-size: cfa.$cfa-fs-body;
            line-height: cfa.$cfa-lh-body;
            color: cfa.$cfa-ink;

            &.is-placeholder {
                color: cfa.$cfa-faint-ink;
            }
        }
        &__drill {
            margin-top: cfa.space(3);
        }
        &__drillchip {
            display: inline-block;
            background: $turq-soft;
            color: $turq-deep;
            border-radius: cfa.$cfa-radius-block;
            padding: cfa.space(2) cfa.space(3);
            font-size: cfa.$cfa-fs-small;
            font-weight: cfa.$cfa-weight-semibold;
        }
        &__aitag {
            margin-top: auto;
            padding-top: cfa.space(3);
            border-top: 1px dashed cfa.$cfa-line;
            font-size: cfa.$cfa-fs-meta;
            color: cfa.$cfa-faint-ink;
        }
    }

    // Node interaction: quiet at rest, a turquoise ring + subtle lift on
    // hover/focus/select. The fill gauge itself is drawn conditionally above.
    .cfa-node {
        cursor: pointer;

        &:focus-visible {
            outline: none;
        }
        &:focus-visible .cfa-node__rest {
            stroke: $turq-deep;
            stroke-width: 3;
        }
    }
    .cfa-node__ring {
        opacity: 0;
        animation: cfa-ring-in 0.18s ease forwards;
    }
    @keyframes cfa-ring-in {
        to {
            opacity: 1;
        }
    }
    .cfa-node__tlabel {
        font-family: cfa.$cfa-font-body;
        font-size: 12.5px;
        font-weight: cfa.$cfa-weight-semibold;
        fill: cfa.$cfa-ink;
        paint-order: stroke;
        stroke: #ffffff;
        stroke-width: 3.2px;
        stroke-linejoin: round;
    }
    .cfa-node__clabel {
        font-family: cfa.$cfa-font-heading;
        font-weight: cfa.$cfa-weight-semibold;
        fill: #ffffff;
        letter-spacing: 0.04em;
    }

    // On-node hover tooltip — the navy chip / white name / turquoise % from the
    // approved spec (and mobile). It fades with hover so the map stays calm at
    // rest; the panel remains the durable, pinned detail surface.
    .cfa-tip {
        &__bg {
            fill: #122b46; // CFA navy chrome (matches the spec tooltip)
        }
        &__name {
            fill: #ffffff;
            font-family: cfa.$cfa-font-body;
            font-size: 15px;
            font-weight: cfa.$cfa-weight-semibold;
        }
        &__pct {
            fill: #4ce0d8; // bright mastery turquoise, per the spec
            font-family: cfa.$cfa-font-body;
            font-size: 13px;
            font-weight: 700;
        }
    }
</style>
