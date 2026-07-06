<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<script lang="ts">
    import type { CongratsInfoResponse } from "@generated/anki/scheduler_pb";
    import { congratsInfo } from "@generated/backend";
    import * as tr from "@generated/ftl";
    import { bridgeLink } from "@tslib/bridgecommand";

    import Col from "$lib/components/Col.svelte";
    import Container from "$lib/components/Container.svelte";

    // CFA design system: the study-session "you're done" screen is a flow
    // surface the learner sees at the end of every session — theme it to the
    // CFA product (brand eyebrow + serif navy heading + accent links) so it
    // reads as a purpose-built CFA session-complete screen, not stock Anki.
    import "$lib/cfa/theme.scss";
    import Eyebrow from "$lib/cfa/Eyebrow.svelte";

    import { buildNextLearnMsg } from "./lib";
    import { onMount } from "svelte";

    export let info: CongratsInfoResponse;
    export let refreshPeriodically = true;

    const congrats = tr.schedulingCongratulationsFinished();
    let nextLearnMsg: string;
    $: nextLearnMsg = buildNextLearnMsg(info);
    const today_reviews = tr.schedulingTodayReviewLimitReached();
    const today_new = tr.schedulingTodayNewLimitReached();

    const unburyThem = bridgeLink("unbury", tr.schedulingUnburyThem());
    const buriedMsg = tr.schedulingBuriedCardsFound({ unburyThem });
    const customStudy = bridgeLink("customStudy", tr.schedulingCustomStudy());
    const customStudyMsg = tr.schedulingHowToCustomStudy({
        customStudy,
    });

    onMount(() => {
        if (refreshPeriodically) {
            setInterval(async () => {
                try {
                    info = await congratsInfo({}, { alertOnError: false });
                } catch {
                    console.log("congrats fetch failed");
                }
            }, 60000);
        }
    });
</script>

<Container --gutter-block="1rem" --gutter-inline="2px" breakpoint="sm">
    <Col --col-justify="center">
        <div class="congrats cfa-app">
            <Eyebrow tone="green">EthosPrep · Level II · Session complete</Eyebrow>
            <h1>{congrats}</h1>

            <p>{nextLearnMsg}</p>

            {#if info.reviewRemaining}
                <p>{today_reviews}</p>
            {/if}

            {#if info.newRemaining}
                <p>{today_new}</p>
            {/if}

            {#if info.bridgeCommandsSupported}
                {#if info.haveSchedBuried || info.haveUserBuried}
                    <p>
                        {@html buriedMsg}
                    </p>
                {/if}

                {#if !info.isFilteredDeck}
                    <p>
                        {@html customStudyMsg}
                    </p>
                {/if}
            {/if}

            {#if info.deckDescription}
                <div class="description">
                    {@html info.deckDescription}
                </div>
            {/if}
        </div>
    </Col>
</Container>

<style lang="scss">
    @use "../../lib/cfa/tokens" as cfa;

    // Themed to the CFA design system: a calm, premium "session complete" card
    // (brand serif heading in navy, warm-accent links, CFA muted body) so this
    // end-of-session flow surface no longer reads as stock Anki.
    .congrats {
        margin-top: cfa.space(9);
        max-width: 34em;
        padding: cfa.space(7);
        border: 1px solid cfa.$cfa-line;
        border-radius: cfa.$cfa-radius-block;
        background: cfa.$cfa-bg;
        color: cfa.$cfa-muted;
        font-family: cfa.$cfa-font-body;
        font-size: cfa.$cfa-fs-body;
        line-height: cfa.$cfa-lh-body;

        h1 {
            margin: cfa.space(2) 0 cfa.space(4);
            font-family: cfa.$cfa-font-heading;
            font-size: cfa.$cfa-fs-title;
            font-weight: cfa.$cfa-weight-semibold;
            line-height: cfa.$cfa-lh-heading;
            color: cfa.$cfa-ink;
        }

        p {
            margin: 0 0 cfa.space(3);
        }

        :global(a) {
            color: cfa.$cfa-accent;
            font-weight: cfa.$cfa-weight-semibold;
            text-decoration: none;

            &:hover {
                color: cfa.$cfa-accent-hover;
                text-decoration: underline;
            }
        }
    }

    .description {
        margin-top: cfa.space(4);
        border: 1px solid cfa.$cfa-line;
        border-radius: cfa.$cfa-radius-block;
        background: cfa.$cfa-surface;
        padding: cfa.space(4);
        color: cfa.$cfa-muted;
    }
</style>
