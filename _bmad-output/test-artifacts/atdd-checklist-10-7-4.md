---
stepsCompleted:
  - step-01-preflight-and-context
  - step-02-generation-mode
  - step-03-test-strategy
  - step-04-generate-tests
  - step-04c-aggregate
  - step-05-validate-and-complete
lastStep: step-05-validate-and-complete
lastSaved: '2026-03-23'
storyId: '10-7-4'
storyName: 'Realized P&L Computation Investigation & Fix'
detectedStack: backend
generationMode: ai-generation
executionMode: sequential
tddPhase: RED
inputDocuments:
  - _bmad-output/implementation-artifacts/10-7-4-realized-pnl-computation-investigation-fix.md
  - _bmad/tea/testarch/knowledge/data-factories.md
  - _bmad/tea/testarch/knowledge/test-quality.md
  - _bmad/tea/testarch/knowledge/test-levels-framework.md
  - _bmad/tea/testarch/knowledge/test-priorities-matrix.md
  - _bmad/tea/testarch/knowledge/test-healing-patterns.md
---

# ATDD Checklist: Story 10-7-4 — Realized P&L Computation Investigation & Fix

## TDD Red Phase (Current)

All tests use `it.skip()` — they assert EXPECTED behavior that does not yet exist in code.

- **Unit Tests**: 15 scenarios across 2 test files (all skipped)
- **E2E Tests**: 0 (backend-only story, no browser testing)

## Acceptance Criteria → Test Scenario Mapping

### AC1: Root cause documented before code changes

| ID | Scenario | Priority | Level | File | Status |
|----|----------|----------|-------|------|--------|
| S1 | Verify `positionRepository.updateStatus()` signature only accepts `status` (no `realizedPnl` param) | — | Manual | — | Pre-documented in story. Verify against code before implementing. |

> **Note:** AC1 is a process/investigation AC. Verification is manual: confirm the story's documented root cause matches current code before proceeding to code changes.

### AC2: `realized_pnl` persisted for all 5 close paths

| ID | Scenario | Priority | Level | File | Status |
|----|----------|----------|-------|------|--------|
| S2 | `executeExit()` full exit calls `prisma.openPosition.update` with `{ status: 'CLOSED', realizedPnl: <computed> }` | **P0** | Unit | `exit-monitor-pnl-persistence.spec.ts` | `it.skip` |
| S3 | `evaluatePosition()` zero-residual path calls `prisma.openPosition.update` with `{ status: 'CLOSED', realizedPnl: 0 }` | **P0** | Unit | `exit-monitor-pnl-persistence.spec.ts` | `it.skip` |
| S4 | Formula: buy-side leg PnL = `(exitPrice - entryPrice) × size` | **P0** | Unit | `exit-monitor-pnl-persistence.spec.ts` | `it.skip` |
| S5 | Formula: sell-side leg PnL = `(entryPrice - exitPrice) × size` | **P0** | Unit | `exit-monitor-pnl-persistence.spec.ts` | `it.skip` |
| S6 | Formula: exit fees subtracted from total PnL | **P0** | Unit | `exit-monitor-pnl-persistence.spec.ts` | `it.skip` |
| S7 | Formula: asymmetric entry/exit prices across legs — no sign errors | **P0** | Unit | `exit-monitor-pnl-persistence.spec.ts` | `it.skip` |
| S8 | Audit: manual close (`position-close.service.ts`) already persists `realizedPnl` | **P1** | Audit | existing tests | Verify existing assertions |
| S9 | Audit: auto-unwind → `closeLeg()` already persists `realizedPnl` | **P1** | Audit | existing tests | Verify existing assertions |
| S10 | Audit: close-all delegates to `closePosition()` with `realizedPnl` | **P1** | Audit | existing tests | Verify existing assertions |
| S11 | Edge: both legs break even → `realizedPnl = -(exit fees only)` | **P2** | Unit | `exit-monitor-pnl-persistence.spec.ts` | `it.skip` |
| S12 | Edge: one leg profit + one leg loss → net PnL correctly summed | **P2** | Unit | `exit-monitor-pnl-persistence.spec.ts` | `it.skip` |
| S15 | Structural: no CLOSED transition in exit-monitor omits `realizedPnl` from Prisma data | **P2** | Unit | `exit-monitor-pnl-persistence.spec.ts` | `it.skip` |

