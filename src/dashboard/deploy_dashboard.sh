#!/usr/bin/env bash
# Create (or update) and publish the "Loyalty program health" AI/BI dashboard from the committed definition.
# Usage: src/dashboard/deploy_dashboard.sh <profile> <warehouse_id> [catalog] [schema] [existing_dashboard_id]
set -euo pipefail
PROFILE="${1:?profile}"; WH="${2:?warehouse_id}"
CATALOG="${3:-loyalty_lapse_demo_catalog}"; SCHEMA="${4:-loyalty}"; DASH_ID="${5:-}"
HERE="$(cd "$(dirname "$0")" && pwd)"
ME=$(databricks current-user me --profile "${PROFILE}" -o json | jq -r .userName)
PARENT="/Workspace/Users/${ME}/dashboards"
databricks workspace mkdirs "${PARENT}" --profile "${PROFILE}"

if [[ -z "${DASH_ID}" ]]; then
  DASH_ID=$(databricks lakeview create \
    --display-name "Loyalty program health and lapse risk" \
    --warehouse-id "${WH}" \
    --dataset-catalog "${CATALOG}" --dataset-schema "${SCHEMA}" \
    --serialized-dashboard "$(cat "${HERE}/loyalty_program_health.lvdash.json")" \
    --json "{\"parent_path\": \"${PARENT}\"}" \
    --profile "${PROFILE}" -o json | jq -r '.dashboard_id')
else
  databricks lakeview update "${DASH_ID}" \
    --dataset-catalog "${CATALOG}" --dataset-schema "${SCHEMA}" \
    --serialized-dashboard "$(cat "${HERE}/loyalty_program_health.lvdash.json")" \
    --profile "${PROFILE}" > /dev/null
fi
databricks lakeview publish "${DASH_ID}" --warehouse-id "${WH}" --profile "${PROFILE}" > /dev/null
HOST=$(databricks auth env --profile "${PROFILE}" -o json | jq -r .env.DATABRICKS_HOST)
echo "DASHBOARD_ID=${DASH_ID}"
echo "draft:     ${HOST}/sql/dashboardsv3/${DASH_ID}"
echo "published: ${HOST}/sql/dashboardsv3/${DASH_ID}/published"
