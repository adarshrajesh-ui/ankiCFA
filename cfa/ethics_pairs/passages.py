# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Load + validate + import the CFA Ethics ONE-PASSAGE bank (passages.jsonl).

F1 one-passage redesign. Each item is a single passage the learner judges Ethical/Unethical and
then highlights EVERY evidence span that supports that verdict — supporting MULTIPLE NON-CONTIGUOUS
spans. The deterministic multi-span grader in ``ethics_scoring`` (find_gold_spans / grade_spans) is
the AI-off fallback; the card template JS mirrors it byte-for-byte.

This module is ADDITIVE: it lives beside the original minimal-pairs pipeline (import_pairs.py /
ethics_notetype.py / pairs.jsonl), which is untouched. It reuses the pure scorer for validation so
the bank can be checked with ``--dry-run`` (no collection, no Anki build needed).

Usage:
    out/pyenv/bin/python cfa/ethics_pairs/passages.py --dry-run           # validate bank only
    PYTHONPATH=out/pylib out/pyenv/bin/python cfa/ethics_pairs/passages.py \
        --col ~/Library/Application\\ Support/Anki2/User\\ 1/collection.anki2
"""

from __future__ import annotations

import argparse
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ethics_scoring import (  # noqa: E402
    VERDICTS,
    find_gold_indices,
    find_gold_spans,
    grade_spans,
)

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PASSAGES = os.path.join(HERE, "passages.jsonl")

# Deck kept as a sibling so these cards never pollute the main CFA deck's FSRS stats.
DECK_NAME = "CFA::Ethics Passages"
NOTETYPE_NAME = "CFA Ethics One-Passage"

_REQUIRED = {
    "item_id",
    "cluster",
    "standard",
    "los_tags",
    "verdict",
    "passage",
    "gold_spans",
    "rationale",
}


class PassageValidationError(ValueError):
    """Raised when the passage bank is structurally or content-invalid."""


def validate_passage(p: dict, where: str) -> None:
    """Validate a single passage record. Raises PassageValidationError on any problem.

    Checks: required keys; verdict enum; >=1 gold span; each span phrase is a NON-EMPTY verbatim,
    whitespace-token-locatable substring of the passage; spans do NOT overlap each other; and the
    union of all spans grades ``"correct"`` under the deterministic multi-span grader (so the
    authored answer key is internally consistent with the AI-off fallback the learner is graded by).
    """
    missing = _REQUIRED - set(p)
    if missing:
        raise PassageValidationError(f"{where}: missing keys {sorted(missing)}")
    if p["verdict"] not in VERDICTS:
        raise PassageValidationError(
            f"{where}: verdict must be one of {VERDICTS}, got {p['verdict']!r}"
        )
    if not p["los_tags"]:
        raise PassageValidationError(f"{where}: need at least one los:: tag")
    passage = p["passage"]
    if not isinstance(passage, str) or not passage.strip():
        raise PassageValidationError(f"{where}: passage must be a non-empty string")
    spans = p["gold_spans"]
    if not isinstance(spans, list) or not spans:
        raise PassageValidationError(f"{where}: need at least one gold_span")

    phrases = []
    for j, span in enumerate(spans):
        if (
            not isinstance(span, dict)
            or "phrase" not in span
            or "rationale" not in span
        ):
            raise PassageValidationError(
                f"{where}: gold_spans[{j}] must have 'phrase' and 'rationale'"
            )
        phrase = span["phrase"]
        if not isinstance(phrase, str) or not phrase.strip():
            raise PassageValidationError(f"{where}: gold_spans[{j}].phrase empty")
        if phrase not in passage:
            raise PassageValidationError(
                f"{where}: gold_spans[{j}].phrase not a verbatim substring: {phrase!r}"
            )
        if not find_gold_indices(passage, phrase):
            raise PassageValidationError(
                f"{where}: gold_spans[{j}].phrase not token-locatable (word boundaries): "
                f"{phrase!r}"
            )
        phrases.append(phrase)

    runs = find_gold_spans(passage, phrases)
    used: set[int] = set()
    for j, run in enumerate(runs):
        s = set(run)
        if used & s:
            raise PassageValidationError(
                f"{where}: gold_spans[{j}] overlaps an earlier span: {phrases[j]!r}"
            )
        used |= s

    perfect = [i for run in runs for i in run]
    grade = grade_spans(perfect, runs)["grade"]
    if grade != "correct":
        raise PassageValidationError(
            f"{where}: union of gold spans grades {grade!r}, expected 'correct'"
        )


def load_passages(path: str = DEFAULT_PASSAGES) -> list[dict]:
    """Parse and fully validate the jsonl bank. Raises PassageValidationError on any bad record."""
    out = []
    seen_ids: set[str] = set()
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            where = f"{os.path.basename(path)}:{lineno}"
            try:
                p = json.loads(line)
            except json.JSONDecodeError as e:
                raise PassageValidationError(f"{where}: invalid JSON: {e}") from e
            validate_passage(p, where)
            if p["item_id"] in seen_ids:
                raise PassageValidationError(
                    f"{where}: duplicate item_id {p['item_id']!r}"
                )
            seen_ids.add(p["item_id"])
            out.append(p)
    return out


# --------------------------------------------------------------------------- Anki import


def _load_templates() -> tuple[str, str, str]:
    """Return (front_html, back_html, css) for the one-passage note type from disk.

    ``css`` is ``""`` when ``style.css`` is absent, mirroring the original create path which only
    set ``css`` when the file existed.
    """
    front_path = os.path.join(HERE, "templates", "passage_front.html")
    back_path = os.path.join(HERE, "templates", "passage_back.html")
    style_path = os.path.join(HERE, "templates", "style.css")
    with open(front_path, encoding="utf-8") as f:
        front = f.read()
    with open(back_path, encoding="utf-8") as f:
        back = f.read()
    css = ""
    if os.path.exists(style_path):
        with open(style_path, encoding="utf-8") as f:
            css = f.read()
    return front, back, css


def _refresh_existing(mm, existing, front: str, back: str, css: str):
    """Refresh the presentation (qfmt/afmt/css) of an existing note type in place.

    Only rewrites ``css`` when the on-disk style is non-empty so a missing ``style.css`` never wipes
    the baked stylesheet. Returns the persisted (re-read) note type dict.
    """
    if existing["tmpls"]:
        existing["tmpls"][0]["qfmt"] = front
        existing["tmpls"][0]["afmt"] = back
    if css:
        existing["css"] = css
    mm.update_dict(existing)
    return mm.by_name(NOTETYPE_NAME)


def refresh_notetype_if_exists(col):
    """Refresh the baked templates/CSS of an EXISTING one-passage note type in place.

    Companion to the minimal-pair ``ethics_notetype.refresh_notetype_if_exists``: it NEVER creates
    the note type (returns ``None`` when it does not yet exist), so the desktop startup refresh only
    pushes current on-disk template fixes onto collections that already have the passages deck and
    never seeds empty content on a fresh profile before the normal seed path runs.
    """
    mm = col.models
    existing = mm.by_name(NOTETYPE_NAME)
    if not existing:
        return None
    front, back, css = _load_templates()
    return _refresh_existing(mm, existing, front, back, css)


def ensure_notetype(col):
    """Create the one-passage note type, or refresh its templates/CSS if it already exists.

    Fields carry the passage + JSON-encoded answer key. Re-running is safe: an existing note type has
    its baked ``qfmt``/``afmt``/``css`` refreshed from disk (so on-disk template fixes land on
    collections that already imported the deck) without duplicating notes or fields.
    """
    mm = col.models
    existing = mm.by_name(NOTETYPE_NAME)
    front, back, css = _load_templates()
    if existing:
        return _refresh_existing(mm, existing, front, back, css)
    m = mm.new(NOTETYPE_NAME)
    for field in (
        "ItemId",
        "Passage",
        "Verdict",
        "GoldSpans",  # JSON: [{"phrase":..,"rationale":..}, ..]
        "Standard",
        "ClusterTag",
        "Rationale",
    ):
        mm.add_field(m, mm.new_field(field))
    tmpl = mm.new_template("One-Passage Highlight")
    tmpl["qfmt"] = front
    tmpl["afmt"] = back
    mm.add_template(m, tmpl)
    if css:
        m["css"] = css
    mm.add(m)
    return mm.by_name(NOTETYPE_NAME)


def _tags_for(p: dict) -> list[str]:
    return list(p["los_tags"]) + [f"cluster::{p['cluster']}", "ethics::one-passage"]


def _set_fields(note, p: dict) -> None:
    note["ItemId"] = html.escape(str(p["item_id"]), quote=False)
    note["Passage"] = html.escape(str(p["passage"]), quote=False)
    note["Verdict"] = html.escape(str(p["verdict"]), quote=False)
    # GoldSpans holds the raw answer key as JSON; the template parses it with JSON.parse and never
    # displays it before the attempt (it lives in the hidden .cfa-src block).
    note["GoldSpans"] = html.escape(
        json.dumps(
            [
                {"phrase": s["phrase"], "rationale": s["rationale"]}
                for s in p["gold_spans"]
            ],
            ensure_ascii=False,
        ),
        quote=False,
    )
    note["Standard"] = html.escape(str(p["standard"]), quote=False)
    note["ClusterTag"] = f"cluster::{p['cluster']}"
    note["Rationale"] = html.escape(str(p["rationale"]), quote=False)


def import_passages(col, passages: list[dict]) -> dict:
    """Import parsed passages into ``col``. Idempotent by ItemId."""
    notetype = ensure_notetype(col)
    deck_id = col.decks.id(DECK_NAME)

    existing: dict[str, int] = {}
    for nid in col.find_notes(f'note:"{NOTETYPE_NAME}"'):
        note = col.get_note(nid)
        existing[note["ItemId"]] = nid

    created = updated = 0
    for p in passages:
        iid = p["item_id"]
        tags = _tags_for(p)
        if iid in existing:
            note = col.get_note(existing[iid])
            _set_fields(note, p)
            note.tags = tags
            col.update_note(note)
            updated += 1
        else:
            note = col.new_note(notetype)
            _set_fields(note, p)
            note.tags = tags
            col.add_note(note, deck_id)
            created += 1
    return {
        "created": created,
        "updated": updated,
        "total": created + updated,
        "deck": DECK_NAME,
        "notetype": NOTETYPE_NAME,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Import CFA Ethics one-passage items.")
    ap.add_argument(
        "--col", help="path to collection.anki2 (must be closed in the app)"
    )
    ap.add_argument(
        "--passages", default=DEFAULT_PASSAGES, help="path to passages.jsonl"
    )
    ap.add_argument("--dry-run", action="store_true", help="validate the bank only")
    args = ap.parse_args(argv)

    passages = load_passages(args.passages)
    n_spans = sum(len(p["gold_spans"]) for p in passages)
    print(
        f"validated {len(passages)} passages ({n_spans} gold spans) from {args.passages}"
    )
    if args.dry_run:
        return 0
    if not args.col:
        ap.error("--col is required unless --dry-run")

    from anki.collection import Collection

    col = Collection(args.col)
    try:
        stats = import_passages(col, passages)
    finally:
        col.close()
    print(
        f"imported into '{stats['deck']}' as '{stats['notetype']}': "
        f"{stats['created']} created, {stats['updated']} updated, {stats['total']} total"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
