# 04 Unity Catalog governance and metric views: executed notebook

Exported from the job run with `databricks jobs export-run`; cell outputs are the real run results.

# 04 Unity Catalog governance: comments, tags, certified tables, metric views, grants

Note: this metastore has a tag policy on the key `domain` (finance, sales, supply_chain, quality, hr, operations), so the build uses `business_area` for the loyalty data product. The policy rejected the first attempt, which is the behavior you want from governed tags.

The small UC investments that make agents accurate: every gold column described, tables tagged with
domain and certification, PII flagged, governed metric views so "lapse rate" means one thing everywhere,
and least-privilege grants for the analyst and app principals.

## Cell 2 (finished)

```python
dbutils.widgets.text("catalog", "loyalty_lapse_demo_catalog")
dbutils.widgets.text("schema", "loyalty")
C, S = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
FQ = lambda t: f"{C}.{S}.{t}"

def run(sql):
    print(sql.strip().splitlines()[0][:110])
    return spark.sql(sql)
```

## Column comments on the gold layer (what Genie reads)

## Cell 4 (finished)

```python
COLUMN_COMMENTS = {
    "gold_member_360": {
        "member_id": "Loyalty member identifier (M + 7 digits). Primary key.",
        "tier": "Loyalty tier: Bronze, Silver or Gold. Gold members are the top 8% by spend.",
        "join_date": "Date the member enrolled in the loyalty program.",
        "tenure_days": "Days since enrollment as of as_of_date.",
        "home_store_id": "Store where the member shops most. S0000 is the online store.",
        "home_store_format": "Format of the home store: online, mall, strip or outlet.",
        "home_region": "Region of the home store: West, Southwest, Midwest, Southeast, Northeast.",
        "preferred_channel": "Marketing channel the member opted into: app, email, sms or none.",
        "birthday_month": "Calendar month (1-12) of the member's birthday reward.",
        "as_of_date": "Latest transaction date in the data; all recency metrics are measured from this date.",
        "last_purchase_date": "Date of the most recent purchase.",
        "days_since_last_purchase": "Recency in days. Members over 90 are lapsed.",
        "lifetime_transactions": "Total number of loyalty-attached transactions.",
        "lifetime_spend": "Total net spend in USD.",
        "spend_12m": "Net spend in USD over the trailing 12 months. Used as annual value at risk.",
        "transactions_12m": "Transactions in the trailing 12 months.",
        "spend_90d": "Net spend in USD over the trailing 90 days.",
        "transactions_90d": "Transactions in the trailing 90 days.",
        "denim_share": "Share (0-1) of lifetime spend in the Denim category.",
        "avg_basket": "Average basket value in USD.",
        "avg_discount_pct": "Average discount percent across baskets; high values indicate discount dependence.",
        "online_share": "Share (0-1) of transactions placed online.",
        "events_30d": "App, web and email engagement events in the trailing 30 days.",
        "events_90d": "Engagement events in the trailing 90 days.",
        "events_180d": "Engagement events in the trailing 180 days.",
        "last_engagement_date": "Most recent engagement event date.",
        "days_since_last_engagement": "Days since the member last opened the app, an email, or visited the site.",
        "returns_90d": "Returns in the trailing 90 days.",
        "fit_returns_90d": "Returns with reason fit or size in the trailing 90 days; the Denim fit-change signal.",
        "refunds_180d": "Refund value in USD over the trailing 180 days.",
        "touches_180d": "Campaign touches received in the trailing 180 days.",
        "responses_180d": "Campaign touches the member responded to in the trailing 180 days.",
        "last_birthday_reward_value": "USD value of the most recent birthday reward offered ($20 before Jul 15 2026, $10 after).",
        "last_win_back_date": "Date of the most recent win-back campaign touch, if any.",
        "lapsed_90d": "TRUE when the member has not purchased in the last 90 days. This is the definition of a lapsed member.",
        "email": "Member email. PII: masked for everyone outside the admins group.",
        "first_name": "Member first name. PII.",
        "last_name": "Member last name. PII.",
    },
    "gold_member_activity_monthly": {
        "member_id": "Loyalty member identifier.",
        "activity_month": "First day of the calendar month of activity.",
        "transactions": "Transactions in the month.",
        "spend": "Net spend in USD in the month.",
        "units": "Units purchased in the month.",
        "denim_spend": "Net spend in USD on Denim in the month.",
        "engagement_events": "App, web and email events in the month.",
        "app_opens": "App open events in the month.",
        "email_interactions": "Email opens plus clicks in the month.",
        "campaign_touches": "Campaign touches received in the month.",
        "campaign_responses": "Campaign touches responded to in the month.",
        "reward_value_offered": "Total USD reward value offered in the month.",
        "returns": "Returns in the month.",
        "refunds": "Refund value in USD in the month.",
        "fit_returns": "Returns with reason fit or size in the month.",
    },
    "member_retention_scores": {
        "member_id": "Loyalty member identifier.",
        "as_of_date": "Date the features were computed.",
        "p_lapse": "Model probability (0-1) that the member makes no purchase in the next 90 days.",
        "risk_band": "High (p_lapse >= 0.60), Medium (0.35-0.60) or Low.",
        "primary_driver": "Main risk driver: engagement_drop, fit_returns, reward_devalued, purchase_recency, unresponsive_to_campaigns, discount_dependent or none.",
        "risk_drivers": "All risk drivers that apply to the member.",
        "recommended_action": "Retention action the console proposes for this member.",
        "spend_12m": "Trailing 12-month net spend in USD.",
        "annual_value_at_risk": "spend_12m multiplied by p_lapse, in USD. Sum this for revenue at risk.",
        "scored_at": "Timestamp of the scoring run.",
    },
}
for table, cols in COLUMN_COMMENTS.items():
    existing = {r.col_name for r in spark.sql(f"DESCRIBE TABLE {FQ(table)}").collect()}
    for col, text in cols.items():
        if col in existing:
            spark.sql(f"COMMENT ON COLUMN {FQ(table)}.{col} IS '{text.replace(chr(39), chr(39)*2)}'")
    print(f"{table}: {len([c for c in cols if c in existing])} columns documented")
```

