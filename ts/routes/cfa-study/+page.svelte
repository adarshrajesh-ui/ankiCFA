<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

The CFA Study route — the deck-first workspace.
-->
<script lang="ts">
    import "$lib/cfa/theme.scss";

    import CfaStudyPage from "$lib/cfa/pages/CfaStudyPage.svelte";
    import type { PageData } from "./$types";

    export let data: PageData;
</script>

<CfaStudyPage data={data.data} />
