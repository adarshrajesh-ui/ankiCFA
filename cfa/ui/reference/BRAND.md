# Mark Meldrum — Brand Value Extraction (source of truth)

Extracted from the **real site** <https://www.markmeldrum.com/> via system Google
Chrome (playwright-core, `channel: chrome`, headless) at **1440×900 desktop**,
using `getComputedStyle` + enumeration of every CSS custom property in
`document.styleSheets`. **All rgb/rgba values converted to uppercase hex.**

- Raw machine dump: [`brand-computed.json`](./brand-computed.json)
- **Platform:** WordPress + **BuddyBoss** theme + **LearnDash**. The brand is
  authored as native CSS custom properties (`--bb-*`, `--mm-*`, `--ld-*`), so
  these are **authoritative, not inferred** — including a literal
  `--mm-accent-color`.
- **Navigation note:** `waitUntil:'networkidle'` **timed out** — this site keeps
  long-poll / analytics sockets open and never reaches network-idle. Re-fetched
  with `waitUntil:'load'` → **HTTP 200**, `document.fonts.ready` resolved, 422 CSS
  custom properties + full DOM captured. Every value below is from a
  fully-rendered page.

> ⚠️ This file is a **reference + PROPOSAL** for downstream stations. This station
> did **not** modify `qt/aqt/cfa_style.py` or any CSS.

---

## COLOR

| Name                              | Value                 | Where observed                                                                                   |
| --------------------------------- | --------------------- | ------------------------------------------------------------------------------------------------ |
| Brand navy (structure / headings) | `#122B46`             | `--bb-headings-color`, `--bb-tooltip-background`; all `h1` section titles; `h4` card titles      |
| MM signature accent — green       | `#009666`             | `--mm-accent-color` (literal Meldrum accent); active pricing toggle                              |
| CTA / link accent — orange        | `#DA5C01`             | `--bb-primary-color`, `--bb-primary-button-background-regular`; primary button; in-content links |
| Orange hover                      | `#C45301`             | `--bb-primary-button-background-hover`                                                           |
| Promo CTA — deep green            | `#0A4B36`             | hero `a.banner-redirection` buttons ("Register…", "Explore…")                                    |
| Feature-band green                | `#007E56`             | green section background                                                                         |
| Teal (Sign-In / header hover)     | `#145959` / `#4C8181` | outline "Sign In" text / `--bb-header-links-hover`                                               |
| Link blue (occasional)            | `#00518A`             | some in-content anchors                                                                          |
| Page background                   | `#FAFBFD`             | `--bb-body-background-color`                                                                     |
| Surface (cards / header)          | `#FFFFFF`             | `--bb-content-background-color`, `--bb-header-background`                                        |
| Surface alt                       | `#FBFBFC`             | `--bb-content-alternate-background-color`                                                        |
| Cool section band                 | `#F3F6F8`             | section background                                                                               |
| Warm cream bands                  | `#F1ECE4`, `#F8F5F1`  | section backgrounds (premium warm surfaces)                                                      |
| Hairline / border                 | `#E7E9EC`             | `--bb-content-border-color`                                                                      |
| Body text                         | `#4D5C6D`             | `--bb-body-text-color` (computed `<body>` = `#474747`)                                           |
| Card body text                    | `#6C7485`             | computed color inside `.card`                                                                    |
| Muted / secondary text            | `#939597`             | `--bb-alternate-text-color`, `--bb-sidenav-text-regular`                                         |
| Header links                      | `#515151`             | `--bb-header-links`                                                                              |
| Cover/overlay slate               | `#607387`             | `--bb-cover-image-background-color`                                                              |

**Site semantic colors (reference only — keep existing pass/fail/warn triad):**
success `#1CD991` (`--bb-success-color`), warning `#F7BA45` (`--bb-warning-color`),
danger `#EF3E46` (`--bb-danger-color`), info `#007CFF` (`--bb-default-notice-color`).

---

## TYPOGRAPHY