Output:

```text
gold_member_360: 38 columns documented
gold_member_activity_monthly: 15 columns documented
member_retention_scores: 10 columns documented
```

## Tags: domain, certification, PII, layer

## Cell 6 (finished)

```python
TABLE_TAGS = {
    "gold_member_360":             {"business_area": "loyalty", "lp_layer": "gold", "lp_certified": "true", "lp_owner_team": "crm_analytics"},
    "gold_member_activity_monthly": {"business_area": "loyalty", "lp_layer": "gold", "lp_certified": "true", "lp_owner_team": "crm_analytics"},
    "member_retention_scores":     {"business_area": "loyalty", "lp_layer": "gold", "lp_certified": "true", "lp_owner_team": "data_science", "model": "loyalty_lapse_model"},
    "silver_transactions":         {"business_area": "loyalty", "lp_layer": "silver", "lp_certified": "false"},
    "silver_members":              {"business_area": "loyalty", "lp_layer": "silver", "lp_certified": "false", "lp_contains_pii": "true"},
    "silver_engagement_events":    {"business_area": "loyalty", "lp_layer": "silver", "lp_certified": "false"},
    "silver_campaign_touches":     {"business_area": "loyalty", "lp_layer": "silver", "lp_certified": "false"},
    "silver_returns":              {"business_area": "loyalty", "lp_layer": "silver", "lp_certified": "false"},
}
for table, tags in TABLE_TAGS.items():
    tag_list = ", ".join(f"'{k}' = '{v}'" for k, v in tags.items())
    run(f"ALTER TABLE {FQ(table)} SET TAGS ({tag_list})")

for col in ("email", "first_name", "last_name"):
    run(f"ALTER TABLE {FQ('gold_member_360')} ALTER COLUMN {col} SET TAGS ('lp_pii' = 'true', 'lp_pii_class' = 'direct_identifier')")
    run(f"ALTER TABLE {FQ('silver_members')} ALTER COLUMN {col} SET TAGS ('lp_pii' = 'true', 'lp_pii_class' = 'direct_identifier')")

run(f"ALTER SCHEMA {C}.{S} SET TAGS ('business_area' = 'loyalty', 'lp_data_product' = 'loyalty_lapse_propensity')")
```

