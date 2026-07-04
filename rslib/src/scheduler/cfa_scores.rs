// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! CFA fork. The shared, read-only "honest" score engine backing the
//! `ComputeCfaScores` RPC.
//!
//! This is a faithful Rust port of `pylib/anki/cfa.py` so that the desktop app
//! and the AnkiDroid mobile client read *identical* numbers from one engine.
//! Parity is achieved by construction: the same SQL queries (including the
//! `extract_fsrs_retrievability` SQL function) feed the same `f64` arithmetic,
//! so there is no second implementation of FSRS or of the statistics to drift.
//!
//! There is **no AI here** — it is pure spaced-repetition statistics:
//!   * Memory     — exam-weighted FSRS retrievability, reported as a range.
//!   * Performance — first-exposure accuracy as a Wilson 95% interval.
//!   * Readiness   — a coarse, deliberately-wide logistic P(pass).
//!   * Bayesian    — the readiness "hero" band that never abstains.
//!
//! One deliberate improvement over `cfa.py`: graded reviews are counted **at
//! most once per (card, scheduling-day)**. An offline dual-device round-trip
//! (review the same card on the phone and the desktop before syncing) would
//! otherwise land two revlog rows for the same card on the same day and
//! double-count the evidence. The de-dup collapses those to one, so the
//! give-up threshold and the per-topic evidence counts stay honest. On data
//! with at most one review per card per day (the common review-card case) the
//! de-dup is a no-op, so the numbers still match `cfa.py`.
//!
//! Read-only throughout: it never writes a card, queue, or scheduling row, so
//! FSRS scheduling and the undo history remain valid.

use std::collections::HashMap;

use anki_proto::scheduler as pb;
use chrono::Local;
use chrono::TimeZone;
use rusqlite::params;
use serde::Deserialize;

use crate::prelude::*;

// --- constants (mirror cfa.py) ----------------------------------------------

const TOPIC_PREFIX: &str = "los::";
const EXAM_CONFIG_KEY: &str = "cfa_exam_config";

/// Authored CFA Level II topic areas, keyed by their `los::<topic>` tag. Used
/// as the syllabus when no exam weights are configured (mirrors
/// `cfa.CANONICAL_TOPICS`; keep sorted, matching `sorted(weights.keys())`).
const CANONICAL_TOPICS: [&str; 8] = [
    "los::altinv",
    "los::corp",
    "los::econ",
    "los::equity",
    "los::ethics",
    "los::fra",
    "los::portmgmt",
    "los::quant",
];

// Give-up rule.
const MIN_GRADED_REVIEWS: u32 = 200;
const MIN_TOPIC_COVERAGE: f64 = 0.50;
const MIN_FIRST_EXPOSURES: u32 = 30;

// Anki ease scale: 1=Again (incorrect); >=2 counts as a successful recall.
const CORRECT_EASE: i64 = 2;

// Readiness (logistic P(pass)).
const READINESS_LABEL: &str = "not validated against real exam data";
const MPS: f64 = 0.65;
const READINESS_K: f64 = 8.0;
const GUESS_RATE: f64 = 1.0 / 3.0;
const READINESS_MARGIN: f64 = 0.15;

// Bayesian readiness.
const PRIOR_A: f64 = 1.0;
const PRIOR_B: f64 = 1.0;
const BAND_Z: f64 = 1.959963984540054;
const WILSON_Z: f64 = 1.96;

/// Only `topic_weights` is needed by the scores; the exam date is used by the
/// exam queue, not here. Missing/invalid config yields an empty weight map,
/// exactly like `get_exam_config(col) or {}` in Python.
#[derive(Deserialize, Default)]
struct CfaExamConfig {
    #[serde(default)]
    topic_weights: HashMap<String, f64>,
}

// --- small numeric helpers (mirror cfa.py) ----------------------------------

fn clamp01(x: f64) -> f64 {
    x.max(0.0).min(1.0)
}

fn fmean(values: &[f64]) -> f64 {
    values.iter().sum::<f64>() / values.len() as f64
}

/// Population standard deviation (matches `statistics.pstdev`), 0.0 for <2
/// values.
fn pstdev(values: &[f64]) -> f64 {
    if values.len() < 2 {
        return 0.0;
    }
    let mean = fmean(values);
    let var = values.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / values.len() as f64;
    var.sqrt()
}

