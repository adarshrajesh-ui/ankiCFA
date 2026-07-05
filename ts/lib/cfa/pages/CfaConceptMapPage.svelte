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

    const NAV_ITEMS = [
        { label: "Today", cmd: "cfa:home" },
        { label: "Study", cmd: "cfa:priority" },
        { label: "Concept Map", cmd: "cfa:conceptmap", active: true },
        { label: "Readiness", cmd: "cfa:readiness" },
    ];

    const SHORT_TOPIC_LABELS: Record<string, string> = {
        "Ethics & Professional Standards": "Ethics",
        "Quantitative Methods": "Quant",
        "Economics": "Economics",
        "Financial Reporting & Analysis": "FRA",
        "Corporate Issuers": "Corp. Issuers",
        "Equity Investments": "Equity",
        "Fixed Income": "Fixed Income",
        "Derivatives": "Derivatives",
        "Alternative Investments": "Alt. Inv.",
        "Portfolio Management": "Portfolio",
    };

    interface PinchStart {
        distance: number;
        scale: number;
        x: number;
        y: number;
        centerX: number;
        centerY: number;
    }

    $: map = buildConceptMap(data.topics);

    let hotId: string | null = null;
    let selId: string | null = null;
    let mapState = { x: 0, y: 0, scale: 1 };
    let pinchStart: PinchStart | null = null;
    $: mapTransform = `translate(${mapState.x} ${mapState.y}) scale(${mapState.scale})`;

    function go(cmd: string): void {
        bridgeCommand(cmd);
    }

    function clamp(value: number, min: number, max: number): number {
        return Math.max(min, Math.min(max, value));
    }

    function shortLabel(n: ConceptNode): string {
        if (n.kind !== "topic") {
            return n.name;
        }
        return SHORT_TOPIC_LABELS[n.full] ?? n.name;
    }

    function onMapWheel(event: WheelEvent): void {
        event.preventDefault();
        mapState = {
            x: clamp(mapState.x - event.deltaX * 0.25, -120, 120),
            y: clamp(mapState.y - event.deltaY * 0.18, -96, 96),
            scale: clamp(mapState.scale + Math.abs(event.deltaY) * 0.00075, 1, 1.32),
        };
    }

    function onMapLeave(): void {
        hotId = null;
        mapState = { ...mapState, scale: Math.max(1, mapState.scale - 0.04) };
    }

    function onTouchStart(event: TouchEvent): void {
        if (event.touches.length !== 2) {
            return;
        }
        const a = event.touches[0];
        const b = event.touches[1];
        pinchStart = {
            distance: Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY),
            scale: mapState.scale,
            x: mapState.x,
            y: mapState.y,
            centerX: (a.clientX + b.clientX) / 2,
            centerY: (a.clientY + b.clientY) / 2,
        };
    }

    function onTouchMove(event: TouchEvent): void {
        if (event.touches.length !== 2 || !pinchStart) {
            return;
        }
        event.preventDefault();
        const a = event.touches[0];
        const b = event.touches[1];
        const distance = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
        const centerX = (a.clientX + b.clientX) / 2;
        const centerY = (a.clientY + b.clientY) / 2;
        const ratio = distance / Math.max(1, pinchStart.distance);
        mapState = {
            scale: clamp(pinchStart.scale * ratio, 0.9, 1.5),
            x: clamp(pinchStart.x + (centerX - pinchStart.centerX) * 0.36, -128, 128),
            y: clamp(pinchStart.y + (centerY - pinchStart.centerY) * 0.36, -104, 104),
        };
    }

    function onTouchEnd(event: TouchEvent): void {
        if (event.touches.length < 2) {
            pinchStart = null;
        }
    }

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
        if (cx > 0.25) {
            return "start";
        }
        if (cx < -0.25) {
            return "end";
        }
        return "middle";
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
    function aiTagFor(status: typeof aiStatus, isAi: boolean): string {
        if (status === "off") {
            return "AI is off — these explanations are the deterministic templated fallback, built from your performance data.";
        }
        if (status === "loading") {
            return "Generating plain-English explanations with AI (one batched call)…";
        }
        if (status === "failed") {
            return "AI explanation failed — showing the deterministic templated fallback, built from your performance data.";
        }
        if (isAi) {
            return "AI-generated from your performance data, in one batched call when the tab opened.";
        }
        return "AI is on, but this node fell back to its deterministic templated explanation.";
    }
    $: aiTag = aiTagFor(aiStatus, activeIsAi);