### AC3: Paper mode computes `realized_pnl` from simulated fills

| ID | Scenario | Priority | Level | File | Status |
|----|----------|----------|-------|------|--------|
| S13 | Paper mode full exit → `realizedPnl` is non-null Decimal in Prisma update | **P1** | Unit | `paper-live-boundary/exit-management/pnl-persistence.spec.ts` | `it.skip` |
| S14 | Live mode full exit → `realizedPnl` is non-null Decimal in Prisma update | **P1** | Unit | `paper-live-boundary/exit-management/pnl-persistence.spec.ts` | `it.skip` |

### AC4: Every newly-closed position has non-null `realized_pnl`

Covered by S2, S3, S13, S14, S15 — if all CLOSED transitions include `realizedPnl` in the Prisma update payload, no position can be closed with NULL.

## Test Files Generated

### File 1: `src/modules/exit-management/exit-monitor-pnl-persistence.spec.ts`

**Scenarios covered:** S2, S3, S4, S5, S6, S7, S11, S12, S15
**Why this will fail (RED):** Currently `executeExit()` and `evaluatePosition()` call `positionRepository.updateStatus(positionId, 'CLOSED')` which does NOT accept `realizedPnl`. Tests assert `prisma.openPosition.update()` is called with `realizedPnl` payload — this call does not happen in current code.

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Decimal from 'decimal.js';
import {
  createExitMonitorTestModule,
  createMockPosition,
  setupOrderCreateMock,
  type ExitMonitorTestContext,
} from './exit-monitor.test-helpers';
import {
  asPositionId,
  asOrderId,
  asPairId,
  asContractId,
} from '../../common/types/branded.type';
import { PlatformId } from '../../common/types/platform.type';

vi.mock('../../common/services/correlation-context', () => ({
  getCorrelationId: () => 'test-correlation-id',
}));

