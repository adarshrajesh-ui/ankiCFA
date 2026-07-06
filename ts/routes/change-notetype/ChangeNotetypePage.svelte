<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<script lang="ts">
    import * as tr from "@generated/ftl";
    import { renderMarkdown } from "@tslib/helpers";

    import "$lib/cfa/theme.scss";

    import Container from "$lib/components/Container.svelte";
    import Row from "$lib/components/Row.svelte";
    import StickyContainer from "$lib/components/StickyContainer.svelte";
    import TitledContainer from "$lib/components/TitledContainer.svelte";
    import Eyebrow from "$lib/cfa/Eyebrow.svelte";
    import { pageTheme } from "$lib/sveltelib/theme";

    import type { ChangeNotetypeState } from "./lib";
    import { MapContext } from "./lib";
    import Mapper from "./Mapper.svelte";
    import NotetypeSelector from "./NotetypeSelector.svelte";
    import StickyHeader from "./StickyHeader.svelte";

    export let state: ChangeNotetypeState;
    $: info = state.info;
</script>

<div class="cfa-changenote cfa-app" class:is-light={!$pageTheme.isDark}>
    <div class="cfa-changenote-head">
        <Eyebrow>EthosPrep · Level II · Change notetype</Eyebrow>
    </div>

    <StickyContainer
        --gutter-block="0.5rem"
        --gutter-inline="0.25rem"
        --sticky-borders="0 0 1px"
        breakpoint="sm"
    >
        <NotetypeSelector {state} />
    </StickyContainer>

    <Container breakpoint="sm" --gutter-inline="0.25rem" --gutter-block="0.75rem">
        <Row --cols={2}>
            <TitledContainer title={tr.changeNotetypeFields()}>
                <Row>
                    <StickyHeader {state} ctx={MapContext.Field} />
                    <Mapper {state} ctx={MapContext.Field} />
                </Row>
            </TitledContainer>
        </Row>
        <Row --cols={2}>
            <TitledContainer title={tr.changeNotetypeTemplates()}>
                <Row>
                    <StickyHeader {state} ctx={MapContext.Template} />
                    {#if $info.templates}
                        <Mapper {state} ctx={MapContext.Template} />
                    {:else}
                        <div>
                            {@html renderMarkdown(tr.changeNotetypeToFromCloze())}
                        </div>
                    {/if}
                </Row>
            </TitledContainer>
        </Row>
    </Container>
</div>

<style lang="scss">
    @use "../../lib/cfa/tokens" as cfa;

    // CFA chrome for the Change-notetype dialog. Scoped to `.cfa-changenote` so
    // it only retones this surface; the stock-Anki blue interactive tokens
    // (--button-primary-bg, --border-focus, --fg-link, --selected-bg) are
    // overridden to CFA navy/accent for every descendant control at once, so the
    // Save button, focus rings, links, and selected notetype row read as CFA
    // rather than stock Anki. Light mode only — the app's dark theme keeps its
    // own tokens.
    .cfa-changenote.is-light {
        min-height: 100vh;
        background: cfa.$cfa-page;

        --button-primary-bg: #{cfa.$cfa-primary};
        --button-primary-gradient-start: #{cfa.$cfa-primary};
        --button-primary-gradient-end: #{cfa.$cfa-primary};
        --border-focus: #{cfa.$cfa-accent};
        --fg-link: #{cfa.$cfa-accent};
        --selected-bg: #{cfa.$cfa-accent-soft};
    }

    .cfa-changenote-head {
        margin: cfa.space(4) 0 cfa.space(2) cfa.space(3);
    }

    // Serif-navy section titles ("Fields"/"Templates") on CFA hairlines (light
    // mode only), matching the themed deck-options / statistics surfaces.
    .cfa-changenote.is-light :global(.container.light h1) {
        font-family: cfa.$cfa-font-heading;
        font-weight: cfa.$cfa-weight-semibold;
        color: cfa.$cfa-ink;
    }
</style>
