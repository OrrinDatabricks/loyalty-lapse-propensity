#!/usr/bin/env bash
# Ask the curated Genie Agent a question through the Conversation API and print the answer, SQL and result rows.
# Usage: tools/ask_genie_agent.sh <profile> <space_id> "<question>"
set -euo pipefail
PROFILE="$1"; SPACE="$2"; Q="$3"

START=$(databricks genie start-conversation "${SPACE}" "${Q}" --profile "${PROFILE}" -o json)
CONV=$(echo "${START}" | jq -r .conversation_id)
MSG=$(echo "${START}" | jq -r .message_id)

for _ in $(seq 1 60); do
  M=$(databricks genie get-message "${SPACE}" "${CONV}" "${MSG}" --profile "${PROFILE}" -o json)
  STATUS=$(echo "${M}" | jq -r .status)
  [[ "${STATUS}" == "COMPLETED" || "${STATUS}" == "FAILED" || "${STATUS}" == "CANCELLED" ]] && break
  sleep 3
done

echo "### Q: ${Q}"
echo
echo "status: ${STATUS}"
echo "${M}" | jq -r '.attachments[]? | select(.text) | "\n" + .text.content'
echo "${M}" | jq -r '.attachments[]? | select(.query) | "\n" + (.query.description // "") + "\n\n```sql\n" + .query.query + "\n```"'
ATT=$(echo "${M}" | jq -r '[.attachments[]? | select(.query) | .attachment_id][0] // empty')
if [[ -n "${ATT}" ]]; then
  R=$(databricks genie get-message-attachment-query-result "${SPACE}" "${CONV}" "${MSG}" "${ATT}" --profile "${PROFILE}" -o json)
  echo
  echo '```text'
  echo "${R}" | jq -r '.statement_response.manifest.schema.columns | map(.name) | join(" | ")'
  echo "${R}" | jq -r '.statement_response.result.data_array[]? | map(tostring) | join(" | ")' | head -25
  echo '```'
fi
echo
