// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import { getCfaStudyView } from "@generated/backend";

import type { CfaStudyPayload } from "$lib/cfa";
import type { PageLoad } from "./$types";

export const load = (async () => {
    const res = await getCfaStudyView({});
    const data = JSON.parse(new TextDecoder().decode(res.json)) as CfaStudyPayload;
    return { data };
}) satisfies PageLoad;
