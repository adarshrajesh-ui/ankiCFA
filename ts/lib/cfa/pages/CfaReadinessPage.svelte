<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->

<script lang="ts">
    import { bridgeCommand } from "@tslib/bridgecommand";

    import type { ExamReadinessPayload } from "$lib/cfa";
    import ProductShellNav from "$lib/cfa/ProductShellNav.svelte";
    import {
        actionPlan,
        bandSub,
        bandValue,
        buildReadinessRisks,
        captionText,
        confidenceChips,
        integer,
        noRecallYet,
        pct,
        readinessLead,
        readinessScoreCards,
        retentionWatchlist,
        syncChipLabel,
        topicRows,
    } from "./readiness";

    /** The full Exam Readiness payload (same shape the backend builds). */
    export let data: ExamReadinessPayload;

    function go(cmd: string): void {
        bridgeCommand(cmd);
    }

    $: scoreCards = readinessScoreCards(data);
    $: rows = topicRows(data.topics);
    $: awaitingRecall = noRecallYet(rows);
    $: lead = readinessLead(data);
    $: syncLabel = syncChipLabel(data);
    $: risks = buildReadinessRisks(data.topics);
    $: chips = confidenceChips(data.topics);
    $: watchlist = retentionWatchlist(data.topics);
    $: plan = actionPlan(risks);
</script>

