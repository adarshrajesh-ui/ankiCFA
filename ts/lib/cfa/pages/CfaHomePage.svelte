<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->

<script lang="ts">
    import { bridgeCommand } from "@tslib/bridgecommand";

    import type { CfaHomePayload, TopicRow } from "$lib/cfa";
    import ProductShellNav from "$lib/cfa/ProductShellNav.svelte";

    import {
        buildConceptMap,
        masteryLabel,
        type ConceptNode,
        VIEW_H,
        VIEW_W,
    } from "./conceptmap";
    import {
        buildPriorityRisks,
        commandCenterLead,
        examCountdown,
        homeMetricChips,
        recommendedSessions,
        shortTopicName,
        syncChipLabel,
        syncSummary,
    } from "./home";

    /** The full CFA Home payload (scores, topics, exam countdown, AI and sync state). */
    export let data: CfaHomePayload;

    interface PinchStart {
        distance: number;
        scale: number;
        x: number;
        y: number;
        centerX: number;
        centerY: number;
    }

    $: countdown = examCountdown(data);
    $: lead = commandCenterLead(data);
    $: metricChips = homeMetricChips(data);
    $: syncLabel = syncChipLabel(data);
    $: syncLine = syncSummary(data);
    $: risks = buildPriorityRisks(data.topics);
    $: sessions = recommendedSessions(risks, data.topics);
    $: map = buildConceptMap(data.topics);

    let nearestMapId = "cfa";
    let hotMapId: string | null = null;
    let selectedMapId: string | null = null;
    let mapState = { x: 0, y: 0, scale: 1 };
    let pinchStart: PinchStart | null = null;
    let aiEnabled = data.aiEnabled;

    $: activeMapId = selectedMapId ?? hotMapId ?? nearestMapId;
    $: activeNode = map.nodes.find((n) => n.id === activeMapId) ?? map.center;
    $: activeTitle = mapActiveTitle(activeNode, selectedMapId === activeNode.id);
    $: activeDetail = mapDetail(activeNode, selectedMapId === activeNode.id);

    function go(cmd: string): void {
        bridgeCommand(cmd);
    }

    function toggleAi(): void {
        aiEnabled = !aiEnabled;
        bridgeCommand(`cfa:ai-toggle:${aiEnabled ? "1" : "0"}`);
    }

    function clamp(value: number, min: number, max: number): number {
        return Math.max(min, Math.min(max, value));
    }

    function shortNodeLabel(node: ConceptNode): string {
        if (node.kind === "cfa") {
            return "CFA";
        }
        return shortTopicName(node.full);
    }

    function topicForNode(node: ConceptNode): TopicRow | null {
        const topicName = node.kind === "sub" ? node.parent : node.full;
        return data.topics.find((topic) => topic.topic === topicName) ?? null;
    }

    function integer(n: number): string {
        return n.toLocaleString("en-US");
    }

    function mapPriority(node: ConceptNode): string {
        if (node.kind === "cfa") {
            return "Overall";
        }
        const topicName = node.kind === "sub" ? node.parent : node.full;
        return (
            risks.find((risk) => risk.topic === topicName)?.label ??
            masteryLabel(node.mastery)
        );
    }

    function mapEvidence(node: ConceptNode): string {
        if (node.kind === "cfa") {
            return `${integer(data.caption.gradedReviews)} graded reviews across ${data.caption.topicsCovered}/${data.caption.topicsTotal} topics`;
        }
        const topic = topicForNode(node);
        if (!topic) {
            return "Topic evidence unavailable";
        }
        return `${integer(topic.gradedReviews)} graded reviews · ${integer(topic.reviewedCards)} reviewed cards`;
    }

    function mapDetail(node: ConceptNode, selected: boolean): string {
        const dependency =
            node.kind === "sub" && node.parent
                ? `inherits ${node.parent} section evidence`
                : "dependency graph pending";
        if (selected) {
            const newPart = node.newCount > 0 ? ` · ${integer(node.newCount)} new` : "";
            return `${integer(node.dueCount)} cards due${newPart}. Open priority study to work this area.`;
        }
        return `Priority: ${mapPriority(node)} · ${mapEvidence(node)} · ${dependency}.`;
    }

    function mapActiveTitle(node: ConceptNode, selected: boolean): string {
        if (selected) {
            return `Cards Due: ${shortNodeLabel(node)}`;
        }
        if (node.kind === "cfa") {
            return "Nearest: CFA";
        }
        return node.full;
    }

    function updateNearestConcept(): void {
        let nearest = map.nodes[0] ?? map.center;
        let nearestDistance = Infinity;
        const cx = VIEW_W / 2;
        const cy = VIEW_H / 2;

        for (const node of map.nodes) {
            const x = node.x * mapState.scale + mapState.x;
            const y = node.y * mapState.scale + mapState.y;
            const distance = Math.hypot(x - cx, y - cy);
            if (distance < nearestDistance) {
                nearest = node;
                nearestDistance = distance;
            }
        }
        nearestMapId = nearest.id;
    }

    function onMapWheel(event: WheelEvent): void {
        event.preventDefault();
        selectedMapId = null;
        mapState = {
            x: clamp(mapState.x - event.deltaX * 0.38, -96, 96),
            y: clamp(mapState.y - event.deltaY * 0.3, -78, 78),
            scale: clamp(mapState.scale + Math.abs(event.deltaY) * 0.0009, 1, 1.38),
        };
        updateNearestConcept();
    }

    function onMapLeave(): void {
        hotMapId = null;
        mapState = { ...mapState, scale: Math.max(1, mapState.scale - 0.06) };
        updateNearestConcept();
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
        selectedMapId = null;
        const a = event.touches[0];
        const b = event.touches[1];
        const distance = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
        const centerX = (a.clientX + b.clientX) / 2;
        const centerY = (a.clientY + b.clientY) / 2;
        const ratio = distance / Math.max(1, pinchStart.distance);
        mapState = {
            scale: clamp(pinchStart.scale * ratio, 0.74, 1.55),
            x: clamp(pinchStart.x + (centerX - pinchStart.centerX) * 0.42, -112, 112),
            y: clamp(pinchStart.y + (centerY - pinchStart.centerY) * 0.42, -88, 88),
        };
        updateNearestConcept();
    }

    function onTouchEnd(event: TouchEvent): void {
        if (event.touches.length < 2) {
            pinchStart = null;
        }
    }

    function selectNode(node: ConceptNode): void {
        selectedMapId = selectedMapId === node.id ? null : node.id;
        nearestMapId = node.id;
    }

    function onNodeKey(event: KeyboardEvent, node: ConceptNode): void {
        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            selectNode(node);
        } else if (event.key === "Escape") {
            selectedMapId = null;
        }
    }

    function nodeRadius(node: ConceptNode): number {
        return node.kind === "sub" && activeMapId === node.id ? node.r * 1.55 : node.r;
    }
