<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

StatCard — VALUE-FIRST, the stats-band pattern: a big calm Source Serif 4
number (weight 400) on top, a small muted label stacked below, and an optional
faint sub-line. Flat 4px card with ~16px padding, or a chrome-less `bare`
variant separated by whitespace only (like the real stats band).
-->
<script lang="ts">
    import type { CfaTone } from "./types";

    /** The big serif value, e.g. "82%", "68–74%", "250,000+". */
    export let value: string | undefined = undefined;
    /** The small muted label under the value. */
    export let label: string | undefined = undefined;
    /** Optional faint sub-line, e.g. "midpoint 71%". */
    export let sub: string | undefined = undefined;
    /** Value colour (default neutral = navy ink; keep semantics for abstain). */
    export let tone: CfaTone = "neutral";
    /** `card` = flat hairline card; `bare` = whitespace-only stack. */
    export let variant: "card" | "bare" = "card";
</script>

<div
    class="cfa-stat"
    class:variant-card={variant === "card"}
    class:variant-bare={variant === "bare"}
>
    <div
        class="cfa-stat__value"
        class:tone-pass={tone === "pass"}
        class:tone-fail={tone === "fail"}
        class:tone-warn={tone === "warn"}
        class:tone-neutral={tone === "neutral"}
    >
        <slot name="value">{value}</slot>
    </div>
    <div class="cfa-stat__label"><slot>{label}</slot></div>
    {#if sub}
        <div class="cfa-stat__sub">{sub}</div>
    {/if}
</div>

<style lang="scss">
    @use "./tokens" as cfa;

    .cfa-stat {
        display: flex;
        flex-direction: column;
        gap: cfa.space(1);

        &.variant-card {
            padding: cfa.space(4);
            background: cfa.$cfa-bg;
            border: 1px solid cfa.$cfa-line;
            border-radius: cfa.$cfa-radius-block;
        }

        &__value {
            font-family: cfa.$cfa-font-heading;
            font-size: cfa.$cfa-fs-stat;
            font-weight: cfa.$cfa-weight-regular;
            line-height: cfa.$cfa-lh-tight;
            font-variant-numeric: tabular-nums;

            &.tone-neutral {
                color: cfa.$cfa-ink;
            }
            &.tone-pass {
                color: cfa.$cfa-pass;
            }
            &.tone-fail {
                color: cfa.$cfa-fail;
            }
            &.tone-warn {
                color: cfa.$cfa-warn;
            }
        }

        &__label {
            font-family: cfa.$cfa-font-body;
            font-size: cfa.$cfa-fs-small;
            font-weight: cfa.$cfa-weight-regular;
            line-height: cfa.$cfa-lh-snug;
            color: cfa.$cfa-muted;
        }

        &__sub {
            font-family: cfa.$cfa-font-body;
            font-size: cfa.$cfa-fs-meta;
            line-height: cfa.$cfa-lh-snug;
            color: cfa.$cfa-faint;
        }
    }
</style>
