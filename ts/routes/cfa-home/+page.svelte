<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

The CFA Home route — the app's native landing screen. Thin by design: wire the
design-system theme, then delegate all markup to CfaHomePage.
-->
<script lang="ts">
    import "$lib/cfa/theme.scss";

    import CfaHomePage from "$lib/cfa/pages/CfaHomePage.svelte";
    import type { PageData } from "./$types";

    export let data: PageData;
</script>

<CfaHomePage data={data.data} />
