-- Silver: typed, deduplicated, quality-checked. Expectations are the governance evidence:
-- violations are recorded in the pipeline event log and bad rows are dropped or fail the update.

CREATE OR REFRESH MATERIALIZED VIEW silver_stores
COMMENT 'Conformed store dimension. store_format is one of online, mall, strip, outlet.'
AS SELECT
  store_id, store_name, store_format, region, city, state, CAST(opened_date AS DATE) AS opened_date
FROM bronze_stores;

CREATE OR REFRESH MATERIALIZED VIEW silver_products
COMMENT 'Conformed product dimension with category, product line and price band.'
AS SELECT product_id, category, product_line, price_band, CAST(list_price AS DECIMAL(10,2)) AS list_price
FROM bronze_products;

CREATE OR REFRESH MATERIALIZED VIEW silver_members (
  CONSTRAINT valid_member_id EXPECT (member_id IS NOT NULL) ON VIOLATION FAIL UPDATE,
  CONSTRAINT valid_tier EXPECT (tier IN ('Bronze', 'Silver', 'Gold')) ON VIOLATION DROP ROW,
  CONSTRAINT known_home_store EXPECT (home_store_format IS NOT NULL) ON VIOLATION DROP ROW
)
COMMENT 'Conformed loyalty member dimension joined to the home store. Email is PII and is masked for non-admins in the gold layer.'
AS SELECT
  m.member_id, m.first_name, m.last_name, m.email, m.tier,
  CAST(m.join_date AS DATE) AS join_date,
  m.home_store_id, s.store_format AS home_store_format, s.region AS home_region,
  m.preferred_channel, CAST(m.birthday_month AS INT) AS birthday_month
FROM bronze_members m
LEFT JOIN silver_stores s ON m.home_store_id = s.store_id;

CREATE OR REFRESH STREAMING TABLE silver_transactions (
  CONSTRAINT valid_txn_id   EXPECT (txn_id IS NOT NULL AND member_id IS NOT NULL) ON VIOLATION FAIL UPDATE,
  CONSTRAINT positive_basket EXPECT (basket_amount > 0) ON VIOLATION DROP ROW,
  CONSTRAINT valid_units    EXPECT (units BETWEEN 1 AND 50) ON VIOLATION DROP ROW,
  CONSTRAINT valid_discount EXPECT (discount_pct BETWEEN 0 AND 90)
)
CLUSTER BY (member_id, txn_date)
COMMENT 'Loyalty-attached transactions, one row per basket. basket_amount is net of discount in USD.'
AS SELECT
  txn_id, member_id, store_id, channel,
  CAST(txn_ts AS TIMESTAMP) AS txn_ts,
  CAST(CAST(txn_ts AS TIMESTAMP) AS DATE) AS txn_date,
  primary_category,
  CAST(units AS INT) AS units,
  CAST(basket_amount AS DECIMAL(10,2)) AS basket_amount,
  CAST(discount_pct AS INT) AS discount_pct
FROM STREAM(bronze_transactions);

CREATE OR REFRESH STREAMING TABLE silver_engagement_events (
  CONSTRAINT valid_event EXPECT (event_id IS NOT NULL AND member_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT known_event_type EXPECT (event_type IN ('app_open', 'email_open', 'email_click', 'web_session')) ON VIOLATION DROP ROW
)
CLUSTER BY (member_id, event_date)
COMMENT 'App, web and email engagement events per member.'
AS SELECT
  event_id, member_id,
  CAST(event_ts AS TIMESTAMP) AS event_ts,
  CAST(CAST(event_ts AS TIMESTAMP) AS DATE) AS event_date,
  event_type, device
FROM STREAM(bronze_engagement_events);

CREATE OR REFRESH STREAMING TABLE silver_campaign_touches (
  CONSTRAINT valid_touch EXPECT (touch_id IS NOT NULL AND member_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT non_negative_reward EXPECT (reward_value >= 0) ON VIOLATION DROP ROW
)
COMMENT 'Campaign touches per member with reward value (USD) and whether the member responded within the attribution window.'
AS SELECT
  touch_id, member_id, campaign_type,
  CAST(touch_ts AS TIMESTAMP) AS touch_ts,
  CAST(CAST(touch_ts AS TIMESTAMP) AS DATE) AS touch_date,
  CAST(reward_value AS DECIMAL(10,2)) AS reward_value,
  CAST(responded AS BOOLEAN) AS responded
FROM STREAM(bronze_campaign_touches);

CREATE OR REFRESH STREAMING TABLE silver_returns (
  CONSTRAINT valid_return EXPECT (return_id IS NOT NULL AND txn_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT positive_refund EXPECT (refund_amount > 0) ON VIOLATION DROP ROW
)
COMMENT 'Returns with reason code. fit and size reasons on Denim are the product-quality signal.'
AS SELECT
  return_id, txn_id, member_id,
  CAST(return_ts AS TIMESTAMP) AS return_ts,
  CAST(CAST(return_ts AS TIMESTAMP) AS DATE) AS return_date,
  primary_category, return_reason,
  CAST(refund_amount AS DECIMAL(10,2)) AS refund_amount
FROM STREAM(bronze_returns);
