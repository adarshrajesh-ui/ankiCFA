// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

// -----------------------------------------------------------------------------
// CFA web design system — public entry point.
//
// Import the theme once per page (fonts + :root tokens + calm page base):
//     import "$lib/cfa/theme.scss";
// then use the components + types:
//     import { Hero, StatCard, DataTable, type ExamReadinessPayload } from "$lib/cfa";
// -----------------------------------------------------------------------------

export { default as Band } from "./Band.svelte";
export { default as Caption } from "./Caption.svelte";
export { default as DataTable } from "./DataTable.svelte";
export { default as Eyebrow } from "./Eyebrow.svelte";
export { default as Hero } from "./Hero.svelte";
export { default as Notice } from "./Notice.svelte";
export { default as PageHeading } from "./PageHeading.svelte";
export { default as StatCard } from "./StatCard.svelte";

export type {
    CfaColumn,
    CfaHomePayload,
    CfaRow,
    CfaTone,
    DeadlinePayload,
    DeadlineRow,
    ExamReadinessCaption,
    ExamReadinessPayload,
    HeroAbstain,
    HeroBayesian,
    ReadinessBand,
    RecallRange,
    ScoreBand,
    TopicRow,
} from "./types";
