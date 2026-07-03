<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

CfaReadinessPage — the self-contained CFA "Exam Readiness" surface, rebuilt as
a calm, premium finance-education page (modelled on markmeldrum.com) from the
shared design system ($lib/cfa). It renders the SAME honest-score data the
desktop dialog shows (qt/aqt/cfa.py):

  * a quiet brand lockup (eyebrow + serif deck name),
  * the verdict HERO — a big weight-400 serif call in the pass/fail colour on a
    hairline/thin-spine card (never a saturated ring), with the accuracy + 95%
    CI lead and the standing "not validated" caveat (or the abstain state),
  * three VALUE-FIRST honest-score StatCards (big serif range on top, muted
    label below, midpoint sub) — abstain stays warn,
  * the per-topic recall DataTable (uppercase muted headers, right-aligned
    numerics, warn recall when low/uncovered, "no data" for null ranges),
  * the coverage caption and the explanatory footer in quiet muted text.

Calm by design: weights <= 600, flat cards, 4px/pill radii, an 8px rhythm, and
the pass/fail/warn semantic triad preserved throughout.
-->
<script lang="ts">
    import {
        Caption,
        DataTable,
        Eyebrow,
        Hero,
        PageHeading,
        StatCard,
    } from "$lib/cfa";
    import type { CfaTone, ExamReadinessPayload, ScoreBand } from "$lib/cfa";
    import {
        bandSub,
        bandTone,
        bandValue,
        captionText,
        pct,
        readinessName,
        TOPIC_COLUMNS,
        type TopicDisplayRow,
        topicRows,
    } from "./readiness";

    /** The full Exam Readiness payload (same shape the backend builds). */
    export let data: ExamReadinessPayload;

    interface ScoreCard {
        name: string;
        meaning: string;
        band: ScoreBand;
    }

    $: scoreCards = [
        { name: data.memory.name, meaning: data.memory.meaning, band: data.memory },
        {
            name: data.performance.name,
            meaning: data.performance.meaning,
            band: data.performance,
        },
        {
            name: readinessName(data.readiness),
            meaning: data.readiness.meaning,
            band: data.readiness,
        },
    ] satisfies ScoreCard[];

    $: rows = topicRows(data.topics);
</script>

<div class="cfa-app cfa-readiness">
    <div class="cfa-readiness__inner">
        <PageHeading eyebrow="Exam Readiness" title={data.deckName} eyebrowTone="green" />

        {#if data.heroMode === "bayesian_call" && data.heroBayesian}
            {@const hb = data.heroBayesian}
            {@const heroTone = (hb.passed ? "pass" : "fail") satisfies CfaTone}
            {@const heroNote =
                `Bayesian — the band starts wide and narrows as reviews accrue `
                + `(${hb.firstExposures} first-seen · ${hb.topicsCovered}/`
                + `${hb.topicsTotal} topics studied). ${hb.label}.`}
            <Hero
                tone={heroTone}
                headline={hb.call}
                sub={`p=${hb.callProb.toFixed(2)}`}
                note={heroNote}
            >
                Estimated exam accuracy
                <strong class="cfa-readiness__em">{pct(hb.accuracy)}</strong>
                <span class="cfa-readiness__muted"
                    >(95% CI {pct(hb.ciLow)}–{pct(hb.ciHigh)})</span
                >
                vs ~{pct(hb.mps)} MPS proxy{#if hb.recall !== null} · est. recall
                    <strong class="cfa-readiness__em">{pct(hb.recall)}</strong>
                    <span class="cfa-readiness__muted">(FSRS R, SM-2 fallback)</span
                    >{/if}
            </Hero>
        {:else if data.heroAbstain}
            {@const ha = data.heroAbstain}
            <Hero
                tone="warn"
                headline="Not enough data — keep studying"
                note={`${ha.reason} · ${ha.readinessLabel}`}
            >
                No pass/fail call yet — the estimate stays hidden until there is
                enough graded review evidence to be honest. It appears here once the
                give-up threshold is met.
            </Hero>
        {/if}

        <section class="cfa-readiness__block">
            <Eyebrow tone="muted">Honest scores</Eyebrow>
            <div class="cfa-readiness__stats">
                {#each scoreCards as card (card.name)}
                    <StatCard
                        value={bandValue(card.band)}
                        tone={bandTone(card.band)}
                        sub={bandSub(card.band)}
                    >
                        <span class="cfa-readiness__stat-name">{card.name}</span>
                        <span class="cfa-readiness__stat-meaning">{card.meaning}</span>
                    </StatCard>
                {/each}
            </div>
            <Caption>{captionText(data.caption)}</Caption>
        </section>

        <section class="cfa-readiness__block">
            <Eyebrow tone="muted">Per-topic recall</Eyebrow>
            <DataTable columns={TOPIC_COLUMNS} {rows} emptyText="No topics studied yet.">
                <svelte:fragment slot="cell" let:column let:row>
                    {@const r = row as TopicDisplayRow}
                    {#if column.key === "recall"}
                        <span
                            class="cfa-readiness__recall"
                            class:is-warn={r.recallTone === "warn"}
                            class:is-faint={r.recallTone === "muted"}>{r.recall}</span
                        >
                    {:else if column.key === "topic"}
                        {r.topic}
                    {:else if column.key === "weight"}
                        {r.weight}
                    {:else if column.key === "reviewed"}
                        {r.reviewed}
                    {:else if column.key === "graded"}
                        {r.graded}
                    {/if}
                </svelte:fragment>
            </DataTable>
        </section>

        <Caption tone="muted">{data.footerText}</Caption>
    </div>
</div>

<style lang="scss">
    @use "../tokens" as cfa;

    .cfa-readiness {
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
            gap: cfa.space(6);
            max-width: 820px;
            margin: 0 auto;
        }

        // A titled section: an uppercase over-line tight above its content.
        &__block {
            display: flex;
            flex-direction: column;
            gap: cfa.space(3);
        }

        // Calm weight-600 emphasis inside the hero lead (never 700 bold).
        &__em {
            font-weight: cfa.$cfa-weight-semibold;
            color: cfa.$cfa-ink;
        }

        &__muted {
            color: cfa.$cfa-muted;
        }

        // Three value-first stat cards, generous gaps, responsive stacking.
        &__stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: cfa.space(5);
        }

        // StatCard label slot: the name reads first, the meaning fainter below.
        &__stat-name {
            display: block;
            font-weight: cfa.$cfa-weight-semibold;
            color: cfa.$cfa-muted;
        }

        &__stat-meaning {
            display: block;
            margin-top: cfa.space(1);
            font-size: cfa.$cfa-fs-meta;
            line-height: cfa.$cfa-lh-snug;
            color: cfa.$cfa-faint;
        }

        // Recall cell: tabular figures, warn for low/uncovered, faint no-data.
        &__recall {
            font-variant-numeric: tabular-nums;

            &.is-warn {
                color: cfa.$cfa-warn;
            }

            &.is-faint {
                color: cfa.$cfa-faint;
            }
        }
    }
</style>
