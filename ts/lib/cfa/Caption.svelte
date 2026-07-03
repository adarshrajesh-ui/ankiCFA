<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

Caption — small, quiet muted footnote / caption text at a comfortable 1.5
leading. Defaults to the AA-safe muted grey (not faint, which fails AA at these
sizes). Renders inline when `inline` is set.
-->
<script lang="ts">
    /** Text to show (falls back to the default slot). */
    export let text: string | undefined = undefined;
    /** `muted` is AA-safe; `faint` is quieter (use only for large text). */
    export let tone: "muted" | "faint" = "muted";
    /** Render as an inline span instead of a block paragraph. */
    export let inline = false;
</script>

{#if inline}
    <span
        class="cfa-caption"
        class:tone-muted={tone === "muted"}
        class:tone-faint={tone === "faint"}
    >
        <slot>{text}</slot>
    </span>
{:else}
    <p
        class="cfa-caption is-block"
        class:tone-muted={tone === "muted"}
        class:tone-faint={tone === "faint"}
    >
        <slot>{text}</slot>
    </p>
{/if}

<style lang="scss">
    @use "./tokens" as cfa;

    .cfa-caption {
        font-family: cfa.$cfa-font-body;
        font-size: cfa.$cfa-fs-meta;
        font-weight: cfa.$cfa-weight-regular;
        line-height: cfa.$cfa-lh-body;

        &.is-block {
            margin: 0;
        }

        &.tone-muted {
            color: cfa.$cfa-muted;
        }
        &.tone-faint {
            color: cfa.$cfa-faint;
        }
    }
</style>