/// (point, low, high) = mean +/- population stdev, clamped to [0, 1].
fn range_of(values: &[f64]) -> (f64, f64, f64) {
    let point = fmean(values);
    let spread = pstdev(values);
    (point, (point - spread).max(0.0), (point + spread).min(1.0))
}

/// (point, low, high) = weighted mean +/- weighted stdev, clamped to [0, 1].
/// Falls back to an equal-weight mean when every weight is zero.
fn weighted_range(pairs: &[(f64, f64)]) -> (f64, f64, f64) {
    let total_w: f64 = pairs.iter().map(|(_, w)| *w).sum();
    if total_w <= 0.0 {
        let values: Vec<f64> = pairs.iter().map(|(v, _)| *v).collect();
        return range_of(&values);
    }
    let point = pairs.iter().map(|(v, w)| v * w).sum::<f64>() / total_w;
    let spread = if pairs.len() > 1 {
        let var = pairs.iter().map(|(v, w)| w * (v - point).powi(2)).sum::<f64>() / total_w;
        var.sqrt()
    } else {
        0.0
    };
    (point, (point - spread).max(0.0), (point + spread).min(1.0))
}

/// (point, low, high) Wilson score interval for a binomial proportion.
fn wilson(successes: u32, n: u32, z: f64) -> (f64, f64, f64) {
    let n = n as f64;
    let phat = successes as f64 / n;
    let denom = 1.0 + z * z / n;
    let center = (phat + z * z / (2.0 * n)) / denom;
    let margin = z * (phat * (1.0 - phat) / n + z * z / (4.0 * n * n)).sqrt() / denom;
    (phat, (center - margin).max(0.0), (center + margin).min(1.0))
}

fn pass_prob(accuracy: f64) -> f64 {
    1.0 / (1.0 + (-READINESS_K * (accuracy - MPS)).exp())
}

/// Standard-normal CDF via `libm::erf` (matches Python's C `math.erf`).
fn norm_cdf(x: f64) -> f64 {
    0.5 * (1.0 + libm::erf(x / 2.0_f64.sqrt()))
}

fn beta_mean_var(a: f64, b: f64) -> (f64, f64) {
    let n = a + b;
    let mean = a / n;
    let var = (a * b) / (n * n * (n + 1.0));
    (mean, var)
}

/// Per-card recall with an SM-2 fallback when FSRS R is NULL (mirrors
/// `cfa.estimate_recall`).
fn estimate_recall(
    r: Option<f64>,
    ivl_days: f64,
    elapsed_days: f64,
    successes: i64,
    total: i64,
) -> Option<f64> {
    if let Some(r) = r {
        return Some(clamp01(r));
    }
    if total <= 0 {
        return None;
    }
    let ivl = ivl_days.max(1.0);
    let elapsed = elapsed_days.max(0.0);
    let curve = 0.9_f64.powf(elapsed / ivl);
    let empirical = successes as f64 / total as f64;
    Some(clamp01(0.5 * curve + 0.5 * empirical))
}

/// Longest-prefix match of a card's `los::` tags against the configured topics.
fn topic_of<'a>(tags: &str, topic_prefixes: &'a [String]) -> Option<&'a str> {
    let mut best: Option<&str> = None;
    for tag in tags.split_whitespace() {
        if !tag.starts_with(TOPIC_PREFIX) {
            continue;
        }
        for prefix in topic_prefixes {
            let matches = tag == prefix
                || tag
                    .strip_prefix(prefix.as_str())
                    .is_some_and(|rest| rest.starts_with("::"));
            if matches && best.map_or(true, |b| prefix.len() > b.len()) {
                best = Some(prefix.as_str());
            }
        }
    }
    best
}

/// The syllabus topics: sorted configured weight keys, else the canonical list.
fn readiness_topic_prefixes(weights: &HashMap<String, f64>) -> Vec<String> {
    if weights.is_empty() {
        CANONICAL_TOPICS.iter().map(|s| s.to_string()).collect()
    } else {
        let mut keys: Vec<String> = weights.keys().cloned().collect();
        keys.sort();
        keys
    }
}

fn iso_local_seconds(secs: i64) -> String {
    Local
        .timestamp_opt(secs, 0)
        .single()
        .map(|dt| dt.format("%Y-%m-%dT%H:%M:%S").to_string())
        .unwrap_or_default()
}

