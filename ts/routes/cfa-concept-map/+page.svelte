<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

The CFA Concept Map route — the radial mastery-map tab. Thin by design: wire the
design-system theme, then delegate all markup to CfaConceptMapPage.
-->
<script lang="ts">
    import "$lib/cfa/theme.scss";

    import CfaConceptMapPage from "$lib/cfa/pages/CfaConceptMapPage.svelte";
    import type { PageData } from "./$types";

    export let data: PageData;
</script>

<CfaConceptMapPage data={data.data} />
