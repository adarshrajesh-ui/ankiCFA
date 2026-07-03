// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! CFA fork (DOK-4): read-only *deadline-retention* analysis.
//!
//! FSRS optimises the least-cost schedule for *indefinite* retention. The CFA
//! exam instead needs peak retention on ONE date. This module backs the
//! read-only `DeadlineRetention` RPC, which for a deck + exam date:
//!
//! 1. predicts each due card's FSRS retrievability **at the exam date**
//!    (reusing the very same `current_retrievability_seconds` helper the rest
//!    of the engine and `BuildExamQueue` use, but advancing the elapsed time
//!    out to the exam instant), and
//! 2. proposes a deadline-adjusted next interval = `min(FSRS interval,
//!    days_to_exam)` so the next review never lands *after* the exam,
//!    tightening as the exam nears.
//!
//! Cards are returned sorted by lowest predicted exam-day recall first, so the
//! weakest-on-the-day cards surface. Like `BuildExamQueue`, nothing is written:
//! it only reads cards and returns values, so FSRS scheduling and the undo
//! history stay valid.
//!
//! This is deliberately NAIVE (a per-card cap + reweight, not an
//! optimal-control solution) but it is a real, second engine change distinct
//! from `BuildExamQueue` — see `docs/cfa/DOK4-DEADLINE.md`.

use std::cmp::Ordering;

use anki_proto::scheduler;
use fsrs::FSRS;
use fsrs::FSRS5_DEFAULT_DECAY;

use crate::card::Card;
use crate::prelude::*;
use crate::scheduler::timing::SchedTimingToday;
use crate::search::JoinSearches;
use crate::search::SearchNode;
use crate::search::StateKind;

const SECS_PER_DAY: i64 = 86_400;

impl Collection {
    /// Read-only deadline-retention analysis backing the `DeadlineRetention`
    /// RPC (CFA fork, DOK-4).
    ///
    /// Gathers the due (review + learning) cards for a deck and its subdecks
    /// *without* mutating any card, queue, or scheduling state, predicts each
    /// card's FSRS retrievability at `exam_date`, caps its next interval at the
    /// days remaining, and returns the parallel arrays sorted by predicted
    /// exam-day recall ascending (weakest first). Because it never writes, FSRS
    /// scheduling and the undo history stay valid.
    pub(crate) fn deadline_retention(
        &mut self,
        input: scheduler::DeadlineRetentionRequest,
    ) -> Result<scheduler::DeadlineRetentionResponse> {
        let now = TimestampSecs::now();
        let days_to_exam = days_until(now, input.exam_date);

        // Read-only gather of the deck tree's due cards (same search shape as
        // BuildExamQueue).
        let search = SearchNode::DeckIdWithChildren(DeckId(input.deck_id))
            .and(SearchNode::State(StateKind::Due));
        let cards = self.all_cards_for_search(search)?;
        if cards.is_empty() {
            return Ok(scheduler::DeadlineRetentionResponse::default());
        }

        let timing = self.timing_today()?;
        let fsrs = FSRS::new(None).unwrap();

        let mut rows: Vec<(CardId, f32, u32)> = cards
            .iter()
            .map(|card| {
                let predicted =
                    predicted_recall_at_exam(&fsrs, card, &timing, input.exam_date, now);
                let suggested = capped_interval(card.interval, days_to_exam);
                (card.id, predicted, suggested)
            })
            .collect();

        // Weakest predicted exam-day recall first; ties broken by ascending id
        // for determinism.
        rows.sort_by(|a, b| {
            a.1.partial_cmp(&b.1)
                .unwrap_or(Ordering::Equal)
                .then(a.0.cmp(&b.0))
        });

        let limit = if input.fetch_limit == 0 {
            rows.len()
        } else {
            (input.fetch_limit as usize).min(rows.len())
        };
        let rows = &rows[..limit];

        Ok(scheduler::DeadlineRetentionResponse {
            card_ids: rows.iter().map(|(id, _, _)| id.0).collect(),
            predicted_recall: rows.iter().map(|(_, r, _)| *r).collect(),
            suggested_interval_days: rows.iter().map(|(_, _, ivl)| *ivl).collect(),
        })
    }
}