impl Collection {
    /// Read-only honest CFA scores for a deck (or the whole collection). Backs
    /// the `ComputeCfaScores` RPC. See the module docs for the algorithm; it is
    /// a faithful port of `pylib/anki/cfa.py` with the (card, day) de-dup.
    pub(crate) fn compute_cfa_scores(
        &mut self,
        input: pb::ComputeCfaScoresRequest,
    ) -> Result<pb::ComputeCfaScoresResponse> {
        let timing = self.timing_today()?;
        let today = timing.days_elapsed as i64;
        let next_day_at = timing.next_day_at.0;
        let now = if input.now != 0 { input.now } else { timing.now.0 };

        // Deck scoping (deck + subdecks), mirroring `deck_and_child_ids`.
        let deck_filter = if input.whole_collection {
            "1".to_string()
        } else {
            let did = DeckId(input.deck_id);
            let dids = match self.storage.get_deck(did)? {
                Some(deck) => self.storage.deck_id_with_children(&deck)?,
                None => vec![did],
            };
            let joined = dids
                .iter()
                .map(|d| d.0.to_string())
                .collect::<Vec<_>>()
                .join(",");
            format!("c.did in ({joined})")
        };

        let cfg: CfaExamConfig = self
            .get_config_optional(EXAM_CONFIG_KEY)
            .unwrap_or_default();
        let weights = cfg.topic_weights;
        let topic_prefixes = readiness_topic_prefixes(&weights);

        let memory = self.cfa_memory_score(
            &deck_filter,
            &topic_prefixes,
            &weights,
            today,
            next_day_at,
            now,
        )?;
        let performance = self.cfa_performance_score(&deck_filter, now)?;
        let readiness = cfa_readiness_score(&memory, &performance, now);
        let bayesian = self.cfa_bayesian_readiness(
            &deck_filter,
            &topic_prefixes,
            &weights,
            today,
            next_day_at,
            now,
        )?;

        Ok(pb::ComputeCfaScoresResponse {
            memory: Some(memory),
            performance: Some(performance),
            readiness: Some(readiness),
            bayesian: Some(bayesian),
        })
    }

