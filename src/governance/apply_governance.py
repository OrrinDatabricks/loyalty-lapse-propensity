# Databricks notebook source
# MAGIC %md
# MAGIC # 04 Unity Catalog governance: comments, tags, certified tables, metric views, grants
# MAGIC
# MAGIC Note: this metastore has a tag policy on the key `domain` (finance, sales, supply_chain, quality, hr, operations), so the build uses `business_area` for the loyalty data product. The policy rejected the first attempt, which is the behavior you want from governed tags.
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

# MAGIC %md ## Descriptions on every object: catalog, schemas, volume, every table, every column
# MAGIC One glossary, applied to every table in both schemas, so bronze, silver, gold, feature sets, scores and the generator truth table all carry
# MAGIC column descriptions. Pipeline-managed tables (streaming tables, materialized views) accept COMMENT ON COLUMN too; the weekly job re-applies this.

# COMMAND ----------

OBJECT_COMMENTS = {
    f"CATALOG {C}": "Loyalty lapse propensity prototype for a specialty apparel retailer. Synthetic data only. Schemas: loyalty (the data product), loyalty_gen (generator ground truth, never read downstream).",
    f"SCHEMA {C}.{S}": "Loyalty data product: raw volume, Lakeflow bronze/silver/gold, ML feature sets and scores, governed metric views. Owner: CRM analytics with data science.",
    f"SCHEMA {C}.{S}_gen": "Synthetic data generator internals: the hidden member profile (cohort flag, planted lapse dates) used to create the raw extracts. Not an input to the pipeline, the model or Genie; kept only to prove the planted signal.",
    f"VOLUME {C}.{S}.raw": "Raw source extracts as delivered by upstream systems: members, stores, products, campaign_touches, returns (CSV); transactions, engagement_events (JSON lines). Auto Loader reads these into bronze.",
    f"TABLE {FQ('ml_training_set')}": "Model training set: point-in-time features for regular shoppers as of 2026-04-30 and 2026-06-30 with the 90-day lapse label from the following window. Built by src/ml/train_lapse_model.py.",
    f"TABLE {FQ('ml_holdout_set')}": "Temporal hold-out for the lapse model: features as of 2026-07-31, labels from Aug 1 to Oct 29 2026. Never used for training; the reported AUC, lift and calibration come from this table.",
    f"TABLE {FQ('ml_scoring_features')}": "Features for the latest scoring run, as of the latest transaction date, for regular shoppers (3+ purchases in 180 days). Input to member_retention_scores.",
    f"TABLE {C}.{S}_gen.member_truth": "Generator ground truth per synthetic member: hidden denim affinity, cohort flag, planted lapse date and disengagement lead. Used only by the generator and the story-check cell; excluded from the model and Genie.",
}
for obj, text in OBJECT_COMMENTS.items():
    run(f"COMMENT ON {obj} IS '{text.replace(chr(39), chr(39)*2)}'")
for r in spark.sql(f"SELECT table_name FROM {C}.information_schema.tables WHERE table_schema = '{S}' AND table_name LIKE 'event\\_log%'").collect():
    try:
        run(f"COMMENT ON TABLE {C}.{S}.{r.table_name} IS 'Lakeflow pipeline event log (system-managed): flow progress, expectation pass/fail counts, update state. Queried in evidence/02_pipeline_tables.md.'")
    except Exception as e:  # event logs are pipeline-owned; some runtimes refuse metadata changes on them
        print(f"  skipped {r.table_name}: {str(e)[:120]}")

