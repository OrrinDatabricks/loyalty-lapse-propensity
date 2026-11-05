# 08 AI/BI dashboard: Loyalty program health and lapse risk

Created and published by `src/dashboard/deploy_dashboard.sh` from `src/dashboard/loyalty_program_health.lvdash.json` (3 datasets on the gold tables, 4 KPI counters, 4 charts with the Jun 1 and Jul 15 event annotations, worklist table, global filters on tier / store format / region, Genie space linked).

Published: https://fevm-loyalty-lapse-demo.cloud.databricks.com/sql/dashboardsv3/01f1d97429dc16c781dbb908c4721dad/published

```json
{
  "dashboard_id": "01f1d97429dc16c781dbb908c4721dad",
  "display_name": "Loyalty program health and lapse risk",
  "lifecycle_state": "ACTIVE",
  "warehouse_id": "b640dd2388fedf8d",
  "path": "/Users/orrin.edenfield@databricks.com/dashboards/Loyalty program health and lapse risk.lvdash.json",
  "create_time": "2026-11-05T23:53:56.722Z",
  "update_time": "2026-11-05T23:53:56.818Z"
}
```

Published state:

```json
{
  "display_name": "Loyalty program health and lapse risk",
  "embed_credentials": false,
  "revision_create_time": "2026-11-05T23:53:57.430Z",
  "warehouse_id": "b640dd2388fedf8d"
}
```

Dataset queries were executed against the warehouse before creation (see the SQL in the dashboard JSON); widget definitions follow the versioned AI/BI widget schema.