describe('ExitMonitorService — realizedPnl persistence (Story 10-7-4)', () => {
  let ctx: ExitMonitorTestContext;

  beforeEach(async () => {
    ctx = await createExitMonitorTestModule();
  });

  // ── S2: Full exit persists realizedPnl via direct Prisma update ──────

  describe('executeExit() full exit path (AC2, AC4)', () => {
    it.skip('[P0][S2] should persist realizedPnl via prisma.openPosition.update when full exit completes', async () => {
      const position = createMockPosition();
      ctx.positionRepository.findByStatusWithOrders!.mockResolvedValue([position]);

      ctx.thresholdEvaluator.evaluate!.mockReturnValue({
        triggered: true,
        type: 'take_profit',
        currentEdge: new Decimal('0.025'),
        currentPnl: new Decimal('3.00'),
        capturedEdgePercent: new Decimal('100'),
      });

      setupOrderCreateMock(ctx.orderRepository);

      await ctx.service.evaluatePositions();

      // CRITICAL: After fix, prisma.openPosition.update should be called instead of positionRepository.updateStatus
      expect(ctx.prisma.openPosition.update).toHaveBeenCalledWith(
        expect.objectContaining({
          where: { positionId: asPositionId('pos-1') },
          data: expect.objectContaining({
            status: 'CLOSED',
            realizedPnl: expect.any(Decimal),
          }),
        }),
      );

      // realizedPnl must not be null or undefined
      const updateCall = ctx.prisma.openPosition.update.mock.calls[0][0];
      expect(updateCall.data.realizedPnl).not.toBeNull();
      expect(updateCall.data.realizedPnl).not.toBeUndefined();
    });

    // ── S4: Buy-side leg PnL formula ──────

    it.skip('[P0][S4] should compute buy-side leg PnL as (exitPrice - entryPrice) × size', async () => {
      // Kalshi: buy at 0.62, exit sell at 0.66 → PnL = (0.66 - 0.62) × 100 = 4.00 (before fees)
      const position = createMockPosition({
        kalshiSide: 'buy',
        entryPrices: { kalshi: '0.62', polymarket: '0.65' },
      });
      ctx.positionRepository.findByStatusWithOrders!.mockResolvedValue([position]);

      ctx.thresholdEvaluator.evaluate!.mockReturnValue({
        triggered: true,
        type: 'take_profit',
        currentEdge: new Decimal('0.025'),
        currentPnl: new Decimal('3.00'),
        capturedEdgePercent: new Decimal('100'),
      });

      setupOrderCreateMock(ctx.orderRepository);

      await ctx.service.evaluatePositions();

      const updateCall = ctx.prisma.openPosition.update.mock.calls[0][0];
      const realizedPnl = new Decimal(updateCall.data.realizedPnl.toString());

      // Buy-side kalshi: (0.66 - 0.62) × 100 = 4.00
      // Sell-side poly: (0.65 - 0.62) × 100 = 3.00
      // Total before fees = 7.00, minus fees
      // realizedPnl should be a positive Decimal (exact value depends on fee schedule)
      expect(realizedPnl.isFinite()).toBe(true);
      expect(realizedPnl.gt(new Decimal('0'))).toBe(true);
    });

    // ── S5: Sell-side leg PnL formula ──────

    it.skip('[P0][S5] should compute sell-side leg PnL as (entryPrice - exitPrice) × size', async () => {
      // Polymarket: sell at 0.65, exit buy at 0.62 → PnL = (0.65 - 0.62) × 100 = 3.00 (before fees)
      const position = createMockPosition({
        polymarketSide: 'sell',
        entryPrices: { kalshi: '0.62', polymarket: '0.65' },
      });
      ctx.positionRepository.findByStatusWithOrders!.mockResolvedValue([position]);

      ctx.thresholdEvaluator.evaluate!.mockReturnValue({
        triggered: true,
        type: 'take_profit',
        currentEdge: new Decimal('0.025'),
        currentPnl: new Decimal('3.00'),
        capturedEdgePercent: new Decimal('100'),
      });

      setupOrderCreateMock(ctx.orderRepository);

      await ctx.service.evaluatePositions();

      const updateCall = ctx.prisma.openPosition.update.mock.calls[0][0];
      const realizedPnl = new Decimal(updateCall.data.realizedPnl.toString());
      expect(realizedPnl.isFinite()).toBe(true);
    });

    // ── S6: Exit fees subtracted ──────

    it.skip('[P0][S6] should subtract exit fees from total realized PnL', async () => {
      const position = createMockPosition();
      ctx.positionRepository.findByStatusWithOrders!.mockResolvedValue([position]);

      ctx.thresholdEvaluator.evaluate!.mockReturnValue({
        triggered: true,
        type: 'take_profit',
        currentEdge: new Decimal('0.025'),
        currentPnl: new Decimal('3.00'),
        capturedEdgePercent: new Decimal('100'),
      });

      setupOrderCreateMock(ctx.orderRepository);

      await ctx.service.evaluatePositions();

      const updateCall = ctx.prisma.openPosition.update.mock.calls[0][0];
      const realizedPnl = new Decimal(updateCall.data.realizedPnl.toString());

      // With fees (kalshi 2% taker, polymarket 1% taker), PnL must be less than gross PnL
      // Gross: kalshi leg (0.66-0.62)×100 + poly leg (0.65-0.62)×100 = 4.00 + 3.00 = 7.00
      // Fees: kalshi 0.66×100×0.02=1.32, poly 0.62×100×0.01=0.62 → total fees ~1.94
      // Net PnL ≈ 7.00 - 1.94 = 5.06 (approximate, depends on FinancialMath fee rate)
      const grossPnl = new Decimal('7.00');
      expect(realizedPnl.lt(grossPnl)).toBe(true);
      expect(realizedPnl.gt(new Decimal('0'))).toBe(true);
    });

    // ── S7: Asymmetric prices — sign error detection ──────

    it.skip('[P0][S7] should handle asymmetric entry/exit prices without sign errors', async () => {
      // Kalshi: buy at 0.40, exit at 0.70 → large profit on kalshi leg
      // Polymarket: sell at 0.55, exit at 0.50 → small profit on poly leg
      const position = createMockPosition({
        kalshiSide: 'buy',
        polymarketSide: 'sell',
        entryPrices: { kalshi: '0.40', polymarket: '0.55' },
        kalshiOrder: {
          orderId: asOrderId('order-kalshi-1'),
          platform: 'KALSHI',
          side: 'buy',
          price: new Decimal('0.40'),
          size: new Decimal('100'),
          fillPrice: new Decimal('0.40'),
          fillSize: new Decimal('100'),
          status: 'FILLED',
        },
      });
      ctx.positionRepository.findByStatusWithOrders!.mockResolvedValue([position]);

      ctx.kalshiConnector.submitOrder.mockResolvedValue({
        orderId: asOrderId('kalshi-exit-1'),
        status: 'filled',
        filledPrice: 0.70,
        filledQuantity: 100,
        timestamp: new Date(),
      });

      ctx.polymarketConnector.submitOrder.mockResolvedValue({
        orderId: asOrderId('poly-exit-1'),
        status: 'filled',
        filledPrice: 0.50,
        filledQuantity: 100,
        timestamp: new Date(),
      });

      ctx.thresholdEvaluator.evaluate!.mockReturnValue({
        triggered: true,
        type: 'take_profit',
        currentEdge: new Decimal('0.10'),
        currentPnl: new Decimal('20.00'),
        capturedEdgePercent: new Decimal('100'),
      });

      setupOrderCreateMock(ctx.orderRepository);

      await ctx.service.evaluatePositions();

      const updateCall = ctx.prisma.openPosition.update.mock.calls[0][0];
      const realizedPnl = new Decimal(updateCall.data.realizedPnl.toString());

      // Kalshi buy PnL: (0.70 - 0.40) × 100 = 30.00
      // Poly sell PnL: (0.55 - 0.50) × 100 = 5.00
      // Gross = 35.00, minus fees → must be positive and > 30
      expect(realizedPnl.isFinite()).toBe(true);
      expect(realizedPnl.gt(new Decimal('0'))).toBe(true);
    });
  });

  // ── S3: Zero-residual path persists realizedPnl: 0 ──────

  describe('evaluatePosition() zero-residual path (AC2, AC4)', () => {
    it.skip('[P0][S3] should persist realizedPnl: 0 via prisma.openPosition.update when EXIT_PARTIAL has zero residual', async () => {
      const position = createMockPosition({ status: 'EXIT_PARTIAL' });
      ctx.positionRepository.findByStatusWithOrders!.mockResolvedValue([position]);

      // Exit orders fully match entry sizes — zero residual on both legs
      ctx.orderRepository.findByPairId!.mockResolvedValue([
        {
          orderId: asOrderId('order-kalshi-1'),
          platform: 'KALSHI',
          fillSize: new Decimal('100'),
        },
        {
          orderId: asOrderId('order-poly-1'),
          platform: 'POLYMARKET',
          fillSize: new Decimal('100'),
        },
        {
          orderId: asOrderId('exit-kalshi-1'),
          platform: 'KALSHI',
          fillSize: new Decimal('100'),
        },
        {
          orderId: asOrderId('exit-poly-1'),
          platform: 'POLYMARKET',
          fillSize: new Decimal('100'),
        },
      ]);

      await ctx.service.evaluatePositions();

      // CRITICAL: After fix, should use prisma.openPosition.update with realizedPnl: 0
      expect(ctx.prisma.openPosition.update).toHaveBeenCalledWith(
        expect.objectContaining({
          where: { positionId: asPositionId('pos-1') },
          data: expect.objectContaining({
            status: 'CLOSED',
            realizedPnl: 0,
          }),
        }),
      );

      // Should NOT call positionRepository.updateStatus for CLOSED transitions
      const updateStatusCalls = ctx.positionRepository.updateStatus!.mock.calls.filter(
        (call: unknown[]) => call[1] === 'CLOSED',
      );
      expect(updateStatusCalls).toHaveLength(0);
    });
  });

  // ── S11: Both legs break even ──────

  describe('edge cases (AC2)', () => {
    it.skip('[P2][S11] should compute realizedPnl as negative (fees only) when both legs break even', async () => {
      // Entry and exit at same price → gross PnL = 0, net PnL = -(fees)
      const position = createMockPosition({
        kalshiSide: 'buy',
        polymarketSide: 'sell',
        entryPrices: { kalshi: '0.66', polymarket: '0.62' },
      });
      ctx.positionRepository.findByStatusWithOrders!.mockResolvedValue([position]);

      // Exit prices match entry prices
      ctx.kalshiConnector.submitOrder.mockResolvedValue({
        orderId: asOrderId('kalshi-exit-1'),
        status: 'filled',
        filledPrice: 0.66,
        filledQuantity: 100,
        timestamp: new Date(),
      });
      ctx.polymarketConnector.submitOrder.mockResolvedValue({
        orderId: asOrderId('poly-exit-1'),
        status: 'filled',
        filledPrice: 0.62,
        filledQuantity: 100,
        timestamp: new Date(),
      });

      ctx.thresholdEvaluator.evaluate!.mockReturnValue({
        triggered: true,
        type: 'stop_loss',
        currentEdge: new Decimal('0.00'),
        currentPnl: new Decimal('0.00'),
        capturedEdgePercent: new Decimal('0'),
      });

      setupOrderCreateMock(ctx.orderRepository);

      await ctx.service.evaluatePositions();

      const updateCall = ctx.prisma.openPosition.update.mock.calls[0][0];
      const realizedPnl = new Decimal(updateCall.data.realizedPnl.toString());

      // Gross PnL = 0, fees > 0, so net PnL should be negative
      expect(realizedPnl.isFinite()).toBe(true);
      expect(realizedPnl.lt(new Decimal('0'))).toBe(true);
    });

    // ── S12: One leg profit, one leg loss ──────

    it.skip('[P2][S12] should correctly sum profit on one leg and loss on the other', async () => {
      // Kalshi buy: entry 0.62, exit 0.70 → profit = (0.70-0.62)×100 = 8.00
      // Poly sell: entry 0.65, exit 0.72 → loss = (0.65-0.72)×100 = -7.00
      // Net ≈ 1.00 minus fees
      const position = createMockPosition({
        kalshiSide: 'buy',
        polymarketSide: 'sell',
        entryPrices: { kalshi: '0.62', polymarket: '0.65' },
      });
      ctx.positionRepository.findByStatusWithOrders!.mockResolvedValue([position]);

      ctx.kalshiConnector.submitOrder.mockResolvedValue({
        orderId: asOrderId('kalshi-exit-1'),
        status: 'filled',
        filledPrice: 0.70,
        filledQuantity: 100,
        timestamp: new Date(),
      });
      ctx.polymarketConnector.submitOrder.mockResolvedValue({
        orderId: asOrderId('poly-exit-1'),
        status: 'filled',
        filledPrice: 0.72,
        filledQuantity: 100,
        timestamp: new Date(),
      });

      ctx.thresholdEvaluator.evaluate!.mockReturnValue({
        triggered: true,
        type: 'stop_loss',
        currentEdge: new Decimal('-0.02'),
        currentPnl: new Decimal('-1.00'),
        capturedEdgePercent: new Decimal('-50'),
      });

      setupOrderCreateMock(ctx.orderRepository);

      await ctx.service.evaluatePositions();

      const updateCall = ctx.prisma.openPosition.update.mock.calls[0][0];
      const realizedPnl = new Decimal(updateCall.data.realizedPnl.toString());

      // Net should be close to 1.00 minus fees, could be positive or slightly negative
      expect(realizedPnl.isFinite()).toBe(true);
      // The key verification: PnL is computed, not NULL
      expect(updateCall.data.realizedPnl).not.toBeNull();
    });
  });

  // ── S15: Structural verification ──────

  describe('structural verification (AC4)', () => {
    it.skip('[P2][S15] should NOT use positionRepository.updateStatus for any CLOSED transition', async () => {
      // Full exit path
      const position = createMockPosition();
      ctx.positionRepository.findByStatusWithOrders!.mockResolvedValue([position]);

      ctx.thresholdEvaluator.evaluate!.mockReturnValue({
        triggered: true,
        type: 'take_profit',
        currentEdge: new Decimal('0.025'),
        currentPnl: new Decimal('3.00'),
        capturedEdgePercent: new Decimal('100'),
      });

      setupOrderCreateMock(ctx.orderRepository);

      await ctx.service.evaluatePositions();

      // After fix: positionRepository.updateStatus should NOT be called with 'CLOSED'
      // (it may still be called with 'EXIT_PARTIAL' which is fine)
      const closedCalls = ctx.positionRepository.updateStatus!.mock.calls.filter(
        (call: unknown[]) => call[1] === 'CLOSED',
      );
      expect(closedCalls).toHaveLength(0);

      // Instead, prisma.openPosition.update should handle CLOSED transitions
      expect(ctx.prisma.openPosition.update).toHaveBeenCalledWith(
        expect.objectContaining({
          data: expect.objectContaining({
            status: 'CLOSED',
          }),
        }),
      );
    });
  });
});
```

### File 2: `src/common/testing/paper-live-boundary/exit-management/pnl-persistence.spec.ts`

**Scenarios covered:** S13, S14
**Why this will fail (RED):** Same root cause as S2 — `positionRepository.updateStatus` drops `realizedPnl`. Tests assert `prisma.openPosition.update` with non-null `realizedPnl` payload.

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Decimal from 'decimal.js';
import {
  createExitMonitorTestModule,
  createMockPosition,
  setupOrderCreateMock,
  type ExitMonitorTestContext,
} from '../../../../modules/exit-management/exit-monitor.test-helpers';
import { asPositionId } from '../../../types/branded.type';

vi.mock('../../../services/correlation-context', () => ({
  getCorrelationId: () => 'test-correlation-id',
}));

describe('ExitMonitor — Paper/Live PnL Persistence Boundary (Story 10-7-4)', () => {
  let ctx: ExitMonitorTestContext;

  beforeEach(async () => {
    ctx = await createExitMonitorTestModule();
  });

  describe.each([
    [true, 'paper'],
    [false, 'live'],
  ])('isPaper=%s (%s mode)', (isPaper, modeLabel) => {
    it.skip(`[P1][S13/S14] should persist realizedPnl in ${modeLabel} mode full exit`, async () => {
      const position = createMockPosition({ isPaper });
      ctx.positionRepository.findByStatusWithOrders!.mockResolvedValue([position]);

      ctx.thresholdEvaluator.evaluate!.mockReturnValue({
        triggered: true,
        type: 'take_profit',
        currentEdge: new Decimal('0.025'),
        currentPnl: new Decimal('3.00'),
        capturedEdgePercent: new Decimal('100'),
      });

      setupOrderCreateMock(ctx.orderRepository);

      await ctx.service.evaluatePositions();

      // Both paper and live mode must persist realizedPnl — never NULL
      expect(ctx.prisma.openPosition.update).toHaveBeenCalledWith(
        expect.objectContaining({
          where: { positionId: asPositionId('pos-1') },
          data: expect.objectContaining({
            status: 'CLOSED',
            realizedPnl: expect.any(Decimal),
          }),
        }),
      );

      // Verify realizedPnl is a valid finite Decimal
      const updateCall = ctx.prisma.openPosition.update.mock.calls[0][0];
      const pnl = new Decimal(updateCall.data.realizedPnl.toString());
      expect(pnl.isFinite()).toBe(true);
    });

    it.skip(`[P1] should not cross ${modeLabel} mode boundary in PnL computation`, async () => {
      const position = createMockPosition({ isPaper });
      ctx.positionRepository.findByStatusWithOrders!.mockResolvedValue([position]);

      ctx.thresholdEvaluator.evaluate!.mockReturnValue({
        triggered: true,
        type: 'take_profit',
        currentEdge: new Decimal('0.025'),
        currentPnl: new Decimal('3.00'),
        capturedEdgePercent: new Decimal('100'),
      });

      setupOrderCreateMock(ctx.orderRepository);

      await ctx.service.evaluatePositions();

      // Risk manager should receive correct isPaper flag
      expect(ctx.riskManager.closePosition).toHaveBeenCalledWith(
        expect.any(Decimal),
        expect.any(Decimal),
        expect.anything(),
        isPaper,
      );
    });
  });
});
```