/// Whole days from `now` until `exam_date` (both Unix seconds), rounded toward
/// zero. Negative when the exam is already in the past.
fn days_until(now: TimestampSecs, exam_date: i64) -> i64 {
    (exam_date - now.0) / SECS_PER_DAY
}

/// Deadline-capped next interval: `min(fsrs_interval, days_to_exam)` clamped to
/// be non-negative, so the next review never lands after the exam. An exam
/// today or in the past caps the interval at 0 (review now; schedule nothing
/// beyond the deadline).
fn capped_interval(fsrs_interval_days: u32, days_to_exam: i64) -> u32 {
    // clamp is safe: the low bound (0) is always <= the high bound (>= 0).
    days_to_exam.clamp(0, fsrs_interval_days as i64) as u32
}

/// Predicted FSRS retrievability at the exam date, in [0,1]. Reuses the exact
/// `current_retrievability_seconds` helper FSRS/BuildExamQueue rely on, but
/// advances the elapsed time out to the exam instant (`elapsed_now + horizon`).
/// Cards with no memory state (never reviewed) are treated as maximally weak
/// (0.0) so they surface first.
fn predicted_recall_at_exam(
    fsrs: &FSRS,
    card: &Card,
    timing: &SchedTimingToday,
    exam_date: i64,
    now: TimestampSecs,
) -> f32 {
    match card.memory_state {
        Some(state) => {
            let elapsed_now = card.seconds_since_last_review(timing).unwrap_or_default() as i64;
            let horizon = exam_date - now.0;
            let elapsed_at_exam = (elapsed_now + horizon).max(0) as u32;
            fsrs.current_retrievability_seconds(
                state.into(),
                elapsed_at_exam,
                card.decay.unwrap_or(FSRS5_DEFAULT_DECAY),
            )
        }
        None => 0.0,
    }
}

#[cfg(test)]
mod tests {
    use anki_proto::scheduler::DeadlineRetentionRequest;
    use fsrs::FSRS5_DEFAULT_DECAY;

    use super::*;
    use crate::card::CardQueue;
    use crate::card::CardType;
    use crate::card::FsrsMemoryState;
    use crate::services::SchedulerService;
    use crate::tests::DeckAdder;

    const DAY: i64 = 86_400;

    /// Adds a note whose single card becomes a *due review* card with the given
    /// optional FSRS memory state (stability, difficulty), stored `interval`,
    /// last reviewed `days_since_review` days ago. Memory state `None` models a
    /// card with no FSRS data.
    fn add_due_card(
        col: &mut Collection,
        deck: DeckId,
        memory: Option<(f32, f32)>,
        interval: u32,
        days_since_review: i64,
    ) -> CardId {
        let nt = col.basic_notetype();
        let mut note = nt.new_note();
        note.set_field(0, "q").unwrap();
        col.add_note(&mut note, deck).unwrap();

        let cid = col.storage.card_ids_of_notes(&[note.id]).unwrap()[0];
        let mut card = col.storage.get_card(cid).unwrap().unwrap();
        card.queue = CardQueue::Review;
        card.ctype = CardType::Review;
        card.due = 0;
        card.interval = interval;
        card.decay = Some(FSRS5_DEFAULT_DECAY);
        card.last_review_time = Some(TimestampSecs::now().adding_secs(-DAY * days_since_review));
        card.memory_state = memory.map(|(stability, difficulty)| FsrsMemoryState {
            stability,
            difficulty,
        });
        col.storage.update_card(&card).unwrap();
        cid
    }