Output:

```text
ALTER TABLE loyalty_lapse_demo_catalog.loyalty.gold_member_360 SET TAGS ('business_area' = 'loyalty', 'lp_laye
ALTER TABLE loyalty_lapse_demo_catalog.loyalty.gold_member_activity_monthly SET TAGS ('business_area' = 'loyal
ALTER TABLE loyalty_lapse_demo_catalog.loyalty.member_retention_scores SET TAGS ('business_area' = 'loyalty', 
ALTER TABLE loyalty_lapse_demo_catalog.loyalty.silver_transactions SET TAGS ('business_area' = 'loyalty', 'lp_
ALTER TABLE loyalty_lapse_demo_catalog.loyalty.silver_members SET TAGS ('business_area' = 'loyalty', 'lp_layer
ALTER TABLE loyalty_lapse_demo_catalog.loyalty.silver_engagement_events SET TAGS ('business_area' = 'loyalty',
ALTER TABLE loyalty_lapse_demo_catalog.loyalty.silver_campaign_touches SET TAGS ('business_area' = 'loyalty', 
ALTER TABLE loyalty_lapse_demo_catalog.loyalty.silver_returns SET TAGS ('business_area' = 'loyalty', 'lp_layer
ALTER TABLE loyalty_lapse_demo_catalog.loyalty.gold_member_360 ALTER COLUMN email SET TAGS ('lp_pii' = 'true',
ALTER TABLE loyalty_lapse_demo_catalog.loyalty.silver_members ALTER COLUMN email SET TAGS ('lp_pii' = 'true', 
ALTER TABLE loyalty_lapse_demo_catalog.loyalty.gold_member_360 ALTER COLUMN first_name SET TAGS ('lp_pii' = 't
ALTER TABLE loyalty_lapse_demo_catalog.loyalty.silver_members ALTER COLUMN first_name SET TAGS ('lp_pii' = 'tr
ALTER TABLE loyalty_lapse_demo_catalog.loyalty.gold_member_360 ALTER COLUMN last_name SET TAGS ('lp_pii' = 'tr
ALTER TABLE loyalty_lapse_demo_catalog.loyalty.silver_members ALTER COLUMN last_name SET TAGS ('lp_pii' = 'tru
ALTER SCHEMA loyalty_lapse_demo_catalog.loyalty SET TAGS ('business_area' = 'loyalty', 'lp_data_product' = 'lo

{'text/plain': 'DataFrame[]'}
```

## Governed metric views
One definition of lapse rate, revenue at risk and campaign response rate, consumed by Genie, dashboards and the app.

## Cell 8 (finished)

