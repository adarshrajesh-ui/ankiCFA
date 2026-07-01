#!/usr/bin/env python
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Author a hand-written CFA Level II deck.

Creates a "CFA Level II" deck whose notes are tagged with hierarchical
``los::<topic>::<reading>`` tags — the join key used by the exam-queue engine
and the memory score — and persists representative per-topic exam weights.

Content is hand-authored (there is no AI/generation anywhere in this app). It is
a representative slice of the ten CFA Level II topic areas, not the full
curriculum.

Usage:
    out/pyenv/bin/python tools/cfa/build_cfa_deck.py --path /tmp/cfa.anki2
    out/pyenv/bin/python tools/cfa/build_cfa_deck.py --path /tmp/cfa.anki2 --apkg /tmp/cfa.apkg
"""

from __future__ import annotations

import argparse
import os
import sys

# Approximate CFA Level II topic weights (midpoints of the published ranges),
# summing to ~1.0. Keys are los:: topic prefixes.
TOPIC_WEIGHTS: dict[str, float] = {
    "los::ethics": 0.12,
    "los::quant": 0.08,
    "los::economics": 0.08,
    "los::fsa": 0.12,
    "los::corporate": 0.08,
    "los::equity": 0.12,
    "los::fixed-income": 0.12,
    "los::derivatives": 0.08,
    "los::alternatives": 0.08,
    "los::portfolio": 0.12,
}

# (topic, reading, front, back). Hand-authored, factual CFA L2 content.
CARDS: list[tuple[str, str, str, str]] = [
    # Ethics
    (
        "ethics",
        "code-standards",
        "Under Standard III(B) Fair Dealing, may a member offer different service levels to clients?",
        "Yes — different levels of service are permitted if disclosed and offered to all clients; they must not disadvantage any client.",
    ),
    (
        "ethics",
        "code-standards",
        "What does Standard VI(A) Disclosure of Conflicts require?",
        "Full and fair disclosure of all matters that could impair independence/objectivity or interfere with duties, in plain language, prominently.",
    ),
    (
        "ethics",
        "gips",
        "Under GIPS, what is the required minimum track record when a firm claims compliance?",
        "At least 5 years of compliant history (or since inception if younger), building to a minimum of 10 years.",
    ),
    # Quantitative methods
    (
        "quant",
        "multiple-regression",
        "In multiple regression, what does an F-test evaluate?",
        "The joint significance of all slope coefficients (H0: all slopes = 0).",
    ),
    (
        "quant",
        "multiple-regression",
        "What problem does a high variance inflation factor (VIF > 5–10) indicate?",
        "Multicollinearity — independent variables are highly correlated, inflating coefficient standard errors.",
    ),
    (
        "quant",
        "time-series",
        "What condition makes an AR(1) time series covariance-stationary?",
        "The absolute value of the lag-1 coefficient is < 1, so the series has a finite mean-reverting level.",
    ),
    # Economics
    (
        "economics",
        "currency",
        "State covered interest rate parity for the forward premium/discount.",
        "The forward rate differs from spot by (1+r_domestic)/(1+r_foreign); the higher-yield currency trades at a forward discount.",
    ),
    (
        "economics",
        "currency",
        "Under the Mundell–Fleming model, how does expansionary fiscal policy affect a currency with high capital mobility?",
        "It raises interest rates, attracts capital inflows, and causes the currency to appreciate.",
    ),
    (
        "economics",
        "growth",
        "In the Solow model, what drives sustained per-capita growth in steady state?",
        "Technological progress (total factor productivity); capital deepening alone faces diminishing returns.",
    ),
    # Financial statement analysis
    (
        "fsa",
        "intercorporate",
        "When is the equity method used for an intercorporate investment?",
        "For significant influence, generally 20–50% ownership; the investment is carried at cost plus share of investee earnings less dividends.",
    ),
    (
        "fsa",
        "intercorporate",
        "Under acquisition-method consolidation, how is goodwill measured (full goodwill)?",
        "Fair value of the entire acquiree (consideration + fair value of NCI) minus the fair value of identifiable net assets.",
    ),
    (
        "fsa",
        "pensions",
        "Where are actuarial gains/losses on a defined-benefit plan reported under IFRS?",
        "Remeasurements are recognized in Other Comprehensive Income and are not amortized to P&L.",
    ),
    # Corporate issuers
    (
        "corporate",
        "capital-structure",
        "Per Modigliani–Miller Proposition II (with taxes), what happens to cost of equity as leverage rises?",
        "Cost of equity increases linearly with the debt-to-equity ratio, but the tax shield lowers WACC.",
    ),
    (
        "corporate",
        "esg",
        "Name two common approaches to integrating ESG into equity analysis.",
        "Negative screening (exclude sectors) and ESG integration / best-in-class selection; also thematic and impact investing.",
    ),
    (
        "corporate",
        "capital-structure",
        "What is the pecking-order theory of financing?",
        "Firms prefer internal funds first, then debt, and issue equity last, due to asymmetric-information signaling costs.",
    ),
    # Equity
    (
        "equity",
        "ddm",
        "State the Gordon (constant) growth dividend discount model.",
        "V0 = D1 / (r − g), valid when the required return r exceeds the constant growth rate g.",
    ),
    (
        "equity",
        "fcfe",
        "Give the formula for FCFE from FCFF.",
        "FCFE = FCFF − Interest×(1−tax) + Net borrowing.",
    ),
    (
        "equity",
        "residual-income",
        "How is residual income defined for one period?",
        "Net income minus an equity charge = NI − (equity capital × cost of equity).",
    ),
    # Fixed income
    (
        "fixed-income",
        "term-structure",
        "What does a positive value of the swap spread indicate about credit/liquidity?",
        "It reflects the premium of the swap (interbank) rate over the comparable-maturity government yield — higher spread = more perceived credit/liquidity risk.",
    ),
    (
        "fixed-income",
        "valuation",
        "How does an arbitrage-free binomial tree value an option-free bond?",
        "Discount cash flows using one-period forward rates at each node, taking the expected present value backward through the tree.",
    ),
    (
        "fixed-income",
        "credit",
        "Define the recovery rate in structural credit models.",
        "The percentage of a bond's par (or market value) that holders receive upon default; loss given default = 1 − recovery rate.",
    ),
    # Derivatives
    (
        "derivatives",
        "forwards-futures",
        "What is the value of a forward contract to the long at initiation, and why?",
        "Zero — the forward price is set so no cash changes hands; value accrues only as the spot/forward diverges thereafter.",
    ),
    (
        "derivatives",
        "options",
        "State put–call parity for European options.",
        "Call + PV(exercise price) = Put + Underlying (c + X/(1+r)^T = p + S0).",
    ),
    (
        "derivatives",
        "swaps",
        "How is the fixed rate on a plain-vanilla interest-rate swap determined at initiation?",
        "It is the rate that sets the present value of fixed and floating legs equal, derived from the current discount factors.",
    ),
    # Alternative investments
    (
        "alternatives",
        "real-estate",
        "Name the three approaches to appraising commercial real estate.",
        "Income (capitalization/DCF), cost, and sales-comparison approaches.",
    ),
    (
        "alternatives",
        "private-equity",
        "What does a J-curve describe in private equity?",
        "Early negative returns from fees and immature investments, followed by positive returns as portfolio companies mature and exit.",
    ),
    (
        "alternatives",
        "commodities",
        "Distinguish contango from backwardation in a futures curve.",
        "Contango: futures price above spot (upward curve). Backwardation: futures below spot (downward curve).",
    ),
    # Portfolio management
    (
        "portfolio",
        "capm",
        "What does the security market line (SML) plot?",
        "Expected return against beta (systematic risk); its slope is the market risk premium.",
    ),
    (
        "portfolio",
        "multifactor",
        "In the Fama–French three-factor model, what are the three factors?",
        "Market excess return, SMB (size), and HML (value).",
    ),
    (
        "portfolio",
        "risk",
        "Define active risk (tracking error).",
        "The standard deviation of active returns (portfolio return minus benchmark return).",
    ),
]


def build(path: str, apkg: str | None) -> None:
    # Ensure the built pylib is importable when run from the repo.
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for p in ("pylib", "out/pylib"):
        full = os.path.join(repo, p)
        if full not in sys.path:
            sys.path.insert(0, full)

    from anki import cfa
    from anki.collection import Collection
    from anki.exporting import AnkiPackageExporter

    col = Collection(path)
    try:
        deck_id = col.decks.id("CFA Level II")
        assert deck_id is not None
        notetype = col.models.by_name("Basic")

        added = 0
        for topic, reading, front, back in CARDS:
            note = col.new_note(notetype)
            note["Front"] = front
            note["Back"] = back
            note.tags = [f"los::{topic}::{reading}"]
            col.add_note(note, deck_id)
            added += 1

        cfa.set_exam_config(
            col,
            exam_date="2026-08-25",  # a representative CFA Level II sitting
            topic_weights=TOPIC_WEIGHTS,
        )

        print(
            f"Added {added} notes across {len(TOPIC_WEIGHTS)} topics to 'CFA Level II'."
        )
        print(f"Exam config stored (exam_date + {len(TOPIC_WEIGHTS)} topic weights).")

        if apkg:
            exporter = AnkiPackageExporter(col)
            exporter.did = deck_id
            exporter.exportInto(apkg)
            print(f"Exported deck to {apkg}")
    finally:
        col.close()


def main() -> None:
    ap = argparse.ArgumentParser(description="Build a hand-authored CFA Level II deck.")
    ap.add_argument(
        "--path", required=True, help="Path to the .anki2 collection to write into."
    )
    ap.add_argument("--apkg", help="Optional path to also export an .apkg for import.")
    args = ap.parse_args()
    build(args.path, args.apkg)


if __name__ == "__main__":
    main()
