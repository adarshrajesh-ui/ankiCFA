<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

CfaConceptMapPage — the CFA Concept Map tab: a radial topic-evidence map. CFA
sits at the centre (biggest), the 10 test sections orbit it (SIZE ∝ exam
weight), each section's subsections beyond. Node FILL goes light-gray →
turquoise by mastery; a node with no evidence yet stays gray (the honest
give-up rule).

Thin by design: all geometry, fill, the abstain rule and the deterministic templated
explanations come from the pure `./conceptmap` engine; this component only draws
what it returns and wires hover (name + %) / click (pin the plain-English why).
-->
<script lang="ts">
    import { onMount } from "svelte";
    import { bridgeCommand } from "@tslib/bridgecommand";

    import type { CfaHomePayload } from "$lib/cfa";
    import ProductShellNav from "$lib/cfa/ProductShellNav.svelte";

    import {
        buildConceptMap,
        type ConceptNode,
        CX,
        CY,
        drillFor,
        EMPTY_FILL,
        masteryLabel,
        templatedExplanation,
        TURQ_FILL,
        VIEW_H,
        VIEW_W,
    } from "./conceptmap";
    import { syncChipLabel } from "./home";

    /** The CFA payload (carries the per-topic rows the map is built from). */
    export let data: CfaHomePayload;

    const SHORT_TOPIC_LABELS: Record<string, string> = {
        "Ethics & Professional Standards": "Ethics",
        "Quantitative Methods": "Quant",
        Economics: "Economics",
        "Financial Reporting & Analysis": "FRA",
        "Corporate Issuers": "Corp. Issuers",
        "Equity Investments": "Equity",
        "Fixed Income": "Fixed Income",
        Derivatives: "Derivatives",
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

    interface DragStart {
        pointerId: number;
        clientX: number;
        clientY: number;
        x: number;
        y: number;
    }

    const PHONE_MEDIA = "(max-width: 720px)";
    const PHONE_MAP_SCALE = 1.42;

    $: map = buildConceptMap(data.topics);
    $: readinessAbstaining = data.heroMode === "abstain" || data.readiness.abstain;
    $: syncLabel = syncChipLabel(data);

    let hotId: string | null = null;
    let selId: string | null = null;
    let mapState = { x: 0, y: 0, scale: 1 };
    let pinchStart: PinchStart | null = null;
    let dragStart: DragStart | null = null;
    let mapWasDragged = false;
    let suppressNextSelect = false;
    let userMovedMap = false;
    $: mapTransform = `translate(${mapState.x} ${mapState.y}) scale(${mapState.scale})`;

    onMount(() => {
        const media = window.matchMedia(PHONE_MEDIA);
        const applyViewportPreset = (): void => {
            if (!userMovedMap) {
                mapState = centeredMapState(media.matches ? PHONE_MAP_SCALE : 1);
            }
        };
        applyViewportPreset();
        media.addEventListener("change", applyViewportPreset);
        return () => media.removeEventListener("change", applyViewportPreset);
    });

    function go(cmd: string): void {
        bridgeCommand(cmd);
    }

    function clamp(value: number, min: number, max: number): number {
        return Math.max(min, Math.min(max, value));
    }

    function clampMapPosition(x: number, y: number, scale: number): typeof mapState {
        const xLimit = Math.max(180, (VIEW_W * Math.max(0, scale - 1)) / 2 + 120);
        const yLimit = Math.max(132, (VIEW_H * Math.max(0, scale - 1)) / 2 + 105);
        return {
            x: clamp(x, -xLimit, xLimit),
            y: clamp(y, -yLimit, yLimit),
            scale,
        };
    }

    function centeredMapState(scale: number): typeof mapState {
        return clampMapPosition(CX * (1 - scale), CY * (1 - scale), scale);
    }

    function shortLabel(n: ConceptNode): string {
        if (n.kind !== "topic") {
            return n.name;
        }
        return SHORT_TOPIC_LABELS[n.full] ?? n.name;
    }

    function onMapWheel(event: WheelEvent): void {
        event.preventDefault();
        userMovedMap = true;
        const svg = event.currentTarget as SVGSVGElement;
        const rect = svg.getBoundingClientRect();
        const anchorX =
            ((event.clientX - rect.left) / Math.max(1, rect.width)) * VIEW_W;
        const anchorY =
            ((event.clientY - rect.top) / Math.max(1, rect.height)) * VIEW_H;
        const nextScale = clamp(
            mapState.scale * Math.exp(-event.deltaY * 0.0012),
            0.92,
            1.8,
        );
        const ratio = nextScale / mapState.scale;
        mapState = {
            ...clampMapPosition(
                anchorX - (anchorX - mapState.x) * ratio,
                anchorY - (anchorY - mapState.y) * ratio,
                nextScale,
            ),
        };
    }

    function onMapLeave(): void {
        hotId = null;
    }

    function onTouchStart(event: TouchEvent): void {
        if (event.touches.length !== 2) {
            return;
        }
        userMovedMap = true;
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
        const nextScale = clamp(pinchStart.scale * ratio, 0.92, 1.8);
        mapState = clampMapPosition(
            pinchStart.x + (centerX - pinchStart.centerX) * 0.36,
            pinchStart.y + (centerY - pinchStart.centerY) * 0.36,
            nextScale,
        );
    }

    function onTouchEnd(event: TouchEvent): void {
        if (event.touches.length < 2) {
            pinchStart = null;
        }
    }

    function onTouchCancel(): void {
        pinchStart = null;
        dragStart = null;
    }

    function onPointerDown(event: PointerEvent): void {
        if (
            (event.pointerType === "mouse" && event.button !== 0) ||
            pinchStart !== null
        ) {
            return;
        }
        userMovedMap = true;
        dragStart = {
            pointerId: event.pointerId,
            clientX: event.clientX,
            clientY: event.clientY,
            x: mapState.x,
            y: mapState.y,
        };
        mapWasDragged = false;
        (event.currentTarget as SVGSVGElement).setPointerCapture(event.pointerId);
    }

    function onPointerMove(event: PointerEvent): void {
        if (
            !dragStart ||
            dragStart.pointerId !== event.pointerId ||
            pinchStart !== null
        ) {
            return;
        }
        const svg = event.currentTarget as SVGSVGElement;
        const rect = svg.getBoundingClientRect();
        const dx = event.clientX - dragStart.clientX;
        const dy = event.clientY - dragStart.clientY;
        if (Math.hypot(dx, dy) > 4) {
            mapWasDragged = true;
            event.preventDefault();
        }
        mapState = clampMapPosition(
            dragStart.x + (dx * VIEW_W) / Math.max(1, rect.width),
            dragStart.y + (dy * VIEW_H) / Math.max(1, rect.height),
            mapState.scale,
        );
    }

    function onPointerUp(event: PointerEvent): void {
        if (!dragStart || dragStart.pointerId !== event.pointerId) {
            return;
        }
        if (mapWasDragged) {
            suppressNextSelect = true;
        }
        const svg = event.currentTarget as SVGSVGElement;
        if (svg.hasPointerCapture(event.pointerId)) {
            svg.releasePointerCapture(event.pointerId);
        }
        dragStart = null;
        mapWasDragged = false;
    }

    // The node currently driving the side panel: the pinned selection wins,
    // otherwise the hovered node, otherwise the centre (a calm default).
    $: activeId = selId ?? hotId ?? map.center.id;
    $: active = map.nodes.find((n) => n.id === activeId) ?? map.center;
    $: activeStrengthLabel = panelStrengthLabel(active);

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
        const pct = pctText(n);
        const w = Math.max(n.name.length * 8.6, pct.length * 7.2, 96) + 26;
        return {
            name: n.name,
            pct,
            x: n.x,
            nameY: ty - 16,
            pctY: ty + 7,
            bgX: n.x - w / 2,
            bgY: ty - 35,
            w,
        };
    }
    $: tipNode =
        hotId !== null ? (map.nodes.find((n) => n.id === hotId) ?? null) : null;
    $: tip = tipNode ? computeTip(tipNode) : null;

    function pctText(n: ConceptNode): string {
        if (n.kind === "cfa") {
            if (n.pct === null) {
                return readinessAbstaining
                    ? "Readiness unavailable"
                    : "No map signal yet";
            }
            return `${n.pct}% mapped topic signal`;
        }
        return n.pct === null ? "No data yet" : `${n.pct}% mastered`;
    }
    function panelStrengthLabel(n: ConceptNode): string {
        if (n.pct === null) {
            return "";
        }
        if (n.kind === "cfa" && readinessAbstaining) {
            return "readiness unavailable";
        }
        return masteryLabel(n.mastery);
    }
    function eyebrowFor(n: ConceptNode): string {
        if (selId === n.id) {
            return "Explanation";
        }
        if (n.kind === "cfa") {
            return "Map overview";
        }
        if (n.kind === "sub") {
            return `Subsection · ${n.parent}`;
        }
        return "Test section";
    }
    function metaFor(n: ConceptNode): string {
        if (n.kind === "cfa") {
            return readinessAbstaining
                ? "Weighted topic signal only · Readiness is awaiting evidence"
                : "Weight-adjusted topic signal across all 10 sections";
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
        return n.x + Math.cos(n.labelAngle) * (n.r + 17);
    }
    function labelY(n: ConceptNode): number {
        return n.y + Math.sin(n.labelAngle) * (n.r + 17) + 4;
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
        if (suppressNextSelect) {
            suppressNextSelect = false;
            return;
        }
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

    // The explanation shown for the active node is fully local and deterministic.
    $: activeExpl = templatedExplanation(active);
</script>

<svelte:window on:keydown={onWindowKey} />

<div class="cfa-app cfa-map">
    <main class="cfa-map__page">
        <ProductShellNav
            active="conceptmap"
            subtitle="CFA Level II"
            syncStatus={syncLabel}
            ariaLabel="CFA sections"
            on:navigate={(event) => go(event.detail)}
        />

        <header class="cfa-map__hero">
            <div class="cfa-map__eyebrow">
                Concept map · topic evidence · instant explanations
            </div>
            <h1>Concept Map</h1>
            <p class="cfa-map__lede">
                Explore how your CFA sections connect, where evidence exists, and which
                heavy topics deserve attention next. The center shows a weighted topic
                signal from the map; Readiness remains the source of any pass/fail call.
            </p>
            <div class="cfa-map__howto" aria-label="Concept Map interaction guide">
                <span>
                    <b>hover</b>
                    see the node's
                    <strong>name</strong>
                    and current signal
                </span>
                <span>
                    <b>click</b>
                    pin a
                    <strong>plain-English</strong>
                    explanation
                </span>
                <span>
                    <b>size</b>
                    follows exam
                    <strong>weight</strong>
                    · fill follows
                    <strong>mastery evidence</strong>
                </span>
            </div>
            <p class="cfa-map__meta">
                Hover, click, tap, or pinch. Explanations are local and deterministic,
                so pinning a node stays instant. Click the same node again or press Esc
                to unpin.
            </p>
        </header>

        <section
            id="stage"
            class="cfa-map__stage"
            aria-label="Interactive Concept Map mastery engine"
        >
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
                    on:touchcancel={onTouchCancel}
                    on:pointerdown={onPointerDown}
                    on:pointermove={onPointerMove}
                    on:pointerup={onPointerUp}
                    on:pointercancel={onPointerUp}
                >
                    <defs>
                        <linearGradient id="cfa-turqfill" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0" stop-color="#9AF0EA" />
                            <stop offset="0.56" stop-color="#22BDB8" />
                            <stop offset="1" stop-color="#034D5D" />
                        </linearGradient>
                        <radialGradient id="cfa-node-glass" cx="32%" cy="20%" r="78%">
                            <stop offset="0" stop-color="#FFFFFF" stop-opacity="0.82" />
                            <stop
                                offset="0.34"
                                stop-color="#FFFFFF"
                                stop-opacity="0.28"
                            />
                            <stop
                                offset="0.66"
                                stop-color="#FFFFFF"
                                stop-opacity="0.08"
                            />
                            <stop offset="1" stop-color="#FFFFFF" stop-opacity="0" />
                        </radialGradient>
                        <radialGradient id="cfa-centerglow" cx="50%" cy="50%" r="50%">
                            <stop
                                offset="0"
                                stop-color={TURQ_FILL}
                                stop-opacity="0.14"
                            />
                            <stop offset="1" stop-color={TURQ_FILL} stop-opacity="0" />
                        </radialGradient>
                        <filter
                            id="cfa-soft"
                            x="-50%"
                            y="-50%"
                            width="200%"
                            height="200%"
                        >
                            <feDropShadow
                                dx="0"
                                dy="4"
                                stdDeviation="4.8"
                                flood-color="#0e3a46"
                                flood-opacity="0.24"
                            />
                            <feDropShadow
                                dx="0"
                                dy="-1"
                                stdDeviation="1.2"
                                flood-color="#ffffff"
                                flood-opacity="0.52"
                            />
                        </filter>
                        <filter
                            id="cfa-halob"
                            x="-70%"
                            y="-70%"
                            width="240%"
                            height="240%"
                        >
                            <feGaussianBlur stdDeviation="8" />
                        </filter>
                        {#each map.nodes as n (n.id)}
                            <clipPath id="cfa-clip-{n.id}">
                                <circle cx={n.x} cy={n.y} r={n.r} />
                            </clipPath>
                        {/each}
                    </defs>

                    <g class="cfa-map__viewport" transform={mapTransform}>
                        <circle
                            cx={map.center.x}
                            cy={map.center.y}
                            r="170"
                            fill="url(#cfa-centerglow)"
                        />

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
                                <circle
                                    class="cfa-node__halo"
                                    cx={n.x}
                                    cy={n.y}
                                    r={n.r + 22}
                                    fill={n.pct === null ? "#AAB7C1" : TURQ_FILL}
                                    filter="url(#cfa-halob)"
                                />
                                <g filter="url(#cfa-soft)">
                                    <circle
                                        class="cfa-node__rest"
                                        cx={n.x}
                                        cy={n.y}
                                        r={n.r}
                                        fill={n.fill}
                                        stroke={n.kind === "cfa"
                                            ? "#BFE4E1"
                                            : "#D7DEE4"}
                                        stroke-width={n.kind === "cfa" ? 2.5 : 1.5}
                                    />
                                    {#if on && n.pct !== null}
                                        <g
                                            class="cfa-node__fillg"
                                            clip-path="url(#cfa-clip-{n.id})"
                                        >
                                            <rect
                                                x={n.x - n.r}
                                                y={n.y - n.r}
                                                width={2 * n.r}
                                                height={2 * n.r}
                                                fill={EMPTY_FILL}
                                            />
                                            <rect
                                                x={n.x - n.r}
                                                y={n.y +
                                                    n.r -
                                                    2 * n.r * (n.mastery ?? 0)}
                                                width={2 * n.r}
                                                height={2 * n.r * (n.mastery ?? 0)}
                                                fill="url(#cfa-turqfill)"
                                            />
                                            <circle
                                                cx={n.x}
                                                cy={n.y}
                                                r={n.r}
                                                fill="none"
                                                stroke="#ffffff"
                                                stroke-width="1"
                                                stroke-opacity="0.5"
                                            />
                                        </g>
                                    {/if}
                                    <circle
                                        class="cfa-node__glass"
                                        cx={n.x}
                                        cy={n.y}
                                        r={n.r}
                                        fill="url(#cfa-node-glass)"
                                    />
                                    <ellipse
                                        class="cfa-node__shine"
                                        cx={n.x - n.r * 0.24}
                                        cy={n.y - n.r * 0.36}
                                        rx={n.r * 0.46}
                                        ry={Math.max(4, n.r * 0.16)}
                                    />
                                    <circle
                                        class="cfa-node__inner-rim"
                                        cx={n.x}
                                        cy={n.y}
                                        r={n.r - 2}
                                        fill="none"
                                        stroke="#ffffff"
                                        stroke-opacity={n.kind === "cfa" ? 0.58 : 0.44}
                                        stroke-width="1.2"
                                    />
                                    {#if on}
                                        <circle
                                            class="cfa-node__ring"
                                            cx={n.x}
                                            cy={n.y}
                                            r={n.r + 5}
                                            fill="none"
                                            stroke="#0E9C97"
                                            stroke-width="4"
                                        />
                                    {/if}
                                </g>

                                {#if n.kind === "cfa"}
                                    <text
                                        class="cfa-node__label cfa-node__clabel"
                                        x={n.x}
                                        y={n.y + 8}
                                        text-anchor="middle"
                                        font-size="24"
                                    >
                                        CFA
                                    </text>
                                {:else if n.persistentLabel}
                                    <text
                                        class="cfa-node__label cfa-node__tlabel"
                                        x={labelX(n)}
                                        y={labelY(n)}
                                        text-anchor={labelAnchor(n)}
                                    >
                                        {shortLabel(n)}
                                    </text>
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
                                    text-anchor="middle"
                                >
                                    {tip.name}
                                </text>
                                <text
                                    class="cfa-tip__pct"
                                    x={tip.x}
                                    y={tip.pctY}
                                    text-anchor="middle"
                                >
                                    {tip.pct}
                                </text>
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
                    Size = exam weight · fill = your mastery · layout is fixed and
                    stable so the map stays memorable
                </p>
            </div>

            <aside class="cfa-map__panel">
                <div class="cfa-map__eyebrow">{eyebrowFor(active)}</div>
                <h3 class="cfa-map__ptitle">{active.full}</h3>
                <div class="cfa-map__ppct">
                    {pctText(active)}{activeStrengthLabel
                        ? ` · ${activeStrengthLabel}`
                        : ""}
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
                        : pctText(active)}
                >
                    {#if active.pct !== null}
                        <i style="width: {active.pct}%"></i>
                    {/if}
                </div>
                <p
                    class="cfa-map__expl"
                    class:is-placeholder={active.pct === null && selId === null}
                >
                    {activeExpl}
                </p>
                {#if selId !== null}
                    <div class="cfa-map__drill">
                        <button
                            type="button"
                            class="cfa-map__drillchip"
                            on:click={() => go("cfa:priority")}
                        >
                            {drillFor(active)}
                        </button>
                    </div>
                {/if}
            </aside>
        </section>
    </main>
</div>

<style lang="scss">
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
        font-size: 18px;
        line-height: 1.5;
        background:
            radial-gradient(
                circle at 12% 0%,
                rgba(255, 255, 255, 0.96),
                transparent 23rem
            ),
            radial-gradient(
                circle at 86% 8%,
                rgba(20, 184, 177, 0.22),
                transparent 28rem
            ),
            radial-gradient(
                circle at 56% 70%,
                rgba(5, 59, 69, 0.16),
                transparent 34rem
            ),
            linear-gradient(
                135deg,
                var(--pearl) 0%,
                #eef9f7 42%,
                #d8f3ef 64%,
                rgba(5, 59, 69, 0.24) 100%
            );
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
                radial-gradient(
                    circle at 18% 18%,
                    rgba(255, 255, 255, 0.72),
                    transparent 13rem
                ),
                radial-gradient(
                    circle at 78% 22%,
                    rgba(20, 184, 177, 0.2),
                    transparent 19rem
                );
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
        h3 {
            margin: 0;
            font-family: var(--cfa-font-heading);
            color: #0b2f38;
        }

        h1 {
            max-width: 790px;
            margin-top: 6px;
            font-size: clamp(38px, 5vw, 64px);
            line-height: 1.01;
            letter-spacing: -0.04em;
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
            max-width: 1440px;
            min-width: 0;
            margin: 0 auto;
            padding: 35px 28px 90px;
        }

        &__hero {
            position: relative;
            overflow: hidden;
            margin-top: 33px;
            padding: 35px;
            border: 1px solid var(--glass-edge);
            border-radius: 40px;
            background:
                linear-gradient(
                    135deg,
                    rgba(255, 255, 255, 0.84),
                    rgba(255, 255, 255, 0.48)
                ),
                radial-gradient(
                    circle at 76% 18%,
                    rgba(20, 184, 177, 0.2),
                    transparent 24rem
                );
            box-shadow: var(--shadow);
            backdrop-filter: blur(26px) saturate(1.18);
            -webkit-backdrop-filter: blur(26px) saturate(1.18);

            &::after {
                content: "";
                position: absolute;
                inset: 1px;
                border-radius: 39px;
                pointer-events: none;
                background: linear-gradient(
                    120deg,
                    rgba(255, 255, 255, 0.7),
                    transparent 30%,
                    rgba(255, 255, 255, 0.18)
                );
                mask: linear-gradient(#000, transparent 70%);
            }
        }

        &__eyebrow {
            color: var(--turq-ink);
            font-size: 14px;
            font-weight: 800;
            letter-spacing: 0.15em;
            text-transform: uppercase;
        }

        &__lede {
            max-width: 850px;
            margin-top: 13px;
            font-size: 20px;
            color: var(--muted);
        }

        &__howto {
            display: flex;
            flex-wrap: wrap;
            gap: 13px 18px;
            margin-top: 24px;
            color: var(--muted);
            font-size: 15px;

            span {
                display: flex;
                align-items: center;
                gap: 7px;
            }

            b {
                display: inline-flex;
                align-items: center;
                min-height: 28px;
                padding: 4px 11px;
                border-radius: 100px;
                background: rgba(20, 184, 177, 0.12);
                color: var(--turq-ink);
                box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.65);
                font-size: 12px;
                font-weight: 700;
                text-transform: lowercase;
            }
        }

        &__meta {
            margin-top: 12px;
            color: var(--faint);
            font-size: 14px;
            font-weight: 700;
        }

        &__stage {
            display: grid;
            grid-template-columns: minmax(0, 1fr) minmax(320px, 390px);
            gap: 20px;
            align-items: stretch;
            min-width: 0;
            margin-top: 23px;

            @media (max-width: 1080px) {
                grid-template-columns: minmax(0, 1fr);
            }
        }

        &__mapbox,
        &__panel {
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
            min-width: 0;
            border-radius: 28px;
            padding: 18px;
            background:
                radial-gradient(
                    circle at 20% 16%,
                    rgba(255, 255, 255, 0.96),
                    transparent 18rem
                ),
                radial-gradient(
                    circle at 78% 14%,
                    rgba(20, 184, 177, 0.22),
                    transparent 24rem
                ),
                radial-gradient(
                    circle at 52% 94%,
                    rgba(3, 77, 93, 0.1),
                    transparent 18rem
                ),
                linear-gradient(
                    135deg,
                    rgba(255, 255, 255, 0.78),
                    rgba(216, 243, 239, 0.32)
                );

            svg {
                display: block;
                width: 100%;
                height: auto;
                min-height: clamp(460px, 48vw, 680px);
                border-radius: 24px;
                background:
                    radial-gradient(
                        circle at 50% 44%,
                        rgba(20, 184, 177, 0.12),
                        transparent 18rem
                    ),
                    radial-gradient(
                        circle at 28% 18%,
                        rgba(255, 255, 255, 0.86),
                        transparent 14rem
                    ),
                    linear-gradient(
                        135deg,
                        rgba(255, 255, 255, 0.76),
                        rgba(255, 255, 255, 0.28)
                    );
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
            padding: 10px 12px 2px;
        }

        &__legend-bar {
            flex: 1;
            height: 13px;
            border: 1px solid rgba(231, 235, 239, 0.82);
            border-radius: 100px;
            background: linear-gradient(
                90deg,
                #e9edf1 0%,
                #e3faf8 40%,
                #4cd3cf 70%,
                #0c8c94 85%,
                #034d5d 100%
            );
        }

        &__legend-end {
            color: var(--faint);
            font-size: 12px;
        }

        &__cap {
            margin: 2px 0 0;
            padding: 0 12px 4px;
            text-align: center;
            color: var(--faint);
            font-size: 13px;
            font-weight: 700;
        }

        &__panel {
            display: flex;
            flex-direction: column;
            min-width: 0;
            border-radius: 28px;
            padding: 24px;
            background: linear-gradient(
                145deg,
                rgba(255, 255, 255, 0.74),
                rgba(244, 247, 247, 0.46)
            );
        }

        &__ptitle {
            margin: 6px 0 0;
            font-family: var(--cfa-font-heading);
            font-size: clamp(27px, 3vw, 38px);
            font-weight: 700;
            line-height: 1.1;
            letter-spacing: -0.03em;
        }

        &__ppct {
            margin-top: 8px;
            color: var(--turq-ink);
            font-size: 15px;
            font-weight: 800;
        }

        &__pmeta {
            margin-top: 4px;
            color: var(--faint);
            font-size: 13px;
            font-weight: 700;
        }

        &__gauge {
            height: 10px;
            border-radius: 100px;
            background: rgba(233, 237, 241, 0.72);
            box-shadow: inset 0 1px 2px rgba(5, 59, 69, 0.08);
            overflow: hidden;
            margin: 18px 0 6px;

            > i {
                display: block;
                height: 100%;
                background: linear-gradient(90deg, #9af0ea, #22bdb8 56%, #034d5d);
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
            margin: 14px 0 0;
            color: var(--ink);
            font-size: 16px;
            line-height: 1.6;

            &.is-placeholder {
                color: var(--faint);
            }
        }

        &__drill {
            margin-top: auto;
            padding-top: 18px;
        }

        &__drillchip {
            display: inline-flex;
            cursor: pointer;
            border: 1px solid rgba(255, 255, 255, 0.72);
            border-radius: 10px;
            background: rgba(20, 184, 177, 0.12);
            color: var(--turq-ink);
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.65);
            padding: 12px 14px;
            font-size: 14px;
            font-weight: 800;

            &:focus-visible {
                outline: 3px solid rgba(20, 184, 177, 0.36);
                outline-offset: 2px;
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
            opacity: 0.24;
        }

        &.is-selected .cfa-node__halo {
            opacity: 0.18;
        }

        &__rest {
            transition:
                opacity 0.18s ease,
                stroke 0.18s ease;
        }

        &__glass,
        &__shine,
        &__inner-rim {
            pointer-events: none;
        }

        &__shine {
            fill: rgba(255, 255, 255, 0.64);
            mix-blend-mode: screen;
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

    .cfa-node__label {
        pointer-events: none;
        paint-order: stroke;
        fill: var(--ink);
        stroke: rgba(255, 255, 255, 0.96);
        stroke-width: 4.5px;
        stroke-linejoin: round;
        filter: drop-shadow(0 1px 2px rgba(5, 59, 69, 0.2));
    }

    .cfa-node__tlabel {
        font-family: var(--cfa-font-body);
        font-size: 14px;
        font-weight: 850;
    }

    .cfa-node__clabel {
        font-family: var(--cfa-font-heading);
        font-weight: 700;
        letter-spacing: 0.04em;
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

    @media (max-width: 720px) {
        .cfa-map {
            font-size: 17px;

            &__page {
                padding-top: 22px;
                padding-bottom: 70px;
                padding-right: 14px;
                padding-left: 14px;
            }

            &__hero {
                padding: 24px;
                border-radius: 30px;

                &::after {
                    border-radius: 29px;
                }
            }

            h1 {
                font-size: clamp(34px, 11vw, 42px);
            }

            &__lede {
                font-size: 17px;
            }

            &__howto {
                display: grid;
                gap: 10px;
                font-size: 14px;

                span {
                    align-items: flex-start;
                }
            }

            &__stage {
                gap: 14px;
            }

            &__mapbox,
            &__panel {
                border-radius: 22px;
            }

            &__mapbox {
                padding: 10px;
                overflow: hidden;
            }

            &__mapbox svg {
                width: 100%;
                height: clamp(500px, 136vw, 650px);
                min-height: 0;
                min-width: 0;
                touch-action: none;
            }

            &__legend {
                min-width: 0;
                padding-inline: 4px;
            }

            &__cap {
                min-width: 0;
                padding-inline: 4px;
            }

            &__panel {
                padding: 20px;
            }

            &__drillchip {
                width: 100%;
                min-height: 48px;
                justify-content: center;
                text-align: center;
            }
        }

        .cfa-node__tlabel {
            font-size: 17px;
            stroke-width: 5.4px;
        }

        .cfa-node__clabel {
            font-size: 27px;
        }

        .cfa-tip__name {
            font-size: 17px;
        }

        .cfa-tip__pct {
            font-size: 14px;
        }
    }
</style>
