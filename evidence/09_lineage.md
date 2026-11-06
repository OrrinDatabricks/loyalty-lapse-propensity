# 09 Unity Catalog lineage: proof the stages are integrated

Query against `system.access.table_lineage` for every table in the build. Each row is a source-to-target edge recorded by Unity Catalog when a pipeline, job or query actually read one table and wrote another. The chain runs raw files > bronze > silver > gold > metric views, silver > feature sets > scores > Lakebase synced table, with no stage standing alone.

```sql
SELECT source_table_full_name, target_table_full_name, entity_type, COUNT(*) AS events, MAX(event_time) AS last_seen
FROM system.access.table_lineage
WHERE (source_table_full_name LIKE 'loyalty_lapse_demo_catalog.loyalty.%' OR target_table_full_name LIKE 'loyalty_lapse_demo_catalog.loyalty.%' OR target_table_full_name LIKE 'loyalty_lakebase.%')
  AND source_table_full_name IS NOT NULL AND target_table_full_name IS NOT NULL
GROUP BY ALL ORDER BY target_table_full_name, source_table_full_name
```

| Source | Target | Written by | Events | Last seen |
|---|---|---|---|---|
| loyalty_lapse_demo_catalog.loyalty.member_retention_scores | loyalty_lakebase.loyalty.member_retention_scores | PIPELINE | 1 | 2026-11-03T17:23:57 |
| loyalty_lapse_demo_catalog.loyalty.silver_campaign_touches | loyalty_lapse_demo_catalog.loyalty.gold_member_360 | PIPELINE | 2 | 2026-11-03T17:32:13 |
| loyalty_lapse_demo_catalog.loyalty.silver_engagement_events | loyalty_lapse_demo_catalog.loyalty.gold_member_360 | PIPELINE | 2 | 2026-11-03T17:32:13 |
| loyalty_lapse_demo_catalog.loyalty.silver_members | loyalty_lapse_demo_catalog.loyalty.gold_member_360 | PIPELINE | 2 | 2026-11-03T17:32:13 |
| loyalty_lapse_demo_catalog.loyalty.silver_returns | loyalty_lapse_demo_catalog.loyalty.gold_member_360 | PIPELINE | 2 | 2026-11-03T17:32:13 |
| loyalty_lapse_demo_catalog.loyalty.silver_transactions | loyalty_lapse_demo_catalog.loyalty.gold_member_360 | PIPELINE | 2 | 2026-11-03T17:32:13 |
| loyalty_lapse_demo_catalog.loyalty.silver_campaign_touches | loyalty_lapse_demo_catalog.loyalty.gold_member_activity_monthly | PIPELINE | 2 | 2026-11-03T17:32:01 |
| loyalty_lapse_demo_catalog.loyalty.silver_engagement_events | loyalty_lapse_demo_catalog.loyalty.gold_member_activity_monthly | PIPELINE | 2 | 2026-11-03T17:32:01 |
| loyalty_lapse_demo_catalog.loyalty.silver_returns | loyalty_lapse_demo_catalog.loyalty.gold_member_activity_monthly | PIPELINE | 2 | 2026-11-03T17:32:01 |
| loyalty_lapse_demo_catalog.loyalty.silver_transactions | loyalty_lapse_demo_catalog.loyalty.gold_member_activity_monthly | PIPELINE | 2 | 2026-11-03T17:32:01 |
| loyalty_lapse_demo_catalog.loyalty.gold_member_activity_monthly | loyalty_lapse_demo_catalog.loyalty.loyalty_activity_metrics | JOB | 1 | 2026-11-03T17:34:47 |
| loyalty_lapse_demo_catalog.loyalty.gold_member_activity_monthly | loyalty_lapse_demo_catalog.loyalty.loyalty_activity_metrics | QUERY (warehouse) | 6 | 2026-11-06T00:29:44 |
| loyalty_lapse_demo_catalog.loyalty.gold_member_360 | loyalty_lapse_demo_catalog.loyalty.loyalty_member_metrics | JOB | 1 | 2026-11-03T17:34:46 |
| loyalty_lapse_demo_catalog.loyalty.gold_member_360 | loyalty_lapse_demo_catalog.loyalty.loyalty_member_metrics | QUERY (warehouse) | 11 | 2026-11-06T00:28:24 |
| loyalty_lapse_demo_catalog.loyalty.ml_scoring_features | loyalty_lapse_demo_catalog.loyalty.member_retention_scores | JOB | 3 | 2026-11-05T23:54:44 |
| loyalty_lapse_demo_catalog.loyalty.silver_campaign_touches | loyalty_lapse_demo_catalog.loyalty.ml_holdout_set | JOB | 7 | 2026-11-05T23:53:11 |
| loyalty_lapse_demo_catalog.loyalty.silver_engagement_events | loyalty_lapse_demo_catalog.loyalty.ml_holdout_set | JOB | 7 | 2026-11-05T23:53:11 |
| loyalty_lapse_demo_catalog.loyalty.silver_members | loyalty_lapse_demo_catalog.loyalty.ml_holdout_set | JOB | 7 | 2026-11-05T23:53:11 |
| loyalty_lapse_demo_catalog.loyalty.silver_returns | loyalty_lapse_demo_catalog.loyalty.ml_holdout_set | JOB | 7 | 2026-11-05T23:53:11 |
| loyalty_lapse_demo_catalog.loyalty.silver_transactions | loyalty_lapse_demo_catalog.loyalty.ml_holdout_set | JOB | 7 | 2026-11-05T23:53:11 |
| loyalty_lapse_demo_catalog.loyalty.silver_campaign_touches | loyalty_lapse_demo_catalog.loyalty.ml_scoring_features | JOB | 5 | 2026-11-05T23:54:11 |
| loyalty_lapse_demo_catalog.loyalty.silver_engagement_events | loyalty_lapse_demo_catalog.loyalty.ml_scoring_features | JOB | 5 | 2026-11-05T23:54:11 |
| loyalty_lapse_demo_catalog.loyalty.silver_members | loyalty_lapse_demo_catalog.loyalty.ml_scoring_features | JOB | 5 | 2026-11-05T23:54:11 |
| loyalty_lapse_demo_catalog.loyalty.silver_returns | loyalty_lapse_demo_catalog.loyalty.ml_scoring_features | JOB | 5 | 2026-11-05T23:54:11 |
| loyalty_lapse_demo_catalog.loyalty.silver_transactions | loyalty_lapse_demo_catalog.loyalty.ml_scoring_features | JOB | 5 | 2026-11-05T23:54:11 |
| loyalty_lapse_demo_catalog.loyalty.silver_campaign_touches | loyalty_lapse_demo_catalog.loyalty.ml_training_set | JOB | 7 | 2026-11-05T23:53:06 |
| loyalty_lapse_demo_catalog.loyalty.silver_engagement_events | loyalty_lapse_demo_catalog.loyalty.ml_training_set | JOB | 7 | 2026-11-05T23:53:06 |
| loyalty_lapse_demo_catalog.loyalty.silver_members | loyalty_lapse_demo_catalog.loyalty.ml_training_set | JOB | 7 | 2026-11-05T23:53:06 |
| loyalty_lapse_demo_catalog.loyalty.silver_returns | loyalty_lapse_demo_catalog.loyalty.ml_training_set | JOB | 7 | 2026-11-05T23:53:06 |
| loyalty_lapse_demo_catalog.loyalty.silver_transactions | loyalty_lapse_demo_catalog.loyalty.ml_training_set | JOB | 7 | 2026-11-05T23:53:06 |
| loyalty_lapse_demo_catalog.loyalty.member_retention_scores | loyalty_lapse_demo_catalog.loyalty.retention_risk_metrics | JOB | 1 | 2026-11-03T17:34:49 |
| loyalty_lapse_demo_catalog.loyalty.member_retention_scores | loyalty_lapse_demo_catalog.loyalty.retention_risk_metrics | QUERY (warehouse) | 11 | 2026-11-06T00:28:27 |
| loyalty_lapse_demo_catalog.loyalty.bronze_campaign_touches | loyalty_lapse_demo_catalog.loyalty.silver_campaign_touches | PIPELINE | 4 | 2026-11-03T17:31:39 |
| loyalty_lapse_demo_catalog.loyalty.bronze_engagement_events | loyalty_lapse_demo_catalog.loyalty.silver_engagement_events | PIPELINE | 4 | 2026-11-03T17:31:49 |
| loyalty_lapse_demo_catalog.loyalty.bronze_members | loyalty_lapse_demo_catalog.loyalty.silver_members | PIPELINE | 2 | 2026-11-03T17:31:47 |
| loyalty_lapse_demo_catalog.loyalty.silver_stores | loyalty_lapse_demo_catalog.loyalty.silver_members | PIPELINE | 2 | 2026-11-03T17:31:47 |
| loyalty_lapse_demo_catalog.loyalty.bronze_products | loyalty_lapse_demo_catalog.loyalty.silver_products | PIPELINE | 2 | 2026-11-03T17:31:37 |
| loyalty_lapse_demo_catalog.loyalty.bronze_returns | loyalty_lapse_demo_catalog.loyalty.silver_returns | PIPELINE | 4 | 2026-11-03T17:31:40 |
| loyalty_lapse_demo_catalog.loyalty.bronze_stores | loyalty_lapse_demo_catalog.loyalty.silver_stores | PIPELINE | 2 | 2026-11-03T17:31:39 |
| loyalty_lapse_demo_catalog.loyalty.bronze_transactions | loyalty_lapse_demo_catalog.loyalty.silver_transactions | PIPELINE | 4 | 2026-11-03T17:31:50 |

Reading the graph: PIPELINE edges are the Lakeflow medallion; JOB edges into `ml_*` and `member_retention_scores` are the training and scoring job; edges into `loyalty_*_metrics` and `retention_risk_metrics` are the governance job creating the metric views (plus warehouse queries from the app, Genie and the dashboard); the edge into `loyalty_lakebase.loyalty.member_retention_scores` is the Lakebase sync pipeline.