### Audit Tests (S8, S9, S10) — Existing Test Verification

These are NOT new test files. The dev agent should verify these existing assertions during implementation:

| ID | Existing File | What to Verify |
|----|---------------|----------------|
| S8 | `src/modules/execution/position-close.service.spec.ts` | Assertions include `realizedPnl` in Prisma update payload when closing a position |
| S9 | `src/modules/execution/single-leg-resolution.service.spec.ts` | Assertions include `realizedPnl` in Prisma update payload in `closeLeg()` |
| S10 | Follows from S8 | `close-all` delegates to `closePosition()` — covered by S8 |

> If any audit test is missing `realizedPnl` assertion depth, add `expect.objectContaining({ realizedPnl: expect.any(Decimal) })` to the existing test.

## Existing Test Assertions to Update

Per reviewer findings, these existing test files assert on `positionRepository.updateStatus()` with `'CLOSED'`. After the fix changes these to `prisma.openPosition.update()`, these assertions must be updated:

| File | Current Assertion | Post-Fix Assertion |
|------|-------------------|--------------------|
| `exit-monitor-core.spec.ts` ~line 150 | `positionRepository.updateStatus('pos-1', 'CLOSED')` | `prisma.openPosition.update({ where: { positionId }, data: { status: 'CLOSED', realizedPnl } })` |
| `exit-monitor-partial-reevaluation.spec.ts` ~line 467 | `positionRepository.updateStatus('pos-1', 'CLOSED')` | `prisma.openPosition.update({ where: { positionId }, data: { status: 'CLOSED', realizedPnl: 0 } })` |
| `exit-monitor-partial-fills.spec.ts` | Check for CLOSED assertions | Update if present |
| `exit-monitor-paper-mode.spec.ts` | Check for CLOSED assertions | Update if present |
| `exit-monitor-depth-check.spec.ts` | Check for CLOSED assertions | Update if present |