    /// Runs the RPC for `deck` with an exam `exam_in_days` from now (negative =
    /// past), returning (card_ids, predicted_recall, suggested_interval_days).
    fn deadline(
        col: &mut Collection,
        deck: DeckId,
        exam_in_days: i64,
    ) -> (Vec<i64>, Vec<f32>, Vec<u32>) {
        let exam_date = TimestampSecs::now().adding_secs(DAY * exam_in_days).0;
        let resp = SchedulerService::deadline_retention(
            col,
            DeadlineRetentionRequest {
                deck_id: deck.0,
                exam_date,
                fetch_limit: 0,
            },
        )
        .unwrap();
        (
            resp.card_ids,
            resp.predicted_recall,
            resp.suggested_interval_days,
        )
    }

    // --- pure helper unit tests -------------------------------------------

    #[test]
    fn capped_interval_is_min_of_fsrs_interval_and_days_to_exam() {
        // Exam farther than the FSRS interval -> keep the FSRS interval.
        assert_eq!(capped_interval(30, 100), 30);
        // Exam nearer than the FSRS interval -> tighten to the days remaining.
        assert_eq!(capped_interval(30, 5), 5);
        // Exam today -> no review scheduled beyond the deadline.
        assert_eq!(capped_interval(30, 0), 0);
        // Exam already passed -> clamp to 0, never negative.
        assert_eq!(capped_interval(30, -7), 0);
        // A zero FSRS interval stays zero regardless of a distant exam.
        assert_eq!(capped_interval(0, 100), 0);
    }

    #[test]
    fn days_until_is_signed_and_rounds_toward_zero() {
        let now = TimestampSecs(1_000_000);
        assert_eq!(days_until(now, 1_000_000 + 10 * DAY), 10);
        assert_eq!(days_until(now, 1_000_000 - 3 * DAY), -3);
        // 1.5 days rounds toward zero to 1.
        assert_eq!(days_until(now, 1_000_000 + DAY + DAY / 2), 1);
    }

    // --- RPC integration tests --------------------------------------------

    #[test]
    fn suggested_interval_is_capped_at_days_to_exam() {
        let mut col = Collection::new();
        // interval 30, reviewed today, strong memory.
        let cid = add_due_card(&mut col, DeckId(1), Some((100.0, 5.0)), 30, 0);

        // Exam in 5 days: 30-day interval must be capped to 5 so the next review
        // sits before the exam.
        let (ids, _, near) = deadline(&mut col, DeckId(1), 5);
        assert_eq!(ids, vec![cid.0]);
        assert_eq!(near, vec![5], "interval capped to the days remaining");

        // Exam in 100 days: interval left at the FSRS value.
        let (_, _, far) = deadline(&mut col, DeckId(1), 100);
        assert_eq!(far, vec![30], "far exam leaves the FSRS interval intact");
    }

    #[test]
    fn lower_predicted_recall_sorts_first() {
        let mut col = Collection::new();
        // Same interval / review age; only stability differs. Lower stability =>
        // lower retrievability at the exam => must rank first.
        let strong = add_due_card(&mut col, DeckId(1), Some((1000.0, 5.0)), 20, 10);
        let weak = add_due_card(&mut col, DeckId(1), Some((3.0, 5.0)), 20, 10);

        let (ids, recall, _) = deadline(&mut col, DeckId(1), 14);
        assert_eq!(ids, vec![weak.0, strong.0], "weaker card ranks first");
        assert!(
            recall[0] < recall[1],
            "predicted recall is ascending: {recall:?}"
        );
    }

    #[test]
    fn never_reviewed_card_is_treated_as_weakest() {
        let mut col = Collection::new();
        let strong = add_due_card(&mut col, DeckId(1), Some((500.0, 5.0)), 15, 1);
        // No memory state -> predicted recall 0.0 -> surfaces first.
        let fresh = add_due_card(&mut col, DeckId(1), None, 15, 1);

        let (ids, recall, _) = deadline(&mut col, DeckId(1), 20);
        assert_eq!(ids[0], fresh.0, "card with no memory state surfaces first");
        assert_eq!(recall[0], 0.0);
        assert_eq!(ids[1], strong.0);
    }

