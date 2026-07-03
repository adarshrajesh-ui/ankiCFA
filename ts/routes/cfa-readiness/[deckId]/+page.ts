// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import type { ExamReadinessPayload } from "$lib/cfa";
import { getCfaExamReadiness } from "@generated/backend";

import type { PageLoad } from "./$types";

export const load = (async ({ params }) => {
    const res = await getCfaExamReadiness({ deckId: BigInt(params.deckId) });
    const data = JSON.parse(new TextDecoder().decode(res.json)) as ExamReadinessPayload;
    return { data };
}) satisfies PageLoad;
