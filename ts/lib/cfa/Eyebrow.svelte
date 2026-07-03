<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

Eyebrow — the small uppercase, letter-spaced over-line that introduces a
heading (the Meldrum "lesson" cue). Calm weight 600 in IBM Plex Sans; coloured
either the AA-safe MM signature green (default) or muted. Never the pass green.
-->
<script lang="ts">
    /** Text to show (falls back to the default slot). */
    export let text: string | undefined = undefined;
    /** `green` = AA-safe MM signature green; `muted` = quiet grey. */
    export let tone: "green" | "muted" = "green";
</script>

<span
    class="cfa-eyebrow"
    class:tone-green={tone === "green"}
    class:tone-muted={tone === "muted"}
>
    <slot>{text}</slot>
</span>

<style lang="scss">
    @use "./tokens" as cfa;

    .cfa-eyebrow {
        display: inline-block;
        margin: 0 0 cfa.space(1);
        font-family: cfa.$cfa-font-body;
        font-size: cfa.$cfa-fs-eyebrow;
        font-weight: cfa.$cfa-weight-semibold;
        line-height: cfa.$cfa-lh-snug;
        letter-spacing: cfa.$cfa-ls-eyebrow;
        text-transform: uppercase;

        &.tone-green {
            color: cfa.$cfa-mm-green;
        }

        &.tone-muted {
            color: cfa.$cfa-muted;
        }
    }
</style>