    /// Graded reviews per card, **de-duplicated to at most one per (card,
    /// scheduling-day)** — the double-count fix. The inner `group by c.id, day`
    /// collapses same-day repeats (intraday learning steps *and* an offline
    /// dual-device round-trip) to one row; the outer count is the number of
    /// distinct study-days on which the card was graded. The day index is the
    /// count of rollover boundaries (`next_day_at - k*86400`) at or before the
    /// review, shifted by a large positive constant so the integer truncation
    /// floors correctly for the (always-past) review timestamps.
    fn graded_reviews_by_card(
        &self,
        deck_filter: &str,
        next_day_at: i64,
    ) -> Result<HashMap<i64, u32>> {
        // ~1e7 days; larger than any real gap so the dividend is positive.
        const DAY_OFFSET: f64 = 86_400.0 * 10_000_000.0;
        let sql = format!(
            "select cid, count(*) from (
               select c.id as cid,
                 cast((cast(r.id as real)/1000.0 - {next_day_at} + {DAY_OFFSET}) / 86400.0
                      as integer) as day
               from revlog r join cards c on r.cid = c.id
               where {deck_filter} and r.ease > 0
               group by c.id, day
             ) group by cid"
        );
        let mut stmt = self.storage.db.prepare(&sql)?;
        let rows = stmt.query_and_then([], |r| -> Result<(i64, u32)> {
            Ok((r.get(0)?, r.get::<_, i64>(1)? as u32))
        })?;
        let mut out = HashMap::new();
        for row in rows {
            let (cid, n) = row?;
            out.insert(cid, n);
        }
        Ok(out)
    }

    fn cfa_memory_score(
        &self,
        deck_filter: &str,
        topic_prefixes: &[String],
        weights: &HashMap<String, f64>,
        today: i64,
        next_day_at: i64,
        now: i64,
    ) -> Result<pb::CfaMemoryScore> {
        let computed_at = iso_local_seconds(now);

        // (card id, tags, retrievability). R is NULL for never-reviewed cards.
        let sql = format!(
            "select c.id, n.tags,
               extract_fsrs_retrievability(
                 c.data, case when c.odue != 0 then c.odue else c.due end,
                 c.ivl, ?, ?, ?)
             from cards c join notes n on c.nid = n.id
             where {deck_filter}"
        );
        let mut stmt = self.storage.db.prepare(&sql)?;
        let card_rows = stmt
            .query_and_then(params![today, next_day_at, now], |r| -> Result<(
                i64,
                String,
                Option<f64>,
            )> {
                Ok((r.get(0)?, r.get(1)?, r.get(2)?))
            })?
            .collect::<Result<Vec<_>>>()?;

        let review_counts = self.graded_reviews_by_card(deck_filter, next_day_at)?;

        let last_ms: Option<i64> = self.storage.db.query_row(
            &format!(
                "select max(r.id) from revlog r join cards c on r.cid = c.id
                 where {deck_filter} and r.ease > 0"
            ),
            [],
            |r| r.get(0),
        )?;
        let last_review_at = last_ms.map(|ms| iso_local_seconds(ms / 1000));

        // Group per-card (tags, R) into per-topic scores.
        let mut per_r: HashMap<&str, Vec<f64>> =
            topic_prefixes.iter().map(|t| (t.as_str(), vec![])).collect();
        let mut per_reviews: HashMap<&str, u32> =
            topic_prefixes.iter().map(|t| (t.as_str(), 0)).collect();
        for (cid, tags, r) in &card_rows {
            let Some(topic) = topic_of(tags, topic_prefixes) else {
                continue;
            };
            *per_reviews.get_mut(topic).unwrap() += review_counts.get(cid).copied().unwrap_or(0);
            if let Some(r) = r {
                per_r.get_mut(topic).unwrap().push(*r);
            }
        }

        let mut topics = Vec::with_capacity(topic_prefixes.len());
        for topic in topic_prefixes {
            let r_values = &per_r[topic.as_str()];
            let reviews = per_reviews[topic.as_str()];
            let (avg_r, r_low, r_high) = if r_values.is_empty() {
                (None, None, None)
            } else {
                let (p, l, h) = range_of(r_values);
                (Some(p), Some(l), Some(h))
            };
            topics.push(pb::CfaTopicScore {
                topic: topic.clone(),
                weight: weights.get(topic).copied().unwrap_or(0.0),
                reviewed_cards: r_values.len() as u32,
                graded_reviews: reviews,
                avg_r,
                r_low,
                r_high,
                covered: reviews > 0 && !r_values.is_empty(),
            });
        }

        let total_reviews: u32 = review_counts.values().sum();
        let topics_total = topic_prefixes.len() as u32;
        let topics_covered = topics.iter().filter(|t| t.covered).count() as u32;
        let coverage_pct = if topics_total > 0 {
            topics_covered as f64 / topics_total as f64
        } else {
            0.0
        };

        let reason = memory_giveup_reason(&topics, total_reviews, coverage_pct, weights);

        let covered: Vec<(f64, f64)> = topics
            .iter()
            .filter(|t| t.covered && t.avg_r.is_some())
            .map(|t| (t.avg_r.unwrap(), t.weight))
            .collect();
        let (point, range_low, range_high) = if reason.is_none() && !covered.is_empty() {
            let (p, l, h) = weighted_range(&covered);
            (Some(p), Some(l), Some(h))
        } else {
            (None, None, None)
        };

        Ok(pb::CfaMemoryScore {
            abstain: reason.is_some(),
            reason: reason.unwrap_or_default(),
            point,
            range_low,
            range_high,
            coverage_pct,
            topics_total,
            topics_covered,
            graded_reviews: total_reviews,
            last_review_at,
            computed_at,
            topics,
        })
    }

    fn cfa_performance_score(
        &self,
        deck_filter: &str,
        now: i64,
    ) -> Result<pb::CfaPerformanceScore> {
        let computed_at = iso_local_seconds(now);

        // First graded review (earliest revlog id) per card, with its ease.
        let sql = format!(
            "select r.ease
             from revlog r
             join cards c on r.cid = c.id
             join (select cid, min(id) as mid from revlog where ease > 0 group by cid) first
               on first.cid = r.cid and first.mid = r.id
             where {deck_filter}"
        );
        let mut stmt = self.storage.db.prepare(&sql)?;
        let eases = stmt
            .query_and_then([], |r| -> Result<i64> { Ok(r.get(0)?) })?
            .collect::<Result<Vec<_>>>()?;

        let first_exposures = eases.len() as u32;
        let correct = eases.iter().filter(|e| **e >= CORRECT_EASE).count() as u32;

        if first_exposures < MIN_FIRST_EXPOSURES {
            return Ok(pb::CfaPerformanceScore {
                abstain: true,
                reason: format!(
                    "not enough data: {first_exposures} first-seen questions (need {MIN_FIRST_EXPOSURES})"
                ),
                point: None,
                range_low: None,
                range_high: None,
                first_exposures,
                correct,
                computed_at,
            });
        }

        let (point, low, high) = wilson(correct, first_exposures, WILSON_Z);
        Ok(pb::CfaPerformanceScore {
            abstain: false,
            reason: String::new(),
            point: Some(point),
            range_low: Some(low),
            range_high: Some(high),
            first_exposures,
            correct,
            computed_at,
        })
    }

    fn cfa_bayesian_readiness(
        &self,
        deck_filter: &str,
        topic_prefixes: &[String],
        weights: &HashMap<String, f64>,
        today: i64,
        next_day_at: i64,
        now: i64,
    ) -> Result<pb::CfaBayesianReadiness> {
        let computed_at = iso_local_seconds(now);

        // Per card: retrievability (NULL when no FSRS state), interval, tags.
        let sql = format!(
            "select c.id, n.tags,
               extract_fsrs_retrievability(
                 c.data, case when c.odue != 0 then c.odue else c.due end,
                 c.ivl, ?, ?, ?), c.ivl
             from cards c join notes n on c.nid = n.id
             where {deck_filter}"
        );
        let mut stmt = self.storage.db.prepare(&sql)?;
        let card_rows = stmt
            .query_and_then(params![today, next_day_at, now], |r| -> Result<(
                i64,
                String,
                Option<f64>,
                i64,
            )> {
                Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?))
            })?
            .collect::<Result<Vec<_>>>()?;

        // Per card: total/success counts, last-review ms, first graded ease.
        // RAW counts (matching cfa.py) — the empirical ratio is de-dup neutral.
        let stats_sql = format!(
            "select c.id, count(*),
               sum(case when r.ease >= {CORRECT_EASE} then 1 else 0 end),
               max(r.id),
               (select r2.ease from revlog r2
                  where r2.cid = c.id and r2.ease > 0 order by r2.id limit 1)
             from revlog r join cards c on r.cid = c.id
             where {deck_filter} and r.ease > 0
             group by c.id"
        );
        let mut stats_stmt = self.storage.db.prepare(&stats_sql)?;
        let mut stats: HashMap<i64, (i64, i64, i64, Option<i64>)> = HashMap::new();
        let stat_rows = stats_stmt.query_and_then([], |r| -> Result<(
            i64,
            i64,
            i64,
            i64,
            Option<i64>,
        )> {
            Ok((
                r.get(0)?,
                r.get(1)?,
                r.get::<_, Option<i64>>(2)?.unwrap_or(0),
                r.get::<_, Option<i64>>(3)?.unwrap_or(0),
                r.get(4)?,
            ))
        })?;
        for row in stat_rows {
            let (cid, total, succ, last_ms, first_ease) = row?;
            stats.insert(cid, (total, succ, last_ms, first_ease));
        }

        // Group per-topic correctness counts and recall estimates.
        let mut per_succ: HashMap<&str, i64> =
            topic_prefixes.iter().map(|t| (t.as_str(), 0)).collect();
        let mut per_fail: HashMap<&str, i64> =
            topic_prefixes.iter().map(|t| (t.as_str(), 0)).collect();
        let mut per_recall: HashMap<&str, Vec<f64>> =
            topic_prefixes.iter().map(|t| (t.as_str(), vec![])).collect();
        for (cid, tags, r, ivl) in &card_rows {
            let Some(topic) = topic_of(tags, topic_prefixes) else {
                continue;
            };
            let (total, succ, last_ms, first_ease) =
                stats.get(cid).copied().unwrap_or((0, 0, 0, None));
            if let Some(fe) = first_ease {
                if fe >= CORRECT_EASE {
                    *per_succ.get_mut(topic).unwrap() += 1;
                } else {
                    *per_fail.get_mut(topic).unwrap() += 1;
                }
            }
            let elapsed = if last_ms != 0 {
                (now as f64 - last_ms as f64 / 1000.0) / 86_400.0
            } else {
                0.0
            };
            if let Some(rec) = estimate_recall(*r, *ivl as f64, elapsed, succ, total) {
                per_recall.get_mut(topic).unwrap().push(rec);
            }
        }

        let z = BAND_Z;
        let mut topics = Vec::with_capacity(topic_prefixes.len());
        for topic in topic_prefixes {
            let s = per_succ[topic.as_str()];
            let f = per_fail[topic.as_str()];
            let (a, b) = (PRIOR_A + s as f64, PRIOR_B + f as f64);
            let (mean, var) = beta_mean_var(a, b);
            let std = var.sqrt();
            let recs = &per_recall[topic.as_str()];
            topics.push(pb::CfaTopicPosterior {
                topic: topic.clone(),
                weight: weights.get(topic).copied().unwrap_or(0.0),
                successes: s as u32,
                failures: f as u32,
                mean,
                ci_low: (mean - z * std).max(0.0),
                ci_high: (mean + z * std).min(1.0),
                recall: if recs.is_empty() {
                    None
                } else {
                    Some(fmean(recs))
                },
                covered: (s + f) > 0,
            });
        }

        // Exam-weighted aggregate; equal weighting when no weights configured.
        let mut raw_w: Vec<f64> = topics.iter().map(|t| t.weight.max(0.0)).collect();
        if raw_w.iter().sum::<f64>() <= 0.0 {
            raw_w = vec![1.0; topics.len()];
        }
        let total_w: f64 = {
            let s = raw_w.iter().sum::<f64>();
            if s == 0.0 {
                1.0
            } else {
                s
            }
        };
        let norm_w: Vec<f64> = raw_w.iter().map(|w| w / total_w).collect();

        let mut mu = 0.0;
        let mut var_agg = 0.0;
        let mut rec_num = 0.0;
        let mut rec_den = 0.0;
        for (t, w) in topics.iter().zip(norm_w.iter()) {
            let (a, b) = (PRIOR_A + t.successes as f64, PRIOR_B + t.failures as f64);
            let (m, v) = beta_mean_var(a, b);
            mu += w * m;
            var_agg += w * w * v;
            if let Some(rec) = t.recall {
                rec_num += w * rec;
                rec_den += w;
            }
        }
        let std_agg = var_agg.sqrt();

        let accuracy = clamp01(mu);
        let ci_low = (mu - z * std_agg).max(0.0);
        let ci_high = (mu + z * std_agg).min(1.0);

        let p_pass = if std_agg > 0.0 {
            clamp01(1.0 - norm_cdf((MPS - mu) / std_agg))
        } else if mu >= MPS {
            1.0
        } else {
            0.0
        };
        let (call, call_prob) = if p_pass >= 0.5 {
            ("likely pass".to_string(), p_pass)
        } else {
            ("likely fail".to_string(), 1.0 - p_pass)
        };

        let first_exposures = topics.iter().map(|t| t.successes + t.failures).sum::<u32>();
        let topics_covered = topics.iter().filter(|t| t.covered).count() as u32;
        Ok(pb::CfaBayesianReadiness {
            accuracy,
            ci_low,
            ci_high,
            call,
            call_prob,
            p_pass,
            mps: MPS,
            recall: if rec_den > 0.0 {
                Some(rec_num / rec_den)
            } else {
                None
            },
            label: READINESS_LABEL.to_string(),
            first_exposures,
            topics_total: topics.len() as u32,
            topics_covered,
            computed_at,
            topics,
        })
    }
}

