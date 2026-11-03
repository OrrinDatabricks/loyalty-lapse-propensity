# 05 Lakebase: synced worklist and app write-back

Lakebase project `loyalty-lapse` (Postgres 17, production branch). The Delta table `member_retention_scores` is synced into Postgres as `loyalty.member_retention_scores` (TRIGGERED mode) and exposed back to Unity Catalog through the `loyalty_lakebase` catalog, which is how these queries run (Lakehouse Federation over the live Postgres table).

## Synced table status

```json
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    import sys,json; d=json.load(sys.stdin); s=d['status']; print(json.dumps({'synced_table_id': d['synced_table_id'], 'detailed_state': s.get('detailed_state'), 'scheduling_policy': d['spec']['scheduling_policy'], 'last_sync': s.get('last_sync')}, indent=2))
                                                                                                                                                                                       ~^^^^^^^^
KeyError: 'spec'
```

## Row count and risk mix read from Postgres (via loyalty_lakebase catalog)

[
  {
    "members": "1408",
    "risk_band": "High",
    "value_at_risk": "1181736.0"
  },
  {
    "members": "36295",
    "risk_band": "Medium",
    "value_at_risk": "4966271.0"
  },
  {
    "members": "63386",
    "risk_band": "Low",
    "value_at_risk": "8262119.0"
  }
]

## Top of the worklist as the console reads it

[
  {
    "annual_value_at_risk": "4557.58",
    "home_store_format": "mall",
    "member_id": "M0184345",
    "p_lapse": "0.8267",
    "primary_driver": "engagement_drop",
    "recommended_action": "App push + personalized new-arrivals email in preferred channel",
    "tier": "Gold"
  },
  {
    "annual_value_at_risk": "4529.39",
    "home_store_format": "mall",
    "member_id": "M0231566",
    "p_lapse": "0.7968",
    "primary_driver": "engagement_drop",
    "recommended_action": "App push + personalized new-arrivals email in preferred channel",
    "tier": "Gold"
  },
  {
    "annual_value_at_risk": "4476.53",
    "home_store_format": "online",
    "member_id": "M0057811",
    "p_lapse": "0.6627",
    "primary_driver": "engagement_drop",
    "recommended_action": "Fit-guarantee outreach: free exchange + stylist fit consult",
    "tier": "Gold"
  },
  {
    "annual_value_at_risk": "4455.02",
    "home_store_format": "mall",
    "member_id": "M0054944",
    "p_lapse": "0.8556",
    "primary_driver": "purchase_recency",
    "recommended_action": "Switch channel; one high-value offer, pause bulk sends",
    "tier": "Gold"
  },
  {
    "annual_value_at_risk": "4091.21",
    "home_store_format": "mall",
    "member_id": "M0067395",
    "p_lapse": "0.8446",
    "primary_driver": "engagement_drop",
    "recommended_action": "App push + personalized new-arrivals email in preferred channel",
    "tier": "Gold"
  }
]
