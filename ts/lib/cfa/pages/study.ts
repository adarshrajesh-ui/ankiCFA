// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import type { CfaStudyDeck, CfaStudyPayload } from "../types";

export const STUDY_NAV = [
    { cmd: "cfa:study", label: "Study", active: true },
    { cmd: "cfa:conceptmap", label: "Concept Map" },
    { cmd: "cfa:readiness", label: "Readiness" },
    { cmd: "cfa:sync", label: "Sync" },
];

export function integer(n: number): string {
    return n.toLocaleString("en-US");
}

export function masteryPct(deck: CfaStudyDeck): string {
    return deck.mastery === null ? "—" : `${Math.round(deck.mastery * 100)}%`;
}

export function masteryWidth(deck: CfaStudyDeck): number {
    return deck.mastery === null ? 0 : Math.max(0, Math.min(100, Math.round(deck.mastery * 100)));
}

export function syncChipLabel(data: CfaStudyPayload): string {
    if (!data.sync.connected) {
        return "Connect & Sync";
    }
    return data.sync.lastSyncedAt ? `Synced ${data.sync.lastSyncedLabel}` : "Sync ready";
}

export function visibleStudyDecks(decks: CfaStudyDeck[], limit = 3): CfaStudyDeck[] {
    return [...decks]
        .sort((a, b) => {
            const aUrgency = a.due * 2 + a.newCount;
            const bUrgency = b.due * 2 + b.newCount;
            return bUrgency - aUrgency || a.name.localeCompare(b.name);
        })
        .slice(0, limit)
        .map((deck, index) => ({ ...deck, featured: index === 0 }));
}