/// Abstain reason if the memory give-up rule fires, else None (mirrors
/// `cfa._giveup_reason`).
fn memory_giveup_reason(
    topics: &[pb::CfaTopicScore],
    total_reviews: u32,
    coverage_pct: f64,
    weights: &HashMap<String, f64>,
) -> Option<String> {
    if topics.is_empty() {
        return Some("not enough data: no topics found (tag notes with los::…)".to_string());
    }
    if total_reviews < MIN_GRADED_REVIEWS || coverage_pct < MIN_TOPIC_COVERAGE {
        return Some(format!(
            "not enough data: {total_reviews} graded reviews (need {MIN_GRADED_REVIEWS}), {:.0}% topic coverage (need {:.0}%)",
            coverage_pct * 100.0,
            MIN_TOPIC_COVERAGE * 100.0
        ));
    }
    // A skipped high-weight topic invalidates the whole score.
    if !weights.is_empty() {
        let positive: Vec<f64> = weights.values().copied().filter(|w| *w > 0.0).collect();
        let threshold = if positive.is_empty() {
            0.0
        } else {
            fmean(&positive)
        };
        let mut skipped: Vec<String> = topics
            .iter()
            .filter(|t| t.weight >= threshold && t.weight > 0.0 && !t.covered)
            .map(|t| t.topic.clone())
            .collect();
        skipped.sort();
        if !skipped.is_empty() {
            return Some(format!(
                "high-weight topic(s) skipped, no score: {}",
                skipped.join(", ")
            ));
        }
    }
    None
}

