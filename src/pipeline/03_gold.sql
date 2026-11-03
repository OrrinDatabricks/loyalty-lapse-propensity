-- Gold: business-ready, one row per member (360) and one row per member-month (trend).
-- These two tables feed the model features, the Genie Agent and the metric views.

CREATE OR REFRESH MATERIALIZED VIEW gold_member_activity_monthly
CLUSTER BY (activity_month)
COMMENT 'Member x month activity: transactions, spend, denim spend, engagement events, campaign touches, returns. Grain = member_id + activity_month.'
AS
WITH months AS (
  SELECT member_id, date_trunc('month', txn_date) AS activity_month FROM silver_transactions
  UNION SELECT member_id, date_trunc('month', event_date) FROM silver_engagement_events
  UNION SELECT member_id, date_trunc('month', touch_date) FROM silver_campaign_touches
),
t AS (
  SELECT member_id, date_trunc('month', txn_date) AS activity_month,
         COUNT(*) AS transactions, SUM(basket_amount) AS spend, SUM(units) AS units,
         SUM(CASE WHEN primary_category = 'Denim' THEN basket_amount ELSE 0 END) AS denim_spend
  FROM silver_transactions GROUP BY 1, 2
),
e AS (
  SELECT member_id, date_trunc('month', event_date) AS activity_month,
         COUNT(*) AS engagement_events,
         SUM(CASE WHEN event_type = 'app_open' THEN 1 ELSE 0 END) AS app_opens,
         SUM(CASE WHEN event_type IN ('email_open', 'email_click') THEN 1 ELSE 0 END) AS email_interactions
  FROM silver_engagement_events GROUP BY 1, 2
),
c AS (
  SELECT member_id, date_trunc('month', touch_date) AS activity_month,
         COUNT(*) AS campaign_touches, SUM(CASE WHEN responded THEN 1 ELSE 0 END) AS campaign_responses,
         SUM(reward_value) AS reward_value_offered
  FROM silver_campaign_touches GROUP BY 1, 2
),
r AS (
  SELECT member_id, date_trunc('month', return_date) AS activity_month,
         COUNT(*) AS returns, SUM(refund_amount) AS refunds,
         SUM(CASE WHEN return_reason IN ('fit', 'size') THEN 1 ELSE 0 END) AS fit_returns
  FROM silver_returns GROUP BY 1, 2
)
SELECT
  m.member_id, CAST(m.activity_month AS DATE) AS activity_month,
  COALESCE(t.transactions, 0) AS transactions, COALESCE(t.spend, 0) AS spend, COALESCE(t.units, 0) AS units,
  COALESCE(t.denim_spend, 0) AS denim_spend,
  COALESCE(e.engagement_events, 0) AS engagement_events, COALESCE(e.app_opens, 0) AS app_opens,
  COALESCE(e.email_interactions, 0) AS email_interactions,
  COALESCE(c.campaign_touches, 0) AS campaign_touches, COALESCE(c.campaign_responses, 0) AS campaign_responses,
  COALESCE(c.reward_value_offered, 0) AS reward_value_offered,
  COALESCE(r.returns, 0) AS returns, COALESCE(r.refunds, 0) AS refunds, COALESCE(r.fit_returns, 0) AS fit_returns
FROM months m
LEFT JOIN t USING (member_id, activity_month)
LEFT JOIN e USING (member_id, activity_month)
LEFT JOIN c USING (member_id, activity_month)
LEFT JOIN r USING (member_id, activity_month);

