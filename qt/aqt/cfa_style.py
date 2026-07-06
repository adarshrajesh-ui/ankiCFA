# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""CFA fork: the shared design system for the desktop CFA surfaces (F5).

A single source of truth for the approved liquid-glass CFA aesthetic — pearl
backgrounds, turquoise depth/accent, navy text, generous spacing and quiet
glass cards — so the Home, Study, Concept Map, Readiness, reviewer chrome and
Ethics card read as one product.

Everything here is pure/presentational: a token table (:data:`TOKENS`), a
:func:`dialog_qss` widget stylesheet, and small HTML builders (:func:`eyebrow`,
:func:`hero`, :func:`band`, :func:`caption`, :func:`section`) that the dialogs
compose. No Anki/collection state, no I/O — trivially unit-testable, and the
same palette is mirrored in ``cfa/ethics_pairs/templates/style.css`` via a
``:root`` token block so the card matches pixel-for-pixel.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Design tokens — the ONE palette + type scale shared across every CFA surface.
# Kept in sync with the ``:root`` block in the ethics card stylesheet.
# ---------------------------------------------------------------------------
TOKENS: dict[str, str] = {
    # Neutrals and liquid-glass surfaces.
    "ink": "#122B46",
    "muted": "#4D5C6D",
    "faint": "#8B97A4",
    "line": "#DDEDEA",
    "surface": "#E4F6F5",
    "bg": "#FBFAF5",
    # Brand — turquoise product accent from the approved new CFA pages.
    "primary": "#14B8B1",
    "primary_soft": "#E4F6F5",
    "primary_hover": "#0E9C97",
    # Semantic — the pass / fail / caution triad.
    "pass": "#15803d",
    "pass_soft": "#f0fdf4",
    "fail": "#b91c1c",
    "fail_soft": "#fef2f2",
    "warn": "#b45309",
    "accent": "#14B8B1",
    "accent_soft": "#DFF5F3",
    # Type scale (px).
    "fs_title": "22",
    "fs_hero": "28",
    "fs_lead": "16",
    "fs_body": "15",
    "fs_meta": "12",
    "fs_eyebrow": "11",
    "font": '"IBM Plex Sans", -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    # Serif display face for headings — the calm MM "learning" feel.
    "font_heading": '"Source Serif 4", Georgia, "Times New Roman", serif',
}

# Convenience aliases so callers read cleanly.
INK = TOKENS["ink"]
MUTED = TOKENS["muted"]
FAINT = TOKENS["faint"]
LINE = TOKENS["line"]
SURFACE = TOKENS["surface"]
BG = TOKENS["bg"]
PRIMARY = TOKENS["primary"]
PASS = TOKENS["pass"]
FAIL = TOKENS["fail"]
WARN = TOKENS["warn"]


def dialog_qss() -> str:
    """Widget stylesheet giving a CFA dialog the calm shared chrome.

    Styles the dialog background, table (quiet header, hairline grid, striped
    rows, comfortable row height) and buttons/date-edit so the native Qt
    surfaces match the HTML content rather than clashing with it.
    """
    t = TOKENS
    return f"""
    QDialog {{ background: {t["bg"]}; }}
    QLabel {{ color: {t["ink"]}; font-family: {t["font"]}; }}
    QTableWidget {{
        background: {t["bg"]};
        border: 1px solid {t["line"]};
        border-radius: 8px;
        gridline-color: {t["line"]};
        font-family: {t["font"]};
        font-size: {t["fs_body"]}px;
        color: {t["ink"]};
        selection-background-color: {t["primary_soft"]};
        selection-color: {t["primary"]};
        alternate-background-color: {t["surface"]};
    }}
    QTableWidget::item {{ padding: 6px 8px; }}
    QHeaderView::section {{
        background: {t["surface"]};
        color: {t["muted"]};
        border: none;
        border-bottom: 1px solid {t["line"]};
        padding: 8px;
        font-size: {t["fs_meta"]}px;
        font-weight: 600;
    }}
    QPushButton {{
        background: {t["primary"]};
        color: #ffffff;
        border: none;
        border-radius: 7px;
        padding: 7px 14px;
        font-weight: 600;
        font-family: {t["font"]};
    }}
    QPushButton:hover {{ background: {t["primary_hover"]}; }}
    QPushButton:disabled {{ background: {t["faint"]}; color: {t["surface"]}; }}
    QDateEdit {{
        border: 1px solid {t["line"]};
        border-radius: 7px;
        padding: 6px 8px;
        background: {t["bg"]};
        color: {t["ink"]};
        font-family: {t["font"]};
    }}
    """


def apply(dialog) -> None:
    """Apply the shared CFA chrome to a Qt dialog (best-effort, never raises)."""
    try:
        dialog.setStyleSheet(dialog_qss())
    except Exception:
        pass


