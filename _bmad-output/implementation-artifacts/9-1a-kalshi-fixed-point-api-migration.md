# Story 9.1a: Kalshi Fixed-Point API Migration

Status: done

## Story

As an operator,
I want the Kalshi connector updated to use the new fixed-point API response format across all methods — orderbook, order submission, order status, and order cancellation,
So that order book data flows, trade execution, and order lifecycle management are fully restored after Kalshi's 2026-03-12 migration removed all legacy integer fields.

## Acceptance Criteria

1. **Given** Kalshi's REST API now returns `orderbook_fp` with `yes_dollars`/`no_dollars` string-tuple arrays instead of `orderbook` with `yes`/`no` integer-tuple arrays
   **When** the system fetches order book data via `getOrderBook()`
   **Then** the response is parsed correctly using the new field names and string types
   **And** prices (already in dollars as strings like `"0.4200"`) are not double-divided by 100
   **And** quantities (now FP strings like `"100.00"`) are parsed to numbers
   **And** the `NormalizedOrderBook` output is identical in shape to pre-migration
   [Source: epics.md Story 9.1a AC1; Kalshi docs — docs.kalshi.com/getting_started/fixed_point_migration — Orderbook removed fields table]

2. **Given** Kalshi's WebSocket now sends `yes_dollars_fp`/`no_dollars_fp` string-tuple arrays in snapshots and `price_dollars` (string) / `delta_fp` (string) in deltas
   **When** the WebSocket client receives orderbook messages
   **Then** snapshots and deltas are parsed and applied correctly using the new field names and string types
   **And** local orderbook state stores string-based price/quantity levels internally
   **And** `emitUpdate()` produces correct `NormalizedOrderBook` output
   [Source: epics.md Story 9.1a AC2; Kalshi docs — WebSocket removed fields: `yes`/`no` → `yes_dollars_fp`/`no_dollars_fp`, `price` → `price_dollars`, `delta` → `delta_fp`]

3. **Given** the Zod validation schemas reference old field names (`yes`/`no` number tuples for snapshots, `price`/`delta` numbers for deltas)
   **When** a Kalshi WebSocket message arrives
   **Then** all schemas validate against the new fixed-point field names and string types
   [Source: epics.md Story 9.1a AC3; Codebase `kalshi-response.schema.ts:48-65`]

4. **Given** Kalshi's Order API now requires `yes_price_dollars` (string) instead of `yes_price` (integer cents) in order submission, and returns `remaining_count_fp`, `fill_count_fp`, `taker_fill_cost_dollars` (all strings) instead of legacy integer fields in responses
   **When** `submitOrder()` creates an order
   **Then** the request sends `yes_price_dollars` as a dollar string (e.g., `"0.42"`) instead of `yes_price` as cents (e.g., `42`)
   **And** the response is parsed using the new FP/dollar field names and string types
   **And** the returned `OrderResult` is correct (fill price in decimal 0-1, quantities as numbers)
   [Source: Kalshi docs — Order removed fields: `yes_price` → `yes_price_dollars`, `taker_fill_cost` → `taker_fill_cost_dollars`, `remaining_count` → `remaining_count_fp`, `fill_count` → `fill_count_fp`]

