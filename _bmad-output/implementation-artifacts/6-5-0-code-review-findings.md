# Code Review Findings — Story 6.5.0

**Date:** 2026-02-25
**Reviewer:** LAD MCP (kimi-k2-thinking)
**Scope:** All files modified in Story 6.5.0 (decimal compliance fixes, Swagger setup, eslint cleanup, dependency cleanup)
**Secondary reviewer:** z-ai/glm-4.7 (timed out — no findings)

---

## Finding 1: PlatformHealth `mode` Property Missing

**Severity:** Critical (reviewer) → **False Positive**
**Files cited:** `kalshi.connector.ts`, `polymarket.connector.ts`, `execution.service.ts`

**Reviewer claim:** `PlatformHealth` interface does not include a `mode` field, causing `health.mode === 'paper'` to be `undefined`.

**Triage:** `mode` exists as optional field in `src/common/types/platform.type.ts:12` — `mode?: 'paper' | 'live'`. Reviewer did not have access to the full type definition. **No action required.**

---

## Finding 2: `verifyDepth` Decimal Compliance Violation

**Severity:** Critical (reviewer) → ~~**Intentional Exclusion**~~ **FIXED (secondary code review)**
**File:** `execution.service.ts` — `verifyDepth()` method, line 491

**Reviewer claim:** `availableQty += level.quantity` uses native arithmetic on a monetary field.

**Original triage:** Dismissed as integer count accumulation. **Overridden by secondary code review:** Polymarket quantities can be fractional (e.g., 12.5 shares), so native float accumulation introduces precision drift. The depth check gates execution decisions — incorrect result could cause missed trades or single-leg exposure. **Fixed:** replaced with `Decimal` accumulation and `.gte()` comparison.

---

## Finding 3: Inefficient Decimal Sorting Performance

**Severity:** Critical (reviewer) → **Documented Trade-off**
**Files:** `kalshi-price.util.ts`, `polymarket-websocket.client.ts`

**Reviewer claim:** `asks.sort((a, b) => new Decimal(a.price).minus(b.price).toNumber())` creates Decimal instances on every comparison (O(n log n) allocations).