```python
run(f"""
CREATE OR REPLACE VIEW {FQ('loyalty_member_metrics')}
WITH METRICS
LANGUAGE YAML
COMMENT 'Governed member-level KPIs for the loyalty program: members, lapse rate, spend, revenue at risk. Grain = one row per member.'
AS $$
version: 1.1
source: {FQ('gold_member_360')}
comment: "Loyalty member KPIs. lapse = no purchase in the last 90 days."
dimensions:
  - name: Tier
    expr: tier
    synonyms: ["loyalty tier", "membership level"]
  - name: Home Store Format
    expr: home_store_format
    synonyms: ["store format", "store type", "channel of home store"]
  - name: Home Region
    expr: home_region
    synonyms: ["region"]
  - name: Preferred Channel
    expr: preferred_channel
    synonyms: ["marketing channel", "opt-in channel"]
  - name: Lapsed
    expr: lapsed_90d
    synonyms: ["churned", "inactive", "lapsed member"]
  - name: Recency Bucket
    expr: "CASE WHEN days_since_last_purchase <= 30 THEN '0-30 days' WHEN days_since_last_purchase <= 60 THEN '31-60 days' WHEN days_since_last_purchase <= 90 THEN '61-90 days' ELSE '90+ days (lapsed)' END"
    synonyms: ["recency", "days since last purchase bucket"]
  - name: Join Year
    expr: "YEAR(join_date)"
measures:
  - name: Members
    expr: COUNT(member_id)
    synonyms: ["member count", "number of members"]
    format:
      type: number
      decimal_places: {{type: exact, places: 0}}
  - name: Lapsed Members
    expr: COUNT(member_id) FILTER (WHERE lapsed_90d)
    synonyms: ["churned members", "inactive members"]
  - name: Lapse Rate
    expr: "COUNT(member_id) FILTER (WHERE lapsed_90d) / COUNT(member_id)"
    comment: "Share of members with no purchase in the last 90 days."
    synonyms: ["churn rate", "attrition rate", "inactive rate"]
    format:
      type: percentage
      decimal_places: {{type: exact, places: 1}}
  - name: Spend 12M
    expr: SUM(spend_12m)
    synonyms: ["trailing twelve month spend", "annual spend", "revenue"]
    format:
      type: currency
      currency_code: USD
      decimal_places: {{type: exact, places: 0}}
  - name: Avg Spend 12M per Member
    expr: AVG(spend_12m)
    format:
      type: currency
      currency_code: USD
      decimal_places: {{type: exact, places: 0}}
  - name: Lapsed Spend 12M
    expr: SUM(spend_12m) FILTER (WHERE lapsed_90d)
    comment: "Trailing-12-month spend of members who have lapsed: revenue already walking out the door."
    synonyms: ["revenue lost to lapse", "lapsed revenue"]
    format:
      type: currency
      currency_code: USD
      decimal_places: {{type: exact, places: 0}}
  - name: Avg Engagement Events 30D
    expr: AVG(events_30d)
  - name: Fit Return Members 90D
    expr: COUNT(member_id) FILTER (WHERE fit_returns_90d > 0)
    synonyms: ["members with fit returns"]
$$
""")

run(f"""
CREATE OR REPLACE VIEW {FQ('loyalty_activity_metrics')}
WITH METRICS
LANGUAGE YAML
COMMENT 'Governed monthly activity KPIs for the loyalty program: active buyers, spend, denim spend, engagement, returns, campaign response. Grain = member x month.'
AS $$
version: 1.1
source: {FQ('gold_member_activity_monthly')}
comment: "Monthly loyalty activity trend. Use Activity Month as the time axis."
dimensions:
  - name: Activity Month
    expr: activity_month
    synonyms: ["month"]
    format:
      type: date
      date_format: locale_short_month
measures:
  - name: Active Buyers
    expr: COUNT(member_id) FILTER (WHERE transactions > 0)
    synonyms: ["buying members", "purchasers"]
  - name: Engaged Members
    expr: COUNT(member_id) FILTER (WHERE engagement_events > 0)
  - name: Transactions
    expr: SUM(transactions)
  - name: Spend
    expr: SUM(spend)
    synonyms: ["revenue", "sales"]
    format:
      type: currency
      currency_code: USD
      decimal_places: {{type: exact, places: 0}}
  - name: Denim Spend
    expr: SUM(denim_spend)
    format:
      type: currency
      currency_code: USD
      decimal_places: {{type: exact, places: 0}}
  - name: Engagement Events
    expr: SUM(engagement_events)
  - name: Returns
    expr: SUM(returns)
  - name: Fit Returns
    expr: SUM(fit_returns)
    synonyms: ["fit and size returns"]
  - name: Fit Return Share
    expr: "SUM(fit_returns) / NULLIF(SUM(returns), 0)"
    format:
      type: percentage
      decimal_places: {{type: exact, places: 1}}
  - name: Campaign Touches
    expr: SUM(campaign_touches)
  - name: Campaign Response Rate
    expr: "SUM(campaign_responses) / NULLIF(SUM(campaign_touches), 0)"
    synonyms: ["response rate", "campaign conversion"]
    format:
      type: percentage
      decimal_places: {{type: exact, places: 1}}
$$
""")

run(f"""
CREATE OR REPLACE VIEW {FQ('retention_risk_metrics')}
WITH METRICS
LANGUAGE YAML
COMMENT 'Governed KPIs from the lapse model worklist: members by risk band, revenue at risk, average lapse probability. Grain = one row per scored member.'
AS $$
version: 1.1
source: {FQ('member_retention_scores')}
comment: "Model-scored retention risk. Revenue at Risk = sum of spend_12m x p_lapse."
dimensions:
  - name: Risk Band
    expr: risk_band
    synonyms: ["risk level", "risk tier"]
  - name: Primary Driver
    expr: primary_driver
    synonyms: ["risk reason", "why at risk", "driver"]
  - name: Recommended Action
    expr: recommended_action
    synonyms: ["next best action", "treatment"]
  - name: Tier
    expr: tier
  - name: Home Store Format
    expr: home_store_format
  - name: Home Region
    expr: home_region
  - name: Preferred Channel
    expr: preferred_channel
measures:
  - name: Scored Members
    expr: COUNT(member_id)
  - name: High Risk Members
    expr: COUNT(member_id) FILTER (WHERE risk_band = 'High')
    synonyms: ["members at high risk", "high risk count"]
  - name: Avg Lapse Probability
    expr: AVG(p_lapse)
    format:
      type: percentage
      decimal_places: {{type: exact, places: 1}}
  - name: Revenue at Risk
    expr: SUM(annual_value_at_risk)
    synonyms: ["value at risk", "spend at risk", "dollars at risk"]
    format:
      type: currency
      currency_code: USD
      decimal_places: {{type: exact, places: 0}}
  - name: Spend 12M
    expr: SUM(spend_12m)
    format:
      type: currency
      currency_code: USD
      decimal_places: {{type: exact, places: 0}}
$$
""")

for mv in ("loyalty_member_metrics", "loyalty_activity_metrics", "retention_risk_metrics"):
    run(f"ALTER VIEW {FQ(mv)} SET TAGS ('business_area' = 'loyalty', 'lp_layer' = 'metrics', 'lp_certified' = 'true')")
```

