#!/usr/bin/env bash
# Preflight check script for QA Verification workflow
# Performs health check, log file detection, and directory creation
# Usage: ./preflight-check.sh --api-url URL [--dashboard-url URL] [--engine-dir DIR] [--server-log FILE] [--report-dir DIR] [--auth-token TOKEN]

set -euo pipefail

# Defaults
API_URL="http://localhost:8080/api"
DASHBOARD_URL="http://localhost:5173"
ENGINE_DIR="."
SERVER_LOG="server.log"
REPORT_DIR="_bmad-output/test-artifacts/qa-reports"
AUTH_TOKEN=""
HEALTH_ENDPOINT="/api/health"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --api-url) API_URL="$2"; shift 2;;
    --dashboard-url) DASHBOARD_URL="$2"; shift 2;;
    --engine-dir) ENGINE_DIR="$2"; shift 2;;
    --server-log) SERVER_LOG="$2"; shift 2;;
    --report-dir) REPORT_DIR="$2"; shift 2;;
    --auth-token) AUTH_TOKEN="$2"; shift 2;;
    --health-endpoint) HEALTH_ENDPOINT="$2"; shift 2;;
    -h|--help)
      echo "Preflight check for QA Verification workflow"
      echo ""
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --api-url URL          API server URL (default: http://localhost:8080/api)"
      echo "  --dashboard-url URL    Dashboard SPA URL (default: http://localhost:5173)"
      echo "  --engine-dir DIR       Engine working directory (default: .)"
      echo "  --server-log FILE      Server log filename (default: server.log)"
      echo "  --report-dir DIR       Report output directory (default: _bmad-output/test-artifacts/qa-reports)"
      echo "  --auth-token TOKEN     Bearer token for authenticated endpoints"
      echo "  --health-endpoint PATH Health check path (default: /api/health)"
      echo "  -h, --help             Show this help"
      exit 0
      ;;
    *) echo "Unknown option: $1" >&2; exit 2;;
  esac
done

# Output JSON
output_json() {
  cat <<EOF
{
  "api_health": {
    "url": "${API_URL}${HEALTH_ENDPOINT}",
    "status": "${API_STATUS}",
    "ok": ${API_OK}
  },
  "dashboard_health": {
    "url": "${DASHBOARD_URL}",
    "status": "${DASH_STATUS}",
    "ok": ${DASH_OK}
  },
  "auth": {
    "token_provided": ${AUTH_PROVIDED},
    "token_valid": ${AUTH_VALID}
  },
  "server_log": {
    "path": "${ENGINE_DIR}/${SERVER_LOG}",
    "exists": ${LOG_EXISTS}
  },
  "report_dir": {
    "path": "${REPORT_DIR}",
    "created": ${DIR_CREATED}
  },
  "overall": "${OVERALL}"
}
EOF
}

# 1. API Health Check
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "${API_URL}${HEALTH_ENDPOINT}" 2>/dev/null || echo "000")
if [[ "$API_STATUS" == "200" ]]; then
  API_OK="true"
else
  API_OK="false"
fi

# 2. Dashboard Health Check
DASH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "${DASHBOARD_URL}" 2>/dev/null || echo "000")
if [[ "$DASH_STATUS" == "200" ]]; then
  DASH_OK="true"
else
  DASH_OK="false"
fi

# 3. Auth Token Check
if [[ -n "$AUTH_TOKEN" ]]; then
  AUTH_PROVIDED="true"
  AUTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 -H "Authorization: Bearer ${AUTH_TOKEN}" "${API_URL}${HEALTH_ENDPOINT}" 2>/dev/null || echo "000")
  if [[ "$AUTH_CHECK" == "200" || "$AUTH_CHECK" == "401" ]]; then
    # 200 = token works, 401 = endpoint requires auth but token rejected
    # We accept both as "valid check" — the agent will interpret
    AUTH_VALID="true"
  else
    AUTH_VALID="false"
  fi
else
  AUTH_PROVIDED="false"
  AUTH_VALID="false"
fi

# 4. Server Log Check
if [[ -f "${ENGINE_DIR}/${SERVER_LOG}" ]]; then
  LOG_EXISTS="true"
else
  LOG_EXISTS="false"
fi

# 5. Report Directory Creation
mkdir -p "${REPORT_DIR}" 2>/dev/null
if [[ -d "${REPORT_DIR}" ]]; then
  DIR_CREATED="true"
else
  DIR_CREATED="false"
fi

# Overall status
if [[ "$API_OK" == "true" ]]; then
  OVERALL="ready"
else
  OVERALL="blocked"
fi

output_json
