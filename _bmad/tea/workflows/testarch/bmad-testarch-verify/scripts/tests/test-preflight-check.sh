#!/usr/bin/env bash
# Unit tests for preflight-check.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT="$SCRIPT_DIR/preflight-check.sh"
PASS=0
FAIL=0

assert_contains() {
  local label="$1" output="$2" expected="$3"
  if echo "$output" | grep -qF -- "$expected"; then
    echo "  PASS: $label"
    ((PASS++))
  else
    echo "  FAIL: $label — expected '$expected' in output"
    ((FAIL++))
  fi
}

assert_json_field() {
  local label="$1" output="$2" field="$3" expected="$4"
  local actual
  actual=$(echo "$output" | python3 -c "import sys,json; print(json.load(sys.stdin)$field)" 2>/dev/null || echo "PARSE_ERROR")
  if [[ "$actual" == "$expected" ]]; then
    echo "  PASS: $label"
    ((PASS++))
  else
    echo "  FAIL: $label — expected $field=$expected, got $actual"
    ((FAIL++))
  fi
}

echo "=== preflight-check.sh tests ==="

# Test 1: --help flag exits cleanly
echo "Test 1: --help flag"
if "$SCRIPT" --help >/dev/null 2>&1; then
  echo "  PASS: --help exits 0"
  ((PASS++))
else
  echo "  FAIL: --help should exit 0"
  ((FAIL++))
fi

# Test 2: Help output contains usage info
echo "Test 2: --help content"
HELP_OUTPUT=$("$SCRIPT" --help 2>&1)
assert_contains "shows usage" "$HELP_OUTPUT" "Usage"
assert_contains "shows api-url option" "$HELP_OUTPUT" "--api-url"

# Test 3: Invalid API URL produces blocked status
echo "Test 3: Unreachable API"
OUTPUT=$("$SCRIPT" --api-url "http://localhost:19999" --report-dir "/tmp/qa-test-$$" 2>&1 || true)
assert_json_field "api not ok" "$OUTPUT" "['api_health']['ok']" "False"
assert_json_field "overall blocked" "$OUTPUT" "['overall']" "blocked"

# Test 4: Report directory gets created
echo "Test 4: Report directory creation"
TEST_DIR="/tmp/qa-preflight-test-$$"
OUTPUT=$("$SCRIPT" --api-url "http://localhost:19999" --report-dir "$TEST_DIR" 2>&1 || true)
if [[ -d "$TEST_DIR" ]]; then
  echo "  PASS: directory created"
  ((PASS++))
  rmdir "$TEST_DIR" 2>/dev/null || true
else
  echo "  FAIL: directory not created"
  ((FAIL++))
fi

# Test 5: No auth token = not provided
echo "Test 5: No auth token"
OUTPUT=$("$SCRIPT" --api-url "http://localhost:19999" --report-dir "/tmp/qa-test-$$" 2>&1 || true)
assert_json_field "auth not provided" "$OUTPUT" "['auth']['token_provided']" "False"

# Test 6: Output is valid JSON
echo "Test 6: Valid JSON output"
OUTPUT=$("$SCRIPT" --api-url "http://localhost:19999" --report-dir "/tmp/qa-test-$$" 2>&1 || true)
if echo "$OUTPUT" | python3 -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
  echo "  PASS: valid JSON"
  ((PASS++))
else
  echo "  FAIL: output is not valid JSON"
  ((FAIL++))
fi

# Cleanup
rm -rf "/tmp/qa-test-$$" "/tmp/qa-preflight-test-$$" 2>/dev/null || true

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
