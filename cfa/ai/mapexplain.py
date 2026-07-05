# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Concept Map — the SINGLE batched AI explanation call.

The Concept Map tab (``.lavish/concept-map-spec.html``) says: click a node → a
casual, plain-English explanation of how that node's score came to be, served
from **one** batched AI call made when the tab opens (templated fallback when AI
is off). This module is that batched call, as a pure, ``anki``-free function so
it unit-tests without a webview or the network.

Contract, mirroring the rest of the CFA AI surface (``cfa/ai/tabfill.py``,
``cfa/ethics_pairs/ai_grading.py``):

* **One call for the whole map.** :func:`explain_map` sends every node in a
  single prompt and asks for a JSON object ``{id: explanation}`` back, so the
  tab costs exactly one completion, not one-per-node.
* **AI OFF is safe and honest.** With no key / the master toggle off, the
  Svelte layer keeps its deterministic templated wording; this module simply
  returns ``ok=False`` with an empty map and a structured ``error`` so the
  caller can say *why* (``no_api_key`` / ``ai_off`` / a parse failure) rather
  than faking an AI badge.
* **Give-up rule preserved.** A node whose ``pct`` is ``None`` (not enough
  evidence yet) is described to the model as *abstaining*; the prompt forbids
  inventing a number for it, so an unearned node never gets a fake confident
  explanation.
* **Never raises.** Any client error / malformed JSON degrades to ``ok=False``
  with an empty ``explanations`` map; the caller falls back per node.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Optional

CompleteFn = Callable[..., dict]

# Cap the batch so a pathological topic set can't blow the prompt/token budget;
# the real map is ~31 nodes (1 centre + 10 topics + 20 subs), well under this.
MAX_NODES = 60


# --- node normalisation ------------------------------------------------------


def _clean_nodes(nodes: Any) -> list[dict]:
    """Coerce the incoming node list into the minimal shape the prompt needs.

    Each kept node is ``{id, full, kind, pct, band, parent}``. Anything without a
    usable ``id`` is dropped; extra keys the Svelte layer sends are ignored.
    """
    if not isinstance(nodes, list):
        return []
    out: list[dict] = []
    seen: set[str] = set()
    for raw in nodes[:MAX_NODES]:
        if not isinstance(raw, dict):
            continue
        nid = str(raw.get("id", "")).strip()
        if not nid or nid in seen:
            continue
        seen.add(nid)
        pct_raw = raw.get("pct", None)
        pct: Optional[int]
        if pct_raw is None:
            pct = None
        else:
            try:
                pct = int(round(float(pct_raw)))
            except (TypeError, ValueError):
                pct = None
        out.append(
            {
                "id": nid,
                "full": str(raw.get("full", nid)).strip() or nid,
                "kind": str(raw.get("kind", "topic")).strip() or "topic",
                "pct": pct,
                "band": (str(raw["band"]).strip() if raw.get("band") else None),
                "parent": (
                    str(raw["parent"]).strip() if raw.get("parent") else None
                ),
            }
        )
    return out


# --- prompt construction -----------------------------------------------------


def build_batch_messages(nodes: list[dict]) -> tuple[str, str]:
    """Build the (system, user) prompt for the ONE batched explanation call."""
    system = (
        "You are a friendly CFA Level II coach narrating a candidate's 'concept "
        "map' — a radial mastery chart where each node is a curriculum area and "
        "its fill (0-100%) is the candidate's current mastery. For EACH node you "
        "are given, write a short, casual, plain-English explanation of how that "
        "score came to be and what would move it. Rules: 1-3 sentences, warm and "
        "concrete, no jargon dumps, no markdown, no headers. Ground it in the "
        "node's percent and exam weight. If a node's mastery is null it is "
        "ABSTAINING (not enough graded reviews yet) — say so plainly and DO NOT "
        "invent a number or fake confidence; brightness is earned, never faked. "
        'Return ONLY a JSON object mapping each node id to its explanation string, '
        'e.g. {"topic:equity": "You\'re at about 62% ..."}. No other text.'
    )
    lines = []
    for n in nodes:
        if n["kind"] == "cfa":
            what = "Overall CFA readiness (weight-adjusted roll-up of all sections)"
        elif n["kind"] == "sub":
            what = f"Subsection '{n['full']}' of the {n['parent']} section"
        else:
            band = f", exam weight {n['band']}" if n["band"] else ""
            what = f"Test section '{n['full']}'{band}"
        mastery = "null (abstaining — not enough evidence yet)" if n["pct"] is None else f"{n['pct']}%"
        lines.append(f'- id "{n["id"]}": {what}. Mastery: {mastery}.')
    user = (
        "Here are the concept-map nodes. Write one explanation per node and "
        "return the JSON id→explanation object:\n\n" + "\n".join(lines)
    )
    return system, user