Output:

```text
CREATE OR REPLACE VIEW loyalty_lapse_demo_catalog.loyalty.loyalty_member_metrics
CREATE OR REPLACE VIEW loyalty_lapse_demo_catalog.loyalty.loyalty_activity_metrics
CREATE OR REPLACE VIEW loyalty_lapse_demo_catalog.loyalty.retention_risk_metrics
ALTER VIEW loyalty_lapse_demo_catalog.loyalty.loyalty_member_metrics SET TAGS ('business_area' = 'loyalty', 'l
ALTER VIEW loyalty_lapse_demo_catalog.loyalty.loyalty_activity_metrics SET TAGS ('business_area' = 'loyalty', 
ALTER VIEW loyalty_lapse_demo_catalog.loyalty.retention_risk_metrics SET TAGS ('business_area' = 'loyalty', 'l
```

## Prove the metric views answer the business questions

## Cell 10 (finished)

```python
print("Lapse rate and lapsed revenue by tier and home store format:")
spark.sql(f"""
SELECT `Tier`, `Home Store Format`, MEASURE(`Members`) AS members, MEASURE(`Lapse Rate`) AS lapse_rate,
       MEASURE(`Lapsed Spend 12M`) AS lapsed_spend_12m
FROM {FQ('loyalty_member_metrics')}
GROUP BY ALL ORDER BY lapse_rate DESC
""").show(20, False)

print("Monthly trend 2026: active buyers, fit return share, campaign response rate:")
spark.sql(f"""
SELECT `Activity Month`, MEASURE(`Active Buyers`) AS active_buyers, MEASURE(`Denim Spend`) AS denim_spend,
       ROUND(MEASURE(`Fit Return Share`), 3) AS fit_return_share, ROUND(MEASURE(`Campaign Response Rate`), 3) AS response_rate
FROM {FQ('loyalty_activity_metrics')}
WHERE `Activity Month` >= '2026-01-01'
GROUP BY ALL ORDER BY `Activity Month`
""").show(20, False)

print("Revenue at risk by risk band and primary driver:")
spark.sql(f"""
SELECT `Risk Band`, `Primary Driver`, MEASURE(`Scored Members`) AS members, ROUND(MEASURE(`Revenue at Risk`), 0) AS revenue_at_risk
FROM {FQ('retention_risk_metrics')}
GROUP BY ALL ORDER BY revenue_at_risk DESC
""").show(20, False)
```

