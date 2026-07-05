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

    import RangeBox from "./RangeBox.svelte";
    import WithGraphData from "./WithGraphData.svelte";

    export let initialSearch: string;
    export let initialDays: number;

    const search = writable(initialSearch);
    const days = writable(initialDays);

    export let graphs: Component<any>[];
    /** See RangeBox */
    export let controller: Component<any> | null = RangeBox;

    function browserSearch(event: CustomEvent) {
        bridgeCommand(`browserSearch: ${$search} ${event.detail.query}`);
    }
</script>

<WithGraphData {search} {days} let:sourceData let:loading let:prefs let:revlogRange>
    <div class="cfa-graphs cfa-app">
        {#if controller}
            <svelte:component this={controller} {search} {days} {loading} />
        {/if}

        <div class="cfa-graphs-head">
            <Eyebrow>ankiCFA · Level II · Study statistics</Eyebrow>
        </div>

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
        <div class="spacer"></div>
    </div>
</WithGraphData>

<style lang="scss">
    @use "../../lib/cfa/tokens" as cfa;

    // CFA chrome for the statistics page. Scoped to `.cfa-graphs` so it only
    // retones this surface, never other TitledContainer/InputBox users.
    .cfa-graphs {
        min-height: 100vh;
        background: cfa.$cfa-page;
    }

    .cfa-graphs-head {
        margin: cfa.space(4) 0 cfa.space(2) cfa.space(3);
    }

    // Serif-navy card titles, CFA hairline card edges (light mode only — leave
    // the app's dark theme to its own tokens).
    .cfa-graphs :global(.container.light) {
        border: 1px solid cfa.$cfa-line;
        border-radius: cfa.$cfa-radius-block;
    }
    .cfa-graphs :global(.container.light h1) {
        font-family: cfa.$cfa-font-heading;
        font-weight: cfa.$cfa-weight-semibold;
        color: cfa.$cfa-ink;
        border-bottom: 1px solid cfa.$cfa-line;
    }

    // The sticky range selector reads as a CFA control strip.
    .cfa-graphs :global(.range-box) {
        background: cfa.$cfa-surface;
        color: cfa.$cfa-ink;
        border-bottom: 1px solid cfa.$cfa-line;
        font-family: cfa.$cfa-font-body;
    }
    // Warm-accent radios/checkboxes/spinner to match the design system.
    .cfa-graphs :global(.range-box input[type="radio"]),
    .cfa-graphs :global(.range-box input[type="checkbox"]) {
        accent-color: cfa.$cfa-accent;
    }
    .cfa-graphs :global(.range-box .spin) {
        color: cfa.$cfa-accent;
    }

    .graphs-container {
        display: grid;
        gap: 1em;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        // required on Safari to stretch whole width
        width: calc(100vw - 3em);
        margin-left: 1em;
        margin-right: 1em;

        @media only screen and (max-width: 600px) {
            width: calc(100vw - 1rem);
            margin-left: 0.5rem;
            margin-right: 0.5rem;
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
</style>
