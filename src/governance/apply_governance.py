# Databricks notebook source
# MAGIC %md
# MAGIC # 04 Unity Catalog governance: comments, tags, certified tables, metric views, grants
# MAGIC
# MAGIC The small UC investments that make agents accurate: every gold column described, tables tagged with
# MAGIC domain and certification, PII flagged, governed metric views so "lapse rate" means one thing everywhere,
# MAGIC and least-privilege grants for the analyst and app principals.

# COMMAND ----------

dbutils.widgets.text("catalog", "loyalty_lapse_demo_catalog")
dbutils.widgets.text("schema", "loyalty")
C, S = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
FQ = lambda t: f"{C}.{S}.{t}"

def run(sql):
    print(sql.strip().splitlines()[0][:110])
    return spark.sql(sql)

# COMMAND ----------

# MAGIC %md ## Column comments on the gold layer (what Genie reads)

# COMMAND ----------

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

# COMMAND ----------

# MAGIC %md ## Tags: domain, certification, PII, layer

# COMMAND ----------

TABLE_TAGS = {
    "gold_member_360":             {"domain": "loyalty", "layer": "gold", "certified": "true", "owner_team": "crm_analytics"},
    "gold_member_activity_monthly": {"domain": "loyalty", "layer": "gold", "certified": "true", "owner_team": "crm_analytics"},
    "member_retention_scores":     {"domain": "loyalty", "layer": "gold", "certified": "true", "owner_team": "data_science", "model": "loyalty_lapse_model"},
    "silver_transactions":         {"domain": "loyalty", "layer": "silver", "certified": "false"},
    "silver_members":              {"domain": "loyalty", "layer": "silver", "certified": "false", "contains_pii": "true"},
    "silver_engagement_events":    {"domain": "loyalty", "layer": "silver", "certified": "false"},
    "silver_campaign_touches":     {"domain": "loyalty", "layer": "silver", "certified": "false"},
    "silver_returns":              {"domain": "loyalty", "layer": "silver", "certified": "false"},
}
for table, tags in TABLE_TAGS.items():
    tag_list = ", ".join(f"'{k}' = '{v}'" for k, v in tags.items())
    run(f"ALTER TABLE {FQ(table)} SET TAGS ({tag_list})")

for col in ("email", "first_name", "last_name"):
    run(f"ALTER TABLE {FQ('gold_member_360')} ALTER COLUMN {col} SET TAGS ('pii' = 'true', 'pii_class' = 'direct_identifier')")
    run(f"ALTER TABLE {FQ('silver_members')} ALTER COLUMN {col} SET TAGS ('pii' = 'true', 'pii_class' = 'direct_identifier')")

run(f"ALTER SCHEMA {C}.{S} SET TAGS ('domain' = 'loyalty', 'data_product' = 'loyalty_lapse_propensity')")

# COMMAND ----------

# MAGIC %md ## Governed metric views
# MAGIC One definition of lapse rate, revenue at risk and campaign response rate, consumed by Genie, dashboards and the app.

# COMMAND ----------

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
    run(f"ALTER VIEW {FQ(mv)} SET TAGS ('domain' = 'loyalty', 'layer' = 'metrics', 'certified' = 'true')")

# COMMAND ----------

# MAGIC %md ## Prove the metric views answer the business questions

# COMMAND ----------

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

# COMMAND ----------

# MAGIC %md ## Least-privilege grants
# MAGIC Analysts get the gold layer and metric views only; silver and bronze stay with engineering.

# COMMAND ----------

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