    #[test]
    fn recall_drops_as_the_exam_moves_farther_out() {
        let mut col = Collection::new();
        add_due_card(&mut col, DeckId(1), Some((30.0, 5.0)), 20, 0);

        let (_, near, _) = deadline(&mut col, DeckId(1), 1);
        let (_, far, _) = deadline(&mut col, DeckId(1), 60);
        assert!(
            near[0] > far[0],
            "recall predicted at a later exam is lower ({} !> {})",
            near[0],
            far[0]
        );
    }

    #[test]
    fn exam_in_the_past_caps_all_intervals_at_zero() {
        let mut col = Collection::new();
        add_due_card(&mut col, DeckId(1), Some((50.0, 5.0)), 30, 2);

        // Exam 3 days ago: still returns the card (with a predicted recall) but
        // never schedules a review past the (already elapsed) deadline.
        let (ids, recall, suggested) = deadline(&mut col, DeckId(1), -3);
        assert_eq!(ids.len(), 1);
        assert_eq!(suggested, vec![0], "past exam -> zero-day cap");
        assert!((0.0..=1.0).contains(&recall[0]));
    }

    #[test]
    fn empty_deck_returns_empty() {
        let mut col = Collection::new();
        let empty = DeckAdder::new("Empty").add(&mut col);
        // A due card exists elsewhere, but the queried deck has none.
        add_due_card(&mut col, DeckId(1), Some((50.0, 5.0)), 30, 0);

        let (ids, recall, suggested) = deadline(&mut col, empty.id, 30);
        assert!(ids.is_empty());
        assert!(recall.is_empty());
        assert!(suggested.is_empty());
    }

    #[test]
    fn fetch_limit_truncates_after_sorting() {
        let mut col = Collection::new();
        let strong = add_due_card(&mut col, DeckId(1), Some((1000.0, 5.0)), 20, 10);
        let weak = add_due_card(&mut col, DeckId(1), Some((3.0, 5.0)), 20, 10);

        let exam_date = TimestampSecs::now().adding_secs(DAY * 14).0;
        let resp = SchedulerService::deadline_retention(
            &mut col,
            DeadlineRetentionRequest {
                deck_id: DeckId(1).0,
                exam_date,
                fetch_limit: 1,
            },
        )
        .unwrap();
        assert_eq!(
            resp.card_ids,
            vec![weak.0],
            "only the single weakest card is returned"
        );
        assert_ne!(resp.card_ids, vec![strong.0]);
    }

    #[test]
    fn deadline_retention_is_read_only_and_preserves_undo() {
        let mut col = Collection::new();
        let cid = add_due_card(&mut col, DeckId(1), Some((10.0, 5.0)), 12, 3);

        // A real, undoable mutation to establish an undo point + baseline state.
        col.set_due_date(&[cid], "0", None).unwrap();
        let before = col.storage.get_card(cid).unwrap().unwrap();
        assert!(col.can_undo().is_some());

        // Running the analysis twice must be idempotent and non-mutating.
        let (ids1, _, _) = deadline(&mut col, DeckId(1), 10);
        let (ids2, _, _) = deadline(&mut col, DeckId(1), 10);
        assert_eq!(ids1, ids2);
        let after = col.storage.get_card(cid).unwrap().unwrap();
        assert_eq!(
            (before.due, before.queue, before.interval),
            (after.due, after.queue, after.interval),
            "analysis must not mutate the card"
        );

        // Undo still targets set_due_date (analysis added no undo step).
        col.undo().unwrap();
        assert_eq!(
            col.storage.get_card(cid).unwrap().unwrap().queue,
            CardQueue::Review,
            "undo restored the pre-set_due_date state"
        );
    }
}
