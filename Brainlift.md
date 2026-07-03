# Brainlift

Purpose
Build an app on top of Anki that overhauls test prep and enables speed-running a test, targeting a lucrative test prep market.
In Scope
Find a target test using willingness to pay, candidate volume, prep-market fragmentation, and fit with spaced repetition.
Analyze SM-2, Anki, and FSRS-style scheduling to understand what they optimize for.
Out of Scope
Full app development architecture.
UI/UX design.
Mobile/desktop implementation details.

DOK 4
Spiky POV 1
Ethics questions trouble CFA Level II candidates, and the solution usually cited is more recognition-based questions. However, the better way to internalize ethics is to treat CFA Level II vignette questions as recall questions. The learner should internalize a schema by being forced to answer with precision and state where the line sits.
Feature
Single scenarios teach labels. Near-miss pairs teach the boundary, and that boundary is the actual tested skill.

Spiky POV 2
The Anki algorithm is unoptimized for test prep for two reasons.
FSRS optimizes for least cost for indefinite retention, while CFA requires optimal retention on a single date. These are two different optimization problems. The assumption of unlimited retention has been assumed at every stage, but retention must be optimized for the specific date of the test.
Feature
Date-aware scheduling: default SRS optimizes memory forever, but the learner enters the exam date and the engine back-plans every interval so recall peaks on test day.
The algorithm should treat the exam as the endpoint. Cards that are weak, high-yield, or fast-decaying should be pulled forward. Cards that are already stable should be spaced out unless they need a final pre-exam refresh. The goal is not minimum review cost forever. The goal is maximum readiness on the test date.

Spiky POV 3
FSRS was largely built from language-learning behavior data, while CFA content has different item types:
formulas;
ethics rules;
conceptual distinctions;
multi-step calculations;
case-style application.
Feature
Content-type-aware weighting: one language-trained curve decays every card alike, but the engine tags each card by item type and tunes its spacing to how that type actually fades.
Formula cards, ethics rules, conceptual distinctions, multi-step calculations, and case-style applications should not be scheduled the same way. High-yield, fast-decaying cards should resurface before they slip.

Algorithm Background
DOK 3
Through the use of data from thousands of students, generalized algorithms are far better than the original SM-2.
The original Anki algorithm was based on predicting review time right before catastrophic forgetting by aligning with the Ebbinghaus forgetting curve. It was built on assumptions that do not align for most users and was unoptimized even for the creator himself because the tweaking was based mostly on his own feeling.

DOK 2
Using time-series data, Jarrett improved upon previous spaced-repetition algorithms by solving scheduling through stochastic dynamic programming as an optimization problem.
Source: From the creator of the modern-day Anki algorithm, FSRS: Jarrett Yi
A Stochastic Shortest Path Algorithm for Optimizing Spaced Repetition Scheduling
https://dl.acm.org/doi/epdf/10.1145/3534678.3539081

DOK 1
Spaced repetition was used for long-term memory, but prior techniques did not adapt to the student dynamically. Instead, they used deterministic controls based on user actions to dictate scheduling.
With over 200 million students’ memory-behavior logs of time-ordered data, all from language-practice data, Jarrett was able to build a more adaptive model.

DOK 1
He used this data by grouping together words of similar difficulty based on their recall rates on the next recall after initial learning. He then put together an equation with variables to encode this trend.
The key variables in the equation were:
half-life;
recall probability;
result of recall;
difficulty, based on next recall after initial learning.
He wrote a script to evaluate the constant factors through stochastic dynamic programming because the optimization problem relied on the expected value of future probabilistic steps.

DOK 2
The original algorithm improved upon SM-0, which worked by scheduling future reviews by applying a constant multiple to the previous inter-repetition interval.
SM-2 refactored this so future scheduling was based on:
the previous inter-repetition interval;
how many times the item had already been reviewed;
the quality of the user’s response in the current session;
the quality of the user’s response in previous sessions.
Items rated below 3 out of 5 on the response scale were added back into the current session queue.

DOK 1
He derived the values for the EF-factor through his own use of the scheduling tool while memorizing 10,000 English vocabulary items.

DOK 1
The key ideas SM-2 was based on were to apply the optimization procedure to the smallest unit, which were problems on individual pages, and to differentiate between items based on their difficulty.
Source: From the creator of the original Anki algorithm, SM-2: Piotr Wozniak
https://super-memory.com/english/ol/sm2.htm

