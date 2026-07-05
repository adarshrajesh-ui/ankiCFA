<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<script context="module" lang="ts">
    export interface Importer {
        doImport: () => Promise<ImportResponse>;
    }
</script>

<script lang="ts">
    import type { ImportResponse } from "@generated/anki/import_export_pb";
    import { importDone } from "@generated/backend";

    import "$lib/cfa/theme.scss";

    import BackendProgressIndicator from "$lib/components/BackendProgressIndicator.svelte";
    import Container from "$lib/components/Container.svelte";
    import ErrorPage from "$lib/components/ErrorPage.svelte";
    import Eyebrow from "$lib/cfa/Eyebrow.svelte";
    import { pageTheme } from "$lib/sveltelib/theme";
    import StickyHeader from "./StickyHeader.svelte";

    import ImportLogPage from "./ImportLogPage.svelte";

    export let path: string;
    export let importer: Importer;
    export const noOptions: boolean = false;

    let importResponse: ImportResponse | undefined = undefined;
    let error: Error | undefined = undefined;
    let importing = noOptions;

    async function onImport(): Promise<ImportResponse> {
        const result = await importer.doImport();
        await importDone({});
        importing = false;
        return result;
    }
</script>

<div class="cfa-import cfa-app" class:is-light={!$pageTheme.isDark}>
    {#if error}
        <ErrorPage {error} />
    {:else if importResponse}
        <ImportLogPage response={importResponse} />
    {:else if importing}
        <BackendProgressIndicator
            task={onImport}
            bind:result={importResponse}
            bind:error
        />
    {:else}
        <div class="cfa-import-head">
            <Eyebrow>ankiCFA · Level II · Import</Eyebrow>
        </div>
        <div class="pre-import-page">
            <StickyHeader {path} onImport={() => (importing = true)} />
            <Container
                breakpoint="sm"
                --gutter-inline="0.25rem"
                --gutter-block="0.5rem"
                class="container-columns"
            >
                <slot />
            </Container>
        </div>
    {/if}
</div>

<style lang="scss">
    @use "../../lib/cfa/tokens" as cfa;

    :global(.row) {
        // rows have negative margins by default
        --bs-gutter-x: 0;
        margin-bottom: 0.5rem;
    }

    .pre-import-page {
        margin: 0 auto;
    }

    // CFA chrome for the shared Import shell (Anki-package + CSV import flows and
    // the post-import results log all render through this component). Scoped to
    // `.cfa-import` so it only retones these surfaces; the stock-Anki blue
    // interactive tokens are overridden to CFA navy/accent so the primary Import
    // button, focus rings, links, and selected rows read as CFA rather than stock
    // Anki. Light mode only — the app's dark theme keeps its own tokens.
    .cfa-import.is-light {
        min-height: 100vh;
        background: cfa.$cfa-page;

        --button-primary-bg: #{cfa.$cfa-primary};
        --button-primary-gradient-start: #{cfa.$cfa-primary};
        --button-primary-gradient-end: #{cfa.$cfa-primary};
        --border-focus: #{cfa.$cfa-accent};
        --fg-link: #{cfa.$cfa-accent};
        --selected-bg: #{cfa.$cfa-accent-soft};
    }

    .cfa-import-head {
        margin: cfa.space(4) 0 cfa.space(2) cfa.space(3);
    }

    // Serif-navy section titles (e.g. "Import options" / "Overview" / "Details")
    // on CFA hairlines (light mode only), matching the themed deck-options /
    // change-notetype / statistics surfaces.
    .cfa-import.is-light :global(.container.light h1) {
        font-family: cfa.$cfa-font-heading;
        font-weight: cfa.$cfa-weight-semibold;
        color: cfa.$cfa-ink;
    }
</style>
