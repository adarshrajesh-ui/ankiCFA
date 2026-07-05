<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

CfaHomePage — the native CFA landing dashboard the app opens into (in place of
the stock Anki deck list). Built from the shared CFA design system ($lib/cfa):

  * a quiet brand lockup + the EXAM COUNTDOWN hero (warn tone inside 14 days),
    with the current honest pass/fail one-liner as the lead,
  * three VALUE-FIRST honest-score StatCards (Memory / Performance / Readiness),
    identical formatting to the Exam Readiness page (shared ./readiness helpers),
  * a STUDY grid of primary CTAs (Ethics minimal-pairs, Exam Priority, the CFA
    deck, Exam Readiness, Peak-on-Exam-Day) — each a bridgeCommand routed to the
    existing CFA entry points,
  * a sync/account status card with one clear Connect & Sync action,
  * an AI-state chip (opens AI settings) and a Decks escape hatch.

Calm by design: weights <= 600, flat cards, 4px/pill radii, 8px rhythm, and the
pass/fail/warn semantic triad preserved.
-->
<script lang="ts">
    import { bridgeCommand } from "@tslib/bridgecommand";

    import { Caption, Eyebrow, Hero, PageHeading, StatCard } from "$lib/cfa";
    import type { CfaHomePayload, CfaTone, ScoreBand } from "$lib/cfa";

    import { bandSub, bandTone, bandValue, captionText, readinessName } from "./readiness";
    import { examCountdown, HOME_CTAS, heroLead } from "./home";

    /** The full CFA Home payload (three scores + exam countdown + AI state). */
    export let data: CfaHomePayload;

    interface ScoreCard {
        name: string;
        meaning: string;
        band: ScoreBand;
    }

    $: countdown = examCountdown(data);
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

    function go(cmd: string): void {
        bridgeCommand(cmd);
    }
</script>

