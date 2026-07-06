<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<script lang="ts">
    import type { CardStatsResponse } from "@generated/anki/stats_pb";

    import Container from "$lib/components/Container.svelte";
    import Row from "$lib/components/Row.svelte";

    // CFA design system: the Card Info screen (reviewer "More → Card Info" and
    // the Browser sidebar) was a 100%-stock-Anki surface — a bare white page
    // with an unstyled key/value stats table and stock traffic-light revlog
    // colours. For a CFA exam-prep product a card's review history is core, so
    // theme its chrome (brand eyebrow, CFA page tint, serif-navy stat labels,
    // CFA hairline table rules, CFA-toned revlog). Presentation-only: the stats
    // query, revlog table, and forgetting-curve chart are all untouched.
    import "$lib/cfa/theme.scss";
    import Eyebrow from "$lib/cfa/Eyebrow.svelte";

    import CardInfoPlaceholder from "./CardInfoPlaceholder.svelte";
    import CardStats from "./CardStats.svelte";
    import Revlog from "./Revlog.svelte";
    import ForgettingCurve from "./ForgettingCurve.svelte";

    export let stats: CardStatsResponse | null = null;
    export let showRevlog: boolean = true;
    export let showCurve: boolean = true;

    $: fsrsEnabled = stats?.memoryState != null;
    $: desiredRetention = stats?.desiredRetention ?? 0.9;
    $: decay = (() => {
        const paramsLength = stats?.fsrsParams?.length ?? 0;
        if (paramsLength === 0) {
            return 0.1542; // default decay for FSRS-6
        }
        if (paramsLength < 21) {
            return 0.5; // default decay for FSRS-4.5 and FSRS-5
        }
        return stats?.fsrsParams?.[20] ?? 0.1542;
    })();
</script>

<div class="cfa-cardinfo cfa-app">
    {#if stats}
        <div class="cfa-cardinfo-head">
            <Eyebrow>ankiCFA · Level II · Card details</Eyebrow>
        </div>
    {/if}

    <Container breakpoint="md" --gutter-inline="1rem" --gutter-block="0.5rem">
        {#if stats}
            <Row>
                <CardStats {stats} />
            </Row>

            {#if showRevlog}
                <Row>
                    <Revlog revlog={stats.revlog} {fsrsEnabled} />
                </Row>
            {/if}
            {#if fsrsEnabled && showCurve}
                <Row>
                    <ForgettingCurve revlog={stats.revlog} {desiredRetention} {decay} />
                </Row>
            {/if}
        {:else}
            <CardInfoPlaceholder />
        {/if}
    </Container>
</div>

<style lang="scss">
    @use "../../lib/cfa/tokens" as cfa;

    // CFA chrome for the Card Info surface. Scoped to `.cfa-cardinfo` so it only
    // retones this screen, never other stats-table / TitledContainer users.
    .cfa-cardinfo {
        min-height: 100vh;
    }
    // Light page tint (leave the app's dark theme to its own tokens).
    :global(body:not(.nightMode)) .cfa-cardinfo {
        background: cfa.$cfa-page;
    }

    .cfa-cardinfo-head {
        margin: cfa.space(4) 0 cfa.space(1) cfa.space(3);
    }

    // Stat key/value table: serif-navy labels, CFA hairline row rules, brand-ink
    // values (the table itself is unstyled stock Anki, reached via :global).
    .cfa-cardinfo :global(.stats-table th) {
        font-family: cfa.$cfa-font-heading;
        font-weight: cfa.$cfa-weight-semibold;
        color: cfa.$cfa-ink;
        padding: cfa.space(1) 0;
    }
    .cfa-cardinfo :global(.stats-table td) {
        color: cfa.$cfa-ink;
        padding: cfa.space(1) 0;
    }
    :global(body:not(.nightMode)) .cfa-cardinfo :global(.stats-table tr) {
        border-bottom: 1px solid cfa.$cfa-line;
    }

    // Revlog: navy column heads, and retone the stock traffic-light review-kind
    // colours to the CFA palette (learn = accent, review = navy ink, relearn =
    // fail-red) so the log reads as one design system, still distinguishable.
    .cfa-cardinfo :global(.column-head) {
        font-family: cfa.$cfa-font-heading;
        color: cfa.$cfa-ink;
    }
    :global(body:not(.nightMode)) .cfa-cardinfo :global(.revlog-review) {
        color: cfa.$cfa-ink;
    }
    :global(body:not(.nightMode)) .cfa-cardinfo :global(.revlog-learn) {
        color: cfa.$cfa-accent;
    }
    :global(body:not(.nightMode)) .cfa-cardinfo :global(.revlog-relearn),
    :global(body:not(.nightMode)) .cfa-cardinfo :global(.revlog-ease1) {
        color: cfa.$cfa-fail;
    }
</style>
