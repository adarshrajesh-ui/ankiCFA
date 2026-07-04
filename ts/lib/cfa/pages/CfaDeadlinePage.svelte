<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

CfaDeadlinePage — the "Peak on exam day" Deadline planner surface, rebuilt as a
self-contained web page component on the shared CFA design system (calm, premium
finance-education; modelled on markmeldrum.com).

Layout, top → bottom:
  * a serif PageHeading lockup + a date-picker row (input + "Set exam date" pill),
  * a quiet summary caption (exam date · card count · data source),
  * either a warn Notice + helper caption (empty state) or the ranked DataTable
    (weakest-first): a de-emphasised card column, right-aligned tabular numerics,
    and warn-coloured predicted recall for at-risk rows (recall < 0.85),
  * a muted explanatory footer.

Persistence is intentionally NOT wired here: pressing "Set exam date" calls the
`onSetExamDate` callback so the integration layer can drive the real
SetCfaExamDate RPC.
-->
<script lang="ts">
    import {
        Caption,
        DataTable,
        Notice,
        PageHeading,
        type CfaColumn,
        type CfaRow,
        type DeadlinePayload,
        type DeadlineRow,
    } from "$lib/cfa";

    /** The full Deadline payload (exam date, ranked rows, provenance). */
    export let data: DeadlinePayload;
    /**
     * Called with the picked ISO date when "Set exam date" is pressed. The real
     * SetCfaExamDate persistence is wired at integration; here it stays a plain
     * callback so the component is self-contained and testable.
     */
    export let onSetExamDate: (iso: string) => void = () => {};

    // Editable local copy backing the <input type="date">.
    let examDate = data.examDate;

    const columns: CfaColumn[] = [
        { key: "cardId", label: "Card" },
        { key: "predictedRecall", label: "Predicted recall @ exam", align: "right" },
        {
            key: "suggestedIntervalDays",
            label: "Capped interval (days)",
            align: "right",
        },
    ];

    $: isEmpty = data.headerMode === "empty";
    $: cardWord = data.cardCount === 1 ? "card" : "cards";
    $: summary = `Exam date ${data.examDate} · ${data.cardCount} ${cardWord} · source: ${data.dataSource}`;

    function formatRecall(recall: number): string {
        return `${(recall * 100).toFixed(1)}%`;
    }

    function handleSetExamDate(): void {
        onSetExamDate(examDate);
    }
</script>

<div class="cfa-app cfa-deadline">
    <div class="cfa-deadline__inner">
        <header class="cfa-deadline__head">
            <PageHeading eyebrow="Peak on exam day" title="Deadline planner" />

            <div class="cfa-deadline__controls">
                <label class="cfa-deadline__date-label" for="cfa-exam-date">
                    Exam date
                </label>
                <input
                    id="cfa-exam-date"
                    class="cfa-deadline__date-input"
                    type="date"
                    bind:value={examDate}
                />
                <button
                    class="cfa-deadline__set"
                    type="button"
                    on:click={handleSetExamDate}
                >
                    Set exam date
                </button>
            </div>
        </header>

        <Caption>{summary}</Caption>

        {#if isEmpty}
            <Notice tone="warn" text="No due cards to rank yet." />
            <Caption>
                Set your exam date and review a few cards — once cards fall due, their
                predicted exam-day recall is ranked weakest-first here.
            </Caption>
        {:else}
            <DataTable
                {columns}
                rows={data.rows as unknown as CfaRow[]}
                maxHeight="460px"
                zebra
            >
                <svelte:fragment slot="cell" let:column let:row>
                    {@const deadlineRow = row as unknown as DeadlineRow}
                    {#if column.key === "cardId"}
                        <span class="cfa-deadline__cardid">{deadlineRow.cardId}</span>
                    {:else if column.key === "predictedRecall"}
                        <span
                            class="cfa-deadline__recall"
                            class:is-warn={deadlineRow.warnLowRecall}
                        >
                            {formatRecall(deadlineRow.predictedRecall)}
                        </span>
                    {:else}
                        {deadlineRow.suggestedIntervalDays}
                    {/if}
                </svelte:fragment>
            </DataTable>
        {/if}

        <footer class="cfa-deadline__foot">
            <Caption>{data.footerText}</Caption>
        </footer>
    </div>
</div>

<style lang="scss">
    @use "../tokens" as cfa;

    .cfa-deadline {
        min-height: 100%;
        padding: cfa.space(8) cfa.space(6); // 40px 24px, on the 8px scale
    }

    .cfa-deadline__inner {
        display: flex;
        flex-direction: column;
        gap: cfa.space(6); // 24px section rhythm
        max-width: 820px;
        margin: 0 auto;
    }

    .cfa-deadline__head {
        display: flex;
        flex-direction: column;
        gap: cfa.space(5); // 20px between the lockup and the controls
    }

    .cfa-deadline__controls {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: cfa.space(3); // 12px
    }

    .cfa-deadline__date-label {
        font-family: cfa.$cfa-font-body;
        font-size: cfa.$cfa-fs-body;
        color: cfa.$cfa-muted; // AA-safe quiet field label
    }

    .cfa-deadline__date-input {
        font-family: cfa.$cfa-font-body;
        font-size: cfa.$cfa-fs-body;
        color: cfa.$cfa-ink;
        background: cfa.$cfa-bg;
        border: 1px solid cfa.$cfa-line;
        border-radius: cfa.$cfa-radius-block; // 4px, matches the site input
        padding: cfa.space(2) cfa.space(3); // 8px 12px
        line-height: cfa.$cfa-lh-snug;

        &:focus {
            outline: none;
            border-color: cfa.$cfa-muted; // calm, no colour shift
        }
    }

    .cfa-deadline__set {
        font-family: cfa.$cfa-font-body;
        font-size: cfa.$cfa-fs-body;
        font-weight: cfa.$cfa-weight-semibold; // 600 — calm, never bold display
        color: cfa.$cfa-bg; // white on navy (~14.4:1, AA)
        background: cfa.$cfa-primary;
        border: none;
        border-radius: cfa.$cfa-radius-pill; // brand pill CTA
        padding: cfa.space(2) cfa.space(5); // 8px 20px
        cursor: pointer;
        transition: background 120ms ease;

        &:hover {
            background: cfa.$cfa-primary-hover;
        }

        &:focus-visible {
            outline: 2px solid cfa.$cfa-primary;
            outline-offset: 2px;
        }
    }

    // De-emphasise the card identifier so a column of near-identical big
    // integers recedes behind the figures that matter.
    .cfa-deadline__cardid {
        color: cfa.$cfa-muted;
        font-size: cfa.$cfa-fs-small; // 13px
    }

    .cfa-deadline__recall {
        font-variant-numeric: tabular-nums;

        &.is-warn {
            color: cfa.$cfa-warn; // at-risk (recall < 0.85), semantic preserved
        }
    }

    .cfa-deadline__foot {
        margin-top: cfa.space(1);
    }
</style>
