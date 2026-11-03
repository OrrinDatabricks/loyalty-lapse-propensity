#!/usr/bin/env bash
# Sync the model worklist into Lakebase Postgres as a managed synced table.
# Reads: <catalog>.<schema>.member_retention_scores (Delta, CDF enabled by the scoring notebook)
# Writes: Postgres table loyalty.member_retention_scores in project loyalty-lapse (UC catalog loyalty_lakebase)
#
# Usage: src/lakebase/create_synced_table.sh <profile> [catalog] [schema] [lakebase_catalog] [project]
set -euo pipefail
PROFILE="${1:?profile}"
CATALOG="${2:-loyalty_lapse_demo_catalog}"
SCHEMA="${3:-loyalty}"
LB_CATALOG="${4:-loyalty_lakebase}"
PROJECT="${5:-loyalty-lapse}"
SYNCED="${LB_CATALOG}.${SCHEMA}.member_retention_scores"

cat > /tmp/synced_table.json <<EOF
{
  "spec": {
    "source_table_full_name": "${CATALOG}.${SCHEMA}.member_retention_scores",
    "primary_key_columns": ["member_id"],
    "scheduling_policy": "TRIGGERED",
    "branch": "projects/${PROJECT}/branches/production",
    "postgres_database": "databricks_postgres",
    "create_database_objects_if_missing": true,
    "new_pipeline_spec": {
      "storage_catalog": "${CATALOG}",
      "storage_schema": "${SCHEMA}"
    }
  }
}
EOF

echo "Creating synced table ${SYNCED} (TRIGGERED mode; re-sync by running its pipeline after each scoring run)"
databricks postgres create-synced-table "${SYNCED}" --json @/tmp/synced_table.json --profile "${PROFILE}" --timeout 30m
databricks postgres get-synced-table "synced_tables/${SYNCED}" --profile "${PROFILE}" -o json
