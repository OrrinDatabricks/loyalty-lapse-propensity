# Model card: loyalty_lapse_model

**Registered as** `loyalty_lapse_demo_catalog.loyalty.loyalty_lapse_model`, alias `champion` (version 4 at the time of writing).
**Source** `src/ml/features.py`, `src/ml/train_lapse_model.py`, `src/ml/score_members.py`. **Evidence** `evidence/03a_train_lapse_model.md`, `evidence/03b_score_members.md`.

## Intended use

Rank regular loyalty shoppers by the probability that they make **no purchase in the next 90 days**, so the retention
team can contact the right members 30 to 60 days before they would otherwise be flagged as lapsed. Output feeds the
Lakebase worklist and the Retention Console. It is a prioritization tool for outreach; it is not used for pricing,
credit, eligibility or any decision that disadvantages a member.

## Population

- **Scored:** members with 3 or more purchases in the trailing 180 days as of the latest transaction date (101,089 of 400,000).
- **Excluded:** lighter buyers, because a 90-day gap is normal cadence for them and would flood the label with noise, and members already lapsed, who belong to the win-back program rather than early intervention.
- Data is synthetic (see README). Scores are computed as of 2026-10-30.

## Label and features

- **Label:** `lapsed = 1` if the member made no purchase in the 90 days after the snapshot date.
- **Features (25 numeric, 4 categorical)**, all computed strictly from data on or before the snapshot date: tenure, recency, purchase frequency and spend over 90/180/365 days, denim share, basket and discount behavior, online share, engagement counts over 30/90/180 days, days since last engagement, engagement velocity (last 30 days vs prior 150-day average), returns and fit/size returns, campaign touches and responses, last birthday reward value, birthday in the last 90 days; tier, home store format, home region, preferred channel.
- **No PII** is used. Names and email never enter the feature set.

## Training and evaluation protocol

- **Training snapshots:** features as of 2026-04-30 and 2026-06-30, labels from the following 90 days (188,003 rows).
- **Hold-out:** features as of 2026-07-31, labels Aug 1 to Oct 29 2026 (94,788 rows). The hold-out is later in time than all training data, so the metrics reflect forecasting, not interpolation.
- **Algorithm:** scikit-learn `HistGradientBoostingClassifier` (400 iterations max, early stopping, learning rate 0.06, 31 leaf nodes, min 200 samples per leaf, L2 1.0) behind a one-hot encoder for the categoricals. Logged with MLflow, `pyfunc_predict_fn="predict_proba"`.

## Results on the hold-out

| Metric | Value |
|---|---|
| Base lapse rate | 31.1% |
| AUC | 0.716 |
| Average precision | 0.519 |
| Precision in top decile | 59.4% |
| Recall in top decile | 19.1% |
| Lift in top decile | 1.91x |
| Lapsed trailing-12M spend captured by top decile | $2.40M (15.6% of all lapsed spend) |
| Expected calibration error | 0.0225 |

Calibration by score bin (hold-out):

| Score bin | Members | Mean score | Actual lapse rate |
|---|---|---|---|
| 0.0 to 0.1 | 11,413 | 0.058 | 0.065 |
| 0.1 to 0.2 | 17,223 | 0.154 | 0.169 |
| 0.2 to 0.3 | 22,946 | 0.247 | 0.258 |
| 0.3 to 0.4 | 17,328 | 0.345 | 0.373 |
| 0.4 to 0.5 | 17,218 | 0.450 | 0.480 |
| 0.5 to 0.6 | 8,074 | 0.528 | 0.578 |
| 0.6 to 0.7 | 392 | 0.636 | 0.885 |
| 0.7 to 0.8 | 142 | 0.748 | 0.965 |
| 0.8 to 1.0 | 52 | 0.840 | 1.000 |

Reading: scores are well calibrated up to 0.6 and conservative above it (members scored 0.6+ lapsed at 89% or more). The
High band (p >= 0.60) is therefore a safe place to spend retention budget; the Medium band (0.35 to 0.60) is where a
holdout test would show whether outreach moves the needle.

Top drivers by permutation importance: days since last engagement, 12-month transaction count, tier, home store format,
lifetime transactions, denim share.

## Risk drivers and recommended actions

The console shows a plain-language driver next to each score. Drivers are rule-based readings of the same features the
model uses (engagement drop, fit returns, devalued birthday reward, purchase recency, unresponsive to campaigns, discount
dependence), each mapped to one recommended action. They explain the score in business terms; they are not SHAP values.

## Limitations

- Trained on synthetic data with planted mechanisms. Real programs will have weaker and noisier signals; expect to re-tune thresholds.
- AUC of 0.72 is a ranking tool, not a crystal ball. About 40% of the top decile will not lapse; the recommended actions are low-regret (a message, an exchange offer, a restored reward) for that reason.
- The label horizon is fixed at 90 days regardless of a member's personal cadence.
- No fairness audit was performed on protected attributes; the features deliberately exclude demographics beyond region and store format.
- The model is retrained weekly on a fixed 2-snapshot window; drift monitoring is not yet in place.

## Refresh

`[loyalty] 03 train and score lapse model` runs every Monday 06:00 Central: retrain, register a new version and promote it to `champion`, rescore, then full-refresh the Lakebase synced worklist.
