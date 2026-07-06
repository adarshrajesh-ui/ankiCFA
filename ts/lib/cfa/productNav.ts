// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

export type CfaProductNavKey =
    | "home"
    | "study"
    | "conceptmap"
    | "readiness"
    | "progress"
    | "sync";

export interface CfaProductNavItem {
    key: CfaProductNavKey;
    cmd: string;
    label: string;
    shortLabel: string;
    sub: string;
    ariaLabel: string;
    active: boolean;
}

const PRODUCT_NAV: Omit<CfaProductNavItem, "active">[] = [
    {
        key: "home",
        cmd: "cfa:home",
        label: "Home",
        shortLabel: "Home",
        sub: "Command center",
        ariaLabel: "Open CFA Home",
    },
    {
        key: "study",
        cmd: "cfa:study",
        label: "Study",
        shortLabel: "Study",
        sub: "Deck workspace",
        ariaLabel: "Open CFA Study",
    },
    {
        key: "conceptmap",
        cmd: "cfa:conceptmap",
        label: "Concept Map",
        shortLabel: "Map",
        sub: "Mastery map",
        ariaLabel: "Open CFA Concept Map",
    },
    {
        key: "readiness",
        cmd: "cfa:readiness",
        label: "Readiness",
        shortLabel: "Ready",
        sub: "Exam risk",
        ariaLabel: "Open CFA Readiness",
    },
    {
        key: "progress",
        cmd: "cfa:progress",
        label: "Progress",
        shortLabel: "Stats",
        sub: "Study statistics",
        ariaLabel: "Open CFA Progress",
    },
    {
        key: "sync",
        cmd: "cfa:sync",
        label: "Sync",
        shortLabel: "Sync",
        sub: "Connect or sync",
        ariaLabel: "Sync CFA progress",
    },
];

export function productNavItems(activeKey: CfaProductNavKey): CfaProductNavItem[] {
    return PRODUCT_NAV.map((item) => ({
        ...item,
        active: item.key === activeKey,
    }));
}