Output:

```text
Lapse rate and lapsed revenue by tier and home store format:
+------+-----------------+-------+-------------------+----------------+
|Tier  |Home Store Format|members|lapse_rate         |lapsed_spend_12m|
+------+-----------------+-------+-------------------+----------------+
|Bronze|online           |42077  |0.5665327851320199 |2002419.21      |
|Bronze|outlet           |55060  |0.5649836541954232 |2609137.44      |
|Bronze|mall             |114755 |0.5623110104134896 |5383998.69      |
|Bronze|strip            |67673  |0.5622921992522867 |3203706.85      |
|Silver|mall             |45446  |0.3950402675703032 |6195502.72      |
|Silver|online           |16522  |0.2927006415688173 |1558035.88      |
|Silver|strip            |26743  |0.2904311408592903 |2478645.08      |
|Silver|outlet           |21933  |0.280855332147905  |1965549.72      |
|Gold  |mall             |4076   |0.24263984298331698|1135320.65      |
|Gold  |strip            |2319   |0.11341095299698145|253586.15       |
|Gold  |outlet           |1927   |0.1126102750389206 |198348.40       |
|Gold  |online           |1469   |0.10551395507147719|139807.81       |
+------+-----------------+-------+-------------------+----------------+

Monthly trend 2026: active buyers, fit return share, campaign response rate:
+--------------+-------------+-----------+----------------+-------------+
|Activity Month|active_buyers|denim_spend|fit_return_share|response_rate|
+--------------+-------------+-----------+----------------+-------------+
|2026-01-01    |65536        |2461943.85 |0.577           |0.172        |
|2026-02-01    |61561        |2267704.99 |0.594           |0.178        |
|2026-03-01    |91662        |3660048.38 |0.584           |0.172        |
|2026-04-01    |91925        |3612803.02 |0.597           |0.174        |
|2026-05-01    |96292        |3818608.74 |0.578           |0.173        |
|2026-06-01    |94770        |3671924.23 |0.736           |0.138        |
|2026-07-01    |97612        |3732059.22 |0.834           |0.172        |
|2026-08-01    |96847        |3653353.06 |0.836           |0.087        |
|2026-09-01    |94141        |3466298.54 |0.832           |0.088        |
|2026-10-01    |94157        |3480273.79 |0.83            |0.089        |
+--------------+-------------+-----------+----------------+-------------+

Revenue at risk by risk band and primary driver:
+---------+-------------------------+-------+---------------+
|Risk Band|Primary Driver           |members|revenue_at_risk|
+---------+-------------------------+-------+---------------+
|Low      |none                     |26539  |3307558.0      |
|Medium   |none                     |13630  |1642482.0      |
|Medium   |purchase_recency         |11056  |1627966.0      |
|Low      |engagement_drop          |11000  |1597401.0      |
|Low      |purchase_recency         |11193  |1519597.0      |
|Low      |fit_returns              |11556  |1440971.0      |
|High     |purchase_recency         |1064   |809102.0       |
|Medium   |fit_returns              |5520   |743552.0       |
|Medium   |engagement_drop          |3095   |579374.0       |
|High     |engagement_drop          |244    |305161.0       |
|Low      |unresponsive_to_campaigns|2263   |296104.0       |
|Medium   |unresponsive_to_campaigns|1306   |179037.0       |
|Medium   |reward_devalued          |1373   |160663.0       |
|Low      |reward_devalued          |730    |87536.0        |
|High     |fit_returns              |80     |58142.0        |
|Medium   |discount_dependent       |315    |33197.0        |
|Low      |discount_dependent       |105    |12952.0        |
|High     |reward_devalued          |14     |5377.0         |
|High     |none                     |5      |2994.0         |
|High     |unresponsive_to_campaigns|1      |960.0          |
+---------+-------------------------+-------+---------------+
```

