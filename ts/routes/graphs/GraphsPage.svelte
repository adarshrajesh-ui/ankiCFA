<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<script lang="ts">
    import { bridgeCommand } from "@tslib/bridgecommand";
    import type { Component } from "svelte";
    import { writable } from "svelte/store";

    import { pageTheme } from "$lib/sveltelib/theme";

    // CFA design system: the statistics screen is stock Anki's biggest reporting
    // surface, and for a CFA exam-prep product "how am I tracking" is core — so
    // theme its chrome (brand eyebrow, CFA page tint, serif-navy card titles,
    // CFA-toned range selector) to the design system. Presentation-only: the d3
    // charts and all data/query behaviour are untouched.
    import "$lib/cfa/theme.scss";
    import Eyebrow from "$lib/cfa/Eyebrow.svelte";
    import ProductShellNav from "$lib/cfa/ProductShellNav.svelte";

    import RangeBox from "./RangeBox.svelte";
    import WithGraphData from "./WithGraphData.svelte";

    export let initialSearch: string;
    export let initialDays: number;

    const search = writable(initialSearch);
    const days = writable(initialDays);

    export let graphs: Component<any>[];
    /** See RangeBox */
    export let controller: Component<any> | null = RangeBox;

    function go(cmd: string): void {
        bridgeCommand(cmd);
    }

    function browserSearch(event: CustomEvent) {
        bridgeCommand(`browserSearch: ${$search} ${event.detail.query}`);
    }
</script>