# ---------------------------------------------------------------------------
# HTML builders — used inside RichText QLabels. Kept to the CSS subset Qt's
# rich-text engine understands (inline styles on div/span/p; no flexbox).
# ---------------------------------------------------------------------------


def eyebrow(text: str) -> str:
    """A small uppercase brand eyebrow label (the Meldrum 'lesson' cue)."""
    return (
        f"<div style='font-family:{TOKENS['font']};"
        f"font-size:{TOKENS['fs_eyebrow']}px;font-weight:700;"
        f"letter-spacing:.08em;text-transform:uppercase;color:{PRIMARY};"
        f"margin:0 0 2px'>{text}</div>"
    )


def title(text: str) -> str:
    return (
        f"<div style='font-family:{TOKENS['font_heading']};"
        f"font-size:{TOKENS['fs_title']}px;font-weight:700;"
        f"color:{INK};margin:0 0 12px'>{text}</div>"
    )


def page_heading(eyebrow_text: str, title_text: str) -> str:
    """Eyebrow + title as a single heading block.

    The wrapper carries the serif heading face so the title reads as the calm
    MM serif display; the eyebrow re-declares the sans body font so it stays a
    quiet uppercase over-line.
    """
    return (
        f"<div style='font-family:{TOKENS['font_heading']};margin:0 0 12px'>"
        f"{eyebrow(eyebrow_text)}{title(text=title_text)}</div>"
    )


def hero(
    *,
    call: str,
    call_prob: float,
    passed: bool,
    lead_html: str,
    note_html: str,
) -> str:
    """The headline verdict card: a coloured left rule, the big call, a lead
    line of key stats and a small caveat note. ``passed`` picks the pass/fail
    palette."""
    color = PASS if passed else FAIL
    soft = TOKENS["pass_soft"] if passed else TOKENS["fail_soft"]
    return (
        f"<div style='background:{soft};border:1px solid {color};"
        f"border-left:4px solid {color};border-radius:10px;"
        f"padding:12px 16px;margin:0 0 14px'>"
        f"<div style='font-family:{TOKENS['font_heading']};"
        f"font-size:{TOKENS['fs_hero']}px;font-weight:800;"
        f"color:{color};line-height:1.1'>{call} "
        f"<span style='font-size:{TOKENS['fs_lead']}px;font-weight:600'>"
        f"p={call_prob:.2f}</span></div>"
        f"<div style='font-size:{TOKENS['fs_body']}px;color:{INK};"
        f"margin-top:6px'>{lead_html}</div>"
        f"<div style='font-size:{TOKENS['fs_meta']}px;color:{WARN};"
        f"margin-top:6px'>{note_html}</div>"
        f"</div>"
    )


def band(*, name: str, meaning: str, value_html: str, abstain: bool = False) -> str:
    """One honest score presented as a quiet labelled row with a hairline rule.

    ``value_html`` is the already-formatted value/range (or the abstain notice).
    """
    return (
        f"<div style='padding:8px 0;border-top:1px solid {LINE}'>"
        f"<div style='font-size:{TOKENS['fs_body']}px;color:{INK}'>"
        f"<b>{name}</b> <span style='color:{MUTED}'>— {meaning}</span></div>"
        f"<div style='margin-top:2px'>{value_html}</div>"
        f"</div>"
    )


def value_range(low: str, high: str, mid: str) -> str:
    return (
        f"<span style='font-size:{TOKENS['fs_lead']}px;font-weight:700;"
        f"color:{INK}'>{low}–{high}</span> "
        f"<span style='color:{MUTED};font-size:{TOKENS['fs_meta']}px'>"
        f"(midpoint {mid})</span>"
    )


def value_abstain(reason: str) -> str:
    return (
        f"<span style='color:{WARN};font-weight:700'>Not enough data</span> "
        f"<span style='color:{MUTED};font-size:{TOKENS['fs_meta']}px'>· {reason}</span>"
    )


def section(text: str) -> str:
    """A quiet uppercase section divider label."""
    return (
        f"<div style='font-size:{TOKENS['fs_eyebrow']}px;font-weight:700;"
        f"letter-spacing:.06em;text-transform:uppercase;color:{FAINT};"
        f"margin:14px 0 4px'>{text}</div>"
    )


def caption(text: str) -> str:
    """Small muted caption/footnote text."""
    return (
        f"<span style='color:{MUTED};font-size:{TOKENS['fs_meta']}px;"
        f"line-height:1.5'>{text}</span>"
    )


def notice(text: str, *, tone: str = "warn") -> str:
    """A short coloured status line (warn/pass/fail)."""
    color = {"warn": WARN, "pass": PASS, "fail": FAIL}.get(tone, WARN)
    return (
        f"<div style='font-size:{TOKENS['fs_body']}px;font-weight:700;"
        f"color:{color};margin:6px 0'>{text}</div>"
    )