</script>

<div class="cfa-app cfa-home">
    <main class="cfa-home__page">
        <ProductShellNav
            active="home"
            subtitle="CFA Level II"
            syncStatus={syncLabel}
            ariaLabel="CFA sections"
            on:navigate={(event) => go(event.detail)}
        />

        <section class="cfa-home__hero">
            <div class="cfa-home__eyebrow">Home · CFA Command Center</div>
            <h1>Today’s work</h1>
            <p class="cfa-home__lede">{lead}</p>
            <div class="cfa-home__actions" aria-label="Primary Home actions">
                <button
                    type="button"
                    class="cfa-home__btn primary"
                    on:click={() => go("cfa:priority")}
                >
                    Begin priority session
                </button>
                <button
                    type="button"
                    class="cfa-home__btn secondary"
                    on:click={() => go("cfa:conceptmap")}
                >
                    Open Concept Map
                </button>
                <button
                    type="button"
                    class="cfa-home__btn secondary"
                    on:click={() => go("cfa:readiness")}
                >
                    View weak areas
                </button>
            </div>
            <div class="cfa-home__meta-row" aria-label="Current CFA metrics">
                {#each metricChips as chip}
                    <span class="cfa-home__meta-chip">{chip}</span>
                {/each}
                <button
                    type="button"
                    class="cfa-home__ai-toggle"
                    class:is-on={aiEnabled}
                    aria-pressed={aiEnabled}
                    on:click={toggleAi}
                >
                    <span>{aiEnabled ? "AI On" : "No AI"}</span>
                    <small>
                        {aiEnabled ? "Semantic grading enabled" : "Deterministic only"}
                    </small>
                </button>
            </div>
            <div class="cfa-home__countdown" data-tone={countdown.tone}>
                <b>{countdown.headline}</b>
                <span>{countdown.sub}</span>
            </div>
            <button
                type="button"
                class="cfa-home__sync-status"
                data-tone={data.sync.tone}
                aria-label="{data.sync.status}: {syncLine} — {data.sync.actionLabel}"
                title={syncLine}
                on:click={() => go("cfa:sync")}
            >
                <span class="cfa-home__sync-dot" aria-hidden="true"></span>
                <span class="cfa-home__sync-text">
                    <b>{data.sync.status}</b>
                    <small>{syncLine}</small>
                </span>
                <span class="cfa-home__sync-action">{data.sync.actionLabel}</span>
            </button>
        </section>

        <section class="cfa-home__grid cfa-home__grid--main">
            <article class="cfa-home__glass-card">
                <div class="cfa-home__card-title">
                    <div>
                        <div class="cfa-home__eyebrow">Priority risk</div>
                        <h2>Heavy topics holding readiness down</h2>
                    </div>
                    <span class="cfa-home__status-pill">Exam-weighted</span>
                </div>
                <div class="cfa-home__risk-list">
                    {#each risks as risk (risk.topic)}
                        <button
                            type="button"
                            class="cfa-home__risk"
                            on:click={() => go("cfa:readiness")}
                        >
                            <span>
                                <strong>{risk.topic}</strong>
                                <small>{risk.detail}</small>
                            </span>
                            <span class="cfa-home__score" data-tone={risk.tone}>
                                {risk.label}
                            </span>
                        </button>
                    {/each}
                </div>
            </article>

            <article class="cfa-home__glass-card cfa-home__map-card">
                <div class="cfa-home__card-title">
                    <div>
                        <div class="cfa-home__eyebrow">Concept Map preview</div>
                        <h2>Mastery shape</h2>
                    </div>
                    <button
                        type="button"
                        class="cfa-home__status-pill as-button"
                        on:click={() => go("cfa:conceptmap")}
                    >
                        Live graph
                    </button>
                </div>
                <div
                    class="cfa-home__map-mini"
                    role="group"
                    aria-label="Interactive Concept Map preview"
                    on:wheel={onMapWheel}
                    on:mouseleave={onMapLeave}
                    on:touchstart={onTouchStart}
                    on:touchmove={onTouchMove}
                    on:touchend={onTouchEnd}
                >
                    <svg
                        viewBox="0 0 {VIEW_W} {VIEW_H}"
                        role="group"
                        aria-label="Interactive CFA concept map preview nodes"
                    >
                        <defs>
                            <radialGradient
                                id="home-map-node-gloss"
                                cx="30%"
                                cy="22%"
                                r="78%"
                            >
                                <stop
                                    offset="0"
                                    stop-color="#ffffff"
                                    stop-opacity="0.95"
                                />
                                <stop
                                    offset="0.44"
                                    stop-color="#7edbd6"
                                    stop-opacity="0.62"
                                />
                                <stop
                                    offset="1"
                                    stop-color="#0e9c97"
                                    stop-opacity="0.82"
                                />
                            </radialGradient>
                            <filter
                                id="home-map-shadow"
                                x="-40%"
                                y="-40%"
                                width="180%"
                                height="180%"
                            >
                                <feDropShadow
                                    dx="0"
                                    dy="12"
                                    stdDeviation="10"
                                    flood-color="#053b45"
                                    flood-opacity="0.16"
                                />
                            </filter>
                        </defs>
                        <g
                            transform="translate({mapState.x} {mapState.y}) scale({mapState.scale})"
                        >
                            <g fill="none" stroke-linecap="round">
                                {#each map.edges as edge}
                                    <line
                                        x1={edge.x1}
                                        y1={edge.y1}
                                        x2={edge.x2}
                                        y2={edge.y2}
                                        stroke={edge.width > 1.5
                                            ? "rgba(20,184,177,.32)"
                                            : "rgba(5,59,69,.14)"}
                                        stroke-width={edge.width}
                                    />
                                {/each}
                            </g>
                            {#each map.nodes as node (node.id)}
                                {@const on = activeMapId === node.id}
                                <g
                                    class="cfa-home__map-node"
                                    class:is-active={on}
                                    class:is-sub={node.kind === "sub"}
                                    role="button"
                                    tabindex="0"
                                    aria-label="{node.full}: {mapDetail(
                                        node,
                                        selectedMapId === node.id,
                                    )}"
                                    on:mouseenter={() => (hotMapId = node.id)}
                                    on:mouseleave={() => (hotMapId = null)}
                                    on:focus={() => (hotMapId = node.id)}
                                    on:blur={() => (hotMapId = null)}
                                    on:click={() => selectNode(node)}
                                    on:keydown={(event) => onNodeKey(event, node)}
                                >
                                    <circle
                                        class="cfa-home__orb-fill"
                                        cx={node.x}
                                        cy={node.y}
                                        r={nodeRadius(node)}
                                        fill={node.fill}
                                        filter="url(#home-map-shadow)"
                                    />
                                    <circle
                                        class="cfa-home__orb-gloss"
                                        cx={node.x}
                                        cy={node.y}
                                        r={nodeRadius(node)}
                                        fill="url(#home-map-node-gloss)"
                                    />
                                    {#if node.kind === "cfa" || node.kind === "topic" || on}
                                        <text
                                            class="cfa-home__map-label"
                                            x={node.x}
                                            y={node.y + (node.kind === "cfa" ? 6 : 4)}
                                            text-anchor="middle"
                                        >
                                            {shortNodeLabel(node)}
                                        </text>
                                    {/if}
                                </g>
                            {/each}
                        </g>
                    </svg>
                </div>
                <div class="cfa-home__hover-note">
                    <b>{activeTitle}</b>
                    {activeDetail}
                </div>
                <p class="cfa-home__tiny">
                    Scroll or trackpad over the map to move through the field; pinch
                    zoom is supported on touch screens.
                </p>
            </article>
        </section>

        <section class="cfa-home__grid cfa-home__grid--sessions">
            {#each sessions as session (session.eyebrow)}
                <article class="cfa-home__glass-card cfa-home__session-card">
                    <div class="cfa-home__eyebrow">{session.eyebrow}</div>
                    <h3>{session.title}</h3>
                    <p>{session.detail}</p>
                    <div class="cfa-home__impact" aria-hidden="true">
                        <i style="width: {session.impactPct}%"></i>
                    </div>
                    <span class="cfa-home__tiny">{session.meta}</span>
                </article>
            {/each}
        </section>
    </main>
</div>

<style lang="scss">
    @use "../tokens" as cfa;

    .cfa-home {
        --ink: #122b46;
        --muted: #4d5c6d;
        --faint: #68707d;
        --line: rgba(255, 255, 255, 0.72);
        --pearl: #fbfaf5;
        --turq: #14b8b1;
        --turq-deep: #0e9c97;
        --turq-ink: #064a54;
        --turq-soft: #e4f6f5;
        --deep: #053b45;
        --red: #b42318;
        --green: #15803d;
        --glass: rgba(255, 255, 255, 0.62);
        --glass-strong: rgba(255, 255, 255, 0.78);
        --shadow: 0 28px 90px rgba(5, 59, 69, 0.16);

        box-sizing: border-box;
        width: 100%;
        min-height: 100vh;
        color: var(--ink);
        font-family: var(--cfa-font-body);
        font-size: 18.75px;
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
                circle at 55% 70%,
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

        button {
            font: inherit;
        }

        *,
        *::before,
        *::after {
            box-sizing: border-box;
        }

        &__page {
            position: relative;
            z-index: 1;
            max-width: 1525px;
            margin: 0 auto;
            padding: 35px 28px 100px;
        }

        &__status-pill {
            display: inline-flex;
            align-items: center;
            gap: 9px;
            border: 1px solid cfa.$cfa-control-border;
            background: rgba(228, 246, 245, 0.58);
            color: var(--turq-ink);
            border-radius: 999px;
            padding: 10px 15px;
            font-size: 15px;
            font-weight: 700;
            white-space: nowrap;
        }

        &__status-pill.as-button {
            cursor: pointer;

            &:hover {
                background: rgba(228, 246, 245, 0.8);
            }
        }

        &__hero,
        &__glass-card {
            border: 1px solid var(--line);
            box-shadow: var(--shadow);
            backdrop-filter: blur(26px) saturate(1.18);
            -webkit-backdrop-filter: blur(26px) saturate(1.18);
        }

        &__hero {
            position: relative;
            overflow: hidden;
            margin-top: 33px;
            border-radius: 40px;
            background:
                linear-gradient(
                    135deg,
                    rgba(255, 255, 255, 0.84),
                    rgba(255, 255, 255, 0.48)
                ),
                radial-gradient(
                    circle at 75% 20%,
                    rgba(20, 184, 177, 0.2),
                    transparent 24rem
                );
            padding: 35px;

            &::after {
                content: "";
                position: absolute;
                inset: 1px;
                border-radius: 39px;
                pointer-events: none;
                background: linear-gradient(
                    120deg,
                    rgba(255, 255, 255, 0.68),
                    transparent 30%,
                    rgba(255, 255, 255, 0.16)
                );
                mask: linear-gradient(#000, transparent 70%);
            }
        }

        &__eyebrow {
            font-size: 14px;
            font-weight: 800;
            letter-spacing: 0.15em;
            text-transform: uppercase;
            color: var(--turq-ink);
        }

        h1,
        h2,
        h3 {
            margin: 0;
            font-family: var(--cfa-font-heading);
            color: var(--ink);
        }

        h1 {
            font-size: 55px;
            line-height: 1.02;
            letter-spacing: -0.035em;
        }

        h2 {
            font-size: 29px;
            line-height: 1.12;
        }

        h3 {
            font-size: 22px;
            line-height: 1.2;
        }

        p {
            margin: 0;
            color: var(--muted);
        }

        &__lede {
            margin-top: 13px;
            max-width: 900px;
            font-size: 20px;
        }

        &__actions {
            display: flex;
            gap: 13px;
            flex-wrap: wrap;
            margin-top: 28px;
        }

        &__btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            border-radius: 18px;
            padding: 15px 19px;
            font-weight: 800;
            font-size: 16px;
            text-decoration: none;
            border: 1px solid rgba(255, 255, 255, 0.72);
            box-shadow:
                inset 0 1px 0 rgba(255, 255, 255, 0.78),
                0 16px 44px rgba(5, 59, 69, 0.1);

            &.primary {
                background: linear-gradient(135deg, #7edbd6, #14b8b1, #0e9c97);
                color: #fff;
                border-color: rgba(255, 255, 255, 0.84);
            }

            &.secondary {
                background: rgba(255, 255, 255, 0.58);
                color: var(--turq-ink);
                border: 1px solid cfa.$cfa-control-border;
            }

            &:focus-visible {
                outline: 3px solid rgba(20, 184, 177, 0.36);
                outline-offset: 2px;
            }
        }

        &__meta-row {
            display: flex;
            gap: 13px;
            flex-wrap: wrap;
            margin-top: 15px;
        }

        &__meta-chip {
            border: 1px solid rgba(255, 255, 255, 0.62);
            background: rgba(255, 255, 255, 0.46);
            border-radius: 15px;
            padding: 11px 14px;
            font-size: 15px;
            font-weight: 700;
            color: var(--muted);
        }

        &__ai-toggle {
            display: inline-grid;
            gap: 1px;
            cursor: pointer;
            border: 1px solid rgba(180, 35, 24, 0.3);
            background: rgba(255, 255, 255, 0.5);
            border-radius: 15px;
            padding: 9px 14px;
            color: var(--red);
            text-align: left;

            span {
                font-size: 15px;
                font-weight: 800;
            }

            small {
                color: var(--muted);
                font-size: 12px;
                font-weight: 700;
            }

            &.is-on {
                border-color: rgba(20, 184, 177, 0.42);
                background: rgba(228, 246, 245, 0.72);
                color: var(--turq-ink);
            }

            &:focus-visible {
                outline: 3px solid rgba(20, 184, 177, 0.36);
                outline-offset: 2px;
            }
        }

        &__countdown {
            display: inline-flex;
            gap: 8px;
            flex-wrap: wrap;
            align-items: center;
            margin-top: 18px;
            border: 1px solid rgba(255, 255, 255, 0.62);
            background: rgba(255, 255, 255, 0.38);
            border-radius: 999px;
            padding: 10px 14px;
            font-size: 14px;
            color: var(--muted);

            b {
                color: var(--turq-ink);
            }

            &[data-tone="warn"] b {
                color: #8a4a00;
            }
        }

        &__sync-status {
            display: flex;
            gap: 12px;
            align-items: center;
            width: 100%;
            margin-top: 12px;
            cursor: pointer;
            text-align: left;
            border: 1px solid rgba(255, 255, 255, 0.62);
            background: rgba(255, 255, 255, 0.42);
            border-radius: 16px;
            padding: 12px 15px;

            &:hover {
                border-color: rgba(20, 184, 177, 0.38);
                transform: translateY(-1px);
            }

            &:focus-visible {
                outline: 3px solid rgba(20, 184, 177, 0.36);
                outline-offset: 2px;
            }
        }

        &__sync-dot {
            width: 10px;
            height: 10px;
            flex: 0 0 auto;
            border-radius: 999px;
            background: var(--faint);

            .cfa-home__sync-status[data-tone="pass"] & {
                background: var(--green);
            }

            .cfa-home__sync-status[data-tone="warn"] & {
                background: #c2790a;
            }
        }

        &__sync-text {
            display: grid;
            gap: 2px;
            min-width: 0;
            flex: 1 1 auto;

            b {
                font-size: 15px;
                color: var(--turq-ink);
            }

            small {
                font-size: 14px;
                color: var(--muted);
                overflow-wrap: anywhere;
            }
        }

        &__sync-action {
            flex: 0 0 auto;
            font-size: 14px;
            font-weight: 800;
            color: var(--turq-ink);
            white-space: nowrap;
        }

        &__grid {
            display: grid;
            gap: 20px;
            margin-top: 23px;
        }

        &__grid--main {
            grid-template-columns: minmax(0, 1.15fr) minmax(0, 0.85fr);
        }

        &__grid--sessions {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        &__glass-card {
            min-width: 0;
            border-radius: 28px;
            padding: 23px;
            background: var(--glass);
            box-shadow:
                inset 0 1px 0 rgba(255, 255, 255, 0.78),
                0 20px 70px rgba(5, 59, 69, 0.12);
        }

        &__card-title {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 15px;
            margin-bottom: 15px;
        }

        &__risk-list {
            display: grid;
            gap: 10px;
        }

        &__risk {
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            gap: 15px;
            align-items: center;
            cursor: pointer;
            text-align: left;
            border: 1px solid rgba(255, 255, 255, 0.62);
            background: rgba(255, 255, 255, 0.44);
            border-radius: 20px;
            padding: 15px;

            strong {
                display: block;
                color: #0b2f38;
            }

            small {
                display: block;
                color: var(--muted);
                font-size: 15px;
                margin-top: 3px;
            }

            &:hover {
                border-color: rgba(20, 184, 177, 0.38);
                transform: translateY(-1px);
            }
        }

        &__score {
            font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
            font-size: 15px;
            font-weight: 700;
            color: var(--red);

            &[data-tone="maintain"] {
                color: var(--green);
            }

            &[data-tone="watch"] {
                color: #8a4a00;
            }
        }

        &__map-mini {
            position: relative;
            min-height: clamp(300px, 32vw, 350px);
            border-radius: 25px;
            border: 1px solid rgba(255, 255, 255, 0.68);
            background:
                radial-gradient(
                    circle at 50% 45%,
                    rgba(20, 184, 177, 0.1),
                    transparent 10rem
                ),
                linear-gradient(
                    135deg,
                    rgba(255, 255, 255, 0.72),
                    rgba(255, 255, 255, 0.3)
                );
            overflow: hidden;
            min-width: 0;
            cursor: grab;
            touch-action: none;

            &:active {
                cursor: grabbing;
            }

            svg {
                display: block;
                width: 100%;
                height: clamp(300px, 32vw, 350px);
            }
        }

        &__map-node {
            cursor: pointer;

            &:focus-visible {
                outline: none;
            }

            &:focus-visible .cfa-home__orb-fill {
                stroke: var(--turq-deep);
                stroke-width: 5px;
            }
        }

        &__orb-fill {
            stroke: rgba(255, 255, 255, 0.82);
            stroke-width: 2px;
        }

        &__orb-gloss {
            opacity: 0.48;
            pointer-events: none;
        }

        &__map-node.is-active {
            .cfa-home__orb-fill {
                stroke: rgba(20, 184, 177, 0.7);
                stroke-width: 5px;
            }

            .cfa-home__orb-gloss {
                opacity: 0.72;
            }
        }

        &__map-label {
            pointer-events: none;
            fill: #fff;
            font-family: var(--cfa-font-body);
            font-size: 18px;
            font-weight: 800;
            line-height: 1.05;
            text-shadow: 0 1px 10px rgba(5, 59, 69, 0.34);

            .cfa-home__map-node.is-sub & {
                font-size: 13px;
            }
        }

        &__hover-note {
            margin-top: 13px;
            border: 1px solid rgba(255, 255, 255, 0.72);
            background: rgba(255, 255, 255, 0.56);
            border-radius: 18px;
            padding: 11px 13px;
            font-size: 15px;
            color: var(--muted);
            box-shadow: 0 14px 34px rgba(5, 59, 69, 0.08);
            overflow-wrap: anywhere;

            b {
                display: block;
                color: var(--turq-ink);
                font-size: 15px;
                margin-bottom: 3px;
            }
        }

        &__tiny {
            font-size: 15px;
            color: var(--faint);
        }

        &__session-card {
            display: grid;
            gap: 10px;
        }

        &__impact {
            height: 7px;
            border-radius: 999px;
            background: rgba(233, 237, 241, 0.72);
            overflow: hidden;

            i {
                display: block;
                height: 100%;
                background: linear-gradient(90deg, #7edbd6, #0e9c97);
            }
        }

        @media (max-width: 940px) {
            &__grid--main,
            &__grid--sessions {
                grid-template-columns: minmax(0, 1fr);
            }
        }

        @media (max-width: 620px) {
            font-size: 16px;

            &__page {
                width: 100%;
                padding: 14px 12px 64px;
            }

            h1 {
                font-size: clamp(34px, 12vw, 42px);
                line-height: 1.04;
                letter-spacing: -0.04em;
            }

            h2 {
                font-size: 24px;
            }

            h3 {
                font-size: 20px;
            }

            &__eyebrow {
                font-size: 12px;
                letter-spacing: 0.12em;
            }

            &__hero {
                margin-top: 16px;
                border-radius: 30px;
                padding: 22px;
            }

            &__hero::after {
                border-radius: 29px;
            }

            &__lede {
                font-size: 16px;
            }

            &__actions,
            &__meta-row {
                display: grid;
                grid-template-columns: minmax(0, 1fr);
                gap: 10px;
            }

            &__actions {
                margin-top: 22px;
            }

            &__btn {
                width: 100%;
                min-height: 48px;
                border-radius: 16px;
                padding: 13px 16px;
            }

            &__meta-chip,
            &__countdown {
                width: 100%;
                border-radius: 16px;
            }

            &__countdown {
                justify-content: flex-start;
            }

            &__sync-status {
                flex-wrap: wrap;
                border-radius: 16px;
            }

            &__sync-action {
                margin-left: 22px;
            }

            &__grid {
                gap: 14px;
                margin-top: 16px;
            }

            &__glass-card {
                border-radius: 24px;
                padding: 18px;
            }

            &__card-title {
                display: grid;
                grid-template-columns: minmax(0, 1fr);
                gap: 10px;

                .cfa-home__status-pill {
                    justify-self: start;
                }
            }

            &__risk {
                grid-template-columns: minmax(0, 1fr);
                gap: 10px;
                min-height: 64px;
                padding: 14px;
            }

            &__score {
                justify-self: start;
            }

            &__map-mini {
                min-height: 280px;
                border-radius: 20px;
                touch-action: pan-y pinch-zoom;

                svg {
                    height: 280px;
                }
            }

            &__hover-note {
                border-radius: 16px;
            }

            &__session-card {
                gap: 8px;
            }
        }
    }
</style>
