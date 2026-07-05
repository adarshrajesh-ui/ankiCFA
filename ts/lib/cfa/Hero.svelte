<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

Hero / Verdict — the headline call. A BIG calm Source Serif 4 headline
(weight 400) carrying the verdict in a semantic colour, a quiet muted
sub-figure, a sans lead line and a small caveat. Chrome is intentionally calm:
a hairline border + a thin semantic left spine (NOT a saturated alert ring).
-->
<script lang="ts">
    import type { CfaTone } from "./types";

    /** The big serif verdict line (falls back to the `headline` slot). */
    export let headline: string | undefined = undefined;
    /** Semantic colour of the headline + spine. */
    export let tone: CfaTone = "neutral";
    /** A quiet muted sub-figure shown after the headline, e.g. "p = 0.82". */
    export let sub: string | undefined = undefined;
    /** A small caveat line below the lead (rendered in the warn tone). */
    export let note: string | undefined = undefined;
    /** Show the 3px semantic left spine. */
    export let spine = true;
    /** `hero` (40px) or `title` (28px) headline size. */
    export let size: "hero" | "title" = "hero";
</script>

<section
    class="cfa-hero"
    class:has-spine={spine}
    class:tone-pass={tone === "pass"}
    class:tone-fail={tone === "fail"}
    class:tone-warn={tone === "warn"}
    class:tone-neutral={tone === "neutral"}
>
    <p
        class="cfa-hero__headline"
        class:size-hero={size === "hero"}
        class:size-title={size === "title"}
    >
        <span class="cfa-hero__call"><slot name="headline">{headline}</slot></span>
        {#if sub}<span class="cfa-hero__sub">{sub}</span>{/if}
    </p>

    <div class="cfa-hero__lead"><slot /></div>

    {#if note}
        <p class="cfa-hero__note">{note}</p>
    {/if}
</section>

<style lang="scss">
    @use "./tokens" as cfa;

    .cfa-hero {
        margin: 0;
        padding: cfa.space(5) cfa.space(6);
        background: cfa.$cfa-bg;
        border: 1px solid cfa.$cfa-line;
        border-radius: cfa.$cfa-radius-block;

        &.has-spine {
            border-left-width: 3px;
        }

        // Semantic spine colour (only visible when has-spine widens the border).
        &.tone-pass {
            border-left-color: cfa.$cfa-pass;
        }
        &.tone-fail {
            border-left-color: cfa.$cfa-fail;
        }
        &.tone-warn {
            border-left-color: cfa.$cfa-warn;
        }
        &.tone-neutral {
            border-left-color: cfa.$cfa-line;
        }

        &__headline {
            margin: 0;
            font-family: cfa.$cfa-font-heading;
            font-weight: cfa.$cfa-weight-regular;
            line-height: cfa.$cfa-lh-tight;

            &.size-hero {
                font-size: cfa.$cfa-fs-hero;
            }
            &.size-title {
                font-size: cfa.$cfa-fs-title;
            }
        }

        // Verdict colour lives on the call text (semantic; carries the meaning).
        &.tone-pass &__call {
            color: cfa.$cfa-pass;
        }
        &.tone-fail &__call {
            color: cfa.$cfa-fail;
        }
        &.tone-warn &__call {
            color: cfa.$cfa-warn;
        }
        &.tone-neutral &__call {
            color: cfa.$cfa-ink;
        }

        &__sub {
            margin-left: cfa.space(2);
            font-family: cfa.$cfa-font-body;
            font-size: cfa.$cfa-fs-lead;
            font-weight: cfa.$cfa-weight-regular;
            color: cfa.$cfa-faint-ink;
        }

        &__lead {
            margin-top: cfa.space(2);
            font-family: cfa.$cfa-font-body;
            font-size: cfa.$cfa-fs-body;
            line-height: cfa.$cfa-lh-body;
            color: cfa.$cfa-ink;

            &:empty {
                display: none;
            }
        }

        &__note {
            margin: cfa.space(2) 0 0;
            font-family: cfa.$cfa-font-body;
            font-size: cfa.$cfa-fs-meta;
            line-height: cfa.$cfa-lh-body;
            color: cfa.$cfa-warn;
        }
    }
</style>
