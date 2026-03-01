# Sprint Change Proposal — Depth-Aware Position Sizing

**Date:** 2026-03-02
**Triggered by:** Story 6-5-5 (Paper Execution Validation)
**Scope Classification:** Minor
**Status:** Approved

---

## Section 1: Issue Summary

During paper trading validation against live Polymarket and Kalshi order books, the execution service's `verifyDepth()` consistently returns `false`, blocking all trade execution.

**Root cause:** `targetSize` is computed as `reservedCapitalUsd / targetPrice` in `execution.service.ts` (lines 155–158). For low-probability contracts (price 0.10–0.25), this produces target sizes of 1200–3000 contracts. Real prediction market order books at those price levels typically have 50–400 contracts of depth. The `verifyDepth()` method (lines 476–499) performs a binary check — `availableQty.gte(targetSize)` — which fails every time.

Position sizing (risk module) operates in USD terms without knowledge of market microstructure, while depth verification (execution module) operates in contract terms reflecting actual liquidity. These two were never reconciled.

**Evidence:**
- `targetSize = 1764`, `availableQty = 317.14` (18% fillable)
- `targetSize = 2142`, `availableQty = 85` (4% fillable)

Both result in `primaryDepthOk = false` → execution aborted → zero trades placed.

**Discovery context:** Identified during preparation for story 6-5-5 (Paper Execution Validation) within Epic 6.5 (Paper Trading Validation), the hard gate before Epic 7.

---

## Section 2: Impact Analysis

### Epic Impact

| Epic | Impact | Details |
|------|--------|---------|
| **Epic 6.5** (Paper Trading Validation) | **Blocked** | Story 6-5-5 cannot pass go/no-go criteria without this fix |
| **Epic 9** (Advanced Risk) | Low-positive | Depth-aware sizing becomes foundation for story 9-3 (confidence-adjusted position sizing) |
| **Epic 10** (Advanced Execution) | Medium-positive | Partial fill infrastructure benefits story 10-4 (adaptive leg sequencing) |
| All other epics | None | No impact |

### Story Impact

- **6-5-5b** (new): Depth-Aware Position Sizing — must be created and completed before 6-5-5
- **6-5-5**: Paper Execution Validation — moved from `ready-for-dev` to `backlog`, blocked by 6-5-5b

### Artifact Conflicts

- **PRD:** No conflicts. FR-EX-03 (depth verification) and FR-RM-01 (3% position sizing) both respected. The change adds intelligent response to depth verification, within the spirit of existing requirements.
- **Architecture:** No conflicts. Same module boundaries, same synchronous hot path pattern, same interfaces.
- **UX/UI:** No conflicts. Dashboard already handles variable position sizes.
- **Prisma Schema:** No changes. Order model already supports variable quantities.

### Technical Impact

- **Files changed:** `execution.service.ts`, `risk-manager.service.ts`, + co-located spec files
- **Interfaces affected:** None — `IPlatformConnector`, `IRiskManager`, `IExecutionEngine` remain stable
- **Schema changes:** None
- **New dependencies:** None

---

## Section 3: Recommended Approach

**Selected:** Direct Adjustment — new sub-story 6-5-5b within Epic 6.5.

**Implementation combines two mechanisms:**

1. **Depth-aware size capping** — before executing, query the order book and cap `targetSize` to `availableQty` at acceptable price levels. The reservation amount is partially released back to the risk budget for the unused portion.

2. **Minimum fill threshold** — configurable minimum (e.g., 25% of ideal `targetSize`). If available depth falls below this threshold, the trade is rejected as not worth the execution risk and fees. This preserves the safety intent of the original depth check.

**Effort estimate:** Low — scoped to 2 service files + tests, no interface changes, no schema changes.
**Risk level:** Low — additive change, doesn't alter module boundaries or data flow, existing tests remain valid.
**Timeline impact:** Minimal — prerequisite fix that enables 6-5-5 rather than delaying it.

**Alternatives considered and rejected:**
- **Rollback (Option 2):** Would require reverting Epic 5 execution infrastructure. Cost vastly outweighs benefit. The depth check itself is correct; only the response to insufficient depth needs improvement.
- **MVP Scope Reduction (Option 3):** Unnecessary. MVP requirements are correct. Only the implementation has a gap.

---

## Section 4: Detailed Change Proposals

### Change 1: Depth-Aware Size Capping in Execution Service

**File:** `pm-arbitrage-engine/src/modules/execution/execution.service.ts`
**Section:** `executeArbitrage()` method, lines 155–168

**OLD:**
```typescript
const targetSize = new Decimal(reservation.reservedCapitalUsd)
  .div(targetPrice)
  .floor()
  .toNumber();

const primaryDepthOk = await this.verifyDepth(
  primaryPlatform, primaryConnector, primaryContractId,
  primarySide, targetPrice.toNumber(), targetSize,
);
```

**NEW (conceptual):**
```typescript
const idealSize = new Decimal(reservation.reservedCapitalUsd)
  .div(targetPrice)
  .floor()
  .toNumber();

const availableDepth = await this.getAvailableDepth(
  primaryConnector, primaryContractId, primarySide, targetPrice.toNumber(),
);

const minFillSize = Math.ceil(idealSize * this.config.minFillRatio);
const targetSize = Math.min(idealSize, availableDepth);

if (targetSize < minFillSize) {
  // Reject — insufficient depth for meaningful trade
}
```

**Rationale:** Replaces binary pass/fail depth check with intelligent size adaptation.

### Change 2: Partial Reservation Release in Risk Manager

**File:** `pm-arbitrage-engine/src/modules/risk-management/risk-manager.service.ts`
**Section:** Budget reservation management

**NEW:** Add method to partially release unused reservation when `actualSize < reservedSize`. The released capital returns to available pool for other opportunities.

**Rationale:** When execution uses fewer contracts than reserved, the excess capital should not remain locked.

### Change 3: Minimum Fill Ratio Configuration

**NEW:** Add `MIN_FILL_RATIO` (default 0.25) to execution configuration. Trades are rejected if available depth < 25% of ideal target size.

**Rationale:** Preserves the safety intent of depth verification — very thin books are still rejected.

---

## Section 5: Implementation Handoff

**Change scope:** Minor — direct implementation by dev team.

| Step | Owner | Action |
|------|-------|--------|
| 1 | Scrum Master | Create story file 6-5-5b with full developer context |
| 2 | Dev Agent | Implement 6-5-5b via TDD workflow |
| 3 | Dev Agent | After 6-5-5b done, proceed to 6-5-5 (paper execution validation) |

**Success criteria:**
- `verifyDepth()` replaced with depth-aware sizing logic
- Trades execute against live order books at depth-capped sizes
- Trades below minimum fill threshold are correctly rejected
- Unused reservation capital is released back to risk budget
- All existing tests pass + new test coverage for depth-aware paths
- Lint clean, full test suite green

**Sprint status updated:**
- Added `6-5-5b-depth-aware-position-sizing: ready-for-dev`
- Moved `6-5-5-paper-execution-validation: backlog` (blocked by 6-5-5b)