GLOSSARY = {
    # keys and identifiers
    "member_id": "Loyalty member identifier (M + 7 digits).", "id": "Generator row index.", "store_id": "Store identifier (S + 4 digits); S0000 is the online store.",
    "home_store_id": "Store where the member shops most; S0000 is the online store.", "product_id": "Product identifier (P + 5 digits).",
    "txn_id": "Transaction identifier (T + 10 digits).", "event_id": "Engagement event identifier.", "touch_id": "Campaign touch identifier.", "return_id": "Return identifier.",
    # member attributes
    "first_name": "Member first name. PII.", "last_name": "Member last name. PII.", "email": "Member email address. PII; masked in gold for non-admins.",
    "tier": "Loyalty tier: Bronze, Silver or Gold.", "join_date": "Date the member enrolled in the loyalty program.",
    "preferred_channel": "Marketing channel the member opted into: app, email, sms or none.", "birthday_month": "Calendar month (1-12) of the member's birthday reward.",
    "home_store_format": "Format of the member's home store: online, mall, strip or outlet.", "home_region": "Region of the member's home store.",
    "tenure_days": "Days since enrollment as of the snapshot date.",
    # stores and products
    "store_name": "Store display name (city plus format).", "store_format": "Store format: online, mall, strip or outlet.", "region": "Sales region: West, Southwest, Midwest, Southeast, Northeast.",
    "city": "Store city.", "state": "Store state abbreviation.", "opened_date": "Store opening date.",
    "category": "Product category: Denim, Tops, Dresses, Outerwear, Accessories, Kids.", "product_line": "Product line within the category (e.g. Core Denim).",
    "price_band": "List-price band: value, core or premium.", "list_price": "List price in USD.",
    # transactions
    "txn_ts": "Transaction timestamp.", "txn_date": "Transaction date.", "channel": "Purchase channel: store or online.", "primary_category": "Category of the largest line in the basket.",
    "units": "Units in the basket.", "basket_amount": "Net basket value in USD after discount.", "discount_pct": "Discount percent applied to the basket (0 to 90).",
    # engagement
    "event_ts": "Engagement event timestamp.", "event_date": "Engagement event date.", "event_type": "Engagement type: app_open, email_open, email_click or web_session.", "device": "Device: ios, android or web.",
    # campaigns
    "campaign_type": "Campaign type: birthday_reward, win_back, new_arrival or denim_launch.", "touch_ts": "Campaign touch timestamp.", "touch_date": "Campaign touch date.",
    "reward_value": "USD value of the reward offered with the touch (0 when none).", "responded": "TRUE when the member responded within the attribution window.",
    # returns
    "return_ts": "Return timestamp.", "return_date": "Return date.", "return_reason": "Return reason code: fit, size, changed_mind, defective or other.", "refund_amount": "Refund value in USD.",
    # ingestion metadata
    "source_file": "Path of the raw file the row was loaded from (Auto Loader metadata).", "ingested_at": "Timestamp the row was ingested into bronze.",
    "_rescued_data": "Auto Loader rescue column: raw data that did not match the inferred schema, kept for audit.",
    # point-in-time features and scores
    "as_of_date": "Snapshot date the features were computed from; all recency and window metrics are measured back from this date.",
    "first_purchase_date": "Date of the member's first purchase.", "last_purchase_date": "Date of the member's most recent purchase on or before as_of_date.",
    "days_since_last_purchase": "Days between as_of_date and the last purchase.", "lifetime_transactions": "Total transactions on or before as_of_date.", "lifetime_spend": "Total net spend in USD on or before as_of_date.",
    "spend_12m": "Net spend in USD in the 365 days before as_of_date.", "transactions_12m": "Transactions in the 365 days before as_of_date.",
    "spend_180d": "Net spend in USD in the 180 days before as_of_date.", "transactions_180d": "Transactions in the 180 days before as_of_date (3 or more qualifies as a regular shopper).",
    "spend_90d": "Net spend in USD in the 90 days before as_of_date.", "transactions_90d": "Transactions in the 90 days before as_of_date.",
    "denim_share": "Share (0-1) of spend in the Denim category.", "avg_basket": "Average basket value in USD.", "avg_discount_pct": "Average discount percent across baskets.", "online_share": "Share (0-1) of transactions placed online.",
    "events_30d": "Engagement events in the 30 days before as_of_date.", "events_90d": "Engagement events in the 90 days before as_of_date.", "events_180d": "Engagement events in the 180 days before as_of_date.",
    "last_engagement_date": "Most recent engagement event date.", "days_since_last_engagement": "Days since the last engagement event (999 when none).",
    "engagement_velocity": "Events in the last 30 days divided by the average 30-day rate over the prior 150 days; below 1 means the member is going quiet.",
    "returns_90d": "Returns in the 90 days before as_of_date.", "fit_returns_90d": "Returns coded fit or size in the 90 days before as_of_date.", "refunds_180d": "Refund value in USD in the 180 days before as_of_date.",
    "touches_180d": "Campaign touches in the 180 days before as_of_date.", "responses_180d": "Campaign touches responded to in the 180 days before as_of_date.",
    "last_birthday_reward_value": "USD value of the most recent birthday reward offered.", "last_win_back_date": "Date of the most recent win-back touch.",
    "birthday_in_last_90d": "1 when a birthday reward was offered in the 90 days before as_of_date, else 0.",
    "lapsed": "Label: 1 when the member made no purchase in the 90 days after as_of_date.", "lapsed_90d": "TRUE when the member has not purchased in the 90 days before as_of_date.",
    "p_lapse": "Model probability (0-1) of no purchase in the next 90 days.", "risk_band": "High (p_lapse >= 0.60), Medium (0.35 to 0.60) or Low.",
    "primary_driver": "Main plain-language risk driver.", "risk_drivers": "All risk drivers that apply.", "recommended_action": "Retention action the console proposes.",
    "annual_value_at_risk": "spend_12m multiplied by p_lapse, in USD.", "scored_at": "Timestamp of the scoring run.",
    # member-month activity (gold_member_activity_monthly)
    "activity_month": "First day of the calendar month of activity.", "transactions": "Transactions in the month.", "spend": "Net spend in USD in the month.",
    "denim_spend": "Net spend in USD on Denim in the month.", "engagement_events": "App, web and email events in the month.", "app_opens": "App open events in the month.",
    "email_interactions": "Email opens plus clicks in the month.", "campaign_touches": "Campaign touches received in the month.", "campaign_responses": "Campaign touches responded to in the month.",
    "reward_value_offered": "Total USD reward value offered in the month.", "returns": "Returns in the month.", "refunds": "Refund value in USD in the month.", "fit_returns": "Returns coded fit or size in the month.",
    # generator truth
    "denim_affinity": "Hidden generator propensity (0-1) to buy denim; drives category mix and cohort membership.", "in_cohort": "Generator flag: Gold/Silver mall-store member with high denim affinity, the segment hit by the planted lapse wave.",
    "lapse_date": "Generator-planted date after which the member stops buying (NULL when the member does not lapse).", "quiet_lead_days": "Generator lead time (30-60 days) by which engagement goes quiet before lapse_date.",
}