<div class="cfa-app cfa-readiness">
    <main class="cfa-readiness__page">
        <ProductShellNav
            active="readiness"
            subtitle={data.deckName}
            syncStatus={syncLabel}
            ariaLabel="CFA Readiness sections"
            on:navigate={(event) => go(event.detail)}
        />

        <section class="cfa-readiness__hero cfa-hero">
            <div class="cfa-readiness__hero-grid">
                <div>
                    <div class="cfa-readiness__eyebrow">
                        Readiness - Exam Risk Console
                    </div>
                    <h1>Are you ready to pass?</h1>
                    <p class="cfa-readiness__lede">{lead}</p>
                    <div
                        class="cfa-readiness__hero-actions"
                        aria-label="Readiness actions"
                    >
                        <button
                            type="button"
                            class="cfa-readiness__btn primary"
                            on:click={() => go("cfa:risk-session")}
                        >
                            Start risk-reduction session
                        </button>
                        <button
                            type="button"
                            class="cfa-readiness__btn secondary"
                            on:click={() => go("cfa:readiness-drill")}
                        >
                            Run readiness drill
                        </button>
                        <button
                            type="button"
                            class="cfa-readiness__btn ghost unavailable"
                            disabled
                            aria-describedby="readiness-mock-unavailable"
                        >
                            Mock review unavailable
                        </button>
                    </div>
                    <p
                        id="readiness-mock-unavailable"
                        class="cfa-readiness__action-note"
                    >
                        Latest mock review needs imported mock results. Use the
                        readiness drill for now.
                    </p>
                    <div
                        class="cfa-readiness__metric-row"
                        aria-label="Readiness evidence counts"
                    >
                        <div class="cfa-readiness__metric">
                            <strong>{integer(data.caption.gradedReviews)}</strong>
                            <span>graded reviews</span>
                        </div>
                        <div class="cfa-readiness__metric">
                            <strong>{integer(data.caption.firstExposures)}</strong>
                            <span>first exposures</span>
                        </div>
                        <div class="cfa-readiness__metric">
                            <strong>
                                {data.caption.topicsCovered}/{data.caption.topicsTotal}
                            </strong>
                            <span>topics covered</span>
                        </div>
                    </div>
                </div>

                <aside
                    class="cfa-readiness__score-card"
                    aria-label="Separate readiness evidence scores"
                >
                    <div>
                        <div class="cfa-readiness__eyebrow">Three separate scores</div>
                        <h2>No blended number.</h2>
                        <p class="cfa-readiness__score-intro">
                            Memory, performance, and readiness stay separate so the
                            learner can see whether the risk is recall decay, exam
                            execution, or projected pass confidence.
                        </p>
                    </div>
                    <div class="cfa-readiness__score-stack">
                        {#each scoreCards as card (card.name)}
                            <article
                                class="cfa-readiness__score-mini cfa-stat"
                                class:abstain={card.band.abstain}
                            >
                                <div class="cfa-readiness__score-head">
                                    <strong class="cfa-stat__label">{card.name}</strong>
                                    <b>{bandValue(card.band)}</b>
                                </div>
                                <small>{card.meaning}</small>
                                <span class="cfa-readiness__score-sub">
                                    {bandSub(card.band, data.caption)}
                                </span>
                            </article>
                        {/each}
                        <article class="cfa-readiness__score-mini abstain">
                            <div class="cfa-readiness__score-head">
                                <strong>Abstain rule</strong>
                                <b>No score</b>
                            </div>
                            <small>
                                If graded evidence or topic coverage is thin, show the
                                missing reason instead of a fake number.
                            </small>
                        </article>
                    </div>
                    <div class="cfa-readiness__confidence">
                        {#each chips as chip}
                            <span
                                class="cfa-readiness__chip"
                                class:turq={chip.tone === "turq"}
                                class:warn={chip.tone === "warn"}
                            >
                                {chip.label}
                            </span>
                        {/each}
                    </div>
                    <p class="cfa-readiness__score-note">
                        Scores are based on stored reviews, first exposures, graded
                        answers, and topic coverage.
                    </p>
                </aside>
            </div>
        </section>

        <section class="cfa-readiness__grid cfa-readiness__console-grid">
            <div class="cfa-readiness__glass-card">
                <div class="cfa-readiness__card-title">
                    <div>
                        <div class="cfa-readiness__eyebrow">Major risk drivers</div>
                        <h2>The 3 issues most likely to change the result</h2>
                    </div>
                    <span class="cfa-readiness__status-pill">Exam-weighted</span>
                </div>
                <div class="cfa-readiness__risk-list">
                    {#if risks.length === 0}
                        <div class="cfa-readiness__risk">
                            <div>
                                <strong>No topic evidence yet</strong>
                                <small>
                                    Start studying to populate exam-weighted risks from
                                    the existing readiness engine.
                                </small>
                            </div>
                            <span class="cfa-readiness__risk-score high">No score</span>
                        </div>
                    {:else}
                        {#each risks as risk}
                            <div class="cfa-readiness__risk">
                                <div>
                                    <strong>{risk.title}</strong>
                                    <small>{risk.detail}</small>
                                </div>
                                <span
                                    class="cfa-readiness__risk-score"
                                    class:high={risk.tone === "high"}
                                    class:med={risk.tone === "med"}
                                    class:keep={risk.tone === "keep"}
                                >
                                    {risk.label}
                                </span>
                            </div>
                        {/each}
                    {/if}
                </div>
            </div>

            <div class="cfa-readiness__glass-card">
                <div class="cfa-readiness__card-title">
                    <div>
                        <div class="cfa-readiness__eyebrow">Topic readiness</div>
                        <h2>Coverage and recall evidence</h2>
                    </div>
                    <span class="cfa-readiness__status-pill">
                        {pct(data.caption.coveragePct)} exam covered
                    </span>
                </div>
                <p class="cfa-readiness__coverage-copy">
                    Topic evidence exposes weight, reviewed coverage, graded proof, and
                    recall range so high-weight gaps are visible before the learner
                    trusts the readiness call.
                </p>
                {#if awaitingRecall}
                    <p class="cfa-readiness__table-hint">
                        No reviews yet - per-topic recall appears here after you study.
                        The map below lists every exam area and its weight.
                    </p>
                {/if}
                <div class="cfa-readiness__topic-list cfa-table">
                    <div class="cfa-readiness__topic header">
                        <span>Topic</span>
                        <span>Weight</span>
                        <span>Reviewed / graded</span>
                        <span>Recall range</span>
                        <span>Range</span>
                    </div>
                    {#each rows as row (row.topic)}
                        <div class="cfa-readiness__topic">
                            <div class="cfa-readiness__topic-name">
                                <strong>{row.topic}</strong>
                                <span>{row.sub}</span>
                            </div>
                            <span class="cfa-readiness__topic-stat" data-label="Weight">
                                {row.weight}
                            </span>
                            <span
                                class="cfa-readiness__topic-stat"
                                data-label="Reviewed / graded"
                            >
                                {row.reviewedGraded}
                            </span>
                            <div
                                class="cfa-readiness__bar"
                                data-label="Recall signal"
                                aria-hidden="true"
                            >
                                <i
                                    class:warn={row.barTone === "warn"}
                                    class:danger={row.barTone === "danger"}
                                    style={`width: ${row.barWidth}%`}
                                ></i>
                            </div>
                            <span
                                class="cfa-readiness__pct"
                                data-label="Range"
                                class:is-warn={row.recallTone === "warn"}
                                class:is-muted={row.recallTone === "muted"}
                            >
                                {row.recall}
                            </span>
                        </div>
                    {/each}
                </div>
            </div>
        </section>

        <section class="cfa-readiness__next-panel">
            <div class="cfa-readiness__card-title">
                <div>
                    <div class="cfa-readiness__eyebrow">What to do next</div>
                    <h2>Turn readiness into today's plan</h2>
                </div>
                <span class="cfa-readiness__status-pill">35 minutes</span>
            </div>
            <p>
                Do not start a broad review. Spend one focused session reducing the
                risks that move pass likelihood fastest.
            </p>
            <div
                class="cfa-readiness__retention-watch"
                aria-label="Forgetting watchlist"
            >
                <div class="cfa-readiness__retention-summary">
                    <div class="cfa-readiness__eyebrow">Forgetting watchlist</div>
                    <strong>{watchlist.length || 0} topics</strong>
                    <span>
                        Topic-level signal from current recall ranges. Use it to refresh
                        areas most likely to weaken before exam day.
                    </span>
                    <div class="cfa-readiness__next-actions compact">
                        <button
                            type="button"
                            class="cfa-readiness__btn primary small"
                            on:click={() => go("cfa:retention-queue")}
                        >
                            Pull retention queue
                        </button>
                    </div>
                    <small class="cfa-readiness__flow-note">
                        Opens the existing deadline-aware weakest-first review flow.
                    </small>
                </div>
                <div class="cfa-readiness__forget-list">
                    {#if watchlist.length === 0}
                        <div class="cfa-readiness__forget-item">
                            <div>
                                <b>No retention evidence yet</b>
                                <span>
                                    Review cards to populate the forgetting watchlist.
                                </span>
                            </div>
                            <em>No score</em>
                        </div>
                    {:else}
                        {#each watchlist as item}
                            <div class="cfa-readiness__forget-item">
                                <div>
                                    <b>{item.title}</b>
                                    <span>{item.detail}</span>
                                </div>
                                <em>{item.risk}</em>
                            </div>
                        {/each}
                    {/if}
                </div>
            </div>
            <div class="cfa-readiness__action-plan">
                {#each plan as item}
                    <article class="cfa-readiness__action">
                        <div>
                            <b>{item.title}</b>
                            <span>{item.detail}</span>
                            <small>{item.routeNote}</small>
                        </div>
                        <div class="cfa-readiness__action-footer">
                            <span class="cfa-readiness__time">{item.time}</span>
                            <button
                                type="button"
                                class="cfa-readiness__btn secondary small"
                                aria-label={item.ariaLabel}
                                on:click={() => go(item.cmd)}
                            >
                                {item.cta}
                            </button>
                        </div>
                    </article>
                {/each}
            </div>
        </section>

        <div class="cfa-readiness__footer-note">
            <p>
                <strong>Evidence summary:</strong>
                {captionText(data.caption)}
            </p>
            <button
                type="button"
                class="cfa-readiness__btn secondary small"
                on:click={() => go("cfa:conceptmap")}
            >
                Review coverage map
            </button>
        </div>
    </main>
</div>

<style lang="scss">
    .cfa-readiness {
        --ink: #122b46;
        --muted: #4d5c6d;
        --faint: #68707d;
        --line: rgba(255, 255, 255, 0.72);
        --pearl: #fbfaf5;
        --turq: #14b8b1;
        --turq-deep: #0e9c97;
        --turq-ink: #064a54;
        --red: #b42318;
        --amber: #7a4b08;
        --green: #15803d;
        --glass: rgba(255, 255, 255, 0.62);
        --shadow: 0 28px 90px rgba(5, 59, 69, 0.16);

        min-height: 100vh;
        overflow-x: hidden;
        color: var(--ink);
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
        font-family: var(--cfa-font-body);
        font-size: 18px;
        line-height: 1.5;
        -webkit-font-smoothing: antialiased;

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

        h1,
        h2 {
            margin: 0;
            color: #0b2f38;
            font-family: var(--cfa-font-heading);
        }

        h1 {
            font-size: clamp(38px, 5vw, 66px);
            line-height: 1.01;
            letter-spacing: -0.04em;
        }

        h2 {
            font-size: clamp(27px, 3vw, 38px);
            line-height: 1.1;
        }

        p {
            margin: 0;
            color: var(--muted);
        }

        button {
            cursor: pointer;
            font: inherit;

            &:focus-visible {
                outline: 3px solid rgba(20, 184, 177, 0.36);
                outline-offset: 2px;
            }
        }

        &__page {
            position: relative;
            z-index: 1;
            max-width: 1440px;
            min-width: 0;
            margin: 0 auto;
            padding: 35px 28px 90px;
        }

        &__hero,
        &__glass-card,
        &__next-panel {
            min-width: 0;
            border: 1px solid var(--line);
            background: var(--glass);
            box-shadow:
                inset 0 1px 0 rgba(255, 255, 255, 0.78),
                0 20px 70px rgba(5, 59, 69, 0.12);
            backdrop-filter: blur(22px) saturate(1.18);
            -webkit-backdrop-filter: blur(22px) saturate(1.18);
        }

        &__hero {
            position: relative;
            overflow: hidden;
            margin-top: 33px;
            border-radius: 40px;
            padding: 35px;
            background:
                linear-gradient(
                    135deg,
                    rgba(255, 255, 255, 0.86),
                    rgba(255, 255, 255, 0.48)
                ),
                radial-gradient(
                    circle at 76% 18%,
                    rgba(20, 184, 177, 0.2),
                    transparent 24rem
                );
            box-shadow: var(--shadow);

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

        &__hero-grid {
            position: relative;
            z-index: 1;
            display: grid;
            grid-template-columns: minmax(0, 1.15fr) minmax(300px, 0.85fr);
            gap: 28px;
            align-items: stretch;
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
            color: var(--muted);
            font-size: 20px;
        }

        &__hero-actions,
        &__next-actions {
            display: flex;
            gap: 13px;
            flex-wrap: wrap;
            margin-top: 28px;
        }

        &__next-actions {
            &.compact {
                margin-top: 14px;
            }
        }

        &__btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 0;
            border: 1px solid rgba(255, 255, 255, 0.72);
            border-radius: 18px;
            box-shadow:
                inset 0 1px 0 rgba(255, 255, 255, 0.78),
                0 16px 44px rgba(5, 59, 69, 0.1);
            padding: 15px 19px;
            text-align: center;
            text-decoration: none;
            font-size: 16px;
            font-weight: 800;

            &.primary {
                border-color: rgba(255, 255, 255, 0.84);
                background: linear-gradient(135deg, #7edbd6, #14b8b1, #0e9c97);
                color: #fff;
            }

            &.secondary {
                background: rgba(255, 255, 255, 0.58);
                color: var(--turq-ink);
            }

            &.ghost {
                background: rgba(255, 255, 255, 0.36);
                color: var(--ink);
            }

            &.unavailable,
            &:disabled {
                cursor: not-allowed;
                opacity: 0.72;
                box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.72);
            }

            &.small {
                border-radius: 15px;
                padding: 12px 13px;
                box-shadow:
                    inset 0 1px 0 rgba(255, 255, 255, 0.72),
                    0 10px 28px rgba(5, 59, 69, 0.08);
                font-size: 14px;
            }
        }

        &__action-note {
            max-width: 660px;
            margin-top: 10px;
            color: var(--faint);
            font-size: 14px;
            font-weight: 700;
        }

        &__metric-row {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 12px;
            margin-top: 24px;
        }

        &__metric {
            min-width: 0;
            border: 1px solid rgba(255, 255, 255, 0.62);
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.46);
            padding: 14px;

            strong {
                display: block;
                color: #0b2f38;
                font-family: var(--cfa-font-heading);
                font-size: 28px;
                line-height: 1;
            }

            span {
                display: block;
                margin-top: 4px;
                color: var(--muted);
                font-size: 13px;
                font-weight: 700;
            }
        }

        &__score-card {
            display: grid;
            align-content: start;
            gap: 14px;
            min-width: 0;
            border-radius: 30px;
            background: linear-gradient(
                145deg,
                rgba(255, 255, 255, 0.8),
                rgba(228, 246, 245, 0.48)
            );
            padding: 24px;
            text-align: left;
        }

        &__score-intro {
            margin-top: 7px;
        }

        &__score-stack {
            display: grid;
            gap: 11px;
            min-width: 0;
        }

        &__score-mini {
            display: grid;
            gap: 5px;
            min-width: 0;
            border: 1px solid rgba(255, 255, 255, 0.66);
            border-radius: 20px;
            background: rgba(255, 255, 255, 0.48);
            padding: 14px;

            b {
                color: #0b2f38;
                font-family: var(--cfa-font-heading);
                font-size: clamp(24px, 3.2vw, 36px);
                line-height: 1;
                letter-spacing: -0.03em;
                white-space: nowrap;
            }

            strong {
                color: #0b2f38;
                font-size: 15px;
                overflow-wrap: anywhere;
            }

            small,
            span {
                display: block;
                color: var(--muted);
                font-size: 13px;
                font-weight: 700;
                overflow-wrap: anywhere;
            }

            &.abstain b {
                color: var(--amber);
                font-family: var(--cfa-font-body);
                font-size: 15px;
                letter-spacing: 0;
            }
        }

        &__score-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            min-width: 0;
        }

        &__score-sub {
            opacity: 0.82;
        }

        &__confidence {
            display: flex;
            justify-content: center;
            gap: 8px;
            flex-wrap: wrap;
            min-width: 0;
        }

        &__chip {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            min-width: 0;
            border: 1px solid rgba(255, 255, 255, 0.62);
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.46);
            color: var(--muted);
            padding: 8px 11px;
            font-size: 13px;
            font-weight: 800;
            overflow-wrap: anywhere;

            &.turq {
                background: rgba(20, 184, 177, 0.12);
                color: var(--turq-ink);
            }

            &.warn {
                background: rgba(183, 121, 31, 0.12);
                color: var(--amber);
            }
        }

        &__score-note {
            color: var(--muted);
            font-size: 13px;
            font-weight: 700;
            overflow-wrap: anywhere;
        }

        &__grid {
            display: grid;
            gap: 20px;
            min-width: 0;
            margin-top: 23px;
        }

        &__console-grid {
            grid-template-columns: minmax(0, 0.92fr) minmax(0, 1.08fr);
            align-items: start;
        }

        &__glass-card,
        &__next-panel {
            border-radius: 28px;
            padding: 23px;
        }

        &__card-title {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 15px;
            min-width: 0;
            margin-bottom: 15px;

            > div {
                min-width: 0;
            }
        }

        &__status-pill {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            background: rgba(20, 184, 177, 0.12);
            color: var(--turq-ink);
            padding: 7px 10px;
            text-align: center;
            font-size: 13px;
            font-weight: 800;
            line-height: 1.2;
        }

        &__risk-list {
            display: grid;
            gap: 12px;
            min-width: 0;
        }

        &__risk {
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            align-items: center;
            gap: 15px;
            min-width: 0;
            border: 1px solid rgba(255, 255, 255, 0.62);
            border-radius: 20px;
            background: rgba(255, 255, 255, 0.44);
            padding: 15px;

            strong {
                display: block;
                color: #0b2f38;
                overflow-wrap: anywhere;
            }

            small {
                display: block;
                margin-top: 3px;
                color: var(--muted);
                font-size: 15px;
                overflow-wrap: anywhere;
            }
        }

        &__risk-score {
            border-radius: 999px;
            padding: 7px 9px;
            font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
            font-size: 13px;
            font-weight: 700;
            white-space: nowrap;

            &.high {
                background: rgba(180, 35, 24, 0.1);
                color: var(--red);
            }

            &.med {
                background: rgba(183, 121, 31, 0.12);
                color: var(--amber);
            }

            &.keep {
                background: rgba(21, 128, 61, 0.1);
                color: var(--green);
            }
        }

        &__coverage-copy,
        &__table-hint {
            margin-bottom: 13px;
            color: var(--muted);
            font-size: 14px;
            overflow-wrap: anywhere;
        }

        &__topic-list {
            display: grid;
            gap: 9px;
            min-width: 0;
        }

        &__topic {
            display: grid;
            grid-template-columns:
                minmax(135px, 0.82fr) minmax(64px, 0.34fr) minmax(92px, 0.42fr)
                minmax(0, 1fr) auto;
            align-items: center;
            gap: 10px;
            min-width: 0;
            border: 1px solid rgba(255, 255, 255, 0.62);
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.42);
            padding: 12px;

            &.header {
                background: rgba(228, 246, 245, 0.38);
                color: var(--turq-ink);
                font-size: 12px;
                font-weight: 800;
                letter-spacing: 0.08em;
                text-transform: uppercase;
            }
        }

        &__topic-name {
            min-width: 0;

            strong {
                display: block;
                color: #0b2f38;
                font-size: 16px;
                overflow-wrap: anywhere;
            }

            span {
                display: block;
                margin-top: 1px;
                color: var(--muted);
                font-size: 13px;
                font-weight: 700;
            }
        }

        &__topic-stat,
        &__pct {
            color: var(--muted);
            font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
            font-size: 12px;
            font-weight: 700;
            white-space: nowrap;
        }

        &__pct {
            color: #0b2f38;
            font-size: 14px;

            &.is-warn {
                color: var(--amber);
            }

            &.is-muted {
                color: var(--faint);
            }
        }

        &__bar {
            min-width: 0;
            height: 10px;
            overflow: hidden;
            border-radius: 999px;
            background: rgba(233, 237, 241, 0.74);
            box-shadow: inset 0 1px 2px rgba(5, 59, 69, 0.08);

            i {
                display: block;
                height: 100%;
                border-radius: 999px;
                background: linear-gradient(90deg, #7edbd6, #0e9c97);

                &.warn {
                    background: linear-gradient(90deg, #f7d997, #b7791f);
                }

                &.danger {
                    background: linear-gradient(90deg, #f7b4ac, #b42318);
                }
            }
        }

        &__next-panel {
            margin-top: 23px;
            background:
                linear-gradient(
                    145deg,
                    rgba(255, 255, 255, 0.76),
                    rgba(228, 246, 245, 0.48)
                ),
                radial-gradient(
                    circle at 90% 12%,
                    rgba(20, 184, 177, 0.18),
                    transparent 20rem
                );
        }

        &__retention-watch {
            display: grid;
            grid-template-columns: minmax(0, 0.82fr) minmax(0, 1.18fr);
            gap: 14px;
            min-width: 0;
            margin-top: 18px;
        }

        &__retention-summary,
        &__forget-list {
            min-width: 0;
            border: 1px solid rgba(255, 255, 255, 0.66);
            border-radius: 22px;
            background: rgba(255, 255, 255, 0.46);
            padding: 17px;
        }

        &__retention-summary {
            strong {
                display: block;
                color: #0b2f38;
                font-family: var(--cfa-font-heading);
                font-size: clamp(26px, 4vw, 42px);
                line-height: 1;
                letter-spacing: -0.03em;
            }

            span {
                display: block;
                margin-top: 7px;
                color: var(--muted);
                font-size: 14px;
                font-weight: 700;
                overflow-wrap: anywhere;
            }
        }

        &__forget-list {
            display: grid;
            gap: 10px;
        }

        &__forget-item {
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            align-items: center;
            gap: 10px;
            min-width: 0;
            border-radius: 16px;
            background: rgba(255, 255, 255, 0.42);
            padding: 11px 12px;

            b {
                display: block;
                color: #0b2f38;
                font-size: 15px;
                overflow-wrap: anywhere;
            }

            span {
                display: block;
                margin-top: 1px;
                color: var(--muted);
                font-size: 13px;
                font-weight: 700;
                overflow-wrap: anywhere;
            }

            em {
                border-radius: 999px;
                background: rgba(183, 121, 31, 0.12);
                color: var(--amber);
                padding: 6px 8px;
                font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
                font-size: 12px;
                font-style: normal;
                font-weight: 700;
                white-space: nowrap;
            }
        }

        &__action-plan {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 13px;
            min-width: 0;
            margin-top: 17px;
        }

        &__action {
            display: grid;
            gap: 12px;
            min-width: 0;
            border: 1px solid rgba(255, 255, 255, 0.66);
            border-radius: 21px;
            background: rgba(255, 255, 255, 0.48);
            padding: 16px;

            b {
                display: block;
                color: #0b2f38;
                font-family: var(--cfa-font-heading);
                font-size: 20px;
                line-height: 1.16;
                overflow-wrap: anywhere;
            }

            span {
                display: block;
                margin-top: 7px;
                color: var(--muted);
                font-size: 14px;
                overflow-wrap: anywhere;
            }

            small {
                display: block;
                margin-top: 7px;
                color: var(--faint);
                font-size: 12px;
                font-weight: 800;
                overflow-wrap: anywhere;
            }

            .cfa-readiness__time {
                display: inline-flex;
                align-items: center;
                border-radius: 999px;
                background: rgba(20, 184, 177, 0.12);
                color: var(--turq-ink);
                padding: 6px 9px;
                font-size: 12px;
                font-weight: 800;
            }
        }

        &__flow-note {
            display: block;
            margin-top: 8px;
            color: var(--faint);
            font-size: 12px;
            font-weight: 800;
        }

        &__action-footer {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            flex-wrap: wrap;
        }

        &__next-actions {
            margin-top: 18px;
        }

        &__footer-note {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 14px;
            flex-wrap: wrap;
            min-width: 0;
            margin-top: 22px;
            border: 1px solid rgba(255, 255, 255, 0.56);
            border-radius: 22px;
            background: rgba(255, 255, 255, 0.34);
            padding: 18px;

            p {
                min-width: 0;
                color: var(--muted);
                font-size: 15px;
                overflow-wrap: anywhere;
            }
        }
    }

    @media (max-width: 1120px) {
        .cfa-readiness {
            &__action-plan {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }
    }

    @media (max-width: 980px) {
        .cfa-readiness {
            &__hero-grid,
            &__console-grid,
            &__metric-row,
            &__action-plan,
            &__retention-watch {
                grid-template-columns: minmax(0, 1fr);
            }
        }
    }

    @media (max-width: 720px) {
        .cfa-readiness {
            font-size: 17px;

            &__page {
                padding: 22px 14px 70px;
            }

            h1 {
                font-size: clamp(34px, 11vw, 42px);
            }

            h2 {
                font-size: clamp(25px, 8vw, 32px);
            }

            &__hero {
                border-radius: 30px;
                padding: 24px;

                &::after {
                    border-radius: 29px;
                }
            }

            &__hero-actions {
                gap: 10px;
                margin-top: 22px;
            }

            &__btn {
                width: 100%;
                min-height: 48px;
                padding: 13px 15px;
            }

            &__btn.small {
                width: 100%;
            }

            &__metric {
                padding: 13px;
            }

            &__score-card,
            &__glass-card,
            &__next-panel {
                border-radius: 22px;
                padding: 18px;
            }

            &__score-head {
                align-items: flex-start;
            }

            &__score-head b {
                text-align: right;
            }

            &__card-title {
                display: grid;
                gap: 10px;
            }

            &__status-pill {
                justify-self: start;
            }

            &__topic,
            &__risk,
            &__forget-item {
                grid-template-columns: minmax(0, 1fr);
            }

            &__topic {
                align-items: stretch;
                gap: 9px;
                padding: 14px;
            }

            &__topic.header {
                display: none;
            }

            &__topic-stat,
            &__pct,
            &__bar {
                display: grid;
                grid-template-columns: minmax(120px, 0.7fr) minmax(0, 1fr);
                align-items: center;
                gap: 10px;
                width: 100%;
                white-space: normal;
            }

            &__topic-stat::before,
            &__pct::before,
            &__bar::before {
                content: attr(data-label);
                color: var(--faint);
                font-family: var(--cfa-font-body);
                font-size: 12px;
                font-weight: 800;
                letter-spacing: 0.08em;
                text-transform: uppercase;
            }

            &__bar {
                height: auto;
                overflow: visible;
                background: transparent;
                box-shadow: none;
            }

            &__bar i {
                height: 11px;
                min-width: 11px;
                box-shadow: inset 0 1px 2px rgba(5, 59, 69, 0.08);
            }

            &__risk-score {
                justify-self: start;
            }

            &__retention-watch {
                gap: 12px;
            }

            &__action-footer {
                align-items: stretch;
            }

            &__footer-note {
                align-items: stretch;
            }
        }
    }
</style>