5. **Given** Kalshi's Order API returns `remaining_count_fp`, `fill_count_fp`, `taker_fill_cost_dollars` (all strings) instead of legacy integer fields
   **When** `getOrder()` checks order status
   **Then** the response is parsed using the new FP/dollar field names and string types
   **And** the returned `OrderStatusResult` is correct
   [Source: Kalshi docs — same Order removed fields as AC #4; Codebase `kalshi.connector.ts:487-555`]

6. **Given** Kalshi's Cancel Order API returns `reduced_by_fp` (string) instead of `reduced_by` (integer)
   **When** `cancelOrder()` cancels an order
   **Then** the Zod schema validates using the new field name and string type
   [Source: Kalshi docs — Cancel/Decrease Order removed fields: `reduced_by` → `reduced_by_fp`; Codebase `kalshi-response.schema.ts:22-34`]

## Tasks / Subtasks

**Execution order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8**

- [x] **Task 1: Update SDK type declarations** (AC: #1, #4, #5, #6)
  - [x] 1.1 In `kalshi-sdk.d.ts`, update `Orderbook` interface: remove `yes?: Array<Array<number>>` and `no?: Array<Array<number>>`, keep `yes_dollars: Array<Array<string>>` and `no_dollars: Array<Array<string>>`
  - [x] 1.2 Update `GetMarketOrderbookResponse`: rename field `orderbook` → `orderbook_fp`, type → `{ yes_dollars: Array<Array<string>>; no_dollars: Array<Array<string>> }`
  - [x] 1.3 Update `CreateOrderRequest`: change `yes_price?: number` → `yes_price_dollars?: string`, `no_price?: number` → `no_price_dollars?: string`
  - [x] 1.4 Update `KalshiOrder` — **remove** legacy fields: `yes_price`, `no_price`, `taker_fill_count`, `taker_fill_cost`, `remaining_count`. **Add** replacements: `yes_price_dollars: string`, `no_price_dollars: string`, `taker_fill_count_fp: string`, `taker_fill_cost_dollars: string`, `remaining_count_fp: string`, `fill_count_fp: string`. Keep `place_count: number` unchanged (not listed in Kalshi's removed fields table — verify at runtime; if removed, update to `place_count_fp: string`)

- [x] **Task 2: Update `normalizeKalshiLevels()` — remove cent-to-dollar division** (AC: #1, #2)
  - [x] 2.1 Change `kalshi-price.util.ts` function signature: accept `[string, string][]` instead of `[number, number][]` for both `yesLevels` and `noLevels` parameters
  - [x] 2.2 Bids mapping: `new Decimal(priceDollars)` instead of `new Decimal(priceCents).div(100)` — prices are already in dollar format, no division needed
  - [x] 2.3 Asks mapping (NO inversion): `new Decimal(1).minus(new Decimal(priceDollars))` — same formula but without the `.div(100)`
  - [x] 2.4 Quantities: parse `new Decimal(qtyString).toNumber()` instead of using integer directly
  - [x] 2.5 Update `KalshiNormalizedLevels` interface JSDoc to reflect new input format

- [x] **Task 3: Update `kalshi-price.util.spec.ts` tests** (AC: #1, #2)
  - [x] 3.1 Convert all test inputs from `[number, number]` integer-cent tuples to `[string, string]` dollar tuples. Example: `[[42, 100]]` → `[["0.4200", "100.00"]]`, `[[35, 10]]` → `[["0.3500", "10.00"]]`, `[[0, 10]]` → `[["0.0000", "10.00"]]`, `[[100, 5]]` → `[["1.0000", "5.00"]]`
  - [x] 3.2 Expected outputs remain the SAME — normalization result is unchanged (prices in decimal 0-1, quantities as numbers)
  - [x] 3.3 Add test for subpenny price input: `[["0.1250", "50.00"]]` → `{ price: 0.125, quantity: 50 }`
  - [x] 3.4 Add test for fractional quantity: `[["0.4200", "1.55"]]` → `{ price: 0.42, quantity: 1.55 }`

- [x] **Task 4: Update TypeScript interfaces + Zod schemas for WebSocket messages** (AC: #2, #3)
  - [x] 4.1 In `kalshi.types.ts`, update `KalshiOrderbookSnapshotMsg`: `yes: Array<[number, number]>` → `yes_dollars_fp: Array<[string, string]>`, `no: Array<[number, number]>` → `no_dollars_fp: Array<[string, string]>`
  - [x] 4.2 Update `KalshiOrderbookDeltaMsg`: `price: number` → `price_dollars: string`, `delta: number` → `delta_fp: string`
  - [x] 4.3 Update `LocalOrderbookState`: `yes: Array<[number, number]>` → `yes: Array<[string, string]>`, `no: Array<[number, number]>` → `no: Array<[string, string]>` (internal state uses dollar-string tuples, field names stay `yes`/`no` internally)
  - [x] 4.4 In `kalshi-response.schema.ts`, update `kalshiSnapshotMsgSchema`: `yes: z.array(z.tuple([z.number(), z.number()]))` → `yes_dollars_fp: z.array(z.tuple([z.string(), z.string()]))`, same for `no` → `no_dollars_fp`
  - [x] 4.5 Update `kalshiDeltaMsgSchema`: `price: z.number()` → `price_dollars: z.string()`, `delta: z.number()` → `delta_fp: z.string()`

- [x] **Task 5: Update Zod schemas for REST order responses** (AC: #4, #5, #6)
  - [x] 5.1 In `kalshi-response.schema.ts`, update `kalshiOrderResponseSchema`: `remaining_count: z.number()` → `remaining_count_fp: z.string()`, `fill_count: z.number()` → `fill_count_fp: z.string()`, `taker_fill_count: z.number()` → `taker_fill_count_fp: z.string()`, `taker_fill_cost: z.number()` → `taker_fill_cost_dollars: z.string()`
  - [x] 5.2 Update `kalshiCancelOrderResponseSchema`: `reduced_by: z.number()` → `reduced_by_fp: z.string()`

- [x] **Task 6: Update `KalshiWebSocketClient`** (AC: #2)
  - [x] 6.1 Update `KalshiOrderBook` interface (`kalshi-websocket.client.ts:19-24`): `yes: [number, number][]` → `yes: [string, string][]`, `no: [number, number][]` → `no: [string, string][]` (internal representation uses string tuples)
  - [x] 6.2 Update `handleSnapshot()`: read `msg.yes_dollars_fp` / `msg.no_dollars_fp` instead of `msg.yes` / `msg.no`
  - [x] 6.3 Update `handleDelta()`: read `msg.price_dollars` / `msg.delta_fp` instead of `msg.price` / `msg.delta`
  - [x] 6.4 Update `applyDelta()` signature and internals: `price` becomes `string`, `delta` becomes `string`. Level matching: `levels.findIndex(([p]) => p === priceDollars)` (string equality — Kalshi normalizes precision consistently per market). Quantity arithmetic: use `new Decimal(level[1]).plus(new Decimal(deltaStr)).toString()` instead of `level[1] += delta` (preserve original precision, don't hardcode `toFixed`). Level removal threshold: `new Decimal(level[1]).lte(0)`. New level insertion + sort: `levels.sort((a, b) => new Decimal(b[0]).minus(new Decimal(a[0])).toNumber())`. Store as string tuples.
  - [x] 6.5 Update `emitUpdate()`: `normalizeKalshiLevels(state.yes, state.no)` — no change needed because `normalizeKalshiLevels` now accepts `[string, string][]` (Task 2)

- [x] **Task 7: Update `KalshiConnector` methods** (AC: #1, #4, #5, #6)
  - [x] 7.1 **`getOrderBook()`**: Change `response.data.orderbook` → `response.data.orderbook_fp`, read `orderbook_fp.yes_dollars` / `orderbook_fp.no_dollars` as `[string, string][]`. Remove the integer-casting `as [number, number][]` and the `.map(([p, q]: number[]) => [p ?? 0, q ?? 0])` safety mapping. Pass string tuples directly to `normalizeKalshiLevels()`.
  - [x] 7.2 **`submitOrder()`**: Replace cent conversion (`new Decimal(params.price.toString()).mul(100).round().toNumber()`) with dollar string formatting (`new Decimal(params.price.toString()).toFixed(2)`). Send `yes_price_dollars: priceDollars` instead of `yes_price: priceCents`. Parse response fields using `Decimal` throughout: `new Decimal(order.remaining_count_fp).toNumber()` for status check, `new Decimal(order.taker_fill_count_fp).toNumber()` for fill quantity, `new Decimal(order.taker_fill_cost_dollars)` for fill cost (keep as Decimal for division). Fill price: `new Decimal(order.taker_fill_cost_dollars).div(new Decimal(order.taker_fill_count_fp)).toNumber()` — no `.div(100)`, and keep operands as Decimal until final `.toNumber()`.
  - [x] 7.3 **`getOrder()`**: Parse all fields via `Decimal`: `new Decimal(order.remaining_count_fp).toNumber()` for status determination, `new Decimal(order.fill_count_fp).toNumber()` for fill count. Fill price: `new Decimal(order.taker_fill_cost_dollars).div(new Decimal(order.fill_count_fp)).toNumber()` — no `.div(100)`, keep as Decimal until final conversion.
  - [x] 7.4 **`cancelOrder()`**: No code changes needed beyond the Zod schema update (Task 5.2) — the method only reads `order.status` (string, unchanged) and doesn't use `reduced_by`. The schema change ensures validation passes.

- [x] **Task 8: Update all test files** (AC: #1–#6)
  - [x] 8.1 **`kalshi-response.schema.spec.ts`**: Update snapshot test data: `yes: [[65, 100]]` → `yes_dollars_fp: [["0.6500", "100.00"]]`, `no: [[35, 200]]` → `no_dollars_fp: [["0.3500", "200.00"]]`. Update delta test data: `price: 65` → `price_dollars: "0.6500"`, `delta: 50` → `delta_fp: "50.00"`. Update order response test data: `remaining_count: 10` → `remaining_count_fp: "10.00"`, `fill_count: 5` → `fill_count_fp: "5.00"`, `taker_fill_count: 5` → `taker_fill_count_fp: "5.00"`, `taker_fill_cost: 250` → `taker_fill_cost_dollars: "2.50"`. Update cancel response: `reduced_by: z.number()` tests → `reduced_by_fp: z.string()`.
  - [x] 8.2 **`kalshi-websocket.client.spec.ts`**: Update snapshot/delta mock data to use new field names and string types. Update `applyDelta` tests for string-based arithmetic.
  - [x] 8.3 **`kalshi.connector.spec.ts`**: Update `mockGetMarketOrderbook` response shape: `{ orderbook_fp: { yes_dollars: [...], no_dollars: [...] } }`. Update `mockCreateOrder` / `mockGetOrder` response fixtures with FP/dollar fields. Update `mockCancelOrder` fixture. Update `submitOrder` test expectations for `yes_price_dollars` string. Verify fill price calculations no longer divide by 100.

## Dev Notes

### Key Conversion Change

**Old format (REMOVED):** Integer cents for prices (e.g., `42` = $0.42, required `/100`). Integer counts for quantities.
**New format (CURRENT):** Dollar strings for prices (e.g., `"0.4200"`, no division needed). FP strings for quantities (e.g., `"100.00"`).

The `/100` division in `normalizeKalshiLevels()` and the `*100` multiplication in `submitOrder()` are the critical conversions to remove. Missing either one produces prices 100x wrong.
[Source: Kalshi docs — docs.kalshi.com/getting_started/fixed_point_migration — "Subpenny Pricing" section]

### Architecture & Patterns

**No interface changes:** `IPlatformConnector`, `NormalizedOrderBook`, `PriceLevel`, `OrderResult`, `OrderStatusResult`, `CancelResult` — none of these change. The migration is entirely internal to the Kalshi connector layer. All downstream consumers (detection, execution, exit-management, dashboard) are unaffected.
[Source: architecture.md module dependency rules; sprint change proposal Section 2 — "No epic restructuring needed"]

**decimal.js for all string-to-number conversions:** ALL `_dollars` and `_fp` fields from Kalshi responses must be parsed via `new Decimal(str)`. Use `.toNumber()` only at the final interface boundary (e.g., when returning `OrderResult.filledPrice`). Keep intermediate arithmetic as `Decimal` — do NOT convert to `number` before dividing. This prevents floating-point precision loss on fractional quantities (e.g., `"1.55"` contracts).
[Source: CLAUDE.md Domain Rules — "ALL financial calculations MUST use decimal.js"]

**Zod `.passthrough()` strategy:** All Kalshi schemas use `.passthrough()` so extra fields from the API don't cause validation failures. This means the new FP/dollar fields were silently passing through already — but the REQUIRED old fields are now missing, causing Zod to throw. Fix: change required field names and types to match the new API.
[Source: Codebase `kalshi-response.schema.ts` — all schemas use `.passthrough()`]

### Codebase Touchpoints

**Files to MODIFY (no new files created):**
- `pm-arbitrage-engine/src/connectors/kalshi/kalshi-sdk.d.ts` — SDK type declarations (4 interfaces)
- `pm-arbitrage-engine/src/connectors/kalshi/kalshi.connector.ts` — `getOrderBook()`, `submitOrder()`, `getOrder()` (3 methods)
- `pm-arbitrage-engine/src/connectors/kalshi/kalshi-websocket.client.ts` — `KalshiOrderBook`, `handleSnapshot()`, `handleDelta()`, `applyDelta()`, `emitUpdate()` (1 interface + 4 methods)
- `pm-arbitrage-engine/src/connectors/kalshi/kalshi.types.ts` — `KalshiOrderbookSnapshotMsg`, `KalshiOrderbookDeltaMsg`, `LocalOrderbookState` (3 interfaces)
- `pm-arbitrage-engine/src/connectors/kalshi/kalshi-response.schema.ts` — `kalshiSnapshotMsgSchema`, `kalshiDeltaMsgSchema`, `kalshiOrderResponseSchema`, `kalshiCancelOrderResponseSchema` (4 schemas)
- `pm-arbitrage-engine/src/common/utils/kalshi-price.util.ts` — `normalizeKalshiLevels()` function signature and body
- `pm-arbitrage-engine/src/common/utils/kalshi-price.util.spec.ts` — all test inputs
- `pm-arbitrage-engine/src/connectors/kalshi/kalshi-response.schema.spec.ts` — all WS + order test fixtures
- `pm-arbitrage-engine/src/connectors/kalshi/kalshi-websocket.client.spec.ts` — snapshot/delta/applyDelta test fixtures
- `pm-arbitrage-engine/src/connectors/kalshi/kalshi.connector.spec.ts` — all mock responses and assertions

### Detailed Method Changes

**`normalizeKalshiLevels(yesLevels, noLevels)` — remove `/100` division:**
```typescript
// BEFORE: integer cents
bids: yesLevels.map(([priceCents, qty]) => ({
  price: new Decimal(priceCents.toString()).div(100).toNumber(),
  quantity: qty,
}));

// AFTER: dollar strings — NO .div(100)
bids: yesLevels.map(([priceDollars, qtyStr]) => ({
  price: new Decimal(priceDollars).toNumber(),
  quantity: new Decimal(qtyStr).toNumber(),
}));
```
Asks formula changes similarly: `new Decimal(1).minus(new Decimal(priceDollars))` — the inversion logic stays, only the cents-to-dollars division is removed.
[Source: Codebase `kalshi-price.util.ts:17-37`]

**`submitOrder()` — remove `*100` conversion:**
```typescript
// BEFORE: multiply to get cents
const priceCents = new Decimal(params.price.toString()).mul(100).round().toNumber();
// sends: yes_price: priceCents

// AFTER: format as dollar string — NO .mul(100)
const priceDollars = new Decimal(params.price.toString()).toFixed(2);
// sends: yes_price_dollars: priceDollars
```

**Fill price calculation — remove response-side `/100`, keep Decimal precision:**
```typescript
// BEFORE (submitOrder): cents-based, early toNumber()
const filledPrice = new Decimal(order.taker_fill_cost.toString())
  .div(filledQuantity).div(100).toNumber();

// AFTER: dollar-based — NO .div(100), keep as Decimal until final .toNumber()
const filledQty = new Decimal(order.taker_fill_count_fp);
const filledPrice = filledQty.greaterThan(0)
  ? new Decimal(order.taker_fill_cost_dollars).div(filledQty).toNumber()
  : 0;
```
Same pattern applies to `getOrder()` fill price.
[Source: Codebase `kalshi.connector.ts:347-427` (submitOrder), `kalshi.connector.ts:487-555` (getOrder)]

**`applyDelta()` — string-based arithmetic:**
```typescript
// BEFORE: number arithmetic
level[1] += delta;
if (level[1] <= 0) levels.splice(levelIndex, 1);

// AFTER: Decimal arithmetic on strings — use .toString() to preserve precision
level[1] = new Decimal(level[1]).plus(new Decimal(deltaStr)).toString();
if (new Decimal(level[1]).lte(0)) levels.splice(levelIndex, 1);
```
Do NOT hardcode `.toFixed(2)` — quantities may have variable precision (fractional markets use 2dp, but `.toString()` preserves whatever Kalshi sends).
[Source: Codebase `kalshi-websocket.client.ts:282-310`]

### Subpenny Pricing Consideration

Kalshi now supports subpenny pricing for select markets (`deci_cent`, `tapered_deci_cent` tiers). Dollar strings can have up to 4 decimal places (e.g., `"0.1250"`). The `normalizeKalshiLevels()` function handles this naturally since `new Decimal("0.1250").toNumber()` = `0.125`. For `submitOrder()`, use `.toFixed(2)` for now (standard cent markets) — subpenny order submission would be a separate enhancement if needed.
[Source: Kalshi docs — "Price Level Structures" section: `linear_cent` (0.01), `deci_cent` (0.001), `tapered_deci_cent` (variable)]

### `taker_fill_count` vs `fill_count` Clarification

The codebase uses TWO different count fields in different methods:
- **`submitOrder()`** reads `order.taker_fill_count` (taker-specific fill count)
- **`getOrder()`** reads `order.fill_count` (total fill count)

Kalshi's removed fields table explicitly lists `fill_count` → `fill_count_fp`. `taker_fill_count` is NOT explicitly listed, but follows the `_fp` naming pattern. **Conservative approach:** update the Zod schema to expect `taker_fill_count_fp: z.string()` and read it as `order.taker_fill_count_fp` in the code. If Kalshi still returns the integer field, `.passthrough()` preserves it — the code reads the `_fp` variant. If the API returns neither, Zod validation will catch it at runtime with a clear error.

### `place_count` Field Note

`place_count` is NOT listed in Kalshi's "Removed Legacy Fields" table for Orders. Keep it as `place_count: number` in the SDK types. If removed at runtime, the Zod schema (which uses `.passthrough()` and does not currently validate `place_count`) will not break. If Kalshi adds `place_count_fp`, it will pass through silently.
[Source: Kalshi docs — Order removed fields table; Codebase `kalshi-sdk.d.ts:84`]

### Testing Strategy

- **Framework:** Vitest 4 (NOT Jest). Co-located tests. Run with `pnpm test`
- **No new test files** — only modify existing spec files
- **Test data conversion:** All mock responses change from integer cents/counts to dollar/FP strings. Expected OUTPUTS remain the same (normalized decimal prices 0-1, numeric quantities)
- **Key assertion changes:** Remove any expectations about `/100` conversions. Verify string parsing correctness.
- **applyDelta tests:** Verify string-based arithmetic produces correct results (e.g., `"100.00"` + `"50.00"` = `"150.00"`, quantity going to zero removes level)
- **Green baseline:** 1868 tests passing across 111 files before this story. All tests must pass after.
- **Smoke check:** After implementation, verify with `pnpm build` that no TypeScript errors remain from the SDK type changes (compiler-driven validation)

### Error Handling

- No new error types needed — existing `PlatformApiError` and Zod validation errors handle all failure modes
- `parseApiResponse()` wrapper already throws structured `PlatformApiError` on Zod validation failure — schema updates make this work correctly with new fields
- If Kalshi returns unexpected response shape (e.g., during partial rollout), Zod catches it and the connector emits a structured error

### Previous Story Intelligence

- **9-0-2 (Zod boundary schemas):** Established the `parseApiResponse()` pattern used by `submitOrder()` and `cancelOrder()`. Schema changes in this story flow through that existing validation path automatically.
- **9-1 (Correlation clusters):** No dependency or interaction. Changes are orthogonal (connector layer vs risk management layer).
- **8-8/8-9 (Rate limiter fixes):** Rate limiter initialization uses `getAccountApiLimits()` which returns `usage_tier`, `read_limit`, `write_limit` — these fields are NOT in the removed list and should still work. No changes needed.
- **Epic 6.5 bug-fix stories:** Kalshi-specific fixes (6-5-5a sort fix, 6-5-5g fee correction, 6-5-5h equal-leg sizing) — all consume `NormalizedOrderBook` output, which this story preserves unchanged.

### Project Structure Notes

- No new files created — purely mechanical field-name/type updates across existing files
- All files remain in their current locations within `connectors/kalshi/` and `common/utils/`
- No module wiring changes — no new providers, no new imports
- `kalshi-sdk.d.ts` is a local type declaration (not an npm package) and is safe to modify directly

### References

- [Source: Kalshi docs — docs.kalshi.com/getting_started/fixed_point_migration] Complete field removal/replacement tables for REST and WebSocket APIs
- [Source: epics.md Story 9.1a] User story, acceptance criteria (orderbook scope)
- [Source: sprint-change-proposal-2026-03-12.md Section 4] Technical impact analysis, original 6-file scope
- [Source: User disambiguation 2026-03-12] Expanded scope confirmed — include order submission, status, and cancellation methods
- [Source: Codebase `kalshi.connector.ts:288-334`] getOrderBook — reads `response.data.orderbook`
- [Source: Codebase `kalshi.connector.ts:347-427`] submitOrder — sends `yes_price` cents, reads `taker_fill_cost`/`taker_fill_count`
- [Source: Codebase `kalshi.connector.ts:429-485`] cancelOrder — reads `reduced_by`
- [Source: Codebase `kalshi.connector.ts:487-555`] getOrder — reads `remaining_count`, `fill_count`, `taker_fill_cost`
- [Source: Codebase `kalshi-websocket.client.ts:19-24`] KalshiOrderBook interface
- [Source: Codebase `kalshi-websocket.client.ts:238-310`] handleSnapshot, handleDelta, applyDelta methods
- [Source: Codebase `kalshi-websocket.client.ts:312-327`] emitUpdate — calls normalizeKalshiLevels
- [Source: Codebase `kalshi-price.util.ts:17-37`] normalizeKalshiLevels — divides by 100
- [Source: Codebase `kalshi-response.schema.ts:48-65`] WS snapshot/delta schemas
- [Source: Codebase `kalshi-response.schema.ts:5-44`] REST order/cancel schemas
- [Source: Codebase `kalshi-sdk.d.ts:56-85`] CreateOrderRequest, KalshiOrder interfaces

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

N/A — no debugging issues encountered.

### Completion Notes List

- All 8 tasks completed in order, all subtasks checked off.
- Baseline: 1868 tests / 111 files → Final: 1874 tests / 111 files (net +6: 4 Kalshi tests — subpenny, fractional qty, cancel schema, passthrough preservation; 2 Polymarket tests — depth truncation, snapshot deduplication).
- `pnpm build` — clean, zero TypeScript errors.
- `pnpm lint` — clean (linter auto-fixed one minor formatting in `kalshi.connector.ts`).
- Additional downstream consumer test file updated: `order-book-normalizer.service.spec.ts` — all 15 Kalshi tests converted from integer cents to dollar string tuples. Not listed in story's original file list but required because it imports `KalshiOrderBook` which changed from `[number, number][]` to `[string, string][]`.
- Lad MCP code review: Primary reviewer (kimi-k2.5) returned 10 findings. All assessed as false positives or pre-existing issues outside story scope (fee formula is correct — returns rate not amount, schema passthrough is intentional, unbounded depth/sequence gaps/pong timeouts are pre-existing). Secondary reviewer (glm-5) timed out on both attempts. No code changes from review.
- No deviations from Dev Notes guidance. All patterns followed exactly as specified.
- [Code review fix] Polymarket WebSocket client updated for consistency: added `deduplicateLevels()`, `MAX_ORDERBOOK_DEPTH` (50) truncation, and sort precision fix (`.minus().toNumber()` → `.comparedTo()`). Out of original story scope but brings Polymarket parity with Kalshi patterns. 2 new tests added.

### File List

**Modified (13 files):**
- `pm-arbitrage-engine/src/connectors/kalshi/kalshi-sdk.d.ts` — SDK type declarations: Orderbook, GetMarketOrderbookResponse, CreateOrderRequest, KalshiOrder
- `pm-arbitrage-engine/src/common/utils/kalshi-price.util.ts` — `normalizeKalshiLevels()` signature and body
- `pm-arbitrage-engine/src/common/utils/kalshi-price.util.spec.ts` — all test inputs + 2 new tests (subpenny, fractional)
- `pm-arbitrage-engine/src/connectors/kalshi/kalshi.types.ts` — KalshiOrderbookSnapshotMsg, KalshiOrderbookDeltaMsg, LocalOrderbookState
- `pm-arbitrage-engine/src/connectors/kalshi/kalshi-response.schema.ts` — 4 Zod schemas (snapshot, delta, order, cancel)
- `pm-arbitrage-engine/src/connectors/kalshi/kalshi-websocket.client.ts` — KalshiOrderBook, handleSnapshot, handleDelta, applyDelta (+ Decimal import)
- `pm-arbitrage-engine/src/connectors/kalshi/kalshi.connector.ts` — getOrderBook, submitOrder, getOrder, KalshiOrderResponse, KalshiCancelOrderResponse interfaces
- `pm-arbitrage-engine/src/connectors/kalshi/kalshi-response.schema.spec.ts` — all WS + order + cancel test fixtures
- `pm-arbitrage-engine/src/connectors/kalshi/kalshi-websocket.client.spec.ts` — applyDelta test fixtures (string tuples)
- `pm-arbitrage-engine/src/connectors/kalshi/kalshi.connector.spec.ts` — all mock responses and assertions
- `pm-arbitrage-engine/src/modules/data-ingestion/order-book-normalizer.service.spec.ts` — all KalshiOrderBook test fixtures (downstream consumer)
- `pm-arbitrage-engine/src/connectors/polymarket/polymarket-websocket.client.ts` — added `deduplicateLevels()`, `MAX_ORDERBOOK_DEPTH` truncation, sort precision fix (Polymarket parity)
- `pm-arbitrage-engine/src/connectors/polymarket/polymarket-websocket.client.spec.ts` — 2 new tests: depth truncation, snapshot deduplication