/// Combine memory + performance + coverage into a wide, uncalibrated P(pass)
/// (mirrors `cfa.readiness_score`).
fn cfa_readiness_score(
    mem: &pb::CfaMemoryScore,
    perf: &pb::CfaPerformanceScore,
    now: i64,
) -> pb::CfaReadinessScore {
    let computed_at = iso_local_seconds(now);

    if mem.abstain || perf.abstain {
        let mut why = Vec::new();
        if mem.abstain {
            why.push(format!("memory ({})", mem.reason));
        }
        if perf.abstain {
            why.push(format!("performance ({})", perf.reason));
        }
        return pb::CfaReadinessScore {
            abstain: true,
            reason: format!("not enough data to estimate readiness: {}", why.join("; ")),
            point: None,
            range_low: None,
            range_high: None,
            label: READINESS_LABEL.to_string(),
            memory_point: mem.point,
            performance_point: perf.point,
            coverage_pct: mem.coverage_pct,
            computed_at,
        };
    }

    let cov = mem.coverage_pct;
    let acc = |m: f64, p: f64| cov * (0.5 * m + 0.5 * p) + (1.0 - cov) * GUESS_RATE;

    let (mp, pl, ph) = (mem.point.unwrap(), mem.range_low.unwrap(), mem.range_high.unwrap());
    let (pp, ppl, pph) = (
        perf.point.unwrap(),
        perf.range_low.unwrap(),
        perf.range_high.unwrap(),
    );
    let point = pass_prob(acc(mp, pp));
    let low = (pass_prob(acc(pl, ppl)) - READINESS_MARGIN).max(0.0);
    let high = (pass_prob(acc(ph, pph)) + READINESS_MARGIN).min(1.0);

    pb::CfaReadinessScore {
        abstain: false,
        reason: String::new(),
        point: Some(point),
        range_low: Some(low),
        range_high: Some(high),
        label: READINESS_LABEL.to_string(),
        memory_point: mem.point,
        performance_point: perf.point,
        coverage_pct: cov,
        computed_at,
    }
}

