#!/bin/sh
# Requires curl and jq. Read one request JSON object from stdin.
set -eu
task_response_dir=$(mktemp -d)
trap 'rm -f "$task_response_dir/body" "$task_response_dir/headers"; rmdir "$task_response_dir"' EXIT HUP INT TERM
task_endpoint=${ZERO_SLOP_API_URL:-https://mcp.zero-slop.ai/v1/deslop}
if ! task_status=$(curl --silent --show-error --max-time 75 --connect-timeout 10 \
    --proto '=http,https' --max-redirs 0 --request POST \
    --header 'Content-Type: application/json' --header 'Accept: application/json' \
    --data-binary @- --dump-header "$task_response_dir/headers" \
    --output "$task_response_dir/body" --write-out '%{http_code}' "$task_endpoint"); then
  printf '%s\n' 'Request failed. No automatic retry; the outcome may be unknown.' >&2
  exit 1
fi
task_retry_after=$(awk 'tolower($1) == "retry-after:" {gsub("\r", ""); print $2}' "$task_response_dir/headers")
if [ "$task_status" != 200 ]; then
  if ! jq --argjson status "$task_status" --arg retry "$task_retry_after" \
    '{httpStatus:$status,retryAfter:(if $retry == "" then null else $retry end),problem:.}' "$task_response_dir/body" >&2; then
    printf '%s\n' 'Response was not JSON. No automatic retry.' >&2
  fi
  exit 1
fi
if ! jq . "$task_response_dir/body"; then
  printf '%s\n' 'Response was not JSON. No automatic retry.' >&2
  exit 1
fi
if ! jq -e '
  def score: type == "number" and . >= 0 and . <= 100;
  . as $r | type == "object" and
  (["text","status","before","after","scoreChange","factsPreserved","passedFinalChecks",
    "independentModelChecks","modelRequests","rolesCompleted","finishingRounds","scorerVersion","durationMs","note"]
    | all(.[]; . as $key | $r | has($key))) and
  (.text | type == "string") and (.before.score | score) and (.after.score | score) and
  (.passedFinalChecks | type == "boolean") and .factsPreserved == true and
  ((.status == "rewritten" and .passedFinalChecks == true) or
   (.status == "already_clear" and .modelRequests == 0 and .scoreChange == 0 and .before.score == .after.score))
' "$task_response_dir/body" >/dev/null; then
  printf '%s\n' 'Review required. Keep the original until the result has been reviewed.' >&2
  exit 3
fi