tables = [(r.database if hasattr(r, "database") else r.namespace, r.tableName) for sch in (S, f"{S}_gen")
          for r in spark.sql(f"SHOW TABLES IN {C}.{sch}").collect()]
metric_views = {r.table_name for r in spark.sql(f"SELECT table_name FROM {C}.information_schema.tables WHERE table_schema = '{S}' AND table_type = 'METRIC_VIEW'").collect()}
undocumented, documented = [], 0
for sch, tbl in tables:
    if tbl.startswith("__") or tbl.startswith("event_log") or tbl in metric_views:
        continue
    for col in spark.sql(f"DESCRIBE TABLE {C}.{sch}.{tbl}").collect():
        name = col.col_name
        if not name or name.startswith("#"):
            break
        if name in GLOSSARY:
            spark.sql(f"COMMENT ON COLUMN {C}.{sch}.{tbl}.`{name}` IS '{GLOSSARY[name].replace(chr(39), chr(39)*2)}'")
            documented += 1
        else:
            undocumented.append(f"{sch}.{tbl}.{name}")
print(f"{documented} columns described across {len(tables)} tables; not in glossary: {undocumented or 'none'}")

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
    comment: "Loyalty tier: Bronze, Silver or Gold."
    expr: tier
    synonyms: ["loyalty tier", "membership level"]
  - name: Home Store Format
    comment: "Format of the member's home store: online, mall, strip or outlet."
    expr: home_store_format
    synonyms: ["store format", "store type", "channel of home store"]
  - name: Home Region
    comment: "Region of the member's home store."
    expr: home_region
    synonyms: ["region"]
  - name: Preferred Channel
    comment: "Marketing channel the member opted into."
    expr: preferred_channel
    synonyms: ["marketing channel", "opt-in channel"]
  - name: Lapsed
    comment: "TRUE when the member has not purchased in the last 90 days."
    expr: lapsed_90d
    synonyms: ["churned", "inactive", "lapsed member"]
  - name: Recency Bucket
    comment: "Days since last purchase grouped into 0-30, 31-60, 61-90 and 90+ (lapsed)."
    expr: "CASE WHEN days_since_last_purchase <= 30 THEN '0-30 days' WHEN days_since_last_purchase <= 60 THEN '31-60 days' WHEN days_since_last_purchase <= 90 THEN '61-90 days' ELSE '90+ days (lapsed)' END"
    synonyms: ["recency", "days since last purchase bucket"]
  - name: Join Year
    comment: "Year the member enrolled."
    expr: "YEAR(join_date)"
