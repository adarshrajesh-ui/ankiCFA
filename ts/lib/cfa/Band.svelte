<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

Band — a quiet fallback score row: a name + meaning label on the left and the
formatted value (a serif range) on the right, separated by a single hairline
rule. The calm, compact alternative to a full StatCard when several honest
scores are listed together. Abstain renders the value in the warn tone.
-->
<script lang="ts">
    import type { CfaTone } from "./types";

    /** Score name, e.g. "Memory". */
    export let name: string;
    /** One-line meaning, e.g. "weighted by topic exam weight". */
    export let meaning: string | undefined = undefined;
    /** Formatted value / range (falls back to the default slot). */
    export let value: string | undefined = undefined;
    /** Value colour. */
    export let tone: CfaTone = "neutral";
    /** When true the value reads as a warn-toned "not enough data". */
    export let abstain = false;
</script>

<div class="cfa-band">
    <div class="cfa-band__label">
        <span class="cfa-band__name">{name}</span>
        {#if meaning}<span class="cfa-band__meaning">— {meaning}</span>{/if}
    </div>
    <div
        class="cfa-band__value"
        class:tone-pass={!abstain && tone === "pass"}
        class:tone-fail={!abstain && tone === "fail"}
        class:tone-warn={abstain || tone === "warn"}
        class:tone-neutral={!abstain && tone === "neutral"}
    >
        <slot>{value}</slot>
    </div>
</div>

<style lang="scss">
    @use "./tokens" as cfa;

    .cfa-band {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: cfa.space(4);
        padding: cfa.space(3) 0;
        border-top: 1px solid cfa.$cfa-line;

        &__label {
            font-family: cfa.$cfa-font-body;
            font-size: cfa.$cfa-fs-body;
            line-height: cfa.$cfa-lh-snug;
        }

        &__name {
            font-weight: cfa.$cfa-weight-semibold;
            color: cfa.$cfa-ink;
        }

        &__meaning {
            color: cfa.$cfa-muted;
        }

        &__value {
            flex: none;
            font-family: cfa.$cfa-font-heading;
            font-size: cfa.$cfa-fs-subtitle;
            font-weight: cfa.$cfa-weight-regular;
            line-height: cfa.$cfa-lh-tight;
            font-variant-numeric: tabular-nums;
            text-align: right;
            white-space: nowrap;

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
    }
</style>