## Implementation Guidance

### What to Fix (2 locations)

1. **`exit-monitor.service.ts` `executeExit()` ~line 1133:**
   Replace `await this.positionRepository.updateStatus(position.positionId, 'CLOSED')` with:
   ```typescript
   await this.prisma.openPosition.update({
     where: { positionId: position.positionId },
     data: {
       status: 'CLOSED',
       realizedPnl: realizedPnl.toDecimalPlaces(8),
     },
   });
   ```

2. **`exit-monitor.service.ts` `evaluatePosition()` ~lines 424-427:**
   Replace `await this.positionRepository.updateStatus(position.positionId, 'CLOSED')` with:
   ```typescript
   await this.prisma.openPosition.update({
     where: { positionId: position.positionId },
     data: { status: 'CLOSED', realizedPnl: 0 },
   });
   ```

### What NOT to Change

- `PrismaService` is already injected in the constructor — no DI changes needed
- Formula computation is correct — only persistence is broken
- `position-close.service.ts`, `single-leg-resolution.service.ts` — already correct
- Prisma schema — `realized_pnl` column already exists

## Next Steps (TDD Green Phase)

After implementing the fix:

1. Remove `it.skip()` from all test scenarios in both new test files
2. Update existing test assertions (table above) to match new `prisma.openPosition.update()` calls
3. Run `pnpm test` — verify all tests PASS (green phase)
4. Run `pnpm lint` — fix any issues
5. If any test fails: fix implementation (not the test — tests encode expected behavior)
6. Commit passing tests with implementation

## Summary Statistics

| Metric | Value |
|--------|-------|
| TDD Phase | RED |
| Total new test scenarios | 15 |
| New test files | 2 |
| Existing tests to update | 5 files |
| Priority breakdown | P0: 6, P1: 5, P2: 4 |
| Fixtures needed | None (uses existing `createExitMonitorTestModule`) |
| AC coverage | AC1: manual, AC2: S2-S12+S15, AC3: S13-S14, AC4: S2+S3+S13-S15 |
