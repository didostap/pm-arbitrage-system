#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Update QA report YAML frontmatter with step completion tracking.

Usage:
    python3 update-report-frontmatter.py REPORT_PATH --step STEP_NAME [--set KEY=VALUE ...]

Examples:
    python3 update-report-frontmatter.py report.md --step api-verification
    python3 update-report-frontmatter.py report.md --step ui-verification --set browser_open=true
    python3 update-report-frontmatter.py report.md --set status=complete --set verdict=PASS
"""

import argparse
import re
import sys
from datetime import datetime, timezone


def parse_frontmatter(content: str) -> tuple[dict, str, str]:
    """Parse YAML frontmatter from markdown content.
    Returns (frontmatter_dict, frontmatter_raw, body).
    """
    match = re.match(r'^---\n(.*?)\n---\n(.*)$', content, re.DOTALL)
    if not match:
        return {}, '', content

    fm_raw = match.group(1)
    body = match.group(2)

    # Simple YAML parsing (no pyyaml dependency needed for flat structures)
    fm = {}
    for line in fm_raw.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if ':' in line:
            key, _, value = line.partition(':')
            key = key.strip()
            value = value.strip()
            # Handle arrays
            if value.startswith('[') and value.endswith(']'):
                items = value[1:-1].strip()
                if items:
                    fm[key] = [i.strip().strip('"').strip("'") for i in items.split(',')]
                else:
                    fm[key] = []
            # Handle booleans
            elif value.lower() in ('true', 'false'):
                fm[key] = value.lower() == 'true'
            # Handle quoted strings
            elif (value.startswith('"') and value.endswith('"')) or \
                 (value.startswith("'") and value.endswith("'")):
                fm[key] = value[1:-1]
            else:
                fm[key] = value

    return fm, fm_raw, body


def serialize_frontmatter(fm: dict) -> str:
    """Serialize frontmatter dict back to YAML string."""
    lines = []
    for key, value in fm.items():
        if isinstance(value, list):
            items = ', '.join(f'"{i}"' for i in value)
            lines.append(f'{key}: [{items}]')
        elif isinstance(value, bool):
            lines.append(f'{key}: {"true" if value else "false"}')
        else:
            # Quote strings that contain special chars
            val_str = str(value)
            if any(c in val_str for c in ':#{}[],"\'') or val_str != val_str.strip():
                lines.append(f'{key}: "{val_str}"')
            else:
                lines.append(f'{key}: {val_str}')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Update QA report YAML frontmatter with step completion tracking.'
    )
    parser.add_argument('report_path', help='Path to the QA report markdown file')
    parser.add_argument('--step', help='Step name to mark as completed')
    parser.add_argument('--set', action='append', default=[],
                        help='Set a frontmatter key=value (can be used multiple times)')
    parser.add_argument('--help-full', action='store_true', help='Show detailed help')

    args = parser.parse_args()

    if args.help_full:
        print(__doc__)
        sys.exit(0)

    # Read file
    try:
        with open(args.report_path, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print(f'{{"error": "File not found: {args.report_path}"}}')
        sys.exit(1)

    fm, _, body = parse_frontmatter(content)

    if not fm:
        print('{"error": "No YAML frontmatter found in file"}')
        sys.exit(1)

    # Update step completion
    if args.step:
        steps = fm.get('stepsCompleted', [])
        if isinstance(steps, str):
            steps = [steps]
        if args.step not in steps:
            steps.append(args.step)
        fm['stepsCompleted'] = steps
        fm['lastStep'] = args.step

    # Update timestamp
    fm['lastSaved'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    # Apply --set overrides
    for kv in args.set:
        if '=' not in kv:
            print(f'{{"error": "Invalid --set format: {kv}. Use KEY=VALUE"}}')
            sys.exit(1)
        key, _, value = kv.partition('=')
        # Parse boolean values
        if value.lower() == 'true':
            fm[key] = True
        elif value.lower() == 'false':
            fm[key] = False
        else:
            fm[key] = value

    # Write back
    new_content = f'---\n{serialize_frontmatter(fm)}\n---\n{body}'
    with open(args.report_path, 'w') as f:
        f.write(new_content)

    # Output result
    import json
    result = {
        'status': 'ok',
        'report': args.report_path,
        'step_completed': args.step,
        'steps_completed': fm.get('stepsCompleted', []),
        'last_saved': fm['lastSaved']
    }
    print(json.dumps(result))


if __name__ == '__main__':
    main()
