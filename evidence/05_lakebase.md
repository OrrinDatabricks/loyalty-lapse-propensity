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

echo
/var/folders/gm/f5htzmcs4090j67lzqy2s27r0000gp/T//kp.mlp7gF: line 3: return: can only `return' from a function or sourced script

echo "## Write-back: decisions the console wrote to Lakebase"
/var/folders/gm/f5htzmcs4090j67lzqy2s27r0000gp/T//kp.mlp7gF: line 3: return: can only `return' from a function or sourced script

echo
/var/folders/gm/f5htzmcs4090j67lzqy2s27r0000gp/T//kp.mlp7gF: line 3: return: can only `return' from a function or sourced script

echo "The app's service principal created schema \`retention_app\` and table \`outreach_actions\` on first start (CAN_CONNECT_AND_CREATE). Rows below were recorded from the Retention worklist tab and read back through the federation catalog."
/var/folders/gm/f5htzmcs4090j67lzqy2s27r0000gp/T//kp.mlp7gF: line 3: return: can only `return' from a function or sourced script

echo
/var/folders/gm/f5htzmcs4090j67lzqy2s27r0000gp/T//kp.mlp7gF: line 3: return: can only `return' from a function or sourced script

databricks experimental aitools tools query --warehouse $W --profile $P "SELECT action_id, member_id, decision, action, channel, p_lapse, value_at_risk, decided_by, decided_at FROM loyalty_lakebase.retention_app.outreach_actions ORDER BY decided_at"
/var/folders/gm/f5htzmcs4090j67lzqy2s27r0000gp/T//kp.mlp7gF: line 3: return: can only `return' from a function or sourced script

echo
/var/folders/gm/f5htzmcs4090j67lzqy2s27r0000gp/T//kp.mlp7gF: line 3: return: can only `return' from a function or sourced script

echo "## Tables now present in the Postgres database"
/var/folders/gm/f5htzmcs4090j67lzqy2s27r0000gp/T//kp.mlp7gF: line 3: return: can only `return' from a function or sourced script

echo
/var/folders/gm/f5htzmcs4090j67lzqy2s27r0000gp/T//kp.mlp7gF: line 3: return: can only `return' from a function or sourced script

databricks experimental aitools tools query --warehouse $W --profile $P "SELECT table_schema, table_name FROM loyalty_lakebase.information_schema.tables WHERE table_schema IN ('loyalty','retention_app') ORDER BY 1,2"
/var/folders/gm/f5htzmcs4090j67lzqy2s27r0000gp/T//kp.mlp7gF: line 3: return: can only `return' from a function or sourced script

## Write-back: decisions the console wrote to Lakebase

The app's service principal created schema `retention_app` and table `outreach_actions` on first start (CAN_CONNECT_AND_CREATE). Rows below were recorded from the Retention worklist tab and read back through the federation catalog.

[
  {
    "action": "App push + personalized new-arrivals email in preferred channel",
    "action_id": "1",
    "channel": "email",
    "decided_at": "2026-11-03T19:22:46.917Z",
    "decided_by": "orrin.edenfield@databricks.com",
    "decision": "approve",
    "member_id": "M0184345",
    "p_lapse": "0.8267",
    "value_at_risk": "4557.58"
  },
  {
    "action": "App push + personalized new-arrivals email in preferred channel",
    "action_id": "2",
    "channel": "email",
    "decided_at": "2026-11-03T19:25:35.627Z",
    "decided_by": "orrin.edenfield@databricks.com",
    "decision": "approve",
    "member_id": "M0184345",
    "p_lapse": "0.8267",
    "value_at_risk": "4557.58"
  }
]

## Tables now present in the Postgres database

[
  {
    "table_name": "member_retention_scores",
    "table_schema": "loyalty"
  },
  {
    "table_name": "outreach_actions",
    "table_schema": "retention_app"
  }
]

echo

echo "## Automatic refresh after the weekly scoring run"

echo

echo "The scoring job's last task (\`refresh_lakebase_worklist\`, a pipeline_task with full_refresh) re-syncs the worklist after each scoring run. Task states from the latest run:"

echo

echo '```text'

cat /tmp/tasks2.txt

awk '{print $1, $3}'

echo '```'

echo

echo '```json'

databricks postgres get-synced-table "synced_tables/loyalty_lakebase.loyalty.member_retention_scores" --profile $P -o json

python3 -c "import sys,json; d=json.load(sys.stdin)['status']; print(json.dumps({'detailed_state': d.get('detailed_state'), 'last_sync': d.get('last_sync')}, indent=2))"

echo '```'

## Automatic refresh after the weekly scoring run

The scoring job's last task (`refresh_lakebase_worklist`, a pipeline_task with full_refresh) re-syncs the worklist after each scoring run. Task states from the latest run:

```text
score SUCCESS
refresh_lakebase_worklist SUCCESS
train SUCCESS
```

```json
{
  "detailed_state": "SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE",
  "last_sync": {
    "delta_table_sync_info": {
      "delta_commit_time": "2026-11-05T23:54:47Z",
      "delta_commit_version": 78
    },
    "sync_end_time": "2026-11-05T23:55:21.923044Z",
    "sync_start_time": "2026-11-05T23:55:09.460717Z"
  }
}
```
