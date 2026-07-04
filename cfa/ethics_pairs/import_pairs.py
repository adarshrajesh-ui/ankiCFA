# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Import the CFA Ethics Minimal-Pair bank (pairs.jsonl) into an Anki collection.

Creates/refreshes the note type and the sibling deck "CFA::Ethics Pairs" (so these cards never
pollute the main CFA deck's FSRS memory stats), then creates one note per pair, tagged with its
``los::`` ethics tag and its ``cluster::`` tag. Re-running is idempotent: notes are keyed by PairId
and updated in place rather than duplicated.

Usage (run against a CLOSED collection):
    PYTHONPATH=out/pylib out/pyenv/bin/python cfa/ethics_pairs/import_pairs.py \
        --col ~/Library/Application\\ Support/Anki2/User\\ 1/collection.anki2
    # add --dry-run to validate the bank without opening a collection
"""

from __future__ import annotations

import argparse
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ethics_notetype as nt  # noqa: E402
from ethics_scoring import (  # noqa: E402
    find_gold_indices,
    find_gold_spans,
    grade_spans,
)

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PAIRS = os.path.join(HERE, "pairs.jsonl")

# jsonl key -> note field (distractors + gold_spans handled separately).
_FIELD_MAP = {
    "pair_id": "PairId",
    "vignette_a": "VignetteA",
    "vignette_b": "VignetteB",
    "answer_a": "AnswerA",
    "answer_b": "AnswerB",
    "decisive_fact": "DecisiveFact",
    "decisive_phrase": "DecisivePhrase",
    "decisive_phrase_case": "DecisivePhraseCase",
    "standard": "Standard",
    "rationale": "Rationale",
}

_REQUIRED = set(_FIELD_MAP) | {"cluster", "los_tags", "distractors"}


def gold_spans_for(pair: dict) -> list[dict]:
    """The multi-span answer key on the violating vignette as ``[{phrase, rationale}]``.

    Uses the authored ``gold_spans`` when present; otherwise derives a single-span key from the
    legacy ``decisive_phrase`` (with ``decisive_fact``/``rationale`` as the span rationale) so older
    banks without ``gold_spans`` still grade. This is the multi-span flagship's answer key and is
    JSON-encoded into the ``GoldSpans`` note field, exactly mirroring the one-passage card.
    """
    spans = pair.get("gold_spans")
    if isinstance(spans, list) and spans:
        return [
            {"phrase": s["phrase"], "rationale": s.get("rationale", "")} for s in spans
        ]
    return [
        {
            "phrase": pair["decisive_phrase"],
            "rationale": pair.get("decisive_fact") or pair.get("rationale", ""),
        }
    ]


def load_pairs(path: str = DEFAULT_PAIRS) -> list[dict]:
    """Parse and structurally validate the jsonl bank. Raises ValueError on any malformed pair."""
    pairs = []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                p = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"{path}:{lineno}: invalid JSON: {e}") from e
            missing = _REQUIRED - set(p)
            if missing:
                raise ValueError(f"{path}:{lineno}: missing keys {sorted(missing)}")
            if p["answer_a"] not in ("conform", "violate") or p["answer_b"] not in (
                "conform",
                "violate",
            ):
                raise ValueError(f"{path}:{lineno}: answers must be conform/violate")
            if p["answer_a"] == p["answer_b"]:
                raise ValueError(
                    f"{path}:{lineno}: a minimal pair must have opposite answers"
                )
            if len(p["distractors"]) != 3:
                raise ValueError(f"{path}:{lineno}: need exactly 3 distractors")
            if not p["los_tags"]:
                raise ValueError(f"{path}:{lineno}: need at least one los:: tag")
            _validate_decisive_phrase(p, path, lineno)
            _validate_gold_spans(p, path, lineno)
            pairs.append(p)
    return pairs


def _validate_decisive_phrase(p: dict, path: str, lineno: int) -> None:
    """The highlight target must be a verbatim, token-locatable phrase in the violating vignette."""
    case = p["decisive_phrase_case"]
    if case not in ("A", "B"):
        raise ValueError(f"{path}:{lineno}: decisive_phrase_case must be 'A' or 'B'")
    # The decisive phrase is the phrase that makes the case a VIOLATION, so it must live in the
    # vignette whose answer is "violate".
    violate_case = "A" if p["answer_a"] == "violate" else "B"
    if case != violate_case:
        raise ValueError(
            f"{path}:{lineno}: decisive_phrase_case ({case}) must be the violating "
            f"vignette ({violate_case})"
        )
    vignette = p["vignette_a"] if case == "A" else p["vignette_b"]
    phrase = p["decisive_phrase"]
    if not isinstance(phrase, str) or not phrase.strip():
        raise ValueError(f"{path}:{lineno}: decisive_phrase must be a non-empty string")
    if phrase not in vignette:
        raise ValueError(
            f"{path}:{lineno}: decisive_phrase is not a verbatim substring of "
            f"vignette_{case.lower()}"
        )
    if not find_gold_indices(vignette, phrase):
        raise ValueError(
            f"{path}:{lineno}: decisive_phrase is not locatable by whitespace tokenization "
            f"in vignette_{case.lower()} (must align to word boundaries)"
        )


def _validate_gold_spans(p: dict, path: str, lineno: int) -> None:
    """Validate the optional multi-span ``gold_spans`` key on the violating vignette.

    When present, every span phrase must be a NON-EMPTY verbatim, token-locatable substring of the
    VIOLATING vignette; spans must NOT overlap each other; the union must grade ``"correct"`` under
    the deterministic multi-span grader; and the union must COVER the legacy ``decisive_phrase`` (so
    the legacy single-phrase contract still holds). Mirrors the one-passage bank's validation so the
    authored answer key is internally consistent with the AI-off fallback the learner is graded by.
    Absent ``gold_spans`` is allowed (the importer derives a single-span key from the legacy field).
    """
    spans = p.get("gold_spans")
    if spans is None:
        return
    if not isinstance(spans, list) or not spans:
        raise ValueError(f"{path}:{lineno}: gold_spans, if present, must be a non-empty list")
    case = p["decisive_phrase_case"]
    vignette = p["vignette_a"] if case == "A" else p["vignette_b"]
    phrases = []
    for j, span in enumerate(spans):
        if not isinstance(span, dict) or "phrase" not in span or "rationale" not in span:
            raise ValueError(
                f"{path}:{lineno}: gold_spans[{j}] must have 'phrase' and 'rationale'"
            )
        phrase = span["phrase"]
        if not isinstance(phrase, str) or not phrase.strip():
            raise ValueError(f"{path}:{lineno}: gold_spans[{j}].phrase empty")
        if phrase not in vignette:
            raise ValueError(
                f"{path}:{lineno}: gold_spans[{j}].phrase not a verbatim substring of "
                f"vignette_{case.lower()}: {phrase!r}"
            )
        if not find_gold_indices(vignette, phrase):
            raise ValueError(
                f"{path}:{lineno}: gold_spans[{j}].phrase not token-locatable in "
                f"vignette_{case.lower()}: {phrase!r}"
            )
        phrases.append(phrase)

    runs = find_gold_spans(vignette, phrases)
    used: set[int] = set()
    for j, run in enumerate(runs):
        s = set(run)
        if used & s:
            raise ValueError(
                f"{path}:{lineno}: gold_spans[{j}] overlaps an earlier span: {phrases[j]!r}"
            )
        used |= s

    perfect = [i for run in runs for i in run]
    grade = grade_spans(perfect, runs)["grade"]
    if grade != "correct":
        raise ValueError(
            f"{path}:{lineno}: union of gold_spans grades {grade!r}, expected 'correct'"
        )

    # The legacy decisive_phrase must be covered by the union of the gold spans, so the multi-span
    # key is a strict superset of the single-phrase contract.
    dp_idx = find_gold_indices(vignette, p["decisive_phrase"])
    if not dp_idx or not set(dp_idx).issubset(used):
        raise ValueError(
            f"{path}:{lineno}: gold_spans union must cover the legacy decisive_phrase"
        )


def _tags_for(pair: dict) -> list[str]:
    return list(pair["los_tags"]) + [
        f"cluster::{pair['cluster']}",
        "ethics::minimal-pair",
    ]


def _set_fields(note, pair: dict) -> None:
    for jkey, field in _FIELD_MAP.items():
        note[field] = html.escape(str(pair[jkey]), quote=False)
    note["ClusterTag"] = f"cluster::{pair['cluster']}"
    # GoldSpans holds the multi-span answer key as JSON; the template parses it with JSON.parse and
    # never displays it before the attempt (it lives in the hidden .cfa-src block). Mirrors the
    # one-passage GoldSpans field exactly. Only added when the note type carries the field, so an
    # older note type (missing GoldSpans) still imports; ensure_notetype adds it on refresh.
    if "GoldSpans" in note:
        note["GoldSpans"] = html.escape(
            json.dumps(gold_spans_for(pair), ensure_ascii=False), quote=False
        )
    for i, d in enumerate(pair["distractors"], 1):
        note[f"DistractorFact{i}"] = html.escape(str(d), quote=False)


def import_pairs(col, pairs: list[dict]) -> dict:
    """Import parsed pairs into ``col``. Returns stats. Idempotent by PairId."""
    notetype = nt.ensure_notetype(col)
    deck_id = col.decks.id(
        nt.DECK_NAME
    )  # creates "CFA" and child "Ethics Pairs" if needed

    # Map existing PairId -> note id for in-place updates.
    existing: dict[str, int] = {}
    for nid in col.find_notes(f'note:"{nt.NOTETYPE_NAME}"'):
        note = col.get_note(nid)
        existing[note["PairId"]] = nid

    created = updated = 0
    for pair in pairs:
        pid = pair["pair_id"]
        tags = _tags_for(pair)
        if pid in existing:
            note = col.get_note(existing[pid])
            _set_fields(note, pair)
            note.tags = tags
            col.update_note(note)
            updated += 1
        else:
            note = col.new_note(notetype)
            _set_fields(note, pair)
            note.tags = tags
            col.add_note(note, deck_id)
            created += 1

    return {
        "created": created,
        "updated": updated,
        "total": created + updated,
        "deck": nt.DECK_NAME,
        "notetype": nt.NOTETYPE_NAME,
        "deck_id": deck_id,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Import CFA Ethics Minimal-Pairs into an Anki collection."
    )
    ap.add_argument(
        "--col", help="path to collection.anki2 (must be closed in the Anki app)"
    )
    ap.add_argument("--pairs", default=DEFAULT_PAIRS, help="path to pairs.jsonl")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="validate the bank only; do not open a collection",
    )
    args = ap.parse_args(argv)

    pairs = load_pairs(args.pairs)
    print(f"validated {len(pairs)} pairs from {args.pairs}")
    if args.dry_run:
        return 0
    if not args.col:
        ap.error("--col is required unless --dry-run")

    from anki.collection import Collection

    col = Collection(args.col)
    try:
        stats = import_pairs(col, pairs)
    finally:
        col.close()
    print(
        f"imported into '{stats['deck']}' as '{stats['notetype']}': "
        f"{stats['created']} created, {stats['updated']} updated, {stats['total']} total"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
