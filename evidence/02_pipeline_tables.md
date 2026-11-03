pipeline_id=236703e1-3aca-4498-87b9-52a4aea9d35a (serverless Lakeflow Spark Declarative Pipeline, full refresh after data regeneration)

## Row counts after the update

[
  {
    "n": "1984951",
    "t": "bronze_transactions"
  },
  {
    "n": "400000",
    "t": "gold_member_360"
  },
  {
    "n": "3767948",
    "t": "gold_member_activity_monthly"
  },
  {
    "n": "1246286",
    "t": "silver_campaign_touches"
  },
  {
    "n": "4174998",
    "t": "silver_engagement_events"
  },
  {
    "n": "400000",
    "t": "silver_members"
  },
  {
    "n": "166342",
    "t": "silver_returns"
  },
  {
    "n": "1984951",
    "t": "silver_transactions"
  }
]

## Expectation results from the pipeline event log (latest update)

[
  {
    "expectation": "non_negative_reward",
    "failed_records": "0",
    "flow_name": "loyalty_lapse_demo_catalog.loyalty.silver_campaign_touches",
    "passed_records": "1246286"
  },
  {
    "expectation": "valid_touch",
    "failed_records": "0",
    "flow_name": "loyalty_lapse_demo_catalog.loyalty.silver_campaign_touches",
    "passed_records": "1246286"
  },
  {
    "expectation": "known_event_type",
    "failed_records": "0",
    "flow_name": "loyalty_lapse_demo_catalog.loyalty.silver_engagement_events",
    "passed_records": "4174998"
  },
  {
    "expectation": "valid_event",
    "failed_records": "0",
    "flow_name": "loyalty_lapse_demo_catalog.loyalty.silver_engagement_events",
    "passed_records": "4174998"
  },
  {
    "expectation": "known_home_store",
    "failed_records": "0",
    "flow_name": "loyalty_lapse_demo_catalog.loyalty.silver_members",
    "passed_records": "400000"
  },
  {
    "expectation": "valid_member_id",
    "failed_records": "0",
    "flow_name": "loyalty_lapse_demo_catalog.loyalty.silver_members",
    "passed_records": "400000"
  },
  {
    "expectation": "valid_tier",
    "failed_records": "0",
    "flow_name": "loyalty_lapse_demo_catalog.loyalty.silver_members",
    "passed_records": "400000"
  },
  {
    "expectation": "positive_refund",
    "failed_records": "0",
    "flow_name": "loyalty_lapse_demo_catalog.loyalty.silver_returns",
    "passed_records": "166342"
  },
  {
    "expectation": "valid_return",
    "failed_records": "0",
    "flow_name": "loyalty_lapse_demo_catalog.loyalty.silver_returns",
    "passed_records": "166342"
  },
  {
    "expectation": "positive_basket",
    "failed_records": "0",
    "flow_name": "loyalty_lapse_demo_catalog.loyalty.silver_transactions",
    "passed_records": "1984951"
  },
  {
    "expectation": "valid_discount",
    "failed_records": "0",
    "flow_name": "loyalty_lapse_demo_catalog.loyalty.silver_transactions",
    "passed_records": "1984951"
  },
  {
    "expectation": "valid_txn_id",
    "failed_records": "0",
    "flow_name": "loyalty_lapse_demo_catalog.loyalty.silver_transactions",
    "passed_records": "1984951"
  },
  {
    "expectation": "valid_units",
    "failed_records": "0",
    "flow_name": "loyalty_lapse_demo_catalog.loyalty.silver_transactions",
    "passed_records": "1984951"
  }
]

## gold_member_360 sanity: lapse rate and lapsed spend by tier and home store format

[
  {
    "home_store_format": "online",
    "lapse_rate": "0.567",
    "lapsed_spend_12m": "2002419",
    "members": "42077",
    "tier": "Bronze"
  },
  {
    "home_store_format": "outlet",
    "lapse_rate": "0.565",
    "lapsed_spend_12m": "2609137",
    "members": "55060",
    "tier": "Bronze"
  },
  {
    "home_store_format": "mall",
    "lapse_rate": "0.562",
    "lapsed_spend_12m": "5383999",
    "members": "114755",
    "tier": "Bronze"
  },
  {
    "home_store_format": "strip",
    "lapse_rate": "0.562",
    "lapsed_spend_12m": "3203707",
    "members": "67673",
    "tier": "Bronze"
  },
  {
    "home_store_format": "mall",
    "lapse_rate": "0.243",
    "lapsed_spend_12m": "1135321",
    "members": "4076",
    "tier": "Gold"
  },
  {
    "home_store_format": "outlet",
    "lapse_rate": "0.113",
    "lapsed_spend_12m": "198348",
    "members": "1927",
    "tier": "Gold"
  },
  {
    "home_store_format": "strip",
    "lapse_rate": "0.113",
    "lapsed_spend_12m": "253586",
    "members": "2319",
    "tier": "Gold"
  },
  {
    "home_store_format": "online",
    "lapse_rate": "0.106",
    "lapsed_spend_12m": "139808",
    "members": "1469",
    "tier": "Gold"
  },
  {
    "home_store_format": "mall",
    "lapse_rate": "0.395",
    "lapsed_spend_12m": "6195503",
    "members": "45446",
    "tier": "Silver"
  },
  {
    "home_store_format": "online",
    "lapse_rate": "0.293",
    "lapsed_spend_12m": "1558036",
    "members": "16522",
    "tier": "Silver"
  },
  {
    "home_store_format": "strip",
    "lapse_rate": "0.29",
    "lapsed_spend_12m": "2478645",
    "members": "26743",
    "tier": "Silver"
  },
  {
    "home_store_format": "outlet",
    "lapse_rate": "0.281",
    "lapsed_spend_12m": "1965550",
    "members": "21933",
    "tier": "Silver"
  }
]