</script>

<svelte:window on:keydown={onWindowKey} />

<div class="cfa-app cfa-map">
    <main class="cfa-map__page">
        <nav class="cfa-map__appbar" aria-label="CFA sections">
            <div class="cfa-map__appbar-in">
                <div class="cfa-map__brand">ankiCFA <small>CFA Level II</small></div>
                <div class="cfa-map__tabs">
                    {#each NAV_ITEMS as item}
                        <button
                            type="button"
                            class:on={item.active}
                            on:click={() => go(item.cmd)}
                            aria-current={item.active ? "page" : undefined}
                        >
                            {item.label}
                        </button>
                    {/each}
                </div>
            </div>
        </nav>

        <header class="cfa-map__hero">
            <div class="cfa-map__eyebrow">Exact build target · liquid glass · same on phone &amp; desktop</div>
            <h1>Concept Map — the mastery engine</h1>
            <p class="cfa-map__lede">
                One node per CFA concept in an <b>organic hierarchy</b>, rendered
                in a pearl → turquoise <b>liquid glass</b> interface. <b>CFA</b>
                sits at the center, the <b>test sections</b> orbit it, and each
                section's <b>subsections</b> sit beyond. Node <b>size = exam
                weight</b>; node <b>fill = your mastery</b>. Minimalist at rest;
                detail appears on interaction.
            </p>
            <div class="cfa-map__howto" aria-label="Concept Map interaction guide">
                <span><b>hover</b> see the node's <strong>name</strong> + how <strong>full</strong> it is (%)</span>
                <span><b>click</b> read a <strong>plain-English</strong> take on why (batched AI)</span>
                <span><b>size</b> = exam <strong>weight</strong> · fill = <strong>mastery</strong></span>
            </div>
            <p class="cfa-map__meta">
                Live map — hover, click, tap, or pinch. This flagship surface is
                hierarchical, weight-sized, turquoise-filled, AI-explained in one
                batch, and designed to feel identical on phone and desktop. Click
                the same node again or press Esc to unpin.
            </p>
        </header>

        <section id="stage" class="cfa-map__stage" aria-label="Interactive Concept Map mastery engine">
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
                    on:wheel={onMapWheel}
                    on:mouseleave={onMapLeave}
                    on:touchstart={onTouchStart}
                    on:touchmove={onTouchMove}
                    on:touchend={onTouchEnd}
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
                        <filter id="cfa-soft" x="-50%" y="-50%" width="200%" height="200%">
                            <feDropShadow dx="0" dy="2" stdDeviation="3.2" flood-color="#0e3a46" flood-opacity="0.18" />
                        </filter>
                        <filter id="cfa-halob" x="-70%" y="-70%" width="240%" height="240%">
                            <feGaussianBlur stdDeviation="6" />
                        </filter>
                        {#each map.nodes as n (n.id)}
                            <clipPath id="cfa-clip-{n.id}">
                                <circle cx={n.x} cy={n.y} r={n.r} />
                            </clipPath>
                        {/each}
                    </defs>

                    <g class="cfa-map__viewport" transform={mapTransform}>
                        <circle cx={map.center.x} cy={map.center.y} r="170" fill="url(#cfa-centerglow)" />

                        <g class="cfa-map__edges" fill="none" stroke-linecap="round">
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
                                class:is-selected={selId === n.id}
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
                                <circle class="cfa-node__halo" cx={n.x} cy={n.y} r={n.r + 15} fill={TURQ_FILL} filter="url(#cfa-halob)" />
                                <g filter="url(#cfa-soft)">
                                    <circle
                                        class="cfa-node__rest"
                                        cx={n.x}
                                        cy={n.y}
                                        r={n.r}
                                        fill={n.fill}
                                        stroke={n.kind === "cfa" ? "#BFE4E1" : "#D7DEE4"}
                                        stroke-width={n.kind === "cfa" ? 2 : 1}
                                    />
                                    {#if on && n.pct !== null}
                                        <g class="cfa-node__fillg" clip-path="url(#cfa-clip-{n.id})">
                                            <rect x={n.x - n.r} y={n.y - n.r} width={2 * n.r} height={2 * n.r} fill={EMPTY_FILL} />
                                            <rect
                                                x={n.x - n.r}
                                                y={n.y + n.r - 2 * n.r * (n.mastery ?? 0)}
                                                width={2 * n.r}
                                                height={2 * n.r * (n.mastery ?? 0)}
                                                fill="url(#cfa-turqfill)"
                                            />
                                            <circle cx={n.x} cy={n.y} r={n.r} fill="none" stroke="#ffffff" stroke-width="1" stroke-opacity="0.5" />
                                        </g>
                                    {/if}
                                    {#if on}
                                        <circle class="cfa-node__ring" cx={n.x} cy={n.y} r={n.r + 3} fill="none" stroke="#0E9C97" stroke-width="3" />
                                    {/if}
                                </g>

                                {#if n.kind === "cfa"}
                                    <text class="cfa-node__clabel" x={n.x} y={n.y + 7} text-anchor="middle" font-size="21">CFA</text>
                                {:else if n.persistentLabel}
                                    <text
                                        class="cfa-node__tlabel"
                                        x={labelX(n)}
                                        y={labelY(n)}
                                        text-anchor={labelAnchor(n)}
                                    >{shortLabel(n)}</text>
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
                    </g>
                </svg>

                <div class="cfa-map__legend">
                    <span class="cfa-map__legend-end">0%</span>
                    <div class="cfa-map__legend-bar"></div>
                    <span class="cfa-map__legend-end">100% mastered</span>
                </div>
                <p class="cfa-map__cap">
                    Size = exam weight · fill = your mastery · layout is fixed
                    and stable so the map stays memorable
                </p>
            </div>

            <aside class="cfa-map__panel">
                <div class="cfa-map__eyebrow">{eyebrowFor(active)}</div>
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
                        <button type="button" class="cfa-map__drillchip" on:click={() => go("cfa:priority")}>
                            {drillFor(active)}
                        </button>
                    </div>
                {/if}
                <div class="cfa-map__aitag">{aiTag}</div>
            </aside>
        </section>

        <section class="cfa-map__info-section" id="mechanic">
            <div class="cfa-map__section-head"><span>1</span><h2>The fill mechanic</h2></div>
            <div class="cfa-map__cards">
                <article class="cfa-map__section-card">
                    <div class="cfa-map__kicker">Default · minimalist</div>
                    <p>Big nodes (CFA + the 10 sections) are labeled. Each node shows one color on the <b>light-gray → turquoise</b> scale. No numbers, no clutter.</p>
                </article>
                <article class="cfa-map__section-card">
                    <div class="cfa-map__kicker">Hover · precise</div>
                    <p>Hover resolves into an exact <b>fill gauge</b> and a chip showing <b>name + %</b>. Subsection names surface here too.</p>
                </article>
                <article class="cfa-map__section-card">
                    <div class="cfa-map__kicker">Click · why (AI)</div>
                    <p>Clicking pins a casual explanation of how that fill was earned and the fastest next drill, from the batched AI wording or deterministic fallback.</p>
                </article>
            </div>
            <div class="cfa-map__callout"><b>Brightness must be earned.</b> Fill reflects existing exam-readiness evidence. A node stays gray when there is not enough data yet.</div>
        </section>

        <section class="cfa-map__info-section" id="hierarchy">
            <div class="cfa-map__section-head"><span>2</span><h2>The hierarchy</h2></div>
            <div class="cfa-map__refrow">
                <div class="cfa-map__phoneframe" aria-label="Mobile Concept Map preview">
                    <div class="cfa-map__phone-top"><span>4:12</span><span>▮▮ ▾</span></div>
                    <svg viewBox="0 0 260 300" role="img" aria-label="Phone preview of CFA Concept Map">
                        <g stroke="#D7DEE4" fill="none" stroke-linecap="round">
                            <line x1="130" y1="150" x2="132" y2="58" />
                            <line x1="130" y1="150" x2="214" y2="118" />
                            <line x1="130" y1="150" x2="192" y2="224" />
                            <line x1="130" y1="150" x2="62" y2="222" />
                            <line x1="130" y1="150" x2="46" y2="116" />
                        </g>
                        <circle cx="132" cy="58" r="18" fill="#7fd8d3" />
                        <circle cx="214" cy="118" r="13" fill="#c9d3da" />
                        <circle cx="192" cy="224" r="17" fill="#a7e0dc" />
                        <circle cx="62" cy="222" r="12" fill="#dfe6ea" />
                        <circle cx="46" cy="116" r="16" fill="#8fdbd6" />
                        <circle cx="130" cy="150" r="30" fill="#3cc2bc" />
                        <text x="130" y="155" text-anchor="middle" font-family="Source Serif 4, serif" font-size="14" font-weight="700" fill="#fff">CFA</text>
                    </svg>
                    <div class="cfa-map__phone-tabs"><span>Today</span><span>Study</span><span class="on">Map</span><span>Readiness</span></div>
                </div>
                <div class="cfa-map__table-wrap">
                    <table class="cfa-map__table">
                        <thead><tr><th>Ring</th><th>What it is</th><th>Size / label</th></tr></thead>
                        <tbody>
                            <tr><td><b>Center</b></td><td><b>CFA</b> — overall exam readiness</td><td>Biggest · always labeled</td></tr>
                            <tr><td><b>Orbit 1</b></td><td>The <b>10 test sections</b> sized by official exam weight</td><td>Always labeled</td></tr>
                            <tr><td><b>Orbit 2</b></td><td><b>Subsections</b> of each section</td><td>Smaller · label on hover/tap</td></tr>
                        </tbody>
                    </table>
                    <p>Node size tracks exam weight. The layout is organic, but fixed and deterministic so it becomes a mental map you navigate by memory.</p>
                </div>
            </div>
        </section>

        <section class="cfa-map__info-section" id="api">
            <div class="cfa-map__section-head"><span>3</span><h2>How the AI stays instant (batched)</h2></div>
            <div class="cfa-map__cards">
                <article class="cfa-map__section-card"><div class="cfa-map__kicker">On tab open</div><p><b>One batched call</b> sends the visible nodes and existing performance data.</p></article>
                <article class="cfa-map__section-card"><div class="cfa-map__kicker">On click</div><p>The explanation is <b>already there</b>, so the panel changes instantly with no per-tap round trip.</p></article>
                <article class="cfa-map__section-card"><div class="cfa-map__kicker">AI off</div><p>The deterministic explanation is the whole explanation; the map, fills and drill button still work offline.</p></article>
            </div>
        </section>

        <section class="cfa-map__info-section" id="parity">
            <div class="cfa-map__section-head"><span>4</span><h2>New tab · identical on phone &amp; desktop</h2></div>
            <div class="cfa-map__callout">
                The same shared data, layout, light-gray → turquoise fill and
                tap-to-pin explanation panel render at every width. Desktop uses
                hover and click; phone widths use tap plus restrained pinch/pan
                so the outer subsection orbit stays usable without changing the
                frozen visual language.
            </div>
        </section>
    </main>
</div>

<style lang="scss">
    @use "../tokens" as cfa;

    .cfa-map {
        --ink: #122b46;
        --muted: #4d5c6d;
        --faint: #68707d;
        --line: rgba(255, 255, 255, 0.72);
        --turq: #14b8b1;
        --turq-deep: #0e9c97;
        --turq-soft: #e4f6f5;
        --turq-ink: #064a54;
        --empty: #e9edf1;
        --pearl: #fbfaf5;
        --deep-turq: #053b45;
        --glass: rgba(255, 255, 255, 0.62);
        --glass-strong: rgba(255, 255, 255, 0.78);
        --glass-edge: rgba(255, 255, 255, 0.72);
        --shadow: 0 28px 90px rgba(5, 59, 69, 0.16);

        width: 100%;
        min-height: 100vh;
        color: var(--ink);
        font-family: var(--cfa-font-body);
        font-size: 15px;
        line-height: 1.55;
        background:
            radial-gradient(circle at 12% 0%, rgba(255, 255, 255, 0.96), transparent 23rem),
            radial-gradient(circle at 84% 10%, rgba(20, 184, 177, 0.22), transparent 28rem),
            linear-gradient(135deg, var(--pearl) 0%, #eef9f7 40%, #d8f3ef 62%, rgba(5, 59, 69, 0.2) 100%);
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
        position: relative;
        overflow-x: hidden;

        &::before {
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            background:
                radial-gradient(circle at 18% 18%, rgba(255, 255, 255, 0.72), transparent 13rem),
                radial-gradient(circle at 78% 22%, rgba(20, 184, 177, 0.2), transparent 19rem);
            mix-blend-mode: screen;
        }

        *,
        *::before,
        *::after {
            box-sizing: border-box;
        }

        button {
            font: inherit;
        }

        h1,
        h2,
        h3 {
            margin: 0;
            font-family: var(--cfa-font-heading);
            color: #0b2f38;
        }

        h1 {
            margin-top: 6px;
            font-size: 32px;
            line-height: 1.1;
            letter-spacing: -0.01em;
        }

        h2 {
            font-size: 24px;
            font-weight: 600;
            letter-spacing: -0.01em;
        }

        p {
            margin: 0;
            color: var(--muted);
        }

        b,
        strong {
            color: var(--ink);
            font-weight: 700;
        }

        &__page {
            position: relative;
            z-index: 1;
            max-width: 1160px;
            margin: 0 auto;
            padding: 0 20px 120px;
        }

        &__appbar {
            position: sticky;
            top: 0;
            z-index: 40;
            margin: 0 -20px;
            border-bottom: 1px solid var(--glass-edge);
            background: rgba(255, 255, 255, 0.7);
            box-shadow: 0 10px 40px rgba(5, 59, 69, 0.08);
            backdrop-filter: blur(22px) saturate(1.25);
            -webkit-backdrop-filter: blur(22px) saturate(1.25);
        }

        &__appbar-in {
            display: flex;
            align-items: center;
            gap: 14px;
            max-width: 1160px;
            margin: 0 auto;
            padding: 9px 20px;
        }

        &__brand {
            min-width: 0;
            color: var(--ink);
            font-family: var(--cfa-font-heading);
            font-size: 17px;
            font-weight: 700;

            small {
                display: block;
                color: var(--turq-ink);
                font-family: var(--cfa-font-body);
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 0.16em;
                text-transform: uppercase;
            }
        }

        &__tabs {
            display: flex;
            flex-wrap: wrap;
            gap: 2px;
            margin-left: auto;

            button {
                cursor: pointer;
                border: 0;
                border-radius: 8px;
                background: transparent;
                color: var(--muted);
                padding: 7px 12px;
                font-size: 13px;
                font-weight: 700;

                &:hover,
                &.on {
                    color: var(--turq-ink);
                    background: rgba(20, 184, 177, 0.12);
                    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.65);
                }

                &:focus-visible {
                    outline: 3px solid rgba(20, 184, 177, 0.36);
                    outline-offset: 2px;
                }
            }
        }

        &__hero {
            position: relative;
            overflow: hidden;
            margin-top: 24px;
            padding: 30px;
            border: 1px solid var(--glass-edge);
            border-radius: 28px;
            background:
                linear-gradient(135deg, rgba(255, 255, 255, 0.82), rgba(255, 255, 255, 0.42)),
                radial-gradient(circle at 78% 18%, rgba(20, 184, 177, 0.18), transparent 22rem);
            box-shadow: var(--shadow);
            backdrop-filter: blur(26px) saturate(1.18);
            -webkit-backdrop-filter: blur(26px) saturate(1.18);

            &::after {
                content: "";
                position: absolute;
                inset: 1px;
                border-radius: 27px;
                pointer-events: none;
                background: linear-gradient(120deg, rgba(255, 255, 255, 0.7), transparent 30%, rgba(255, 255, 255, 0.18));
                mask: linear-gradient(#000, transparent 70%);
            }
        }

        &__eyebrow {
            color: var(--turq-ink);
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 0.15em;
            text-transform: uppercase;
        }

        &__lede {
            max-width: 770px;
            margin-top: 10px;
            font-size: 16px;
            color: var(--muted);
        }

        &__howto {
            display: flex;
            flex-wrap: wrap;
            gap: 18px;
            margin-top: 14px;
            color: var(--muted);
            font-size: 13px;

            span {
                display: flex;
                align-items: center;
                gap: 7px;
            }

            b {
                display: inline-flex;
                align-items: center;
                min-height: 20px;
                padding: 2px 9px;
                border-radius: 100px;
                background: rgba(20, 184, 177, 0.12);
                color: var(--turq-ink);
                box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.65);
                font-size: 11px;
                font-weight: 700;
                text-transform: lowercase;
            }
        }

        &__meta {
            margin-top: 12px;
            color: var(--faint);
            font-size: 12px;
        }

        &__stage {
            display: grid;
            grid-template-columns: minmax(0, 1.7fr) minmax(0, 1fr);
            gap: 16px;
            align-items: stretch;
            margin-top: 38px;

            @media (max-width: 940px) {
                grid-template-columns: minmax(0, 1fr);
            }
        }

        &__mapbox,
        &__panel,
        &__section-card,
        &__callout,
        &__table,
        &__phoneframe {
            border: 1px solid var(--glass-edge);
            background: var(--glass);
            box-shadow:
                inset 0 1px 0 rgba(255, 255, 255, 0.78),
                0 20px 70px rgba(5, 59, 69, 0.12);
            backdrop-filter: blur(22px) saturate(1.18);
            -webkit-backdrop-filter: blur(22px) saturate(1.18);
        }

        &__mapbox {
            position: relative;
            overflow: hidden;
            border-radius: 16px;
            padding: 10px;
            background:
                radial-gradient(circle at 22% 18%, rgba(255, 255, 255, 0.88), transparent 17rem),
                radial-gradient(circle at 78% 16%, rgba(20, 184, 177, 0.18), transparent 19rem),
                linear-gradient(135deg, rgba(255, 255, 255, 0.76), rgba(216, 243, 239, 0.36));

            svg {
                display: block;
                width: 100%;
                height: auto;
                border-radius: 18px;
                background:
                    radial-gradient(circle at 50% 44%, rgba(20, 184, 177, 0.1), transparent 18rem),
                    linear-gradient(135deg, rgba(255, 255, 255, 0.72), rgba(255, 255, 255, 0.3));
                touch-action: none;
            }
        }

        &__viewport {
            transform-origin: 500px 366px;
            transition: transform 0.16s ease;
        }

        &__legend {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 6px 12px 2px;
        }

        &__legend-bar {
            flex: 1;
            height: 12px;
            border: 1px solid rgba(231, 235, 239, 0.82);
            border-radius: 100px;
            background: linear-gradient(90deg, #e8edf0, #7edbd6, #0e9c97);
        }

        &__legend-end {
            color: var(--faint);
            font-size: 12px;
        }

        &__cap {
            margin: 2px 0 0;
            padding: 0 12px 8px;
            text-align: center;
            color: var(--faint);
            font-size: 12px;
        }

        &__panel {
            display: flex;
            flex-direction: column;
            min-width: 0;
            border-radius: 16px;
            padding: 18px;
            background: linear-gradient(145deg, rgba(255, 255, 255, 0.74), rgba(244, 247, 247, 0.46));
        }

        &__ptitle {
            margin: 4px 0 0;
            font-family: var(--cfa-font-heading);
            font-size: 20px;
            font-weight: 700;
            line-height: 1.2;
        }

        &__ppct {
            margin-top: 2px;
            color: var(--turq-ink);
            font-size: 13px;
            font-weight: 800;
        }

        &__pmeta {
            margin-top: 2px;
            color: var(--faint);
            font-size: 12px;
        }

        &__gauge {
            height: 10px;
            border-radius: 100px;
            background: rgba(233, 237, 241, 0.72);
            box-shadow: inset 0 1px 2px rgba(5, 59, 69, 0.08);
            overflow: hidden;
            margin: 12px 0 4px;

            > i {
                display: block;
                height: 100%;
                background: linear-gradient(90deg, #7edbd6, #0e9c97);
                transition: width 0.35s ease;
            }

            // Abstaining node: a neutral diagonal hatch reads as "awaiting
            // evidence / not applicable", never as a measured 0% fill.
            &.is-nodata {
                background: repeating-linear-gradient(
                    -45deg,
                    var(--empty),
                    var(--empty) 4px,
                    rgba(255, 255, 255, 0.74) 4px,
                    rgba(255, 255, 255, 0.74) 8px
                );
                border: 1px solid rgba(231, 235, 239, 0.82);
            }
        }

        &__expl {
            margin: 12px 0 0;
            color: var(--ink);
            font-size: 14px;
            line-height: 1.6;

            &.is-placeholder {
                color: var(--faint);
            }
        }

        &__drill {
            margin-top: auto;
            padding-top: 12px;
        }

        &__drillchip {
            display: inline-flex;
            cursor: pointer;
            border: 1px solid rgba(255, 255, 255, 0.72);
            border-radius: 10px;
            background: rgba(20, 184, 177, 0.12);
            color: var(--turq-ink);
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.65);
            padding: 9px 12px;
            font-size: 13px;
            font-weight: 800;

            &:focus-visible {
                outline: 3px solid rgba(20, 184, 177, 0.36);
                outline-offset: 2px;
            }
        }

        &__aitag {
            margin-top: auto;
            padding-top: 10px;
            border-top: 1px dashed rgba(231, 235, 239, 0.82);
            color: var(--faint);
            font-size: 11.5px;
        }

        &__info-section {
            margin-top: 38px;
        }

        &__section-head {
            display: flex;
            align-items: baseline;
            gap: 12px;
            flex-wrap: wrap;
            margin-bottom: 14px;

            span {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                flex: 0 0 auto;
                width: 28px;
                height: 28px;
                border-radius: 50%;
                background: linear-gradient(135deg, var(--turq-ink), var(--deep-turq));
                box-shadow: 0 10px 30px rgba(5, 59, 69, 0.18);
                color: #fff;
                font-family: var(--cfa-font-heading);
                font-size: 13px;
                font-weight: 700;
            }
        }

        &__cards {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 16px;
        }

        &__section-card {
            border-radius: 14px;
            padding: 18px;
            min-width: 0;

            p {
                font-size: 13.5px;
            }
        }

        &__kicker {
            margin-bottom: 6px;
            color: var(--faint);
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 0.1em;
            text-transform: uppercase;
        }

        &__callout {
            margin-top: 16px;
            border-left: 4px solid var(--turq);
            border-radius: 0 12px 12px 0;
            background: rgba(255, 255, 255, 0.58);
            padding: 14px 16px;
            color: var(--muted);
        }

        &__refrow {
            display: grid;
            grid-template-columns: minmax(0, 0.8fr) minmax(0, 1.4fr);
            gap: 16px;
            align-items: center;
        }

        &__phoneframe {
            width: min(250px, 100%);
            margin: 0 auto;
            border-radius: 26px;
            padding: 10px;
            background: rgba(255, 255, 255, 0.62);

            svg {
                display: block;
                width: 100%;
                border-inline: 1px solid rgba(231, 235, 239, 0.82);
                background: rgba(255, 255, 255, 0.62);
            }
        }

        &__phone-top,
        &__phone-tabs {
            display: flex;
            justify-content: space-between;
            background: rgba(255, 255, 255, 0.62);
            color: var(--muted);
            font-size: 10px;
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
        }

        &__phone-top {
            border: 1px solid rgba(231, 235, 239, 0.82);
            border-bottom: 0;
            border-radius: 18px 18px 0 0;
            padding: 8px 10px;
        }

        &__phone-tabs {
            border: 1px solid rgba(231, 235, 239, 0.82);
            border-top: 0;
            border-radius: 0 0 18px 18px;

            span {
                flex: 1;
                text-align: center;
                padding: 7px 1px;
                color: var(--faint);
                font-size: 8.5px;

                &.on {
                    color: var(--turq-ink);
                    font-weight: 800;
                }
            }
        }

        &__table-wrap {
            min-width: 0;

            p {
                margin-top: 12px;
                font-size: 13px;
            }
        }

        &__table {
            width: 100%;
            border-collapse: collapse;
            overflow: hidden;
            border-radius: 12px;
            font-size: 13px;

            th,
            td {
                padding: 9px 12px;
                border-bottom: 1px solid rgba(231, 235, 239, 0.82);
                text-align: left;
                vertical-align: top;
            }

            th {
                background: rgba(255, 255, 255, 0.48);
                color: var(--muted);
                font-size: 11px;
                letter-spacing: 0.04em;
                text-transform: uppercase;
            }

            tr:last-child td {
                border-bottom: 0;
            }
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
            stroke: var(--turq-deep);
            stroke-width: 3;
        }

        &__halo {
            opacity: 0;
            transition: opacity 0.2s ease;
        }

        &.on .cfa-node__halo {
            opacity: 0.16;
        }

        &.is-selected .cfa-node__halo {
            opacity: 0.1;
        }

        &__rest {
            transition: opacity 0.18s ease, stroke 0.18s ease;
        }
    }

    .cfa-node__fillg {
        animation: cfa-fill-in 0.2s ease forwards;
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

    @keyframes cfa-fill-in {
        from {
            opacity: 0;
        }
        to {
            opacity: 1;
        }
    }

    .cfa-node__tlabel {
        font-family: var(--cfa-font-body);
        font-size: 12.5px;
        font-weight: 700;
        fill: var(--ink);
        paint-order: stroke;
        stroke: rgba(255, 255, 255, 0.86);
        stroke-width: 3.2px;
        stroke-linejoin: round;
    }

    .cfa-node__clabel {
        font-family: var(--cfa-font-heading);
        font-weight: 700;
        fill: #ffffff;
        letter-spacing: 0.04em;
        paint-order: stroke;
        stroke: rgba(5, 59, 69, 0.16);
        stroke-width: 2px;
        stroke-linejoin: round;
    }

    // On-node hover tooltip — the navy chip / white name / turquoise % from the
    // approved spec (and mobile). It fades with hover so the map stays calm at
    // rest; the panel remains the durable, pinned detail surface.
    .cfa-tip {
        &__bg {
            fill: #122b46;
        }

        &__name {
            fill: #ffffff;
            font-family: var(--cfa-font-body);
            font-size: 15px;
            font-weight: 700;
        }

        &__pct {
            fill: #4ce0d8;
            font-family: var(--cfa-font-body);
            font-size: 13px;
            font-weight: 800;
        }
    }

    @media (max-width: 820px) {
        .cfa-map {
            &__cards,
            &__refrow {
                grid-template-columns: minmax(0, 1fr);
            }
        }
    }

    @media (max-width: 720px) {
        .cfa-map {
            font-size: 14px;

            &__page {
                padding-right: 14px;
                padding-left: 14px;
            }

            &__appbar {
                margin: 0 -14px;
            }

            &__appbar-in {
                gap: 10px;
            }

            &__tabs {
                width: 100%;
                margin-left: 0;
            }

            &__tabs button {
                flex: 1 1 auto;
                padding: 7px 8px;
                font-size: 12px;
            }

            &__hero {
                padding: 22px;
                border-radius: 26px;
            }

            h1 {
                font-size: 30px;
            }

            &__lede {
                font-size: 15px;
            }

            &__mapbox,
            &__panel {
                border-radius: 16px;
            }

            &__mapbox {
                padding: 8px;
            }

            &__mapbox svg {
                min-width: 640px;
            }

            &__mapbox {
                overflow-x: auto;
            }

            &__legend {
                min-width: 620px;
            }

            &__cap {
                min-width: 620px;
            }
        }
    }
</style>
