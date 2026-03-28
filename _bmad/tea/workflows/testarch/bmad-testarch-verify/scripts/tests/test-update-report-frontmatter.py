#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Unit tests for update-report-frontmatter.py"""

import json
import os
import subprocess
import sys
import tempfile

SCRIPT = os.path.join(os.path.dirname(__file__), '..', 'update-report-frontmatter.py')
PASS = 0
FAIL = 0


def run_script(*args):
    """Run the frontmatter update script and return (stdout, returncode)."""
    result = subprocess.run(
        [sys.executable, SCRIPT, *args],
        capture_output=True, text=True
    )
    return result.stdout.strip(), result.returncode


def create_test_report(content: str) -> str:
    """Create a temporary report file with given content."""
    fd, path = tempfile.mkstemp(suffix='.md')
    with os.fdopen(fd, 'w') as f:
        f.write(content)
    return path


def assert_eq(label: str, actual, expected):
    global PASS, FAIL
    if actual == expected:
        print(f'  PASS: {label}')
        PASS += 1
    else:
        print(f'  FAIL: {label} — expected {expected!r}, got {actual!r}')
        FAIL += 1


def assert_in(label: str, needle: str, haystack: str):
    global PASS, FAIL
    if needle in haystack:
        print(f'  PASS: {label}')
        PASS += 1
    else:
        print(f'  FAIL: {label} — {needle!r} not in output')
        FAIL += 1


SAMPLE_REPORT = """---
title: "QA Verification: Test"
status: "in-progress"
mode: "story"
stepsCompleted: ["preflight"]
lastStep: "preflight"
lastSaved: "2026-01-01T00:00:00Z"
browser_open: false
---

# QA Report

## Summary
"""


print('=== update-report-frontmatter.py tests ===')

# Test 1: Add step completion
print('Test 1: Add step completion')
path = create_test_report(SAMPLE_REPORT)
stdout, rc = run_script(path, '--step', 'api-verification')
assert_eq('exit code 0', rc, 0)
result = json.loads(stdout)
assert_eq('step recorded', result['step_completed'], 'api-verification')
assert_in('steps list', 'api-verification', str(result['steps_completed']))
assert_in('preflight still there', 'preflight', str(result['steps_completed']))
os.unlink(path)

# Test 2: Set key-value pairs
print('Test 2: Set key-value pairs')
path = create_test_report(SAMPLE_REPORT)
stdout, rc = run_script(path, '--set', 'status=complete', '--set', 'verdict=PASS')
assert_eq('exit code 0', rc, 0)
with open(path) as f:
    content = f.read()
assert_in('status updated', 'status: complete', content)
assert_in('verdict added', 'verdict: PASS', content)
os.unlink(path)

# Test 3: Boolean handling
print('Test 3: Boolean handling')
path = create_test_report(SAMPLE_REPORT)
stdout, rc = run_script(path, '--set', 'browser_open=true')
assert_eq('exit code 0', rc, 0)
with open(path) as f:
    content = f.read()
assert_in('boolean true', 'browser_open: true', content)
os.unlink(path)

# Test 4: Timestamp auto-updated
print('Test 4: Timestamp auto-updated')
path = create_test_report(SAMPLE_REPORT)
stdout, rc = run_script(path, '--step', 'ui-verification')
result = json.loads(stdout)
assert_eq('has timestamp', 'last_saved' in result, True)
# Should not be the original timestamp
with open(path) as f:
    content = f.read()
assert_eq('timestamp changed', '2026-01-01T00:00:00Z' not in content, True)
os.unlink(path)

# Test 5: No duplicate steps
print('Test 5: No duplicate steps')
path = create_test_report(SAMPLE_REPORT)
run_script(path, '--step', 'preflight')  # preflight already in list
stdout, _ = run_script(path, '--step', 'preflight')
result = json.loads(stdout)
count = result['steps_completed'].count('preflight')
assert_eq('no duplicate', count, 1)
os.unlink(path)

# Test 6: Missing file error
print('Test 6: Missing file error')
stdout, rc = run_script('/tmp/nonexistent-report-xyz.md', '--step', 'test')
assert_eq('exit code 1', rc, 1)
assert_in('error message', 'error', stdout.lower())

# Test 7: File without frontmatter
print('Test 7: File without frontmatter')
path = create_test_report('# No frontmatter\nJust content')
stdout, rc = run_script(path, '--step', 'test')
assert_eq('exit code 1', rc, 1)
assert_in('error message', 'error', stdout.lower())
os.unlink(path)

print()
print(f'=== Results: {PASS} passed, {FAIL} failed ===')
sys.exit(0 if FAIL == 0 else 1)