## Least-privilege grants
Analysts get the gold layer and metric views only; silver and bronze stay with engineering.

## Cell 12 (finished)

```python
run(f"CREATE GROUP IF NOT EXISTS loyalty_analysts") if False else None  # groups are account-level; created by an admin outside the bundle
GRANTEE = "account users"  # demo stand-in for the loyalty_analysts group
run(f"GRANT USE CATALOG ON CATALOG {C} TO `{GRANTEE}`")
run(f"GRANT USE SCHEMA ON SCHEMA {C}.{S} TO `{GRANTEE}`")
for obj in ("gold_member_360", "gold_member_activity_monthly", "member_retention_scores",
            "loyalty_member_metrics", "loyalty_activity_metrics", "retention_risk_metrics"):
    run(f"GRANT SELECT ON TABLE {FQ(obj)} TO `{GRANTEE}`")

print("\nGrants on the gold layer:")
spark.sql(f"SHOW GRANTS ON TABLE {FQ('gold_member_360')}").show(truncate=False)
print("Tags on gold_member_360 columns flagged PII:")
spark.sql(f"""SELECT column_name, tag_name, tag_value FROM {C}.information_schema.column_tags
             WHERE schema_name = '{S}' AND table_name = 'gold_member_360' ORDER BY column_name, tag_name""").show(truncate=False)
spark.sql(f"""SELECT table_name, tag_name, tag_value FROM {C}.information_schema.table_tags
             WHERE schema_name = '{S}' ORDER BY table_name, tag_name""").show(60, truncate=False)
```

Output:

