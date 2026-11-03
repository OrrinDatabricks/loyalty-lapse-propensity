#!/usr/bin/env bash
# Create (or update) the Loyalty Retention Genie Agent from the committed serialized_space payload.
# Usage: src/genie/deploy_genie_agent.sh <profile> <warehouse_id> [catalog] [schema] [existing_space_id]
set -euo pipefail
PROFILE="${1:?profile}"
WAREHOUSE_ID="${2:?warehouse_id}"
CATALOG="${3:-loyalty_lapse_demo_catalog}"
SCHEMA="${4:-loyalty}"
SPACE_ID="${5:-}"
HERE="$(cd "$(dirname "$0")" && pwd)"

python3 "${HERE}/build_genie_agent.py" "${CATALOG}" "${SCHEMA}" > "${HERE}/genie_agent.json"
SERIALIZED=$(jq -c '.' "${HERE}/genie_agent.json" | jq -Rs '.')
ME=$(databricks current-user me --profile "${PROFILE}" -o json | jq -r .userName)
PARENT="/Workspace/Users/${ME}/genie_agents"
databricks workspace mkdirs "${PARENT}" --profile "${PROFILE}"

if [[ -z "${SPACE_ID}" ]]; then
  databricks genie create-space --profile "${PROFILE}" -o json --json "{
    \"warehouse_id\": \"${WAREHOUSE_ID}\",
    \"title\": \"Loyalty Retention\",
    \"description\": \"Ask about loyalty lapse, revenue at risk, campaign response and which members to contact. Built on governed metric views and the lapse model worklist.\",
    \"parent_path\": \"${PARENT}\",
    \"serialized_space\": ${SERIALIZED}
  }" | tee "${HERE}/genie_space.json"
  SPACE_ID=$(jq -r .space_id "${HERE}/genie_space.json")
else
  databricks genie update-space "${SPACE_ID}" --profile "${PROFILE}" --json "{\"serialized_space\": ${SERIALIZED}}" > /dev/null
fi
echo "GENIE_SPACE_ID=${SPACE_ID}"
