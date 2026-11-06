# Results quoted in the deck, with their source

All numbers come from committed run outputs. Synthetic data; dollar figures are for the simulated retailer.

| Figure | Value | Evidence |
|---|---|---|
| Loyalty members | 400,000 (Bronze 70%, Silver 22%, Gold 8%) | `evidence/01_generate_synthetic_data.md`, `evidence/02_pipeline_tables.md` |
| Gold + Silver share of members / of trailing-12M spend | 30.1% / 67.2% | gold_member_360 query (this file's generation step) |
| Transactions / engagement events / campaign touches / returns ingested | 1.95M / 4.1M / 1.25M / 163K | `evidence/02_pipeline_tables.md` |
| Pipeline expectations | 13 rules, 0 failed records | `evidence/02_pipeline_tables.md` |
| Unity Catalog documentation coverage | 305 columns across 24 tables described (0 undocumented), every metric-view dimension and measure, catalog, both schemas, the raw volume and the registered model; comments survive pipeline updates and are re-applied weekly | `evidence/04_governance.md` |
| Overall 90-day lapse rate (all members) | 49.0% | `evidence/06_genie_agent.md` (Genie answer), gold_member_360 |
| Trailing-12M spend held by lapsed members | $27.1M total, $13.9M Gold + Silver | gold_member_360 query |
| Lapse rate, Gold + Silver at mall stores vs other formats | 38.2% vs 27.4% | gold_member_360 query |
| Mall-store Gold/Silver cohort active buyers, May to Sep 2026 | 6,683 to 2,962 (down 56%); everyone else flat (89.6K to 91.2K) | `evidence/01_generate_synthetic_data.md` story check |
| Denim return rate, before vs after the Jun 1 fit change | 7 to 8% (Mar to May) vs 22% (Jul to Sep) | `evidence/01_generate_synthetic_data.md` |
| Birthday reward response rate, before vs after the Jul 15 cut | 34.0% vs 13.9% | `evidence/01_generate_synthetic_data.md` |
| Model training rows / hold-out rows | 188,003 / 94,788 | `evidence/03a_train_lapse_model.md` |
| Hold-out AUC / average precision | 0.716 / 0.519 | `evidence/03a_train_lapse_model.md` |
| Base lapse rate in the modeled population | 31.1% | `evidence/03a_train_lapse_model.md` |
| Top-decile precision / lift / recall | 59.4% / 1.91x / 19.1% | `evidence/03a_train_lapse_model.md` |
| Lapsed spend captured by the top decile | $2.40M, 15.6% of all lapsed spend, in 10% of volume | `evidence/03a_train_lapse_model.md` |
| Top drivers (permutation importance) | days since last engagement, 12M transactions, tier, home store format, lifetime transactions, denim share | `evidence/03a_train_lapse_model.md` |
| Regular shoppers scored (3+ purchases in 180 days) | 101,089 | `evidence/03b_score_members.md` |
| High risk members / revenue at risk | 1,408 / $1.18M | `evidence/03b_score_members.md`, `evidence/05_lakebase.md` |
| High + Medium risk members / revenue at risk | 37,703 / $6.15M | member_retention_scores query |
| Total model revenue at risk (all scored) | $14.4M | member_retention_scores query |
| High risk Gold/Silver mall members / revenue at risk | 1,260 / $1.07M | member_retention_scores query |
| Share of High risk that is Gold or Silver at mall stores | 89% (1,260 of 1,408) | `evidence/03b_score_members.md` |
| Expected calibration error (hold-out) | 0.0225; members scored 0.6+ lapsed at 89% or more | `evidence/03a_train_lapse_model.md`, `MODEL.md` |
| Lakebase synced table | `loyalty_lakebase.loyalty.member_retention_scores`, ONLINE, 101,089 rows, refreshed automatically by the scoring job | `evidence/05_lakebase.md` |
| Decisions written back from the console | 2 approve decisions in `retention_app.outreach_actions` | `evidence/05_lakebase.md` |
| Genie Agent conversation answers | 6 of 6 questions COMPLETED with correct metric view SQL | `evidence/06_genie_agent.md` |
| Genie Agent benchmark evaluation run | 4 of 4 correct | `evidence/06_genie_agent.md` |
| AI/BI dashboard | published, 3 datasets, 4 KPIs, 4 charts, worklist, global filters | `evidence/08_dashboard.md` |

Definitions: *lapsed* = no purchase in the trailing 90 days. *Revenue at risk* = trailing-12-month spend x model
probability of lapse, summed. *Regular shopper* = 3 or more purchases in the trailing 180 days.