| Name                                      | Value                                                                                                          | Where observed                          |
| ----------------------------------------- | -------------------------------------------------------------------------------------------------------------- | --------------------------------------- |
| Heading font                              | `"Source Serif 4"` (serif)                                                                                     | every `h1`                              |
| Body font (computed stack)                | `-apple-system, "system-ui", "Segoe UI", Roboto, Oxygen-Sans, Ubuntu, Cantarell, "Helvetica Neue", sans-serif` | `<body>`                                |
| Body font (loaded web font actually used) | **IBM Plex Sans**                                                                                              | hero lead `<p>`, pricing toggle buttons |
| Hero H1                                   | **40px / weight 400 / line-height 42px** / Source Serif 4 / `#122B46` (white over hero imagery)                | `h1.home-h1`                            |
| Stats display                             | **55px / weight 400** / Source Serif 4 / `#122B46`                                                             | `h1.home-h1.mm-stats-heading`           |
| H2 / H3                                   | _not present on homepage_ — the page builder styles section titles as `h1.home-h1`                             | —                                       |
| H4 (card title)                           | **18px / weight 600 / line-height 24px** / system stack / `#122B46`                                            | `h4` ("Lecture Videos", …)              |
| Body / lead                               | **16px / line-height 24px (1.5) / weight 400** / `#4D5C6D`                                                     | `p`                                     |
| Small text                                | 13px                                                                                                           | `--wp--preset--font-size--small`        |
| WP preset sizes                           | small 13 · normal 16 · medium 20 · large 36 · x-large/huge 42 (px)                                             | `--wp--preset--font-size--*`            |

---

## FONTS-LOADED

Named web fonts actually loaded (via `[...document.fonts]`, deduped):

| Family             | Role                                    |
| ------------------ | --------------------------------------- |
| **Source Serif 4** | headings / hero / stats (serif display) |
| **IBM Plex Sans**  | body / lead / interactive labels        |
| SF UI Display      | system-ish display fallback loaded      |
| SF UI Text         | system-ish text fallback loaded         |

_Icon/plugin fonts (excluded from brand): Font Awesome 5 Free/Brands, FontAwesome,
Elusive-Icons, Genericons, dashicons, bb-icons, bb-icons-legacy, ld-icons,
foundation-icons, WooCommerce, slick, star, affirm._

---

## BUTTONS

| Name               | Value                                                                                                                                      | Where observed                                                       |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------- |
| **Primary button** | bg `#DA5C01` · text `#FFFFFF` · border `1px solid #DA5C01` · **radius `100px` (pill)** · padding `0 20px` · weight `500` · hover `#C45301` | `a.button.small.full`; `--bb-primary-button-*`, `--bb-button-radius` |
| Secondary button   | bg `#FFFFFF` · border+text `#DA5C01` · radius `100px`                                                                                      | `--bb-secondary-button-*`                                            |
| Promo CTA (hero)   | bg `#0A4B36` · text `#FFFFFF` · radius `3px` · padding `5px 15px` · weight `700` · 16px                                                    | `a.banner-redirection`                                               |
| Pricing toggle     | bg `#009666` (active) / `#FFFFFF` · radius `4px` · padding `8px 20px` · weight `500` · IBM Plex Sans                                       | `button.pricing-table-year-btn`                                      |
| Radii tokens       | pill `100px` (`--bb-button-radius`) · block `4px` (`--bb-block-radius`) · option `3px` · input `4px`                                       | —                                                                    |

---

## CARDS

| Name                      | Value                                                                                                                  | Where observed                     |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| Feature / pricing card    | bg `#FFFFFF` · **radius `4px`** · border none · **own box-shadow `none`** · margin-bottom `24px` · body text `#6C7485` | `div.card.text-center.card-shadow` |
| Tooltip overlay card      | bg `#122B46` @ 0.95 · text `#FFFFFF` · radius `4px` · padding `7px 15px` · 13px · letter-spacing `-0.24px`             | `label.mm-feature-box-tooltip`     |
| Quiet elevation reference | `rgba(139,141,157,0.05) 0 1px 0`, `rgba(65,71,108,0.15) 0 0 1px`                                                       | `header#masthead` box-shadow       |
| Block radius token        | `4px`                                                                                                                  | `--bb-block-radius`                |

> Note: the `.card-shadow` element itself computes `box-shadow: none`; use the
> site-header quiet double-shadow above as the elevation reference.

---

## SPACING / LAYOUT

| Name                     | Value                                                                   | Where observed                                         |
| ------------------------ | ----------------------------------------------------------------------- | ------------------------------------------------------ |
| Container max-width      | **`1200px`**                                                            | dominant `max-width` (12×) + centered content wrappers |
| Container gutter         | `~10–15px`                                                              | container `padding-left`                               |
| Inner text column        | `540px`                                                                 | 18× `max-width:540px`                                  |
| Two-column split         | `45% / 60%`                                                             | content halves                                         |
| Section vertical padding | **`80px` top** (9×), **`64px` symmetric** (5×), 32px                    | large section blocks                                   |
| Card / content gap       | `24px` (card margin), `32px` (content grid), `96px 64px` (feature grid) | flex/grid `gap` + margins                              |
| Spacing scale (fixed px) | `4, 8, 12, 16, 20, 24, 32, 36, 40, 48, 56, 64, 80, 96, 128`             | `--ld-spacer-fixed-*`                                  |
| Spacing scale (rem)      | `0.25 → 8rem`                                                           | `--ld-spacer-*`                                        |
| Inferred rhythm          | **base 8px**; section 64–80px; card gap 24–32px; container 1200px       | —                                                      |