#[cfg(test)]
mod tests {
    use fsrs::FSRS5_DEFAULT_DECAY;

    use super::*;
    use crate::card::CardQueue;
    use crate::card::CardType;
    use crate::card::FsrsMemoryState;
    use crate::revlog::RevlogEntry;
    use crate::revlog::RevlogId;
    use crate::revlog::RevlogReviewKind;
    use crate::timestamp::TimestampMillis;

    /// Add a card tagged `tags` as a due review card with FSRS memory state
    /// (so retrievability is non-null), reviewed `days_since_review` days ago.
    fn add_reviewed_card(col: &mut Collection, tags: &[&str], days_since_review: i64) -> CardId {
        let nt = col.basic_notetype();
        let mut note = nt.new_note();
        note.set_field(0, "q").unwrap();
        note.tags = tags.iter().map(ToString::to_string).collect();
        col.add_note(&mut note, DeckId(1)).unwrap();
        let cid = col.storage.card_ids_of_notes(&[note.id]).unwrap()[0];
        let mut card = col.storage.get_card(cid).unwrap().unwrap();
        card.queue = CardQueue::Review;
        card.ctype = CardType::Review;
        card.due = 0;
        card.interval = 30;
        card.decay = Some(FSRS5_DEFAULT_DECAY);
        card.last_review_time =
            Some(TimestampSecs::now().adding_secs(-86_400 * days_since_review));
        card.memory_state = Some(FsrsMemoryState {
            stability: 100.0,
            difficulty: 5.0,
        });
        col.storage.update_card(&card).unwrap();
        cid
    }

    /// Insert one graded revlog row for `cid` at the given millisecond id.
    fn add_review(col: &mut Collection, cid: CardId, id_ms: i64, ease: u8) {
        let entry = RevlogEntry {
            id: RevlogId(id_ms),
            cid,
            usn: Usn(0),
            button_chosen: ease,
            interval: 30,
            last_interval: 10,
            ease_factor: 2500,
            taken_millis: 1000,
            review_kind: RevlogReviewKind::Review,
        };
        col.storage.add_revlog_entry(&entry, false).unwrap();
    }