Anki Usage
DOK 2
Source expert: Alec Palmerton, MD, How To Use Anki Like A Pro: Full Step-by-Step Walkthrough
Keep settings mostly default. Cap new cards at 50 per day total across decks and set max reviews very high, such as 9,999, so nothing gets hidden. Use Basic + reversed cards for bidirectional recall, and understand New / Learn / Due so you do not drown in reviews.
Use Browse, Stats, and Sync deliberately. Browse is your searchable knowledge base. Stats show why long intervals keep around 24,000 cards manageable in under an hour per day. When syncing, always upload from the device with the latest reviews and never blindly download from AnkiWeb, or progress can be wiped.
Learning Science
Case Comparison
Source: Alfieri, Nokes-Malach & Schunn, 2013, Learning Through Case Comparisons: A Meta-Analytic Review, Educational Psychologist
doi:10.1080/00461520.2013.775712
DOK 1
The meta-analysis looked at 57 experiments and 336 tests. Random-effects analysis found that case comparison beat other forms of case study and instruction with an overall test-level effect of d = 0.50, 95% CI [.44, .56]. This number is accurate, but it should be stated as a pooled comparison against sequential study, single-case study, nonanalogous study, traditional instruction, and control groups, not only sequential or single-case study. Against sequential case study specifically, the effect was smaller but still meaningful: d = 0.37, 95% CI [.31, .44].\
The moderators that matter most are asking learners to find similarities across cases and presenting the governing principle after the comparison instead of before it. The strongest setup was “find similarities” plus “principle after comparison,” which produced a large average effect, d = 1.18, 95% CI [.93, 1.44].

Source: Gentner, Loewenstein & Thompson, 2003, Learning and Transfer: A General Role for Analogical Encoding, Journal of Educational Psychology
doi:10.1037/0022-0663.95.2.393
Supporting Source: Loewenstein, Thompson & Gentner, 1999, Analogical Encoding Facilitates Knowledge Transfer in Negotiation, Psychonomic Bulletin & Review
DOK 1
Gentner, Loewenstein & Thompson gave learners the same two negotiation cases, but changed whether the learners compared the cases or studied them separately. In Experiment 2, 128 undergraduate students were randomly assigned to the comparison condition or the separate-cases condition. The comparison group transferred the principle 48% of the time versus 19% for the separate-case group.\
The old “MBAs, accountants, and consultants” line should be reworded. The 48% vs. 19% number came from undergraduates, not professionals. The professional support comes from the authors’ earlier negotiation work, where graduate management students who compared two cases were nearly three times more likely to use the trained strategy in a later negotiation than students who received the same cases separately.

Source: Corral, Kurtz & Jones, 2018, Learning Relational Concepts From Within- Versus Between-Category Comparisons, Journal of Experimental Psychology: General
doi:10.1037/xge0000517
DOK 1
Corral, Kurtz & Jones should be cited as 2018, not 2020. They tested two-item category-learning trials where items were either from the same category or from different categories. The contrast condition, meaning items from different categories, outperformed the match condition for feature-based categories and across four relational-category experiments. This is directly relevant to CFA Ethics because the product is teaching candidates to discriminate between nearby Standards, not just recognize one Standard in isolation.

Source: Rittle-Johnson & Star, 2007, Does Comparing Solution Methods Facilitate Conceptual and Procedural Knowledge? An Experimental Study on Learning to Solve Equations, Journal of Educational Psychology
doi:10.1037/0022-0663.99.3.561
Source: Schwartz, Chase, Oppezzo & Chin, 2011, Practicing Versus Inventing With Contrasting Cases: The Effects of Telling First on Learning and Transfer, Journal of Educational Psychology
doi:10.1037/a0025140
DOK 1
Rittle-Johnson & Star randomly assigned 70 seventh-grade students to compare alternative algebra solution methods or study the same methods one at a time. The comparison group gained more procedural knowledge and flexibility, but conceptual knowledge gains were comparable across groups. So this source should be used to support “comparison improves flexible application,” not “comparison improves every learning outcome.”\
Schwartz et al. showed a related effect in physics: students who first invented with contrasting cases learned deeper ratio structure and transferred better than students who were told formulas first and then practiced. In Experiment 2, 120 eighth-graders were used; ICC students had better deep-structure recall and transfer, while the groups did not differ on surface-feature recall or standard word-problem performance. The old d = 0.31 should not be used as a general headline for all case comparison; it is better treated as a specific transfer result inside that physics RCT.

DOK 2
This is a different mechanism than interleaving because the strongest compare-vs-separate studies used the same cases and only varied whether learners compared them directly. The win cannot just be a spacing effect. It is structural alignment: actually discovering the diagnostic feature.
That matters for product design. The product should not just ask, “Which Standard is this?” It should ask candidates to compare two confusable CFA Ethics scenarios, identify which one conforms or violates, name the controlling Standard, and explain the diagnostic fact that changes the answer.
It is deterministic to score too: two conform/violate calls plus a which-Standard multiple choice. It needs zero new Rust and reuses the same infrastructure as the first feature.

DOK 3
The product implication is that the app should sequence the principle after the comparison when possible. First, show the candidate two near-miss cases and force the candidate to locate the boundary. Then reveal the governing CFA Standard and explanation.
That matches Alfieri’s moderator finding that principle-after-comparison is stronger than principle-before-comparison, and it keeps the learner from prematurely memorizing a label before seeing the diagnostic structure.
DOK 2
Put together, this is at least five independent pillars from separate research groups and separate domains:
education;
negotiation;
category learning;
math;
physics.
It is also a different mechanism than interleaving because the compare-vs-separate studies used the exact same items and only varied whether they were shown together. The win cannot just be a spacing effect. It is structural alignment: actually discovering the diagnostic feature.
It is deterministic to score too: two conform/violate calls plus a which-Standard multiple choice. It needs zero new Rust and reuses the same infrastructure as the first feature.

