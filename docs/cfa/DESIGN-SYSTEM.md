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

## Palette

| Token                    | Hex                   | Role                                          |
| ------------------------ | --------------------- | --------------------------------------------- |
| `ink`                    | `#1e293b`             | primary text (deep slate)                     |
| `muted`                  | `#64748b`             | secondary text                                |
| `faint`                  | `#94a3b8`             | captions / disabled                           |
| `line`                   | `#e2e8f0`             | hairline borders                              |
| `surface`                | `#f8fafc`             | panels / table stripes                        |
| `primary`                | `#0f4c81`             | calm finance navy — structure, not decoration |
| `primary_soft`           | `#e8f0f8`             | navy tint fill (selected, AI block)           |
| `pass` / `pass_soft`     | `#15803d` / `#f0fdf4` | "likely pass"                                 |
| `fail` / `fail_soft`     | `#b91c1c` / `#fef2f2` | "likely fail"                                 |
| `warn`                   | `#b45309`             | caution / caveats                             |
| `accent` / `accent_soft` | `#b45309` / `#fef3c7` | warm evidence-highlight span                  |

Type scale (px): title 22 · hero 26 · lead 15 · body 14 · meta 12 · eyebrow 11.

## Surfaces restyled

- **Exam Readiness dialog** — eyebrow + title heading, a coloured hero verdict
  card (pass/fail palette, or the warn/accent palette when it abstains below the
  give-up threshold), quiet `HONEST SCORES` / `PER-TOPIC RECALL` section
  labels, and a clean gridless striped table with a full-width topic column.
- **Deadline planner dialog** — matching heading, a styled date picker + navy
  action button, and the same table chrome.
- **Ethics card** — navy cluster tag + verdict buttons, warm-gold evidence
  highlights, navy primary button, all driven by the shared `:root` tokens.

## Proof

`tools/cfa/render_f5_proof.py --tag {before|after}` grabs the real dialogs
(offscreen Qt) and the real ethics card (headless Chrome) to
`proof/gnhf2/f5-{readiness,deadline,ethics-card}-{before,after}.png` for an
honest side-by-side. Run `just cfa-f5-test` for the test suite.