measures:
  - name: Members
    comment: "Count of loyalty members."
    expr: COUNT(member_id)
    synonyms: ["member count", "number of members"]
    format:
      type: number
      decimal_places: {{type: exact, places: 0}}
  - name: Lapsed Members
    comment: "Members with no purchase in the last 90 days."
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
    comment: "Trailing-12-month net spend in USD."
    expr: SUM(spend_12m)
    synonyms: ["trailing twelve month spend", "annual spend", "revenue"]
    format:
      type: currency
      currency_code: USD
      decimal_places: {{type: exact, places: 0}}
  - name: Avg Spend 12M per Member
    comment: "Average trailing-12-month spend per member in USD."
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
    comment: "Average app, web and email events per member in the last 30 days."
    expr: AVG(events_30d)
  - name: Fit Return Members 90D
    comment: "Members with at least one fit or size return in the last 90 days."
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
    comment: "First day of the calendar month of activity."
    expr: activity_month
    synonyms: ["month"]
    format:
      type: date
      date_format: locale_short_month
measures:
  - name: Active Buyers
    comment: "Members with at least one transaction in the month."
    expr: COUNT(member_id) FILTER (WHERE transactions > 0)
    synonyms: ["buying members", "purchasers"]
  - name: Engaged Members
    comment: "Members with at least one engagement event in the month."
    expr: COUNT(member_id) FILTER (WHERE engagement_events > 0)
  - name: Transactions
    comment: "Transactions in the month."
    expr: SUM(transactions)
  - name: Spend
    comment: "Net spend in USD in the month."
    expr: SUM(spend)
    synonyms: ["revenue", "sales"]
    format:
      type: currency
      currency_code: USD
      decimal_places: {{type: exact, places: 0}}
  - name: Denim Spend
    comment: "Net spend in USD on Denim in the month."
    expr: SUM(denim_spend)
    format:
      type: currency
      currency_code: USD
      decimal_places: {{type: exact, places: 0}}
  - name: Engagement Events
    comment: "App, web and email events in the month."
    expr: SUM(engagement_events)
  - name: Returns
    comment: "Returns in the month."
    expr: SUM(returns)
  - name: Fit Returns
    comment: "Returns coded fit or size in the month."
    expr: SUM(fit_returns)
    synonyms: ["fit and size returns"]
  - name: Fit Return Share
    comment: "Fit and size returns as a share of all returns."
    expr: "SUM(fit_returns) / NULLIF(SUM(returns), 0)"
    format:
      type: percentage
      decimal_places: {{type: exact, places: 1}}
  - name: Campaign Touches
    comment: "Campaign touches in the month."
    expr: SUM(campaign_touches)
  - name: Campaign Response Rate
    comment: "Responses divided by touches."
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
    comment: "High (p_lapse >= 0.60), Medium (0.35 to 0.60) or Low."
    expr: risk_band
    synonyms: ["risk level", "risk tier"]
  - name: Primary Driver
    comment: "Main plain-language risk driver for the member."
    expr: primary_driver
    synonyms: ["risk reason", "why at risk", "driver"]
  - name: Recommended Action
    comment: "Retention action the console proposes."
    expr: recommended_action
    synonyms: ["next best action", "treatment"]
  - name: Tier
    comment: "Loyalty tier: Bronze, Silver or Gold."
    expr: tier
  - name: Home Store Format
    comment: "Format of the member's home store: online, mall, strip or outlet."
    expr: home_store_format
  - name: Home Region
    comment: "Region of the member's home store."
    expr: home_region
  - name: Preferred Channel
    comment: "Marketing channel the member opted into."
    expr: preferred_channel