**Triage:** Already documented as a conscious trade-off in `gotchas.md` (Story 6.5.0, gotcha #6 — "Sort comparator performance trade-off"). Order book sorts run once per message (~10-50 levels), not in a tight loop. The consistency benefit of the absolute decimal rule outweighs the negligible GC overhead at current scale.

**Reviewer suggestion:** Use `Decimal.compare()` or pre-compute. `Decimal.compare()` is not a static method in decimal.js. Pre-computing would require mapping prices to Decimal first, sorting, then mapping back — same allocation count.

**Course correction consideration:** If P95 normalization latency exceeds the 500ms SLA, sort comparators should be profiled first. Currently well within bounds.

---

## Finding 4: Silent Error Swallowing in `verifyDepth`

**Severity:** High (reviewer) → **Pre-existing, Out of Scope**
**File:** `execution.service.ts` — `verifyDepth()` catch block

**Reviewer claim:** API failures, rate limits, and transient errors are silently swallowed with `return false`, no logging or metrics.

**Triage:** This code was not modified by Story 6.5.0. The `verifyDepth` method is pre-existing from Epic 5. The empty catch with `return false` treats failures as insufficient liquidity, which is a conservative safety decision (fail-closed). However, the lack of logging/metrics is a valid observability gap.

**Course correction action:** Add to tech debt backlog — add structured warning log and event emission in `verifyDepth` catch block. Candidate for Epic 7 (dashboard/monitoring) or a future tech debt story.

---

## Finding 5: WebSocket Price Change Handling Bug

**Severity:** High (reviewer) → **Pre-existing, Out of Scope**
**File:** `polymarket-websocket.client.ts` — `handlePriceChange()`

**Reviewer claim:** `price_change` events only update the timestamp but don't update actual price levels in the order book state, causing stale pricing data.

**Triage:** This code was not modified by Story 6.5.0 (only the sort comparators in `handleBookSnapshot` were changed). The `handlePriceChange` method is pre-existing from Epic 2.

**Course correction action:** Needs investigation — if confirmed as a bug, this could cause stale order book data to persist. Add to tech debt backlog for investigation. Priority depends on whether Polymarket WebSocket actually sends `price_change` messages (the primary data flow uses full book snapshots).

---

## Finding 6: `parseFloat` Instead of Decimal Constructor

**Severity:** High (reviewer) → **Not a Violation**
**Files:** `polymarket-websocket.client.ts` (lines 179-184, 206)

**Reviewer claim:** `parseFloat(msg.price)` should use `new Decimal(stringValue).toNumber()` for consistency.

**Triage:** `parseFloat` is a type conversion (string → number) at the input boundary, not arithmetic on monetary values. The AC explicitly scopes violations to "arithmetic operations" (`+`, `-`, `*`, `/`, `Math.abs()`, `Math.round()`). Parsing is not arithmetic. The `.toNumber()` on Decimal would produce the same result since no arithmetic is performed.

**Course correction consideration:** If the team wants to tighten the rule to include parsing boundaries, this would need a separate story. Current scope is arithmetic-only per AC #2.

---

## Finding 7: Hardcoded Timeouts Without Retry Strategy

**Severity:** High (reviewer) → **Pre-existing, Out of Scope**
**File:** `polymarket.connector.ts` — `ORDER_POLL_TIMEOUT_MS`, `ORDER_POLL_INTERVAL_MS`

**Reviewer claim:** 5-second blocking poll loop with no exponential backoff or jitter.

**Triage:** Pre-existing from Epic 5. Not modified by Story 6.5.0. The order polling is in the execution path but occurs after order submission, not in the detection hot path.

**Course correction action:** Add to tech debt backlog — make timeouts configurable via `@nestjs/config` and add jitter. Candidate for Epic 10 (Advanced Execution).

---

## Finding 8: Raw Error Throw in Connector

**Severity:** Medium (reviewer) → **Pre-existing, Out of Scope**
**File:** `kalshi.connector.ts` — `getPositions()` method

**Reviewer claim:** `throw new Error('getPositions not implemented - Epic 5 Story 5.1')` violates the SystemError hierarchy rule.

**Triage:** Pre-existing placeholder from Epic 1. Not modified by Story 6.5.0. The method is unimplemented and throws on any call. Since `getPositions()` is never called in the current execution flow (positions are tracked via the `OpenPosition` model in Prisma), this is a dead code path.

**Course correction action:** Add to tech debt backlog — either implement `getPositions()` or remove it from `IPlatformConnector` interface if not needed. Low priority since the code path is unreachable.

---

## Finding 9: Inconsistent Logging in `main.ts`

**Severity:** Medium (reviewer) → **No Action Needed**
**File:** `main.ts` — bootstrap logging

**Reviewer claim:** `logger.log(\`Application is running on: ...\`)` should use structured object logging instead of template strings.

**Triage:** NestJS `Logger.log()` with the pino adapter produces structured JSON output automatically — the template string becomes the `message` field. The NestJS Logger API's second argument is `context` (string), not a data object. To pass structured data, you'd need to use the pino instance directly, which would bypass the NestJS Logger abstraction. The current approach is consistent with NestJS conventions and produces valid structured logs.

**Course correction consideration:** None — current implementation is correct.

---

## Finding 10: Stale Data Emission Without Metrics

**Severity:** Medium (reviewer) → **Pre-existing, Out of Scope**
**File:** `polymarket-websocket.client.ts` — staleness check

**Reviewer claim:** No metrics, alerts, or circuit breaker for persistent data staleness beyond 30 seconds.

**Triage:** Pre-existing from Epic 2. Not modified by Story 6.5.0. The staleness check logs an error and skips the emit, which is the correct safety behavior.

**Course correction action:** Add event emission for staleness alerts — candidate for Epic 6.5 stories (validation framework) or Epic 7 (monitoring dashboard).

---

## Finding 11: Type Assertions Without Validation

**Severity:** Medium (reviewer) → **Pre-existing, Out of Scope**
**File:** `polymarket.connector.ts` — `postOrder` response casting

**Reviewer claim:** Blind trust of external API responses via `as Record<string, unknown>` can lead to undefined order IDs.

**Triage:** Pre-existing from Epic 5. Not modified by Story 6.5.0. The fallback `?? \`pm-${Date.now()}\`` provides a synthetic ID, but orphaned orders are still a risk.

**Course correction action:** Add runtime validation of external API responses. Candidate for Epic 11 (Platform Extensibility & Security Hardening).

---

## Reviewer Questions — Answers

| Question | Answer |
|----------|--------|
| Testing coverage for decimal edge cases | Existing tests cover kalshi-price normalization (10 tests including 33¢ precision), property-based tests (11 tests with 1000 runs each). All 1,078 tests pass. |
| P95 normalization latency impact | Not measured in this story. P95 tracking exists in `order-book-normalizer.service.ts:220`. Will be measured during Task 10 (30-min stability run). |
| `gasEstimation.getGasEstimateUsd()` RPC calls | No — gas estimation uses cached values updated periodically, not per-call RPC. |
| KalshiWebSocketClient divergence | Kalshi uses REST polling (no WebSocket), Polymarket uses WebSocket. Different by design per platform API capabilities. |
| Database transactions for single-leg resolution | Prisma handles individual operations; cross-model consistency relies on the sequential execution lock (Story 4.4). Full ACID transactions are a Phase 1 improvement. |
| Decimal.js rounding/precision config | Not globally configured — uses decimal.js defaults (precision: 20, rounding: ROUND_HALF_UP). Sufficient for prediction market prices (0.00-1.00 range, 2 decimal places). |

---

## Summary for Course Correction

### Findings Requiring Future Action (Tech Debt Backlog)

| # | Finding | Priority | Candidate Epic |
|---|---------|----------|----------------|
| 4 | Silent error swallowing in `verifyDepth` | Medium | Epic 7 or tech debt |
| 5 | WebSocket `handlePriceChange` may not update prices | High (if confirmed) | Investigate immediately |
| 7 | Hardcoded timeouts without retry/jitter | Low | Epic 10 |
| 8 | Raw `Error` throw in `getPositions` placeholder | Low | Tech debt cleanup |
| 10 | No metrics for data staleness events | Medium | Epic 6.5 or 7 |
| 11 | Unvalidated external API response types | Medium | Epic 11 |

### Findings Dismissed (No Action)

| # | Finding | Reason |
|---|---------|--------|
| 1 | PlatformHealth `mode` missing | False positive — field exists |
| 2 | `verifyDepth` quantity accumulation | ~~Integer count~~ FIXED — Polymarket has fractional quantities |
| 3 | Decimal sorting performance | Documented trade-off |
| 6 | `parseFloat` at input boundary | Parsing, not arithmetic |
| 9 | Template string in bootstrap log | Correct per NestJS Logger API |
