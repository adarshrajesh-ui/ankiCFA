<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<!--
Placeholder JSON-dump page. The real Exam Readiness UI (built from the shared
ts/lib/cfa components) is owned by a separate page agent and wired in later; this
route only proves the backend data-loader end to end.
-->
<script lang="ts">
    import type { PageData } from "./$types";

    export let data: PageData;
</script>

<pre>{JSON.stringify(data, null, 2)}</pre>