<div class="cfa-app cfa-home">
    <div class="cfa-home__inner">
        <PageHeading eyebrow="ankiCFA · Level II" title="Exam Home" eyebrowTone="green" />

        <Hero
            tone={countdown.tone as CfaTone}
            headline={countdown.headline}
            sub={countdown.sub}
        >
            {heroLead(data)}
        </Hero>

        <section class="cfa-home__block">
            <Eyebrow tone="muted">Your honest scores</Eyebrow>
            <div class="cfa-home__stats">
                {#each scoreCards as card (card.name)}
                    <StatCard
                        value={bandValue(card.band)}
                        tone={bandTone(card.band)}
                        sub={bandSub(card.band)}
                        nowrap={!card.band.abstain}
                    >
                        <span class="cfa-home__stat-name">{card.name}</span>
                        <span class="cfa-home__stat-meaning">{card.meaning}</span>
                    </StatCard>
                {/each}
            </div>
            <Caption>{captionText(data.caption)}</Caption>
        </section>

        <section class="cfa-home__sync" aria-label="CFA sync status">
            <div>
                <Eyebrow tone={data.sync.connected ? "green" : "muted"}>Settings & sync</Eyebrow>
                <div class="cfa-home__sync-title">{data.sync.status}</div>
                <div class="cfa-home__sync-meta">
                    <span>{data.sync.account}</span>
                    <span>{data.sync.lastSynced}</span>
                    <span>{data.sync.detail}</span>
                </div>
            </div>
            <button type="button" class="cfa-home__sync-action" on:click={() => go("cfa:sync")}>
                {data.sync.actionLabel}
            </button>
        </section>

        <section class="cfa-home__block">
            <Eyebrow tone="muted">Study</Eyebrow>
            <div class="cfa-home__ctas">
                {#each HOME_CTAS as cta (cta.cmd)}
                    <button
                        type="button"
                        class="cfa-home__cta"
                        class:is-primary={cta.primary}
                        on:click={() => go(cta.cmd)}
                    >
                        <span class="cfa-home__cta-label">{cta.label}</span>
                        <span class="cfa-home__cta-sub">{cta.sub}</span>
                    </button>
                {/each}
            </div>
        </section>

        <div class="cfa-home__foot">
            <button
                type="button"
                class="cfa-home__chip"
                class:is-on={data.aiEnabled}
                on:click={() => go("cfa:ai")}
            >
                AI {data.aiEnabled ? "On" : "Off"} · settings
            </button>
            <button type="button" class="cfa-home__chip" on:click={() => go("cfa:decks")}>
                Browse decks
            </button>
        </div>

        <details class="cfa-home__methodology">
            <summary>How these scores work</summary>
            <Caption tone="muted">{data.footerText}</Caption>
        </details>
    </div>
</div>

<style lang="scss">
    @use "../tokens" as cfa;

    .cfa-home {
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

        &__block {
            display: flex;
            flex-direction: column;
            gap: cfa.space(3);
        }

        &__stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: cfa.space(5);
        }

        &__sync {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: cfa.space(5);
            padding: cfa.space(5);
            background: cfa.$cfa-bg;
            border: 1px solid cfa.$cfa-line;
            border-left: 4px solid cfa.$cfa-primary;
            border-radius: cfa.$cfa-radius-block;

            @media (max-width: 560px) {
                align-items: stretch;
                flex-direction: column;
            }
        }

        &__sync-title {
            margin-top: cfa.space(1);
            font-family: cfa.$cfa-font-heading;
            font-size: cfa.$cfa-fs-subtitle;
            font-weight: cfa.$cfa-weight-semibold;
            line-height: cfa.$cfa-lh-heading;
            color: cfa.$cfa-ink;
        }

        &__sync-meta {
            display: flex;
            flex-wrap: wrap;
            gap: cfa.space(2);
            margin-top: cfa.space(2);
            color: cfa.$cfa-muted;
            font-size: cfa.$cfa-fs-meta;
            line-height: cfa.$cfa-lh-snug;

            > span:not(:last-child)::after {
                content: "·";
                margin-left: cfa.space(2);
                color: cfa.$cfa-faint-ink;
            }
        }

        &__sync-action {
            flex: 0 0 auto;
            cursor: pointer;
            padding: cfa.space(3) cfa.space(5);
            font-family: inherit;
            font-size: cfa.$cfa-fs-small;
            font-weight: cfa.$cfa-weight-semibold;
            color: cfa.$cfa-bg;
            background: cfa.$cfa-primary;
            border: 1px solid cfa.$cfa-primary;
            border-radius: cfa.$cfa-radius-pill;

            &:hover {
                background: cfa.$cfa-primary-hover;
            }

            &:focus-visible {
                outline: 2px solid cfa.$cfa-accent;
                outline-offset: 2px;
            }
        }

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
            color: cfa.$cfa-faint-ink;
        }

        // CTA grid — the flagship primary drill spans the full width as a
        // featured tile; the remaining four form a clean, symmetric 2×2 so the
        // grid never leaves an orphaned empty cell (D1-4). Collapses to a single
        // column on narrow widths.
        &__ctas {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: cfa.space(4);

            @media (max-width: 560px) {
                grid-template-columns: minmax(0, 1fr);
            }
        }

        &__cta {
            display: flex;
            flex-direction: column;
            gap: cfa.space(1);
            padding: cfa.space(4) cfa.space(5);
            text-align: left;
            cursor: pointer;
            background: cfa.$cfa-bg;
            border: 1px solid cfa.$cfa-control-border; // AA non-text (WCAG 1.4.11)
            border-radius: cfa.$cfa-radius-block;
            color: cfa.$cfa-ink;
            transition:
                border-color 0.12s ease,
                background 0.12s ease,
                transform 0.12s ease;

            &:hover {
                border-color: cfa.$cfa-accent;
                transform: translateY(-1px);
            }

            &:focus-visible {
                outline: 2px solid cfa.$cfa-accent;
                outline-offset: 2px;
            }

            &.is-primary {
                grid-column: 1 / -1;
                background: cfa.$cfa-accent-soft;
                border-color: cfa.$cfa-accent;
            }
        }

        &__cta-label {
            font-weight: cfa.$cfa-weight-semibold;
            font-size: cfa.$cfa-fs-body;
        }

        &__cta-sub {
            font-size: cfa.$cfa-fs-meta;
            line-height: cfa.$cfa-lh-snug;
            color: cfa.$cfa-muted;
        }

        &__foot {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            justify-content: space-between;
            gap: cfa.space(3);
        }

        // Both footer controls share ONE pill affordance (D1-5) — no mixed
        // pill-vs-text-link-with-arrow treatment.
        &__chip {
            cursor: pointer;
            padding: cfa.space(2) cfa.space(4);
            font-family: inherit;
            font-size: cfa.$cfa-fs-meta;
            font-weight: cfa.$cfa-weight-semibold;
            border-radius: cfa.$cfa-radius-pill;
            border: 1px solid cfa.$cfa-control-border; // AA non-text (WCAG 1.4.11)
            background: cfa.$cfa-bg;
            color: cfa.$cfa-muted;

            &:hover {
                border-color: cfa.$cfa-accent;
                color: cfa.$cfa-ink;
            }

            &:focus-visible {
                outline: 2px solid cfa.$cfa-accent;
                outline-offset: 2px;
            }
        }

        &__chip.is-on {
            color: cfa.$cfa-pass;
            border-color: cfa.$cfa-pass;
        }

        // The dense methodology paragraph is collapsed behind a quiet disclosure
        // (D1-6) so first-run microcopy no longer dominates the page foot; the
        // summary is a calm, tappable one-liner.
        &__methodology {
            > summary {
                cursor: pointer;
                list-style: none;
                font-size: cfa.$cfa-fs-meta;
                font-weight: cfa.$cfa-weight-semibold;
                color: cfa.$cfa-muted;

                &::-webkit-details-marker {
                    display: none;
                }

                &::before {
                    content: "▸ ";
                    color: cfa.$cfa-faint-ink;
                }

                &:hover {
                    color: cfa.$cfa-ink;
                }

                &:focus-visible {
                    outline: 2px solid cfa.$cfa-accent;
                    outline-offset: 2px;
                }
            }

            &[open] > summary {
                margin-bottom: cfa.space(2);

                &::before {
                    content: "▾ ";
                }
            }
        }
    }
</style>