measures:
  - name: Scored Members
    comment: "Regular shoppers scored by the lapse model."
    expr: COUNT(member_id)
  - name: High Risk Members
    comment: "Scored members with p_lapse >= 0.60."
    expr: COUNT(member_id) FILTER (WHERE risk_band = 'High')
    synonyms: ["members at high risk", "high risk count"]
  - name: Avg Lapse Probability
    comment: "Mean model probability of lapse."
    expr: AVG(p_lapse)
    format:
      type: percentage
      decimal_places: {{type: exact, places: 1}}
  - name: Revenue at Risk
    comment: "Sum of trailing-12-month spend multiplied by lapse probability, in USD."
    expr: SUM(annual_value_at_risk)
    synonyms: ["value at risk", "spend at risk", "dollars at risk"]
    format:
      type: currency
      currency_code: USD
      decimal_places: {{type: exact, places: 0}}
  - name: Spend 12M
    comment: "Trailing-12-month net spend in USD."
    expr: SUM(spend_12m)
    format:
      type: currency
      currency_code: USD
      decimal_places: {{type: exact, places: 0}}
$$
""")

for mv in ("loyalty_member_metrics", "loyalty_activity_metrics", "retention_risk_metrics"):
    run(f"ALTER VIEW {FQ(mv)} SET TAGS ('business_area' = 'loyalty', 'lp_layer' = 'metrics', 'lp_certified' = 'true')")

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

# MAGIC %md ## Describe the registered model

# COMMAND ----------

import mlflow
from mlflow import MlflowClient
mlflow.set_registry_uri("databricks-uc")
mc = MlflowClient()
MODEL = FQ("loyalty_lapse_model")
mc.update_registered_model(MODEL, "Loyalty lapse propensity: probability that a regular shopper (3+ purchases in 180 days) makes no purchase in the next 90 days. HistGradientBoosting on point-in-time features from silver; trained on two snapshots, evaluated on a later hold-out. Output feeds member_retention_scores and the Lakebase worklist. See MODEL.md in the repo.")
champ = mc.get_model_version_by_alias(MODEL, "champion")
mc.update_model_version(MODEL, champ.version, f"Champion version {champ.version}. Weekly retrain; predict_proba exposed via pyfunc. Hold-out metrics are logged on the MLflow run and summarized in evidence/03a_train_lapse_model.md.")
print(f"described {MODEL} and champion version {champ.version}")

# COMMAND ----------

# MAGIC %md ## Verify: nothing left undocumented

# COMMAND ----------

print("Tables without a comment (internal and event-log tables excluded):")
spark.sql(f"""SELECT table_schema, table_name, table_type FROM {C}.information_schema.tables
             WHERE table_schema IN ('{S}', '{S}_gen') AND table_name NOT LIKE '\\\\_\\\\_%' AND table_name NOT LIKE 'event\\\\_log%'
               AND (comment IS NULL OR comment = '') ORDER BY 1, 2""").show(50, False)
print("Columns without a comment, by table (internal and event-log tables excluded):")
spark.sql(f"""SELECT table_name, COUNT(*) AS columns, SUM(CASE WHEN comment IS NULL OR comment = '' THEN 1 ELSE 0 END) AS missing
             FROM {C}.information_schema.columns
             WHERE table_schema IN ('{S}', '{S}_gen') AND table_name NOT LIKE '\\\\_\\\\_%' AND table_name NOT LIKE 'event\\\\_log%'
             GROUP BY table_name ORDER BY missing DESC, table_name""").show(50, False)
print("Catalog, schema and volume comments:")
spark.sql(f"SELECT 'catalog' AS object, catalog_name AS name, comment FROM {C}.information_schema.catalogs").show(truncate=80)
spark.sql(f"SELECT 'schema' AS object, schema_name AS name, comment FROM {C}.information_schema.schemata WHERE schema_name IN ('{S}', '{S}_gen')").show(truncate=80)
spark.sql(f"SELECT 'volume' AS object, volume_name AS name, comment FROM {C}.information_schema.volumes WHERE volume_schema = '{S}'").show(truncate=80)

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
