<script lang="ts">
    import { bridgeCommand } from "@tslib/bridgecommand";

    import type { CfaStudyDeck, CfaStudyPayload } from "$lib/cfa";

    import {
        integer,
        masteryPct,
        masteryWidth,
        STUDY_NAV,
        syncChipLabel,
        visibleStudyDecks,
    } from "./study";

    export let data: CfaStudyPayload;

    $: decks = visibleStudyDecks(data.decks);
    $: selectedDeck = decks[0] ?? null;
    $: syncLabel = syncChipLabel(data);

    function go(cmd: string): void {
        bridgeCommand(cmd);
    }

    function deckCmd(prefix: "study" | "add", deck: CfaStudyDeck | null): string {
        return deck ? `${prefix}:${deck.id}` : prefix;
    }
</script>

<div class="cfa-app cfa-study">
    <main class="cfa-study__page">
        <nav class="cfa-study__appbar" aria-label="CFA Study sections">
            <div class="cfa-study__appbar-in">
                <div class="cfa-study__brand">ankiCFA <small>CFA Level II</small></div>
                <div class="cfa-study__tabs">
                    {#each STUDY_NAV as item}
                        <button
                            type="button"
                            class:on={item.active}
                            aria-current={item.active ? "page" : undefined}
                            on:click={() => go(item.cmd)}
                        >
                            {item.label}
                        </button>
                    {/each}
                </div>
                <button type="button" class="cfa-study__sync-chip" on:click={() => go("cfa:sync-settings")}>
                    <span class="cfa-study__dot"></span>{syncLabel}
                </button>
            </div>
        </nav>

        <section class="cfa-study__hero">
            <div class="cfa-study__hero-grid">
                <div>
                    <div class="cfa-study__eyebrow">Study - Deck Command Center</div>
                    <h1>Your CFA decks, ready to build and study.</h1>
                    <p class="cfa-study__lede">
                        The Study tab now starts with the deck library. Create a
                        new deck, see what is due, and add cards to any topic
                        without digging through secondary screens.
                    </p>
                    <div class="cfa-study__hero-actions">
                        <button type="button" class="cfa-study__btn primary" on:click={() => go("create")}>
                            Create new deck
                        </button>
                        <button type="button" class="cfa-study__btn secondary" on:click={() => go(deckCmd("add", selectedDeck))}>
                            Add card to selected deck
                        </button>
                        <button type="button" class="cfa-study__btn ghost" on:click={() => go("import")}>
                            Import CFA notes
                        </button>
                    </div>
                    <div class="cfa-study__metric-row">
                        <div class="cfa-study__metric"><strong>{integer(data.totals.activeDecks)}</strong><span>active decks</span></div>
                        <div class="cfa-study__metric"><strong>{integer(data.totals.dueToday)}</strong><span>cards due today</span></div>
                        <div class="cfa-study__metric"><strong>{integer(data.totals.newQueued)}</strong><span>new cards queued</span></div>
                    </div>
                </div>
                <aside class="cfa-study__create-card">
                    <div>
                        <div class="cfa-study__eyebrow">Fast create</div>
                        <h2>New deck in one step.</h2>
                        <p>Choose a CFA topic, name the deck, and start adding exam-style prompts immediately.</p>
                    </div>
                    <button type="button" class="cfa-study__btn primary" on:click={() => go("create-cfa")}>
                        Create CFA deck
                    </button>
                </aside>
            </div>
        </section>

        <section class="cfa-study__workspace-grid">
            <div class="cfa-study__glass-card">
                <div class="cfa-study__card-title">
                    <div>
                        <div class="cfa-study__eyebrow">Decks</div>
                        <h2>Pick a deck to study or expand</h2>
                    </div>
                    <span class="cfa-study__tag">Top 3 by urgency</span>
                </div>
                <div class="cfa-study__deck-grid">
                    {#if decks.length === 0}
                        <article class="cfa-study__deck-card featured">
                            <div class="cfa-study__deck-top">
                                <div class="cfa-study__deck-icon"></div>
                                <div>
                                    <h3>No CFA decks yet</h3>
                                    <p>Create a CFA deck or import notes to start building the workspace.</p>
                                </div>
                            </div>
                            <div class="cfa-study__deck-actions single">
                                <button type="button" class="cfa-study__btn primary small" on:click={() => go("create-cfa")}>
                                    Create CFA deck
                                </button>
                            </div>
                        </article>
                    {:else}
                        {#each decks as deck}
                            <article class="cfa-study__deck-card" class:featured={deck.featured}>
                                <div class="cfa-study__deck-top">
                                    <div class="cfa-study__deck-icon"></div>
                                    <div>
                                        <h3>{deck.name}</h3>
                                        <p>{deck.description}</p>
                                    </div>
                                </div>
                                <div class="cfa-study__deck-meta">
                                    <div class="cfa-study__deck-stat"><b>{integer(deck.due)}</b><span>due</span></div>
                                    <div class="cfa-study__deck-stat"><b>{integer(deck.newCount)}</b><span>new</span></div>
                                    <div class="cfa-study__deck-stat"><b>{masteryPct(deck)}</b><span>mastery</span></div>
                                </div>
                                <div class="cfa-study__mastery" aria-hidden="true"><i style="width: {masteryWidth(deck)}%"></i></div>
                                <div class="cfa-study__deck-actions">
                                    <button type="button" class="cfa-study__btn primary small" on:click={() => go(deckCmd("study", deck))}>
                                        Study deck
                                    </button>
                                    <button type="button" class="cfa-study__btn secondary small" on:click={() => go(deckCmd("add", deck))}>
                                        Add cards
                                    </button>
                                </div>
                            </article>
                        {/each}
                    {/if}
                </div>
            </div>

            <aside class="cfa-study__add-card-panel">
                <div class="cfa-study__eyebrow">Add cards</div>
                <h2>Quick add to any deck</h2>
                <p>
                    A lightweight composer stays beside the deck list, so adding
                    a vignette card feels immediate but does not dominate the screen.
                </p>
                <div class="cfa-study__composer">
                    <div class="cfa-study__field">
                        <span class="cfa-study__field-label">Deck</span>
                        <div>{selectedDeck?.name ?? "Choose or create a CFA deck"}</div>
                    </div>
                    <div class="cfa-study__field">
                        <span class="cfa-study__field-label">Prompt</span>
                        <div class="textarea">When does a lease classification change affect both leverage and interest coverage in a vignette?</div>
                    </div>
                    <div class="cfa-study__field">
                        <span class="cfa-study__field-label">Answer</span>
                        <div class="textarea">Compare recognition, liability measurement, and expense timing before drawing the ratio conclusion.</div>
                    </div>
                    <button type="button" on:click={() => go(deckCmd("add", selectedDeck))}>Add card draft</button>
                </div>

                <div class="cfa-study__quick-add-list">
                    {#each decks as deck}
                        <div class="cfa-study__quick-add-row">
                            <div><strong>{deck.name}</strong><small>{integer(deck.newCount)} new cards staged</small></div>
                            <button type="button" on:click={() => go(deckCmd("add", deck))}>Add</button>
                        </div>
                    {/each}
                </div>
            </aside>
        </section>

        <div class="cfa-study__footer-note">
            <p><strong>Production note:</strong> {data.footerText}</p>
            <button type="button" class="cfa-study__btn secondary small" on:click={() => go("cfa:conceptmap")}>
                Open Concept Map
            </button>
        </div>
    </main>
</div>

<style lang="scss">
    .cfa-study {
        --ink: #122b46;
        --muted: #4d5c6d;
        --faint: #68707d;
        --line: rgba(255, 255, 255, 0.72);
        --pearl: #fbfaf5;
        --turq: #14b8b1;
        --turq-deep: #0e9c97;
        --turq-ink: #064a54;
        --turq-soft: #e4f6f5;
        --deep: #053b45;
        --glass: rgba(255, 255, 255, 0.62);
        --shadow: 0 28px 90px rgba(5, 59, 69, 0.16);

        min-height: 100vh;
        overflow-x: hidden;
        color: var(--ink);
        background:
            radial-gradient(circle at 12% 0%, rgba(255, 255, 255, 0.96), transparent 23rem),
            radial-gradient(circle at 86% 8%, rgba(20, 184, 177, 0.22), transparent 28rem),
            radial-gradient(circle at 56% 70%, rgba(5, 59, 69, 0.16), transparent 34rem),
            linear-gradient(135deg, var(--pearl) 0%, #eef9f7 42%, #d8f3ef 64%, rgba(5, 59, 69, 0.24) 100%);
        font-family: var(--cfa-font-body);
        font-size: 18px;
        line-height: 1.5;
        -webkit-font-smoothing: antialiased;

        &::before {
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            background:
                radial-gradient(circle at 18% 18%, rgba(255, 255, 255, 0.72), transparent 13rem),
                radial-gradient(circle at 78% 22%, rgba(20, 184, 177, 0.2), transparent 19rem);
            mix-blend-mode: screen;
        }

        *,
        *::before,
        *::after {
            box-sizing: border-box;
        }

        h1,
        h2,
        h3 {
            margin: 0;
            color: var(--ink);
            font-family: var(--cfa-font-heading);
        }

        h1 {
            max-width: 790px;
            font-size: clamp(38px, 5vw, 64px);
            line-height: 1.01;
            letter-spacing: -0.04em;
        }

        h2 {
            font-size: clamp(27px, 3vw, 38px);
            line-height: 1.1;
        }

        h3 {
            font-size: 23px;
            line-height: 1.16;
        }

        p {
            margin: 0;
            color: var(--muted);
        }

        button {
            cursor: pointer;
            font: inherit;
        }

        &__page {
            position: relative;
            z-index: 1;
            max-width: 1440px;
            min-width: 0;
            margin: 0 auto;
            padding: 35px 28px 90px;
        }

        &__appbar {
            position: sticky;
            top: 20px;
            z-index: 30;
            border: 1px solid var(--line);
            border-radius: 28px;
            background: rgba(255, 255, 255, 0.7);
            box-shadow: 0 14px 50px rgba(5, 59, 69, 0.1);
            backdrop-filter: blur(22px) saturate(1.25);
            -webkit-backdrop-filter: blur(22px) saturate(1.25);
        }

        &__appbar-in {
            display: flex;
            align-items: center;
            gap: 20px;
            flex-wrap: wrap;
            min-width: 0;
            padding: 15px 18px;
        }

        &__brand {
            color: var(--ink);
            font-family: var(--cfa-font-heading);
            font-size: 24px;
            font-weight: 700;
            letter-spacing: -0.01em;

            small {
                display: block;
                color: var(--turq-ink);
                font-family: var(--cfa-font-body);
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.16em;
                text-transform: uppercase;
            }
        }

        &__tabs {
            display: flex;
            gap: 4px;
            flex-wrap: wrap;
            min-width: 0;
            margin-left: auto;

            button {
                border: 0;
                border-radius: 999px;
                background: transparent;
                color: var(--muted);
                padding: 10px 16px;
                font-size: 16px;
                font-weight: 700;
                white-space: nowrap;

                &:hover,
                &.on {
                    color: var(--turq-ink);
                    background: rgba(20, 184, 177, 0.12);
                    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.65);
                }
            }
        }

        &__sync-chip {
            display: inline-flex;
            align-items: center;
            gap: 9px;
            border: 1px solid rgba(20, 184, 177, 0.22);
            border-radius: 999px;
            background: rgba(228, 246, 245, 0.58);
            color: var(--turq-ink);
            padding: 10px 15px;
            font-weight: 700;
            font-size: 15px;
            white-space: nowrap;
        }

        &__dot {
            width: 8px;
            height: 8px;
            border-radius: 999px;
            background: var(--turq);
        }

        &__hero,
        &__glass-card,
        &__add-card-panel,
        &__create-card {
            min-width: 0;
            border: 1px solid var(--line);
            background: var(--glass);
            box-shadow:
                inset 0 1px 0 rgba(255, 255, 255, 0.78),
                0 20px 70px rgba(5, 59, 69, 0.12);
            backdrop-filter: blur(22px) saturate(1.18);
            -webkit-backdrop-filter: blur(22px) saturate(1.18);
        }

        &__hero {
            position: relative;
            overflow: hidden;
            margin-top: 33px;
            border-radius: 40px;
            padding: 35px;
            background:
                linear-gradient(135deg, rgba(255, 255, 255, 0.84), rgba(255, 255, 255, 0.48)),
                radial-gradient(circle at 76% 18%, rgba(20, 184, 177, 0.2), transparent 24rem);
            box-shadow: var(--shadow);

            &::after {
                content: "";
                position: absolute;
                inset: 1px;
                border-radius: 39px;
                pointer-events: none;
                background: linear-gradient(120deg, rgba(255, 255, 255, 0.68), transparent 30%, rgba(255, 255, 255, 0.16));
                mask: linear-gradient(#000, transparent 70%);
            }
        }

        &__hero-grid {
            position: relative;
            z-index: 1;
            display: grid;
            grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
            gap: 24px;
            align-items: stretch;
        }

        &__eyebrow {
            color: var(--turq-ink);
            font-size: 14px;
            font-weight: 800;
            letter-spacing: 0.15em;
            text-transform: uppercase;
        }

        &__lede {
            max-width: 820px;
            margin-top: 13px;
            color: var(--muted);
            font-size: 20px;
        }

        &__hero-actions {
            display: flex;
            gap: 13px;
            flex-wrap: wrap;
            margin-top: 28px;
        }

        &__btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 0;
            border: 1px solid rgba(255, 255, 255, 0.72);
            border-radius: 18px;
            box-shadow:
                inset 0 1px 0 rgba(255, 255, 255, 0.78),
                0 16px 44px rgba(5, 59, 69, 0.1);
            padding: 15px 19px;
            text-align: center;
            text-decoration: none;
            font-size: 16px;
            font-weight: 800;

            &.primary {
                border-color: rgba(255, 255, 255, 0.84);
                background: linear-gradient(135deg, #7edbd6, #14b8b1, #0e9c97);
                color: #fff;
            }

            &.secondary {
                background: rgba(255, 255, 255, 0.58);
                color: var(--turq-ink);
            }

            &.ghost {
                background: rgba(255, 255, 255, 0.36);
                color: var(--ink);
            }

            &.small {
                border-radius: 15px;
                padding: 12px 13px;
                box-shadow:
                    inset 0 1px 0 rgba(255, 255, 255, 0.72),
                    0 10px 28px rgba(5, 59, 69, 0.08);
                font-size: 14px;
            }
        }

        &__metric-row {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 12px;
            margin-top: 24px;
        }

        &__metric {
            border: 1px solid rgba(255, 255, 255, 0.62);
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.46);
            padding: 14px;

            strong {
                display: block;
                color: #0b2f38;
                font-family: var(--cfa-font-heading);
                font-size: 28px;
                line-height: 1;
            }

            span {
                display: block;
                margin-top: 4px;
                color: var(--muted);
                font-size: 13px;
                font-weight: 700;
            }
        }

        &__create-card {
            display: grid;
            align-content: space-between;
            gap: 24px;
            border-radius: 28px;
            padding: 24px;
            background: linear-gradient(145deg, rgba(255, 255, 255, 0.78), rgba(228, 246, 245, 0.48));

            h2 {
                font-size: 34px;
            }

            p {
                margin-top: 8px;
            }
        }

        &__workspace-grid {
            display: grid;
            grid-template-columns: minmax(0, 1fr) minmax(320px, 390px);
            gap: 20px;
            align-items: start;
            min-width: 0;
            margin-top: 23px;
        }

        &__glass-card,
        &__add-card-panel {
            border-radius: 28px;
            padding: 23px;
        }

        &__card-title {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 15px;
            margin-bottom: 15px;
        }

        &__tag {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            background: rgba(20, 184, 177, 0.12);
            color: var(--turq-ink);
            padding: 7px 10px;
            font-size: 13px;
            font-weight: 800;
            line-height: 1.2;
        }

        &__deck-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 15px;
        }

        &__deck-card {
            display: grid;
            gap: 16px;
            min-width: 0;
            border: 1px solid rgba(255, 255, 255, 0.66);
            border-radius: 24px;
            background: rgba(255, 255, 255, 0.5);
            padding: 18px;

            &.featured {
                outline: 3px solid rgba(20, 184, 177, 0.15);
                background: linear-gradient(145deg, rgba(255, 255, 255, 0.72), rgba(228, 246, 245, 0.58));
            }
        }

        &__deck-top {
            display: grid;
            grid-template-columns: auto minmax(0, 1fr);
            gap: 13px;
            align-items: start;
        }

        &__deck-icon {
            width: 45px;
            height: 45px;
            border-radius: 16px;
            background: linear-gradient(135deg, rgba(126, 219, 214, 0.95), rgba(14, 156, 151, 0.95));
            box-shadow:
                inset 0 1px 0 rgba(255, 255, 255, 0.55),
                0 14px 28px rgba(5, 59, 69, 0.14);
        }

        &__deck-card h3 {
            color: #0b2f38;
            overflow-wrap: anywhere;
        }

        &__deck-card p {
            margin-top: 4px;
            font-size: 15px;
        }

        &__deck-meta {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 8px;
        }

        &__deck-stat {
            min-width: 0;
            border: 1px solid rgba(255, 255, 255, 0.62);
            border-radius: 15px;
            background: rgba(255, 255, 255, 0.46);
            padding: 10px;

            b {
                display: block;
                color: #0b2f38;
                font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
                font-size: 16px;
                white-space: nowrap;
            }

            span {
                display: block;
                margin-top: 2px;
                color: var(--muted);
                font-size: 12px;
                font-weight: 700;
            }
        }

        &__mastery {
            height: 9px;
            overflow: hidden;
            border-radius: 999px;
            background: rgba(233, 237, 241, 0.74);

            i {
                display: block;
                height: 100%;
                background: linear-gradient(90deg, #7edbd6, #0e9c97);
            }
        }

        &__deck-actions {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 9px;

            &.single {
                grid-template-columns: minmax(0, 1fr);
            }
        }

        &__add-card-panel {
            position: sticky;
            top: 128px;
        }

        &__composer {
            display: grid;
            gap: 12px;
            margin-top: 16px;

            > button {
                border: 0;
                border-radius: 15px;
                background: linear-gradient(135deg, #7edbd6, #14b8b1, #0e9c97);
                box-shadow:
                    inset 0 1px 0 rgba(255, 255, 255, 0.72),
                    0 10px 28px rgba(5, 59, 69, 0.08);
                color: #fff;
                padding: 12px 14px;
                font-weight: 800;
            }
        }

        &__field {
            min-width: 0;
            border: 1px solid rgba(255, 255, 255, 0.68);
            border-radius: 17px;
            background: rgba(255, 255, 255, 0.48);
            padding: 13px;

            .cfa-study__field-label {
                display: block;
                color: var(--turq-ink);
                font-size: 12px;
                font-weight: 800;
                letter-spacing: 0.12em;
                text-transform: uppercase;
            }

            div {
                margin-top: 6px;
                color: #0b2f38;
                overflow-wrap: anywhere;
                font-weight: 700;
            }

            .textarea {
                min-height: 86px;
            }
        }

        &__quick-add-list {
            display: grid;
            gap: 10px;
            margin-top: 18px;
        }

        &__quick-add-row {
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            gap: 10px;
            align-items: center;
            border: 1px solid rgba(255, 255, 255, 0.62);
            border-radius: 16px;
            background: rgba(255, 255, 255, 0.42);
            padding: 12px;

            strong {
                display: block;
                color: #0b2f38;
                overflow-wrap: anywhere;
                font-size: 15px;
            }

            small {
                display: block;
                margin-top: 2px;
                color: var(--muted);
                font-size: 13px;
            }

            button {
                border: 0;
                border-radius: 15px;
                background: linear-gradient(135deg, #7edbd6, #14b8b1, #0e9c97);
                box-shadow:
                    inset 0 1px 0 rgba(255, 255, 255, 0.72),
                    0 10px 28px rgba(5, 59, 69, 0.08);
                color: #fff;
                padding: 12px 14px;
                font-weight: 800;
            }
        }

        &__footer-note {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 14px;
            flex-wrap: wrap;
            margin-top: 22px;
            border: 1px solid rgba(255, 255, 255, 0.56);
            border-radius: 22px;
            background: rgba(255, 255, 255, 0.34);
            padding: 18px;
        }
    }

    @media (max-width: 980px) {
        .cfa-study {
            &__hero-grid,
            &__workspace-grid,
            &__metric-row {
                grid-template-columns: minmax(0, 1fr);
            }

            &__add-card-panel {
                position: static;
            }

            &__tabs {
                margin-left: 0;
            }
        }
    }

    @media (max-width: 720px) {
        .cfa-study {
            &__page {
                padding: 22px 14px 70px;
            }

            &__hero {
                border-radius: 30px;
                padding: 24px;
            }

            &__deck-grid,
            &__deck-meta,
            &__deck-actions {
                grid-template-columns: minmax(0, 1fr);
            }

            &__appbar {
                top: 10px;
                border-radius: 22px;
            }

            &__sync-chip {
                white-space: normal;
            }
        }
    }
</style>