CREATE OR REFRESH MATERIALIZED VIEW gold_member_360
COMMENT 'One row per loyalty member with profile, recency/frequency/monetary, engagement, returns and campaign behavior as of the latest data. lapsed_90d = no purchase in the last 90 days. Email masked for non-admins.'
AS
WITH as_of AS (SELECT MAX(txn_date) AS as_of_date FROM silver_transactions),
txn AS (
  SELECT t.member_id,
         MAX(t.txn_date) AS last_purchase_date,
         MIN(t.txn_date) AS first_purchase_date,
         COUNT(*) AS lifetime_transactions,
         SUM(t.basket_amount) AS lifetime_spend,
         SUM(CASE WHEN t.txn_date > a.as_of_date - INTERVAL 365 DAYS THEN t.basket_amount ELSE 0 END) AS spend_12m,
         SUM(CASE WHEN t.txn_date > a.as_of_date - INTERVAL 365 DAYS THEN 1 ELSE 0 END) AS transactions_12m,
         SUM(CASE WHEN t.txn_date > a.as_of_date - INTERVAL 90 DAYS THEN t.basket_amount ELSE 0 END) AS spend_90d,
         SUM(CASE WHEN t.txn_date > a.as_of_date - INTERVAL 90 DAYS THEN 1 ELSE 0 END) AS transactions_90d,
         SUM(CASE WHEN t.primary_category = 'Denim' THEN t.basket_amount ELSE 0 END) / NULLIF(SUM(t.basket_amount), 0) AS denim_share,
         AVG(t.basket_amount) AS avg_basket,
         AVG(t.discount_pct) AS avg_discount_pct,
         SUM(CASE WHEN t.channel = 'online' THEN 1 ELSE 0 END) / COUNT(*) AS online_share
  FROM silver_transactions t CROSS JOIN as_of a
  GROUP BY t.member_id
),
eng AS (
  SELECT e.member_id,
         SUM(CASE WHEN e.event_date > a.as_of_date - INTERVAL 30 DAYS THEN 1 ELSE 0 END) AS events_30d,
         SUM(CASE WHEN e.event_date > a.as_of_date - INTERVAL 90 DAYS THEN 1 ELSE 0 END) AS events_90d,
         SUM(CASE WHEN e.event_date > a.as_of_date - INTERVAL 180 DAYS THEN 1 ELSE 0 END) AS events_180d,
         MAX(e.event_date) AS last_engagement_date
  FROM silver_engagement_events e CROSS JOIN as_of a
  GROUP BY e.member_id
),
ret AS (
  SELECT r.member_id,
         SUM(CASE WHEN r.return_date > a.as_of_date - INTERVAL 90 DAYS THEN 1 ELSE 0 END) AS returns_90d,
         SUM(CASE WHEN r.return_date > a.as_of_date - INTERVAL 90 DAYS AND r.return_reason IN ('fit', 'size') THEN 1 ELSE 0 END) AS fit_returns_90d,
         SUM(CASE WHEN r.return_date > a.as_of_date - INTERVAL 180 DAYS THEN r.refund_amount ELSE 0 END) AS refunds_180d
  FROM silver_returns r CROSS JOIN as_of a
  GROUP BY r.member_id
),
cmp AS (
  SELECT c.member_id,
         SUM(CASE WHEN c.touch_date > a.as_of_date - INTERVAL 180 DAYS THEN 1 ELSE 0 END) AS touches_180d,
         SUM(CASE WHEN c.touch_date > a.as_of_date - INTERVAL 180 DAYS AND c.responded THEN 1 ELSE 0 END) AS responses_180d,
         MAX(CASE WHEN c.campaign_type = 'birthday_reward' THEN c.reward_value END) AS last_birthday_reward_value,
         MAX(CASE WHEN c.campaign_type = 'win_back' THEN c.touch_date END) AS last_win_back_date
  FROM silver_campaign_touches c CROSS JOIN as_of a
  GROUP BY c.member_id
)
SELECT
  m.member_id, m.first_name, m.last_name,
  CASE WHEN is_account_group_member('admins') THEN m.email ELSE regexp_replace(m.email, '^[^@]+', '***') END AS email,
  m.tier, m.join_date, DATEDIFF(a.as_of_date, m.join_date) AS tenure_days,
  m.home_store_id, m.home_store_format, m.home_region, m.preferred_channel, m.birthday_month,
  a.as_of_date,
  txn.first_purchase_date, txn.last_purchase_date,
  DATEDIFF(a.as_of_date, txn.last_purchase_date) AS days_since_last_purchase,
  COALESCE(txn.lifetime_transactions, 0) AS lifetime_transactions,
  COALESCE(txn.lifetime_spend, 0) AS lifetime_spend,
  COALESCE(txn.spend_12m, 0) AS spend_12m, COALESCE(txn.transactions_12m, 0) AS transactions_12m,
  COALESCE(txn.spend_90d, 0) AS spend_90d, COALESCE(txn.transactions_90d, 0) AS transactions_90d,
  COALESCE(txn.denim_share, 0) AS denim_share, COALESCE(txn.avg_basket, 0) AS avg_basket,
  COALESCE(txn.avg_discount_pct, 0) AS avg_discount_pct, COALESCE(txn.online_share, 0) AS online_share,
  COALESCE(eng.events_30d, 0) AS events_30d, COALESCE(eng.events_90d, 0) AS events_90d,
  COALESCE(eng.events_180d, 0) AS events_180d, eng.last_engagement_date,
  DATEDIFF(a.as_of_date, eng.last_engagement_date) AS days_since_last_engagement,
  COALESCE(ret.returns_90d, 0) AS returns_90d, COALESCE(ret.fit_returns_90d, 0) AS fit_returns_90d,
  COALESCE(ret.refunds_180d, 0) AS refunds_180d,
  COALESCE(cmp.touches_180d, 0) AS touches_180d, COALESCE(cmp.responses_180d, 0) AS responses_180d,
  cmp.last_birthday_reward_value, cmp.last_win_back_date,
  (txn.last_purchase_date IS NULL OR DATEDIFF(a.as_of_date, txn.last_purchase_date) > 90) AS lapsed_90d
FROM silver_members m
CROSS JOIN as_of a
LEFT JOIN txn ON m.member_id = txn.member_id
LEFT JOIN eng ON m.member_id = eng.member_id
LEFT JOIN ret ON m.member_id = ret.member_id
LEFT JOIN cmp ON m.member_id = cmp.member_id;
