<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<script lang="ts">
    import type { Writable } from "svelte/store";

    import "$lib/sveltelib/export-runtime";
    import "$lib/cfa/theme.scss";

    import Container from "$lib/components/Container.svelte";
    import Row from "$lib/components/Row.svelte";
    import Eyebrow from "$lib/cfa/Eyebrow.svelte";
    import { pageTheme } from "$lib/sveltelib/theme";
    import type { DynamicSvelteComponent } from "$lib/sveltelib/dynamicComponent";

    import Addons from "./Addons.svelte";
    import AdvancedOptions from "./AdvancedOptions.svelte";
    import AudioOptions from "./AudioOptions.svelte";
    import AutoAdvance from "./AutoAdvance.svelte";
    import BuryOptions from "./BuryOptions.svelte";
    import ConfigSelector from "./ConfigSelector.svelte";
    import DailyLimits from "./DailyLimits.svelte";
    import DisplayOrder from "./DisplayOrder.svelte";
    import FsrsOptionsOuter from "./FsrsOptionsOuter.svelte";
    import HtmlAddon from "./HtmlAddon.svelte";
    import LapseOptions from "./LapseOptions.svelte";
    import type { DeckOptionsState } from "./lib";
    import NewOptions from "./NewOptions.svelte";
    import TimerOptions from "./TimerOptions.svelte";
    import EasyDays from "./EasyDays.svelte";

    export let state: DeckOptionsState;
    const addons = state.addonComponents;

    export function auxData(): Writable<Record<string, unknown>> {
        return state.currentAuxData;
    }

    export function addSvelteAddon(component: DynamicSvelteComponent): void {
        $addons = [...$addons, component];
    }

    export function addHtmlAddon(html: string, mounted: () => void): void {
        $addons = [
            ...$addons,
            {
                component: HtmlAddon,
                html,
                mounted,
            },
        ];
    }

    export const options = {};
    export const dailyLimits = {};
    export const newOptions = {};
    export const lapseOptions = {};
    export const buryOptions = {};
    export const displayOrder = {};
    export const timerOptions = {};
    export const audioOptions = {};
    export const advancedOptions = {};
    export const easyDays = {};

    let dailyLimitsComponent: DailyLimits | undefined;
    let fsrsOptionsOuterComponent: FsrsOptionsOuter | undefined;

    function onPresetChange() {
        if (dailyLimitsComponent) {
            dailyLimitsComponent.onPresetChange();
        }
        if (fsrsOptionsOuterComponent) {
            fsrsOptionsOuterComponent.onPresetChange();
        }
    }
</script>

<div class="cfa-deckopts cfa-app" class:is-light={!$pageTheme.isDark}>
    <div class="cfa-deckopts-head">
        <Eyebrow>EthosPrep · Level II · Study settings</Eyebrow>
    </div>

    <ConfigSelector {state} on:presetchange={onPresetChange} />

    <div class="deck-options-page">
        <Container
            breakpoint="sm"
            --gutter-inline="0.25rem"
            --gutter-block="0.75rem"
            class="container-columns"
        >
            <div>
                <Row class="row-columns">
                    <DailyLimits
                        {state}
                        api={dailyLimits}
                        bind:this={dailyLimitsComponent}
                    />
                </Row>

                <Row class="row-columns">
                    <NewOptions {state} api={newOptions} />
                </Row>

                <Row class="row-columns">
                    <LapseOptions {state} api={lapseOptions} />
                </Row>

                <Row class="row-columns">
                    <DisplayOrder {state} api={displayOrder} />
                </Row>

                <Row class="row-columns">
                    <FsrsOptionsOuter
                        {state}
                        api={{}}
                        bind:this={fsrsOptionsOuterComponent}
                    />
                </Row>
            </div>

            <div>
                <Row class="row-columns">
                    <BuryOptions {state} api={buryOptions} />
                </Row>

                <Row class="row-columns">
                    <AudioOptions {state} api={audioOptions} />
                </Row>

                <Row class="row-columns">
                    <TimerOptions {state} api={timerOptions} />
                </Row>

                <Row class="row-columns">
                    <AutoAdvance {state} api={timerOptions} />
                </Row>

                {#if $addons.length}
                    <Row class="row-columns">
                        <Addons {state} />
                    </Row>
                {/if}

                <Row class="row-columns">
                    <EasyDays {state} api={easyDays} />
                </Row>

                <Row class="row-columns">
                    <AdvancedOptions {state} api={advancedOptions} />
                </Row>
            </div>
        </Container>
    </div>
</div>

<style lang="scss">
    @use "$lib/sass/breakpoints" as bp;
    @use "../../lib/cfa/tokens" as cfa;

    // CFA chrome for the deck-options (Study settings) dialog. Scoped to
    // `.cfa-deckopts` so it only retones this surface; the stock-Anki blue
    // interactive tokens (--button-primary-bg, --border-focus, --fg-link,
    // --accent-card, --selected-bg) are overridden to CFA navy/accent for every
    // descendant control at once, so the Save button, focus rings, links, and
    // selected rows read as CFA rather than stock Anki. Light mode only — the
    // app's dark theme keeps its own tokens.
    .cfa-deckopts.is-light {
        min-height: 100vh;
        background: cfa.$cfa-page;

        --button-primary-bg: #{cfa.$cfa-primary};
        --button-primary-gradient-start: #{cfa.$cfa-primary};
        --button-primary-gradient-end: #{cfa.$cfa-primary};
        --border-focus: #{cfa.$cfa-accent};
        --fg-link: #{cfa.$cfa-accent};
        --accent-card: #{cfa.$cfa-primary};
        --selected-bg: #{cfa.$cfa-accent-soft};
    }

    .cfa-deckopts-head {
        margin: cfa.space(4) 0 cfa.space(2) cfa.space(3);
    }

    // Serif-navy section titles on CFA hairlines (light mode only), matching the
    // themed statistics/card-info surfaces.
    .cfa-deckopts.is-light :global(.container.light h1) {
        font-family: cfa.$cfa-font-heading;
        font-weight: cfa.$cfa-weight-semibold;
        color: cfa.$cfa-ink;
    }

    .deck-options-page {
        overflow-x: hidden;
        word-break: break-word;

        :global(.container-columns) {
            display: grid;
            gap: 0px;
        }

        @include bp.with-breakpoint("lg") {
            :global(.container-columns) {
                grid-template-columns: repeat(2, 1fr);
                gap: 20px;
            }
        }
    }
</style>