<WithGraphData {search} {days} let:sourceData let:loading let:prefs let:revlogRange>
    <div class="cfa-graphs cfa-app">
        <div class="cfa-progress-appbar-wrap">
            <ProductShellNav
                active="progress"
                subtitle="Progress"
                ariaLabel="CFA sections"
                on:navigate={(event) => go(event.detail)}
            />
        </div>

        {#if controller}
            <svelte:component this={controller} {search} {days} {loading} />
        {/if}

        <div class="cfa-graphs-shell">
            <section class="cfa-progress-hero">
                <Eyebrow>EthosPrep · Level II · Study statistics</Eyebrow>
                <div class="cfa-progress-hero__body">
                    <div>
                        <h1>Progress Command Center</h1>
                        <p>
                            Track workload, retention, and review shape without leaving
                            the CFA study shell. Click any chart segment to drill into
                            the underlying cards.
                        </p>
                    </div>
                    <div class="cfa-progress-hero__meta" aria-label="Progress scope">
                        <span>FSRS memory signal</span>
                        <span>365-day default view</span>
                        <span>Deck-aware drill-down</span>
                    </div>
                </div>
            </section>

            <div class="graphs-container">
                {#if sourceData && revlogRange}
                    {#each graphs as graph}
                        <svelte:component
                            this={graph}
                            {sourceData}
                            {prefs}
                            {revlogRange}
                            nightMode={$pageTheme.isDark}
                            on:search={browserSearch}
                        />
                    {/each}
                {/if}
            </div>
        </div>
        <div class="spacer"></div>
    </div>
</WithGraphData>

<style lang="scss">
    @use "../../lib/cfa/tokens" as cfa;

    // CFA chrome for the statistics page. Scoped to `.cfa-graphs` so it only
    // retones this surface, never other TitledContainer/InputBox users.
    .cfa-graphs {
        min-height: 100vh;
        background:
            radial-gradient(
                circle at 12% 0%,
                rgba(218, 92, 1, 0.11),
                transparent 30rem
            ),
            radial-gradient(circle at 88% 6%, rgba(0, 126, 86, 0.1), transparent 28rem),
            linear-gradient(180deg, #ffffff 0%, cfa.$cfa-page 34%, #eef3f7 100%);
        padding-bottom: cfa.space(6);
    }

    .cfa-graphs-shell {
        width: min(1320px, calc(100vw - 3em));
        margin: 0 auto;
    }

    .cfa-progress-appbar-wrap {
        width: min(1320px, calc(100vw - 3em));
        margin: cfa.space(4) auto 0;
    }

    .cfa-progress-hero {
        margin: cfa.space(6) 0 cfa.space(4);
        padding: cfa.space(6);
        overflow: hidden;
        background:
            linear-gradient(
                135deg,
                rgba(255, 255, 255, 0.9),
                rgba(243, 246, 248, 0.72)
            ),
            radial-gradient(
                circle at 100% 0%,
                rgba(218, 92, 1, 0.16),
                transparent 18rem
            );
        border: 1px solid rgba(18, 43, 70, 0.1);
        border-radius: 18px;
        box-shadow: 0 22px 60px rgba(18, 43, 70, 0.12);
        backdrop-filter: blur(18px);
    }

    .cfa-progress-hero__body {
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        gap: cfa.space(6);
        align-items: end;
        margin-top: cfa.space(2);
    }

    .cfa-progress-hero h1 {
        margin: 0;
        color: cfa.$cfa-ink;
        font-family: cfa.$cfa-font-heading;
        font-size: clamp(32px, 4vw, 52px);
        font-weight: cfa.$cfa-weight-regular;
        line-height: cfa.$cfa-lh-tight;
    }

    .cfa-progress-hero p {
        max-width: 660px;
        margin: cfa.space(3) 0 0;
        color: cfa.$cfa-muted;
        font-size: cfa.$cfa-fs-lead;
        line-height: cfa.$cfa-lh-body;
    }

    .cfa-progress-hero__meta {
        display: flex;
        flex-wrap: wrap;
        justify-content: flex-end;
        gap: cfa.space(2);
        max-width: 360px;
    }

    .cfa-progress-hero__meta span {
        padding: 7px 12px;
        color: cfa.$cfa-ink;
        background: rgba(255, 255, 255, 0.72);
        border: 1px solid rgba(18, 43, 70, 0.12);
        border-radius: cfa.$cfa-radius-pill;
        font-size: cfa.$cfa-fs-meta;
        font-weight: cfa.$cfa-weight-medium;
        box-shadow: 0 8px 24px rgba(18, 43, 70, 0.08);
    }

    // Serif-navy card titles, CFA hairline card edges (light mode only — leave
    // the app's dark theme to its own tokens).
    .cfa-graphs :global(.container.light) {
        overflow: hidden;
        background: rgba(255, 255, 255, 0.84);
        border: 1px solid rgba(18, 43, 70, 0.1);
        border-radius: 18px;
        box-shadow: 0 18px 48px rgba(18, 43, 70, 0.1);
        backdrop-filter: blur(14px);
    }
    .cfa-graphs :global(.container.light h1) {
        font-family: cfa.$cfa-font-heading;
        font-weight: cfa.$cfa-weight-semibold;
        color: cfa.$cfa-ink;
        background: linear-gradient(
            180deg,
            rgba(255, 255, 255, 0.66),
            rgba(243, 246, 248, 0.5)
        );
        border-bottom: 1px solid rgba(18, 43, 70, 0.08);
    }
    .cfa-graphs :global(.container.light .graph) {
        color: cfa.$cfa-muted;
    }
    .cfa-graphs :global(.container.light svg text) {
        fill: cfa.$cfa-muted;
    }
    .cfa-graphs :global(.container.light .subtitle) {
        color: cfa.$cfa-faint-ink;
    }

    // The sticky range selector reads as a CFA control strip.
    .cfa-graphs :global(.range-box) {
        box-sizing: border-box;
        background: rgba(255, 255, 255, 0.86);
        color: cfa.$cfa-ink;
        border-bottom: 1px solid rgba(18, 43, 70, 0.1);
        font-family: cfa.$cfa-font-body;
        box-shadow: 0 12px 34px rgba(18, 43, 70, 0.1);
        backdrop-filter: blur(18px);
    }
    .cfa-graphs :global(.range-box > div:not(.spin)) {
        flex-wrap: wrap;
        gap: 8px;
        justify-content: center;
    }
    // Warm-accent radios/checkboxes/spinner to match the design system.
    .cfa-graphs :global(.range-box input[type="radio"]),
    .cfa-graphs :global(.range-box input[type="checkbox"]) {
        accent-color: cfa.$cfa-accent;
    }
    .cfa-graphs :global(.range-box input[type="text"]) {
        color: cfa.$cfa-ink;
        background: rgba(255, 255, 255, 0.72);
        border-color: cfa.$cfa-control-border;
        border-radius: cfa.$cfa-radius-pill;
    }
    .cfa-graphs :global(.range-box label) {
        color: cfa.$cfa-muted;
        font-weight: cfa.$cfa-weight-medium;
    }
    .cfa-graphs :global(.range-box .spin) {
        color: cfa.$cfa-accent;
    }

    .graphs-container {
        display: grid;
        gap: cfa.space(4);
        grid-template-columns: repeat(3, minmax(0, 1fr));
        width: 100%;

        @media only screen and (max-width: 600px) {
            width: 100%;
        }

        @media only screen and (max-width: 1400px) {
            grid-template-columns: 1fr 1fr;
        }
        @media only screen and (max-width: 1200px) {
            grid-template-columns: 1fr;
        }
        @media only screen and (max-width: 600px) {
            font-size: 12px;
        }

        @media only print {
            // grid layout does not honor page-break-inside
            display: block;
            margin-top: 3em;
        }
    }

    .spacer {
        height: 1.5em;
    }

    @media only screen and (max-width: 800px) {
        .cfa-progress-appbar-wrap,
        .cfa-graphs-shell {
            width: min(100% - 1rem, 1320px);
        }

        .cfa-progress-hero {
            margin-top: cfa.space(4);
            padding: cfa.space(5);
            border-radius: 14px;
        }

        .cfa-progress-hero__body {
            grid-template-columns: 1fr;
            align-items: start;
        }

        .cfa-progress-hero__meta {
            justify-content: flex-start;
        }
    }

    @media only screen and (max-width: 600px) {
        .cfa-graphs {
            padding-bottom: cfa.space(4);
        }

        .cfa-progress-appbar-wrap {
            margin-top: cfa.space(3);
        }

        .cfa-graphs :global(.range-box) {
            display: grid;
            grid-template-columns: 1fr;
            gap: 8px;
            width: 100%;
            padding: 10px;
        }

        .cfa-graphs :global(.range-box > div:not(.spin)) {
            justify-content: flex-start;
        }

        .cfa-graphs :global(.range-box input[type="text"]) {
            width: min(100%, 18rem);
            min-height: 38px;
        }

        .cfa-progress-hero {
            margin-block: cfa.space(3);
            padding: cfa.space(4);
        }

        .cfa-progress-hero h1 {
            font-size: clamp(30px, 11vw, 42px);
        }

        .cfa-progress-hero p {
            font-size: 16px;
        }

        .cfa-progress-hero__meta span {
            font-size: 12px;
        }
    }
</style>