    fn scores(col: &mut Collection) -> pb::ComputeCfaScoresResponse {
        col.compute_cfa_scores(pb::ComputeCfaScoresRequest {
            deck_id: 0,
            whole_collection: true,
            now: 0,
        })
        .unwrap()
    }

    #[test]
    fn abstains_on_empty_collection_but_bayesian_still_answers() {
        let mut col = Collection::new();
        let out = scores(&mut col);
        let mem = out.memory.unwrap();
        assert!(mem.abstain, "no reviews -> memory abstains");
        assert!(mem.reason.contains("graded reviews"));
        assert!(out.performance.unwrap().abstain, "no first exposures");
        assert!(out.readiness.unwrap().abstain, "readiness abstains too");
        // The Bayesian hero never abstains: with no evidence it sits at the
        // uniform prior (accuracy 0.5) and a wide band.
        let bay = out.bayesian.unwrap();
        assert!((bay.accuracy - 0.5).abs() < 1e-9, "prior mean is 0.5");
        assert!(bay.ci_high - bay.ci_low > 0.4, "band is wide with no data");
        assert_eq!(bay.first_exposures, 0);
    }

    #[test]
    fn happy_path_produces_all_scores() {
        let mut col = Collection::new();
        let now_ms = TimestampMillis::now().0;
        // 30 cards in each of the 8 canonical topics, one graded review each,
        // spread over prior days so they don't collide on one (card, day).
        for (ti, topic) in CANONICAL_TOPICS.iter().enumerate() {
            for i in 0..30 {
                let tag = format!("{topic}::r{i}");
                let cid = add_reviewed_card(&mut col, &[&tag], 1);
                // distinct ids, all in the past; ~80% correct.
                let ease = if i % 5 == 0 { 1 } else { 3 };
                add_review(&mut col, cid, now_ms - ((ti * 100 + i) as i64) * 86_400_000, ease);
            }
        }
        let out = scores(&mut col);
        let mem = out.memory.unwrap();
        assert!(!mem.abstain, "240 reviews / 100% coverage -> no abstain: {}", mem.reason);
        assert_eq!(mem.graded_reviews, 240);
        assert_eq!(mem.topics_total, 8);
        assert_eq!(mem.topics_covered, 8);
        let p = mem.point.expect("memory point");
        assert!(p > 0.0 && p < 1.0, "memory point in (0,1): {p}");
        assert!(mem.range_low.unwrap() <= p && p <= mem.range_high.unwrap());

        let perf = out.performance.unwrap();
        assert!(!perf.abstain, "240 first exposures");
        assert_eq!(perf.first_exposures, 240);
        assert!(perf.point.unwrap() > 0.5, "~80% correct");

        let rd = out.readiness.unwrap();
        assert!(!rd.abstain);
        assert_eq!(rd.label, READINESS_LABEL);
        assert!(rd.point.unwrap() > 0.0 && rd.point.unwrap() < 1.0);

        let bay = out.bayesian.unwrap();
        assert_eq!(bay.first_exposures, 240);
        assert!(bay.accuracy > 0.5, "mostly-correct -> accuracy above prior");
        assert!(bay.call == "likely pass" || bay.call == "likely fail");
    }

    #[test]
    fn double_count_fix_dedups_same_day_reviews() {
        let mut col = Collection::new();
        let now_ms = TimestampMillis::now().0;
        let cid = add_reviewed_card(&mut col, &["los::ethics::r1"], 1);

        // Two graded reviews on the SAME day (a dual-device round-trip / an
        // intraday repeat). They must count as ONE.
        add_review(&mut col, cid, now_ms, 3);
        add_review(&mut col, cid, now_ms - 1000, 3);

        let out = scores(&mut col);
        let mem = out.memory.unwrap();
        let ethics = mem
            .topics
            .iter()
            .find(|t| t.topic == "los::ethics")
            .unwrap();
        assert_eq!(
            ethics.graded_reviews, 1,
            "two same-day reviews de-duplicate to one"
        );
        assert_eq!(mem.graded_reviews, 1, "total also de-duplicated");

        // A review on a DIFFERENT day is separate evidence -> counts as two.
        add_review(&mut col, cid, now_ms - 2 * 86_400_000, 3);
        let out2 = scores(&mut col);
        let ethics2 = out2
            .memory
            .unwrap()
            .topics
            .into_iter()
            .find(|t| t.topic == "los::ethics")
            .unwrap();
        assert_eq!(
            ethics2.graded_reviews, 2,
            "distinct days are distinct evidence"
        );
    }
}
