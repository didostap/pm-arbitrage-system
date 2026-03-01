# Sprint Change Proposal — 2026-03-01b

## Issue Summary

Two implementation defects discovered during Epic 6.5 deployment preparation block paper trading validation (story 6-5-5):

1. **Polymarket WebSocket instability:** The WebSocket connection frequently closes with code 1006 (abnormal closure). No keepalive/ping mechanism exists, so the server closes idle connections. The health service treats every single timeout observation as an immediate degradation trigger, causing constant healthy↔degraded flapping on transient reconnects. This makes platform health unreliable for paper trading validation.

2. **Structured log payload serialization:** `EventConsumerService.summarizeEvent()` replaces all object-typed event fields with the literal string `[object]` — including `Date` instances, arrays (`healthyPlatforms`), and nested objects (`impactSummary`). Operators cannot diagnose degradation events, execution failures, or any event with structured metadata from logs.

## Impact Analysis

- **Epic Impact:** Epic 6.5 only. Story 6-5-5 (paper execution validation) cannot pass with flapping health status. No other epic structure changes.
- **Story Impact:** No existing stories are modified. A new story 6-5-4 is added before 6-5-5.
- **Artifact Conflicts:** None. PRD requirements (FR-DI-01, FR-DI-03, NFR-I3) are met by existing architecture; these are implementation-level fixes. Architecture doc should gain a one-line convention note about event payload serializability.
- **Technical Impact:** 4 files modified, all in existing modules:
  - `src/connectors/polymarket/polymarket-websocket.client.ts` — add ping keepalive
  - `src/modules/data-ingestion/platform-health.service.ts` — debounce degradation triggering
  - `src/modules/monitoring/event-consumer.service.ts` — fix `summarizeEvent()` serialization
  - Corresponding spec files updated

## Recommended Approach

**Direct Adjustment** — Add a single bug-fix story (6-5-4) within Epic 6.5, positioned before 6-5-5.

- Effort: Low-Medium
- Risk: Low (isolated changes in well-tested files, no API or schema changes)
- Timeline impact: Adds ~1 story worth of work but is required for 6-5-5 to pass

## Detailed Change Proposals

### 1. ADD Story 6-5-4: WebSocket Stability & Structured Log Payloads

**Files to modify:**

#### A. `polymarket-websocket.client.ts` — Add keepalive ping

- On `open`: start a periodic ping interval (every 30s via `ws.ping()`)
- On `close`/`disconnect`: clear the ping interval
- Track `lastPongTime`; log warning if pong not received within expected window
- Emit structured disconnect log with code, reason, and last activity timestamp

#### B. `platform-health.service.ts` — Debounce degradation activation

- Add per-platform consecutive timeout counter
- Only activate degradation protocol after 2+ consecutive timeout observations on 30s health ticks (~141s total elapsed since last data)
- Reset counter on any successful `recordUpdate()` call
- Only deactivate degradation after 2+ consecutive healthy observations
- Make both thresholds configurable (constructor injection from config)

#### C. `event-consumer.service.ts` — Fix `summarizeEvent()` serialization

- Replace the `[object]` fallback with proper serialization:
  - `Date` → `.toISOString()`
  - `Array` → map elements (recursively handle Date elements)
  - Plain objects → `JSON.parse(JSON.stringify(value))` for safe shallow clone
- Ensure no class instances or circular references leak into log output
- Add a depth guard to prevent unbounded recursion on deeply nested objects

#### D. Spec files — Update tests

- `polymarket-websocket.client.spec.ts`: test ping interval start/stop, reconnect clears ping, pong timeout logging
- `platform-health.service.spec.ts`: test debounce behavior — single timeout does not degrade, 2 consecutive timeouts do, recovery requires 2 healthy ticks
- `event-consumer.service.spec.ts`: test `summarizeEvent()` with Date, array, nested object, null, and primitive inputs

### 2. UPDATE `epics.md` — Epic 6.5 section

- Add Story 6.5.4 definition with acceptance criteria
- Update sequencing: `6.5.3 → 6.5.4 → 6.5.5 → 6.5.6`
- Update Story 6.5.5 dependencies to include "Requires 6.5.4 complete"

### 3. UPDATE `sprint-status.yaml`

- Add line: `6-5-4-websocket-stability-structured-log-payloads: backlog`

## Implementation Handoff

- **Scope:** Minor — Direct implementation by development team
- **Executed by:** Dev agent (TDD workflow with story file)
- **Prerequisites:** Story file must be created via Create Story workflow
- **Success criteria:**
  - WebSocket stays connected during idle periods (no 1006 from inactivity)
  - Health status does not flap on transient reconnects
  - Degradation only activates on sustained connectivity loss (2+ consecutive timeout ticks)
  - All event log entries show real values (ISO timestamps, arrays, objects) — zero `[object]` in logs
  - All existing tests pass; new tests cover the added behavior
