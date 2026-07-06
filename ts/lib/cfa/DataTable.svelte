<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

DataTable — the calm Meldrum table: an UPPERCASE, letter-spaced, muted header
on the cool surface band; comfortable rows separated by hairline rules;
right-aligned (tabular) numeric columns; a 4px hairline container; and a THIN
custom scrollbar (not the chunky native one) when a max-height is set.

Cells render `row[column.key]` by default; use the `cell` slot for custom
rendering (e.g. warn colouring):
    <DataTable {columns} {rows}>
        <svelte:fragment slot="cell" let:column let:value let:row>
            ...custom...
        </svelte:fragment>
    </DataTable>
-->
<script lang="ts">
    import type { CfaColumn, CfaRow } from "./types";

    /** Column definitions (order = display order). */
    export let columns: CfaColumn[] = [];
    /** Row objects, keyed by column `key`. */
    export let rows: CfaRow[] = [];
    /** Enables vertical scroll + the thin custom scrollbar (any CSS length). */
    export let maxHeight: string | undefined = undefined;
    /** Tighter row padding. */
    export let dense = false;
    /** Subtle zebra striping (off by default; hairlines carry the structure). */
    export let zebra = false;
    /** Message shown when there are no rows. */
    export let emptyText = "No rows to show.";

    function display(v: unknown): string {
        return v === undefined || v === null ? "" : String(v);
    }
</script>

<div
    class="cfa-table"
    class:is-dense={dense}
    class:is-zebra={zebra}
    style={maxHeight ? `--cfa-table-max-height:${maxHeight}` : ""}
>
    <div class="cfa-table__scroll" class:is-scrollable={maxHeight != null}>
        <table>
            <thead>
                <tr>
                    {#each columns as column (column.key)}
                        <th
                            class="cfa-table__th"
                            class:is-right={column.align === "right"}
                            style={column.width ? `width:${column.width}` : ""}
                        >
                            {column.label}
                        </th>
                    {/each}
                </tr>
            </thead>
            <tbody>
                {#if rows.length === 0}
                    <tr>
                        <td class="cfa-table__empty" colspan={columns.length}>
                            {emptyText}
                        </td>
                    </tr>
                {:else}
                    {#each rows as row, i (i)}
                        <tr>
                            {#each columns as column (column.key)}
                                <td
                                    class="cfa-table__td"
                                    class:is-right={column.align === "right"}
                                    data-label={column.label}
                                >
                                    <slot
                                        name="cell"
                                        {row}
                                        {column}
                                        value={row[column.key]}
                                    >
                                        {display(row[column.key])}
                                    </slot>
                                </td>
                            {/each}
                        </tr>
                    {/each}
                {/if}
            </tbody>
        </table>
    </div>
</div>

<style lang="scss">
    @use "./tokens" as cfa;

    .cfa-table {
        background: cfa.$cfa-bg;
        border: 1px solid cfa.$cfa-line;
        border-radius: cfa.$cfa-radius-block;
        overflow: hidden; // clip the header/rows to the rounded container

        &__scroll {
            width: 100%;
            overflow: auto;

            &.is-scrollable {
                max-height: var(--cfa-table-max-height, none);
            }

            // Thin, calm custom scrollbar (Firefox + WebKit/Blink).
            scrollbar-width: thin;
            scrollbar-color: cfa.$cfa-faint transparent;

            &::-webkit-scrollbar {
                width: 8px;
                height: 8px;
            }
            &::-webkit-scrollbar-track {
                background: transparent;
            }
            &::-webkit-scrollbar-thumb {
                background: cfa.$cfa-faint;
                border-radius: cfa.$cfa-radius-pill;
                border: 2px solid cfa.$cfa-bg; // inset so the thumb reads slim
            }
            &::-webkit-scrollbar-thumb:hover {
                background: cfa.$cfa-muted;
            }
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-family: cfa.$cfa-font-body;
        }

        &__th {
            position: sticky;
            top: 0;
            z-index: 1;
            background: cfa.$cfa-surface;
            color: cfa.$cfa-muted;
            font-size: cfa.$cfa-fs-meta;
            font-weight: cfa.$cfa-weight-semibold;
            letter-spacing: cfa.$cfa-ls-caps;
            text-transform: uppercase;
            text-align: left;
            padding: cfa.space(2) cfa.space(3);
            border-bottom: 1px solid cfa.$cfa-line;
            white-space: nowrap;

            &.is-right {
                text-align: right;
            }
        }

        &__td {
            font-size: cfa.$cfa-fs-body;
            color: cfa.$cfa-ink;
            padding: cfa.space(3) cfa.space(3);
            border-bottom: 1px solid cfa.$cfa-line;
            vertical-align: middle;

            &.is-right {
                text-align: right;
                font-variant-numeric: tabular-nums;
            }
        }

        &.is-dense &__td {
            padding: cfa.space(2) cfa.space(3);
        }

        &.is-zebra tbody tr:nth-child(even) &__td {
            background: cfa.$cfa-surface;
        }

        tbody tr:last-child &__td {
            border-bottom: none;
        }

        &__empty {
            padding: cfa.space(6) cfa.space(3);
            text-align: center;
            color: cfa.$cfa-muted;
            font-size: cfa.$cfa-fs-body;
        }
    }

    @media (max-width: 640px) {
        .cfa-table {
            overflow: visible;

            &__scroll,
            &__scroll.is-scrollable {
                max-height: none;
                overflow: visible;
            }

            table,
            thead,
            tbody,
            tr,
            th,
            td {
                display: block;
            }

            thead {
                display: none;
            }

            tr {
                border-bottom: 1px solid cfa.$cfa-line;
            }

            tbody tr:last-child {
                border-bottom: 0;
            }

            &__td,
            &.is-dense &__td {
                display: grid;
                grid-template-columns: minmax(112px, 0.72fr) minmax(0, 1fr);
                gap: cfa.space(3);
                align-items: center;
                min-height: 46px;
                padding: cfa.space(3);
                text-align: left;
                border-bottom: 0;
                overflow-wrap: anywhere;
            }

            &__td.is-right {
                text-align: left;
            }

            &__td::before {
                content: attr(data-label);
                color: cfa.$cfa-muted;
                font-size: cfa.$cfa-fs-meta;
                font-weight: cfa.$cfa-weight-semibold;
                letter-spacing: cfa.$cfa-ls-caps;
                text-transform: uppercase;
            }
        }
    }
</style>
