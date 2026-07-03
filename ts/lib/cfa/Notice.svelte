<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

Notice — a short, calm status line carrying a semantic tone (warn / pass /
fail / info). A soft tinted 4px strip with a thin coloured left rule and
tone-coloured text; never a loud alert. The pass/fail/warn triad is preserved.
-->
<script lang="ts">
    /** Semantic tone. */
    export let tone: "warn" | "pass" | "fail" | "info" = "warn";
    /** Text to show (falls back to the default slot). */
    export let text: string | undefined = undefined;
</script>

<div
    class="cfa-notice"
    class:tone-warn={tone === "warn"}
    class:tone-pass={tone === "pass"}
    class:tone-fail={tone === "fail"}
    class:tone-info={tone === "info"}
    role="status"
>
    <slot>{text}</slot>
</div>

<style lang="scss">
    @use "./tokens" as cfa;

    .cfa-notice {
        padding: cfa.space(2) cfa.space(3);
        border-radius: cfa.$cfa-radius-block;
        border-left: 3px solid transparent;
        font-family: cfa.$cfa-font-body;
        font-size: cfa.$cfa-fs-body;
        font-weight: cfa.$cfa-weight-medium;
        line-height: cfa.$cfa-lh-body;

        &.tone-warn {
            background: cfa.$cfa-warn-soft;
            border-left-color: cfa.$cfa-warn;
            color: cfa.$cfa-warn;
        }
        &.tone-pass {
            background: cfa.$cfa-pass-soft;
            border-left-color: cfa.$cfa-pass;
            color: cfa.$cfa-pass;
        }
        &.tone-fail {
            background: cfa.$cfa-fail-soft;
            border-left-color: cfa.$cfa-fail;
            color: cfa.$cfa-fail;
        }
        &.tone-info {
            background: cfa.$cfa-surface;
            border-left-color: cfa.$cfa-faint;
            color: cfa.$cfa-muted;
        }
    }
</style>
