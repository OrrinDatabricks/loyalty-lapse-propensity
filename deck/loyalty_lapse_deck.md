---
title: "Stop the quiet lapse: predicting and preventing loyalty member churn"
subtitle: "Specialty apparel retail | Loyalty lapse propensity on Databricks"
---

# Stop the quiet lapse

**Predicting which loyalty members go silent next, and acting 60 days earlier**

Specialty apparel retail | Prototype built on Databricks, November 2026

Audience: SVP Customer & Loyalty (executive sponsor), Director of CRM / Retention Marketing (domain owner)

---

# The problem in one line

Our best members do not cancel. They just stop coming back, and we find out 90 days later.

- 400K active loyalty members; Gold and Silver are 30% of members and {{GS_SPEND_SHARE}} of spend
- {{LAPSED_SPEND_12M}} of trailing-12-month spend now sits with members who have not bought in 90+ days
- The second half of 2026 saw a lapse wave concentrated in Gold and Silver members at mall stores
- Today's win-back campaign fires after the 90-day mark, when the member is already gone and the offer has to be deep

---

# What the data said when we finally looked

Two operational decisions in June and July quietly broke the program for our most valuable segment.

| Date | Event | Signal in the data |
|---|---|---|
| Jun 1 | Core Denim fit change | Denim return rate {{DENIM_RET_BEFORE}} to {{DENIM_RET_AFTER}}, 70% coded "fit" |
| Jul 15 | Birthday reward cut from $20 to $10 | Response rate {{BDAY_RESP_BEFORE}} to {{BDAY_RESP_AFTER}} |
| Jun to Sep | Lapse wave | Mall-store Gold/Silver active buyers down {{COHORT_DROP_PCT}} vs flat elsewhere |

The leading indicator was there all along: members go quiet in the app and email 30 to 60 days before their last purchase.

---

# What we built

An integrated data journey, not a dashboard. Every stage feeds the next and the retention team closes the loop.

1. **Lakeflow** ingests loyalty, POS, engagement, campaign and returns extracts into bronze, silver, gold with 13 data quality rules
2. **Unity Catalog** governs it: every gold column described, PII tagged and masked, certified tables, one definition of "lapse rate" and "revenue at risk" in metric views
3. **MLflow model** predicts the chance a regular shopper buys nothing in the next 90 days, with plain-language drivers
4. **Lakebase** serves the ranked worklist to the console in milliseconds and stores every approve / suppress / contacted decision
5. **Genie Agent** answers the CRM team's questions in English against the governed metrics
6. **Retention Console** (Databricks App) is where the team works the list

---

# The model, in business terms

Trained on two historical snapshots, judged on a third it had never seen (features as of Jul 31, outcomes Aug to Oct).

| Metric | Result | What it means |
|---|---|---|
| Hold-out AUC | {{AUC}} | Ranks members well above chance |
| Lift in top decile | {{LIFT}}x | The top 10% of the list lapses {{LIFT}}x more often than average |
| Precision in top decile | {{PREC10}} | {{PREC10}} of the first 10% we contact would have lapsed |
| Members scored | {{N_SCORED}} regular shoppers | 3+ purchases in the last 180 days |
| High-risk members | {{N_HIGH}} | p(lapse) 0.60 or higher |
| Revenue at risk (High) | {{VAR_HIGH}} | 12-month spend weighted by lapse probability |

Top drivers: {{TOP_DRIVERS}}

---

# What the retention team sees

The console turns a score into a decision.

- **Worklist** from Lakebase: member, tier, p(lapse), driver, recommended action, value at risk, sorted by dollars
- **Recommended actions** are specific: fit-guarantee exchange for fit-return members, restored $20 birthday reward for devalued members, app push for the disengaging, channel switch for the unresponsive
- **Write-back**: approve, suppress or mark contacted; every decision lands in Lakebase with who, when and why
- **Ask Genie**: "Which Gold members in mall stores are at high risk and what should we do?" answered from governed metrics, with the SQL shown

---

# Value for the executive sponsor

Framed in the KPIs the loyalty P&L is measured on.

| KPI | Baseline | With early intervention | Basis |
|---|---|---|---|
| Lapsed-member spend (trailing 12M) | {{LAPSED_SPEND_12M}} | Target 15% recovered: {{RECOVERY_15}} | Industry win-back rates of 10 to 20% when contacted before lapse |
| Retention offer cost per saved member | Deep discount after 90 days | Targeted, lighter offer at day 30 to 60 | Earlier contact needs a smaller incentive |
| Campaign response rate | {{BDAY_RESP_AFTER}} after reward cut | Restore to {{BDAY_RESP_BEFORE}} for devalued segment | Observed before/after in our own data |
| Time to detect a segment problem | ~90 days | Days | Weekly scoring plus metric views |

Decision asked of the sponsor: fund a 90-day pilot with the CRM team on the High-risk Gold/Silver mall segment ({{N_HIGH_GS_MALL}} members, {{VAR_HIGH_GS_MALL}} at risk).

---

# Value for the domain owner

For the Director of CRM, this changes the Monday morning.

- A ranked list with a reason and an action, not a 400K-row export
- The list is sized to the team: High band only is {{N_HIGH}} members; filter to Gold/Silver mall and it is {{N_HIGH_GS_MALL}}
- Suppress and contacted flags stop double-touching and feed back into next week's list
- Genie replaces the ad-hoc SQL queue: lapse rate by tier, revenue at risk by driver, response before and after the reward cut
- Governance is already done: the same "lapse rate" in the console, in Genie and in finance's reporting

---

# Why Databricks

One platform carried the whole journey, which is why it took hours, not quarters.

- Serverless Lakeflow pipeline with declarative quality rules, no cluster management
- Unity Catalog metric views: define the KPI once, every consumer (Genie, app, dashboard) gets the same number
- MLflow and the UC model registry: versioned, aliased, auditable model promotion
- Lakebase: Postgres for the operational worklist and write-back, synced from Delta without an ETL team
- Genie Agent: natural language over governed data, with instructions and benchmarks checked in like code
- Databricks Apps: the business surface sits next to the data, inheriting its permissions

---

# Next steps

1. Pilot: 90 days, High-risk Gold/Silver mall segment, holdout group for measured lift
2. Add the stores' product-fit feedback loop so merchandising sees fit-return spikes within the week
3. Move scoring to weekly with the synced worklist refreshing automatically
4. Extend the Genie Agent to store operations and merchandising questions on the same governed layer

Appendix: repo with code, run logs and committed outputs: github.com/OrrinDatabricks/loyalty-lapse-propensity
