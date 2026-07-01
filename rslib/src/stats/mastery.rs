// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! Per-deck "mastery query": for every deck, compute how many of its cards are
//! considered mastered and the average recall proxy across its reviewed cards.
//!
//! This is computed entirely in the Rust engine so both the desktop and mobile
//! clients get identical numbers over the same collection, without duplicating
//! the definition of "mastered" in each front-end language.

use std::collections::HashMap;

use anki_proto::stats::deck_mastery_response::DeckMastery;
use anki_proto::stats::DeckMasteryResponse;

use crate::card::CardType;
use crate::prelude::*;

/// A card counts as "mastered" once it is a review card whose current interval
/// is at least this many days.
pub(crate) const MASTERY_INTERVAL_DAYS: u32 = 21;

#[derive(Default)]
struct DeckMasteryAccumulator {
    total_cards: u32,
    mastered_count: u32,
    /// Sum of per-card recall over cards that have been reviewed at least once.
    recall_sum: f32,
    /// Number of cards that have been reviewed at least once.
    reviewed_cards: u32,
}

impl DeckMasteryAccumulator {
    fn add_card(&mut self, card: &Card) {
        self.total_cards += 1;
        if card.ctype == CardType::Review && card.interval >= MASTERY_INTERVAL_DAYS {
            self.mastered_count += 1;
        }
        if card.reps > 0 {
            // reps is always >= lapses, so this stays within 0.0..=1.0.
            let correct = card.reps.saturating_sub(card.lapses);
            self.recall_sum += correct as f32 / card.reps as f32;
            self.reviewed_cards += 1;
        }
    }

    fn avg_recall(&self) -> f32 {
        if self.reviewed_cards == 0 {
            0.0
        } else {
            self.recall_sum / self.reviewed_cards as f32
        }
    }
}

impl Collection {
    /// Returns a mastery summary for every (non-filtered) deck, ordered by deck
    /// id for deterministic output. Decks with no cards are included with zero
    /// counts.
    pub fn deck_mastery(&mut self) -> Result<DeckMasteryResponse> {
        let decks = self.storage.get_all_decks()?;

        // Seed an accumulator for every real deck so empty decks still appear.
        let mut per_deck: HashMap<DeckId, DeckMasteryAccumulator> = HashMap::new();
        let mut names: HashMap<DeckId, String> = HashMap::new();
        for deck in &decks {
            if deck.is_filtered() {
                continue;
            }
            per_deck.entry(deck.id).or_default();
            names.insert(deck.id, deck.human_name());
        }

        for card in self.storage.all_cards()? {
            // Cards temporarily pulled into a filtered deck retain their home
            // deck in original_deck_id; attribute them there so mastery is
            // stable regardless of study state.
            let home_deck = if card.original_deck_id.0 != 0 {
                card.original_deck_id
            } else {
                card.deck_id
            };
            per_deck.entry(home_deck).or_default().add_card(&card);
        }

        let mut deck_ids: Vec<DeckId> = per_deck.keys().copied().collect();
        deck_ids.sort_unstable();

        let decks = deck_ids
            .into_iter()
            .map(|id| {
                let acc = &per_deck[&id];
                DeckMastery {
                    deck_id: id.0,
                    deck_name: names.get(&id).cloned().unwrap_or_default(),
                    total_cards: acc.total_cards,
                    mastered_count: acc.mastered_count,
                    avg_recall: acc.avg_recall(),
                }
            })
            .collect();

        Ok(DeckMasteryResponse { decks })
    }
}

#[cfg(test)]
mod test {
    use super::*;
    use crate::tests::DeckAdder;
    use crate::tests::NoteAdder;

    /// Fetches the single mastery entry for the given deck id.
    fn mastery_for(col: &mut Collection, deck: DeckId) -> DeckMastery {
        col.deck_mastery()
            .unwrap()
            .decks
            .into_iter()
            .find(|d| d.deck_id == deck.0)
            .unwrap_or_else(|| panic!("no mastery entry for deck {}", deck.0))
    }

    /// Adds a card to the default deck and applies the given mutation, so tests
    /// can shape ctype/interval/reps/lapses directly.
    fn add_card_with(col: &mut Collection, f: impl FnOnce(&mut Card)) {
        let note = NoteAdder::basic(col).add(col);
        let mut card = col.storage.all_cards_of_note(note.id).unwrap().remove(0);
        f(&mut card);
        col.storage.update_card(&card).unwrap();
    }

    #[test]
    fn empty_deck_reports_zeroes() {
        let mut col = Collection::new();
        let deck = DeckAdder::new("Finance").add(&mut col);
        let m = mastery_for(&mut col, deck.id);
        assert_eq!(m.total_cards, 0);
        assert_eq!(m.mastered_count, 0);
        assert_eq!(m.avg_recall, 0.0);
        assert_eq!(m.deck_name, "Finance");
    }

    #[test]
    fn all_new_cards_are_never_mastered() {
        let mut col = Collection::new();
        // Freshly added cards are New with interval 0 and no reviews.
        NoteAdder::basic(&mut col).add(&mut col);
        NoteAdder::basic(&mut col).add(&mut col);
        let m = mastery_for(&mut col, DeckId(1));
        assert_eq!(m.total_cards, 2);
        assert_eq!(m.mastered_count, 0);
        // No reviewed cards -> recall proxy is 0.
        assert_eq!(m.avg_recall, 0.0);
    }

    #[test]
    fn mixed_deck_counts_mastered_and_averages_recall() {
        let mut col = Collection::new();
        // A new, never-reviewed card.
        add_card_with(&mut col, |_| {});
        // A young review card (below the mastery interval) with perfect recall.
        add_card_with(&mut col, |c| {
            c.ctype = CardType::Review;
            c.interval = 5;
            c.reps = 4;
            c.lapses = 0;
        });
        // A mature review card (>= 21d) that has lapsed twice out of ten reps.
        add_card_with(&mut col, |c| {
            c.ctype = CardType::Review;
            c.interval = 40;
            c.reps = 10;
            c.lapses = 2;
        });

        let m = mastery_for(&mut col, DeckId(1));
        assert_eq!(m.total_cards, 3);
        // Only the interval-40 review card clears the 21-day threshold.
        assert_eq!(m.mastered_count, 1);
        // Reviewed cards: recall 1.0 (4/4) and 0.8 (8/10) -> mean 0.9. The new
        // card has no reps and is excluded from the average.
        assert!(
            (m.avg_recall - 0.9).abs() < 1e-6,
            "avg_recall = {}",
            m.avg_recall
        );
    }

    #[test]
    fn just_under_threshold_is_not_mastered() {
        let mut col = Collection::new();
        add_card_with(&mut col, |c| {
            c.ctype = CardType::Review;
            c.interval = MASTERY_INTERVAL_DAYS - 1;
            c.reps = 3;
            c.lapses = 0;
        });
        add_card_with(&mut col, |c| {
            c.ctype = CardType::Review;
            c.interval = MASTERY_INTERVAL_DAYS;
            c.reps = 3;
            c.lapses = 0;
        });
        let m = mastery_for(&mut col, DeckId(1));
        assert_eq!(m.mastered_count, 1);
    }
}