---

## Proposed TOKENS reconciliation

> **PROPOSAL for the tokens-reconciliation station only.** `cfa_style.py` and all
> CSS were **not** modified here. The `pass`/`fail`/`warn` semantic triad is kept
> as-is. Values are observed on-site unless marked **DERIVED**.
>
> **Key tension:** the site's _interactive_ primary (`--bb-primary-color`) is warm
> **orange `#DA5C01`**, while its _structural_ colour is calm **navy `#122B46`**,
> plus a signature **green `#009666`** (`--mm-accent-color`). This proposal keeps
> the existing token intent (`primary` = calm structural navy, `accent` = warm
> highlight) and surfaces the MM green separately.

| Token                  | Current                                                                  | Proposed                                                                                  | Site source                                                                         |
| ---------------------- | ------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `ink`                  | `#1e293b`                                                                | `#122B46`                                                                                 | `--bb-headings-color`                                                               |
| `muted`                | `#64748b`                                                                | `#4D5C6D`                                                                                 | `--bb-body-text-color`                                                              |
| `faint`                | `#94a3b8`                                                                | `#939597`                                                                                 | `--bb-alternate-text-color`                                                         |
| `line`                 | `#e2e8f0`                                                                | `#E7E9EC`                                                                                 | `--bb-content-border-color`                                                         |
| `surface`              | `#f8fafc`                                                                | `#F3F6F8`                                                                                 | observed cool band (alt `#FBFBFC` = `--bb-content-alternate-background-color`)      |
| `bg`                   | `#ffffff`                                                                | `#FFFFFF`                                                                                 | `--bb-content-background-color` (page tint `#FAFBFD` available)                     |
| `primary`              | `#0f4c81`                                                                | `#122B46`                                                                                 | site structural navy — _coincides with `ink`_; keep-distinct alt = orange `#DA5C01` |
| `primary_soft`         | `#e8f0f8`                                                                | `#F3F6F8`                                                                                 | observed cool band (soft navy/slate tint)                                           |
| `accent`               | `#b45309`                                                                | `#DA5C01`                                                                                 | `--bb-primary-color` (warm CTA orange; hover `#C45301`)                             |
| `accent_soft`          | `#fef3c7`                                                                | `#FCEBDA` **(DERIVED)**                                                                   | soft tint of `#DA5C01` — no exact on-site value                                     |
| `pass`                 | `#15803d`                                                                | **KEEP**                                                                                  | ref `--bb-success-color #1CD991`                                                    |
| `pass_soft`            | `#f0fdf4`                                                                | **KEEP**                                                                                  | —                                                                                   |
| `fail`                 | `#b91c1c`                                                                | **KEEP**                                                                                  | ref `--bb-danger-color #EF3E46`                                                     |
| `fail_soft`            | `#fef2f2`                                                                | **KEEP**                                                                                  | —                                                                                   |
| `warn`                 | `#b45309`                                                                | **KEEP**                                                                                  | ref `--bb-warning-color #F7BA45`                                                    |
| `accent`               | `#b45309`                                                                | `#DA5C01`                                                                                 | (see above)                                                                         |
| `font`                 | `-apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif` | `"IBM Plex Sans", -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif` | loaded body web font                                                                |
| `font_heading` _(new)_ | _(none)_                                                                 | `"Source Serif 4", Georgia, "Times New Roman", serif`                                     | `h1` headings — propose a serif display token for the MM feel                       |
| `fs_hero`              | `26`                                                                     | `28`                                                                                      | hero 40px serif @400 scaled to dialog                                               |
| `fs_title`             | `22`                                                                     | `22`                                                                                      | keep                                                                                |
| `fs_lead`              | `15`                                                                     | `16`                                                                                      | site body 16px                                                                      |
| `fs_body`              | `14`                                                                     | `15`                                                                                      | site body 16px → 15 dialog-scale (line-height ~1.5)                                 |
| `fs_meta`              | `12`                                                                     | `12`                                                                                      | site small 13px                                                                     |
| `fs_eyebrow`           | `11`                                                                     | `11`                                                                                      | site pre-title 12px                                                                 |

**Extra recommendations for the tokens station**

- **MM signature green `#009666`** has no current token slot. Add a secondary /
  brand-accent token (or use it for eyebrows, hero rules, progress). **Do not**
  overwrite the semantic `pass` green.
- Body **line-height ≈ 1.5**.
- **Primary button radius `100px` (pill)**; blocks/cards `4px`.
- **Container `1200px`**, **section padding `64–80px`**, base spacing unit **8px**.
