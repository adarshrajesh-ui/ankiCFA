// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import { getCfaHomeView } from "@generated/backend";

import type { CfaHomePayload } from "$lib/cfa";
import type { PageLoad } from "./$types";

// The concept map is built from the SAME payload the CFA Home dashboard uses
// (it carries the per-topic rows with exam weight + recall ranges), so the map
// and the scores stay in lockstep and no new backend RPC is needed yet.
export const load = (async () => {
    const res = await getCfaHomeView({});
    const data = JSON.parse(new TextDecoder().decode(res.json)) as CfaHomePayload;
    return { data };
}) satisfies PageLoad;
