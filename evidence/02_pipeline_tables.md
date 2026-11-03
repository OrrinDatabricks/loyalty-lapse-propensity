pipeline_id=236703e1-3aca-4498-87b9-52a4aea9d35a

## Row counts after the first update

[
  {
    "n": "1948914",
    "t": "bronze_transactions"
  },
  {
    "n": "400000",
    "t": "gold_member_360"
  },
  {
    "n": "3727448",
    "t": "gold_member_activity_monthly"
  },
  {
    "n": "1254012",
    "t": "silver_campaign_touches"
  },
  {
    "n": "4102903",
    "t": "silver_engagement_events"
  },
  {
    "n": "400000",
    "t": "silver_members"
  },
  {
    "n": "162757",
    "t": "silver_returns"
  },
  {
    "n": "1948914",
    "t": "silver_transactions"
  }
]

## Expectation results from the pipeline event log

[
  {
    "expectation": "non_negative_reward",
    "failed_records": "0",
    "flow_name": "loyalty_lapse_demo_catalog.loyalty.silver_campaign_touches",
    "passed_records": "1254012"
  },
  {
    "expectation": "valid_touch",
    "failed_records": "0",
    "flow_name": "loyalty_lapse_demo_catalog.loyalty.silver_campaign_touches",
    "passed_records": "1254012"
  },
  {
    "expectation": "known_event_type",
    "failed_records": "0",
    "flow_name": "loyalty_lapse_demo_catalog.loyalty.silver_engagement_events",
    "passed_records": "4102903"
  },
  {
    "expectation": "valid_event",
    "failed_records": "0",
    "flow_name": "loyalty_lapse_demo_catalog.loyalty.silver_engagement_events",
    "passed_records": "4102903"
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
    "passed_records": "162757"
  },
  {
    "expectation": "valid_return",
    "failed_records": "0",
    "flow_name": "loyalty_lapse_demo_catalog.loyalty.silver_returns",
    "passed_records": "162757"
  },
  {
    "expectation": "positive_basket",
    "failed_records": "0",
    "flow_name": "loyalty_lapse_demo_catalog.loyalty.silver_transactions",
    "passed_records": "1948914"
  },
  {
    "expectation": "valid_discount",
    "failed_records": "0",
    "flow_name": "loyalty_lapse_demo_catalog.loyalty.silver_transactions",
    "passed_records": "1948914"
  },
  {
    "expectation": "valid_txn_id",
    "failed_records": "0",
    "flow_name": "loyalty_lapse_demo_catalog.loyalty.silver_transactions",
    "passed_records": "1948914"
  },
  {
    "expectation": "valid_units",
    "failed_records": "0",
    "flow_name": "loyalty_lapse_demo_catalog.loyalty.silver_transactions",
    "passed_records": "1948914"
  }
]

## gold_member_360 sanity

[
  {
    "home_store_format": "online",
    "lapse_rate": "0.577",
    "lapsed_spend_12m": "2004506",
    "members": "42077",
    "tier": "Bronze"
  },
  {
    "home_store_format": "outlet",
    "lapse_rate": "0.576",
    "lapsed_spend_12m": "2629365",
    "members": "55060",
    "tier": "Bronze"
  },
  {
    "home_store_format": "mall",
    "lapse_rate": "0.573",
    "lapsed_spend_12m": "5399138",
    "members": "114755",
    "tier": "Bronze"
  },
  {
    "home_store_format": "strip",
    "lapse_rate": "0.573",
    "lapsed_spend_12m": "3202155",
    "members": "67673",
    "tier": "Bronze"
  },
  {
    "home_store_format": "mall",
    "lapse_rate": "0.419",
    "lapsed_spend_12m": "6383983",
    "members": "45446",
    "tier": "Silver"
  },
  {
    "home_store_format": "online",
    "lapse_rate": "0.327",
    "lapsed_spend_12m": "1640678",
    "members": "16522",
    "tier": "Silver"
  },
  {
    "home_store_format": "strip",
    "lapse_rate": "0.324",
    "lapsed_spend_12m": "2623533",
    "members": "26743",
    "tier": "Silver"
  },
  {
    "home_store_format": "outlet",
    "lapse_rate": "0.317",
    "lapsed_spend_12m": "2106738",
    "members": "21933",
    "tier": "Silver"
  },
  {
    "home_store_format": "mall",
    "lapse_rate": "0.273",
    "lapsed_spend_12m": "1208522",
    "members": "4076",
    "tier": "Gold"
  },
  {
    "home_store_format": "outlet",
    "lapse_rate": "0.166",
    "lapsed_spend_12m": "260349",
    "members": "1927",
    "tier": "Gold"
  },
  {
    "home_store_format": "strip",
    "lapse_rate": "0.155",
    "lapsed_spend_12m": "299452",
    "members": "2319",
    "tier": "Gold"
  },
  {
    "home_store_format": "online",
    "lapse_rate": "0.15",
    "lapsed_spend_12m": "176999",
    "members": "1469",
    "tier": "Gold"
  }
]