DOK 3
The confusable-Standard clusters, like Suitability vs. MNPI vs. Diligence, are exactly where candidates lose points on the real exam. The minimal pair is built to teach that discrimination instead of just teaching the label.

How the Topic of CFA Was Chosen
DOK 3 — Insights
Tests bought by companies, entities, professional bodies, or universities are more lucrative to produce because of the price elasticity of companies. They can and will pay more.
The medical market is already very saturated despite being so big because med students need to learn a massive amount, so many products already exist.
The CFA credential is worldwide, unlike most post-grad tests in the U.S., and is growing greatly in the number of takers in Asia. CFA prep is fragmented and has not yet adapted to improved test prep, where AI can implement parts of learning science that were not implementable at scale before.
As such, CFA test prep is a key entry.

Market Discovery
DOK 2 — Knowledge Tree
Source: College Test Preparation Market Research Report 2034 — MarketIntelo, 2026
https://marketintelo.com/report/college-test-preparation-market
DOK 1
Market share of each test for post-graduate / work-only prep:
GRE leads post-grad prep at 15.2%;
GMAT has 12.8%;
LSAT has 7.1%;
MCAT has 3.8%.
Graduate tests carry higher price points due to content complexity and admission stakes.
DOK 2 Summary
Among grad-school admissions tests, GRE is the largest prep market, followed by GMAT, LSAT, and MCAT.

CFA Exam Prep Market Size
DOK 1
Winning Source: Navagant, 2024, Growth and Innovation in Exam & Test Preparation Industry — Score: 8/10
https://navagant.com/wp-content/uploads/2024/08/Test-Prep-Industry-Report_vF.pdf
DOK 1 Facts
U.S. exam prep is approximately $3.44B.
Certifications are approximately 20%, or $690M.
CFA FY2024 had 208,300 administrations.
Derived global CFA prep is approximately $400M–$600M.
CFA ranks around 5th post-grad.
Per-user spend is approximately $1,000–$3,000 across three levels.
DOK 2 Summary
CFA has mid-tier total dollars but high per-candidate spend.
This is derived from Navigant segment shares plus CFA Institute volume.

CPA Comparison
DOK 1
Source: The NASBA Report: Candidate Performance on the Uniform CPA Examination — 2024 Edition
https://nasba.org/wp-content/uploads/2025/08/The-NASBA-Report-2024-Edition-Now-Available_Final-19Aug25.pdf
DOK 1 Facts
74,165 unique CPA candidates in 2024.
Approximately 148,000 section sittings.
128,000 Core sittings.
19,900 Discipline sittings.
Derived global CPA prep is approximately $700M–$1.0B.
CPA ranks #2 post-grad.
Per-user spend is approximately $1,200–$4,000 across four sections.
DOK 2 Summary
CPA has a smaller candidate pool than CFA, but higher per-user spend and mandatory licensure.
It is #2 on total prep dollars among post-grad certifications.

Tests With the Highest Amount Spent Per User
DOK 1
Winning Source: Bhatnagar et al., 2019 + AAMC PMQ, 2023 — Score: 9/10
The Cost of Board Examination and Preparation: An Overlooked Factor in Medical Student Debt
https://doi.org/10.7759/cureus.4168
Supporting: AAMC PMQ
https://www.aamc.org/media/50146/download
Supporting: Buchmann, 2010
https://doi.org/10.1353/sof.2010.0105
DOK 1 Facts
#1 USMLE / board: Bhatnagar, 2019 found $4,129 mean prep and $7,499 with fees across three steps.
#2 MCAT: $1,000–$7,000.
#3 Bar / CPA / CFA: approximately $1,200–$4,000.
#4 LSAT / SAT: $1,500–$6,900.
DOK 2 Summary
The medical pipeline wins on cumulative spend per person.
Admissions tests have high tutoring ceilings but lower typical spend.

Memory-Heavy Tests and Spaced-Repetition Fit
DOK 1
Source: The Impact of Test Preparation on Performance of Large-Scale Educational Tests — Meta-analysis
https://doi.org/10.3102/00346543251360775
Supporting: Kann et al., 2024
https://doi.org/10.1186/s12909-024-05517-9
Supporting: Mackey et al., 2013
https://doi.org/10.1523/JNEUROSCI.4141-12.2013
DOK 1 Facts
Most memory-heavy:
USMLE Step 1;
MCAT science;
CPA;
CFA Level I.
Least memory-heavy:
LSAT;
GRE verbal;
GMAT reasoning.
Prep effect: g ≈ 0.26, according to Hao, 2025.
DOK 2 Summary
Content-heavy, high-coachability certifications reward flashcard-style prep.
Reasoning-dominant tests resist drill-and-memorize gains.

CFA Institute Prep Provider Program
DOK 1
The CFA Institute Prep Provider Program shows multiple providers and an official multi-vendor ecosystem.
DOK 1
The multi-vendor official ecosystem shows that CFA prep is validated but fragmented.
Kann, Huang et al., 2024 reviewed medical market concentration.
https://link.springer.com/article/10.1007/s40670-024-02116-7
