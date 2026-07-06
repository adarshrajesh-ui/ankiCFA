<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->

<script lang="ts">
    import { createEventDispatcher } from "svelte";

    import type { CfaProductNavKey } from "./productNav";
    import { productNavItems } from "./productNav";

    export let active: CfaProductNavKey;
    export let subtitle = "CFA Level II";
    export let syncStatus = "";
    export let ariaLabel = "CFA product navigation";

    const dispatch = createEventDispatcher<{ navigate: string }>();

    $: items = productNavItems(active);

    function go(cmd: string): void {
        dispatch("navigate", cmd);
    }
</script>

<nav class="cfa-product-nav" data-active={active} aria-label={ariaLabel}>
    <div class="cfa-product-nav__in">
        <div class="cfa-product-nav__brand">
            EthosPrep
            <small>{subtitle}</small>
        </div>
        <div class="cfa-product-nav__tabs">
            {#each items as item (item.key)}
                <button
                    type="button"
                    class:on={item.active}
                    class:is-action={item.key === "sync"}
                    aria-current={item.active ? "page" : undefined}
                    aria-label={item.key === "sync" && syncStatus
                        ? `${item.ariaLabel}: ${syncStatus}`
                        : item.ariaLabel}
                    title={item.key === "sync" && syncStatus ? syncStatus : item.sub}
                    on:click={() => go(item.cmd)}
                >
                    {#if item.key === "sync"}
                        <span class="cfa-product-nav__dot" aria-hidden="true"></span>
                    {/if}
                    <span class="cfa-product-nav__label">{item.label}</span>
                    <span class="cfa-product-nav__short-label">{item.shortLabel}</span>
                </button>
            {/each}
        </div>
    </div>
</nav>

<style lang="scss">
    @use "./tokens" as cfa;

    .cfa-product-nav {
        position: sticky;
        top: 20px;
        z-index: 30;
        width: 100%;
        max-width: 100%;
        overflow: hidden;
        background: rgba(255, 255, 255, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.72);
        border-radius: 28px;
        box-shadow: 0 14px 50px rgba(5, 59, 69, 0.1);
        backdrop-filter: blur(22px) saturate(1.25);
        -webkit-backdrop-filter: blur(22px) saturate(1.25);
    }

    .cfa-product-nav__in {
        display: flex;
        flex-wrap: wrap;
        gap: 20px;
        align-items: center;
        min-width: 0;
        padding: 15px 18px;
    }

    .cfa-product-nav__brand {
        min-width: 0;
        color: cfa.$cfa-ink;
        font-family: cfa.$cfa-font-heading;
        font-size: 24px;
        font-weight: cfa.$cfa-weight-semibold;
        letter-spacing: -0.01em;
        white-space: nowrap;
    }

    .cfa-product-nav__brand small {
        display: block;
        overflow: hidden;
        color: cfa.$cfa-primary;
        font-family: cfa.$cfa-font-body;
        font-size: 11px;
        font-weight: cfa.$cfa-weight-semibold;
        letter-spacing: 0.16em;
        text-overflow: ellipsis;
        text-transform: uppercase;
        white-space: nowrap;
    }

    .cfa-product-nav__tabs {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
        align-items: center;
        min-width: 0;
        max-width: 100%;
        margin-left: auto;
    }

    .cfa-product-nav__tabs button {
        display: inline-flex;
        gap: 8px;
        align-items: center;
        justify-content: center;
        min-height: 44px;
        padding: 10px 16px;
        color: cfa.$cfa-muted;
        font: inherit;
        font-size: 16px;
        font-weight: cfa.$cfa-weight-semibold;
        line-height: 1;
        white-space: nowrap;
        cursor: pointer;
        background: transparent;
        border: 0;
        border-radius: cfa.$cfa-radius-pill;
        scroll-snap-align: start;
        -webkit-tap-highlight-color: transparent;
    }

    .cfa-product-nav__tabs button:hover,
    .cfa-product-nav__tabs button:focus-visible,
    .cfa-product-nav__tabs button.on {
        color: cfa.$cfa-primary;
        background: rgba(20, 184, 177, 0.12);
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.65);
    }

    .cfa-product-nav__tabs button:focus-visible {
        outline: 3px solid rgba(20, 184, 177, 0.36);
        outline-offset: 2px;
    }

    .cfa-product-nav__tabs button.on {
        cursor: default;
    }

    .cfa-product-nav__tabs button.is-action {
        border: 1px solid rgba(20, 184, 177, 0.22);
        background: rgba(228, 246, 245, 0.58);
    }

    .cfa-product-nav__dot {
        width: 8px;
        height: 8px;
        flex: 0 0 auto;
        background: cfa.$cfa-primary;
        border-radius: cfa.$cfa-radius-pill;
    }

    .cfa-product-nav__short-label {
        display: none;
    }

    @media (max-width: 980px) {
        .cfa-product-nav__in {
            gap: 12px;
            padding: 13px 14px;
        }

        .cfa-product-nav__tabs button {
            min-height: 42px;
            padding: 9px 12px;
            font-size: 15px;
        }

        .cfa-product-nav__label {
            display: none;
        }

        .cfa-product-nav__short-label {
            display: inline;
        }
    }

    @media (max-width: 720px) {
        .cfa-product-nav {
            top: 10px;
            border-radius: 22px;
        }

        .cfa-product-nav__in {
            display: grid;
            grid-template-columns: minmax(0, 1fr);
            gap: 10px;
            padding: 12px;
        }

        .cfa-product-nav__brand {
            font-size: 22px;
        }

        .cfa-product-nav__tabs {
            flex-wrap: nowrap;
            width: 100%;
            margin-left: 0;
            padding-bottom: 2px;
            overflow-x: auto;
            overscroll-behavior-x: contain;
            scroll-snap-type: x proximity;
            scrollbar-width: none;
            -webkit-overflow-scrolling: touch;
        }

        .cfa-product-nav__tabs::-webkit-scrollbar {
            display: none;
        }

        .cfa-product-nav__tabs button {
            flex: 0 0 auto;
            min-width: 68px;
            padding: 9px 12px;
            font-size: 14px;
        }
    }

    @media (max-width: 380px) {
        .cfa-product-nav__short-label {
            display: inline;
        }
    }
</style>