```text
GRANT USE CATALOG ON CATALOG loyalty_lapse_demo_catalog TO `account users`
GRANT USE SCHEMA ON SCHEMA loyalty_lapse_demo_catalog.loyalty TO `account users`
GRANT SELECT ON TABLE loyalty_lapse_demo_catalog.loyalty.gold_member_360 TO `account users`
GRANT SELECT ON TABLE loyalty_lapse_demo_catalog.loyalty.gold_member_activity_monthly TO `account users`
GRANT SELECT ON TABLE loyalty_lapse_demo_catalog.loyalty.member_retention_scores TO `account users`
GRANT SELECT ON TABLE loyalty_lapse_demo_catalog.loyalty.loyalty_member_metrics TO `account users`
GRANT SELECT ON TABLE loyalty_lapse_demo_catalog.loyalty.loyalty_activity_metrics TO `account users`
GRANT SELECT ON TABLE loyalty_lapse_demo_catalog.loyalty.retention_risk_metrics TO `account users`

Grants on the gold layer:
+------------------------------------+--------------+----------+--------------------------------------------------+
|Principal                           |ActionType    |ObjectType|ObjectKey                                         |
+------------------------------------+--------------+----------+--------------------------------------------------+
|account users                       |SELECT        |TABLE     |loyalty_lapse_demo_catalog.loyalty.gold_member_360|
|account users                       |READ METADATA |METASTORE |metastore_aws_us_west_2                           |
|aec5be3d-de3c-404c-8e60-feed0f265fd3|ALL PRIVILEGES|CATALOG   |loyalty_lapse_demo_catalog                        |
|aec5be3d-de3c-404c-8e60-feed0f265fd3|MANAGE        |CATALOG   |loyalty_lapse_demo_catalog                        |
|orrin.edenfield@databricks.com      |ALL PRIVILEGES|CATALOG   |loyalty_lapse_demo_catalog                        |
|orrin.edenfield@databricks.com      |MANAGE        |CATALOG   |loyalty_lapse_demo_catalog                        |
+------------------------------------+--------------+----------+--------------------------------------------------+

Tags on gold_member_360 columns flagged PII:
+-----------+------------+-----------------+
|column_name|tag_name    |tag_value        |
+-----------+------------+-----------------+
|email      |lp_pii      |true             |
|email      |lp_pii_class|direct_identifier|
|first_name |lp_pii      |true             |
|first_name |lp_pii_class|direct_identifier|
|last_name  |lp_pii      |true             |
|last_name  |lp_pii_class|direct_identifier|
+-----------+------------+-----------------+

+----------------------------+---------------+-------------------+
|table_name                  |tag_name       |tag_value          |
+----------------------------+---------------+-------------------+
|gold_member_360             |business_area  |loyalty            |
|gold_member_360             |lp_certified   |true               |
|gold_member_360             |lp_layer       |gold               |
|gold_member_360             |lp_owner_team  |crm_analytics      |
|gold_member_activity_monthly|business_area  |loyalty            |
|gold_member_activity_monthly|lp_certified   |true               |
|gold_member_activity_monthly|lp_layer       |gold               |
|gold_member_activity_monthly|lp_owner_team  |crm_analytics      |
|loyalty_activity_metrics    |business_area  |loyalty            |
|loyalty_activity_metrics    |lp_certified   |true               |
|loyalty_activity_metrics    |lp_layer       |metrics            |
|loyalty_member_metrics      |business_area  |loyalty            |
|loyalty_member_metrics      |lp_certified   |true               |
|loyalty_member_metrics      |lp_layer       |metrics            |
|member_retention_scores     |business_area  |loyalty            |
|member_retention_scores     |lp_certified   |true               |
|member_retention_scores     |lp_layer       |gold               |
|member_retention_scores     |lp_owner_team  |data_science       |
|member_retention_scores     |model          |loyalty_lapse_model|
|retention_risk_metrics      |business_area  |loyalty            |
|retention_risk_metrics      |lp_certified   |true               |
|retention_risk_metrics      |lp_layer       |metrics            |
|silver_campaign_touches     |business_area  |loyalty            |
|silver_campaign_touches     |lp_certified   |false              |
|silver_campaign_touches     |lp_layer       |silver             |
|silver_engagement_events    |business_area  |loyalty            |
|silver_engagement_events    |lp_certified   |false              |
|silver_engagement_events    |lp_layer       |silver             |
|silver_members              |business_area  |loyalty            |
|silver_members              |lp_certified   |false              |
|silver_members              |lp_contains_pii|true               |
|silver_members              |lp_layer       |silver             |
|silver_returns              |business_area  |loyalty            |
|silver_returns              |lp_certified   |false              |
|silver_returns              |lp_layer       |silver             |
|silver_transactions         |business_area  |loyalty            |
|silver_transactions         |lp_certified   |false              |
|silver_transactions         |lp_layer       |silver             |
+----------------------------+---------------+-------------------+
```