# --- robust JSON extraction --------------------------------------------------


def _extract_json_object(text: str) -> Optional[dict]:
    """Parse the model's reply into a ``{id: str}`` dict, tolerating fences.

    Handles a bare object, a ```json fenced block, or an object embedded in
    surrounding prose. Returns None if nothing usable is found.
    """
    if not text:
        return None
    candidate = text.strip()
    # Strip a leading/trailing code fence if present.
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", candidate, re.DOTALL)
    if fence:
        candidate = fence.group(1).strip()
    # Try a direct parse first; otherwise grab the outermost {...}.
    for attempt in (candidate, _first_brace_block(candidate)):
        if not attempt:
            continue
        try:
            obj = json.loads(attempt)
        except ValueError:
            continue
        if isinstance(obj, dict):
            return obj
    return None


def _first_brace_block(text: str) -> Optional[str]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start : end + 1]


# --- the batched call --------------------------------------------------------


def explain_map(
    nodes: Any,
    *,
    complete_fn: Optional[CompleteFn] = None,
    max_tokens: int = 1100,
) -> dict:
    """Explain every node in ONE batched LLM call. Never raises.

    Returns ``{ok, explanations, error, model, count}`` where ``explanations``
    is an ``{id: text}`` dict (only ids that both existed in the input and came
    back non-empty). On AI-off / any failure ``ok`` is False and
    ``explanations`` is empty, so the caller keeps its templated fallback.
    """
    clean = _clean_nodes(nodes)
    if not clean:
        return {"ok": False, "explanations": {}, "error": "no_nodes", "model": None, "count": 0}

    if complete_fn is None:
        from cfa.ai.llm_client import complete as complete_fn  # type: ignore

    system, user = build_batch_messages(clean)
    try:
        res = complete_fn(
            system,
            user,
            max_tokens=max_tokens,
            temperature=0.3,
            purpose="concept_map_explain",
        )
    except Exception as exc:  # pragma: no cover - client is no-raise; belt+braces
        return {
            "ok": False,
            "explanations": {},
            "error": f"client_error:{type(exc).__name__}",
            "model": None,
            "count": 0,
        }

    if not isinstance(res, dict) or not res.get("ok"):
        return {
            "ok": False,
            "explanations": {},
            "error": (res or {}).get("error", "ai_unavailable"),
            "model": (res or {}).get("model"),
            "count": 0,
        }

    parsed = _extract_json_object(res.get("text") or "")
    if not parsed:
        return {
            "ok": False,
            "explanations": {},
            "error": "bad_json",
            "model": res.get("model"),
            "count": 0,
        }

    valid_ids = {n["id"] for n in clean}
    explanations: dict[str, str] = {}
    for nid, val in parsed.items():
        key = str(nid).strip()
        if key in valid_ids and isinstance(val, str) and val.strip():
            explanations[key] = val.strip()

    if not explanations:
        return {
            "ok": False,
            "explanations": {},
            "error": "empty_map",
            "model": res.get("model"),
            "count": 0,
        }

    return {
        "ok": True,
        "explanations": explanations,
        "error": None,
        "model": res.get("model"),
        "count": len(explanations),
    }


__all__ = ["build_batch_messages", "explain_map", "MAX_NODES"]
