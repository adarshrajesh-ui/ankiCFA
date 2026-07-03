<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<!--
Deadline (peak-on-exam-day) route: renders the shared CfaDeadlinePage against the
ranked payload the +page.ts loader fetches over the GetCfaDeadlineView RPC. The
date picker lives in the page component; committing a date persists it through the
SetCfaExamDate RPC here, then invalidateAll re-runs the loader so the ranking
re-computes against the new exam date. Importing the CFA theme once wires the
brand fonts + tokens.
-->
<script lang="ts">
    import "$lib/cfa/theme.scss";

    import { invalidateAll } from "$app/navigation";
    import CfaDeadlinePage from "$lib/cfa/pages/CfaDeadlinePage.svelte";
    import { setCfaExamDate } from "@generated/backend";
    import type { PageData } from "./$types";

    export let data: PageData;

    async function onSetExamDate(iso: string): Promise<void> {
        await setCfaExamDate({ examDate: iso });
        await invalidateAll();
    }
</script>

<CfaDeadlinePage data={data.data} {onSetExamDate} />
