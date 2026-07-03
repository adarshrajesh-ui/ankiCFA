# CFA design system (F5)

The CFA fork ships one calm, finance-education visual language — modelled on the
_learning_ aesthetic of Mark Meldrum's lessons (restrained type scale, generous
spacing, a quiet slate/navy palette, understated card + table chrome, **no**
marketing chrome) — shared across every CFA surface so they read as one product.

## Single source of truth

- **`qt/aqt/cfa_style.py` — `TOKENS`** is the canonical palette + type scale. It
  provides the desktop dialog stylesheet (`dialog_qss`) and small HTML builders
  (`eyebrow`, `page_heading`, `hero`, `band`, `section`, `caption`, `notice`)
  that the Qt dialogs compose instead of hand-rolling inline styles.
- **`cfa/ethics_pairs/templates/style.css` — `:root`** mirrors those tokens as
  CSS custom properties (`--cfa-ink`, `--cfa-primary`, `--cfa-accent`, …) so the
  ethics card matches the dialogs exactly.

The two are kept in lock-step by a **parity test**
(`qt/tests/test_cfa_f5_style.py::test_card_root_mirrors_python_tokens`): the
card's `:root` hex values must equal the Python tokens, or CI fails. This is the
guardrail that keeps the palette from drifting.

## Brand source of truth

The palette + type scale are reconciled to the **real markmeldrum.com** brand,
extracted (via headless Chrome + `getComputedStyle` over the site's authored
BuddyBoss/LearnDash CSS custom properties) into
[`cfa/ui/reference/BRAND.md`](../../cfa/ui/reference/BRAND.md) (with the raw
machine dump in `cfa/ui/reference/brand-computed.json` and the desktop/mobile
section captures under `cfa/ui/reference/site/`). That reference is the single
source of truth for every hex and font below. The one deliberate divergence is
the **semantic pass/fail/warn triad**, which is kept as-is (the site's own
success/danger/warning colours are noted in `BRAND.md` for reference only).

## Palette

Every value below is sourced from the real site (see `BRAND.md`); the semantic
triad is intentionally preserved.

| Token                    | Hex                   | Role → site source                                          |
| ------------------------ | --------------------- | ----------------------------------------------------------- |
| `ink`                    | `#122B46`             | primary text — brand navy (`--bb-headings-color`)           |
| `muted`                  | `#4D5C6D`             | secondary text (`--bb-body-text-color`)                     |
| `faint`                  | `#939597`             | captions / disabled (`--bb-alternate-text-color`)           |
| `line`                   | `#E7E9EC`             | hairline borders (`--bb-content-border-color`)              |
| `surface`                | `#F3F6F8`             | panels / table stripes (cool section band)                  |
| `bg`                     | `#ffffff`             | page background (`--bb-content-background-color`)           |
| `primary`                | `#122B46`             | structural navy — coincides with `ink` on the real site     |
| `primary_soft`           | `#F3F6F8`             | soft navy/slate tint fill (selected, AI block)              |
| `pass` / `pass_soft`     | `#15803d` / `#f0fdf4` | "likely pass" (semantic triad — **kept**)                   |
| `fail` / `fail_soft`     | `#b91c1c` / `#fef2f2` | "likely fail" (semantic triad — **kept**)                   |
| `warn`                   | `#b45309`             | caution / caveats (semantic triad — **kept**)               |
| `accent` / `accent_soft` | `#DA5C01` / `#FCEBDA` | warm CTA accent (`--bb-primary-color`; soft = derived tint) |

Type scale (px): title 22 · hero 28 · lead 16 · body 15 · meta 12 · eyebrow 11.

Fonts: **body** `IBM Plex Sans` (the site's loaded body web font, → system
fallbacks); **headings** `font_heading` = `Source Serif 4` (the site's serif
display face for every `h1`, → Georgia / serif) wired into the `title`,
`page_heading` and `hero` verdict builders so headings read as the calm MM serif.

## Website section → app surface

How the real site's sections map onto the CFA desktop surfaces:

| markmeldrum.com section          | App surface                                            |
| -------------------------------- | ------------------------------------------------------ |
| Hero (serif H1 over imagery)     | Dialog headers (`page_heading`: eyebrow + serif title) |
| Stats band (large serif figures) | Exam Readiness verdict (`hero`) + honest-score bands   |
| Pricing / schedule table         | Deadline planner table                                 |
| Feature cards                    | Menu / score cards                                     |
| Question-bank / lesson pages     | Ethics card                                            |

Per-surface before/after captures live under `cfa/ui/reference/app/` and will be
embedded here as the overhaul lands surface by surface.

## Surfaces restyled

- **Exam Readiness dialog** — eyebrow + title heading, a coloured hero verdict
  card (pass/fail palette), quiet `HONEST SCORES` / `PER-TOPIC RECALL` section
  labels, and a clean gridless striped table with a full-width topic column.
- **Deadline planner dialog** — matching heading, a styled date picker + navy
  action button, and the same table chrome.
- **Ethics card** — navy cluster tag + verdict buttons, warm-orange evidence
  highlights, navy primary button, all driven by the shared `:root` tokens.

## Proof

`tools/cfa/render_f5_proof.py --tag {before|after}` grabs the real dialogs
(offscreen Qt) and the real ethics card (headless Chrome) to
`proof/gnhf2/f5-{readiness,deadline,ethics-card}-{before,after}.png` for an
honest side-by-side. Run `just cfa-f5-test` for the test suite.
