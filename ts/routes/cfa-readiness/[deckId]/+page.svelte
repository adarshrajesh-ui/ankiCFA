<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<!--
Exam Readiness route: renders the shared CfaReadinessPage (built from the
ts/lib/cfa design system) against the honest-score payload the +page.ts loader
fetches over the GetCfaExamReadiness RPC. Importing the CFA theme once here wires
the brand @font-face faces + :root tokens so the page renders in the Meldrum
serif/sans rather than a system fallback.
-->
<script lang="ts">
    import "$lib/cfa/theme.scss";

    import CfaReadinessPage from "$lib/cfa/pages/CfaReadinessPage.svelte";
    import type { PageData } from "./$types";

    export let data: PageData;
</script>

<CfaReadinessPage data={data.data} />
