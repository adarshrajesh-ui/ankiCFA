<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

PageHeading — a brand lockup: an optional uppercase Eyebrow over a calm
Source Serif 4 title (weight 400, navy). The one dominant heading per surface.
-->
<script lang="ts">
    import Eyebrow from "./Eyebrow.svelte";

    /** Optional over-line above the title. */
    export let eyebrow: string | undefined = undefined;
    /** Title text (falls back to the default slot). */
    export let title: string | undefined = undefined;
    /** Eyebrow colour. */
    export let eyebrowTone: "green" | "muted" = "green";
    /** Semantic heading level. */
    export let level: "h1" | "h2" | "h3" = "h1";
    /** `title` (28px) or `hero` (40px) display size. */
    export let size: "title" | "hero" = "title";
</script>

<div class="cfa-page-heading">
    {#if eyebrow}
        <Eyebrow text={eyebrow} tone={eyebrowTone} />
    {/if}
    <svelte:element
        this={level}
        class="cfa-page-heading__title"
        class:size-title={size === "title"}
        class:size-hero={size === "hero"}
    >
        <slot>{title}</slot>
    </svelte:element>
</div>

<style lang="scss">
    @use "./tokens" as cfa;

    .cfa-page-heading {
        &__title {
            margin: 0;
            font-family: cfa.$cfa-font-heading;
            font-weight: cfa.$cfa-weight-regular;
            line-height: cfa.$cfa-lh-heading;
            color: cfa.$cfa-ink;

            &.size-title {
                font-size: cfa.$cfa-fs-title;
            }

            &.size-hero {
                font-size: cfa.$cfa-fs-hero;
                line-height: cfa.$cfa-lh-tight;
            }
        }
    }
</style>
