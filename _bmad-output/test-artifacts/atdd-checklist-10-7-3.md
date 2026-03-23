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
inputDocuments:
  - _bmad-output/implementation-artifacts/10-7-3-c5-exit-depth-slippage-band-correction.md
  - pm-arbitrage-engine/src/modules/exit-management/exit-monitor-depth-check.spec.ts
  - pm-arbitrage-engine/src/modules/exit-management/exit-monitor.test-helpers.ts
  - pm-arbitrage-engine/src/modules/exit-management/exit-monitor.service.ts
  - _bmad/tea/testarch/knowledge/data-factories.md
  - _bmad/tea/testarch/knowledge/test-quality.md
  - _bmad/tea/testarch/knowledge/test-levels-framework.md
  - _bmad/tea/testarch/knowledge/test-priorities-matrix.md
  - _bmad/tea/testarch/knowledge/test-healing-patterns.md
---

# ATDD Checklist: Story 10-7-3 — C5 Exit Depth Slippage Band Correction

## TDD Red Phase

All 14 failing tests generated with `it.skip()`.

| Test File | Test Count | Status |
|---|---|---|
| `src/modules/exit-management/exit-monitor-depth-check.spec.ts` | 8 | Skipped (RED) |
| `src/common/config/config-defaults.spec.ts` | 3 | Skipped (RED) |
| `src/common/config/config-accessor.service.spec.ts` | 1 | Skipped (RED) |
| `src/dashboard/settings.service.spec.ts` | 1 | Skipped (RED) |
| `src/dashboard/dto/update-settings.dto.spec.ts` (if exists) | 1 | Skipped (RED) |
| **Total** | **14** | **All skipped** |

## Story Summary

**As an** operator,
**I want** the C5 liquidity_deterioration criterion to count depth within a configurable slippage band around VWAP,
**So that** the depth metric doesn't systematically understate executable liquidity.

**Root cause:** `getAvailableExitDepth()` uses VWAP as a hard price cutoff, excluding the very liquidity that produced the VWAP. Only the single best-level quantity passes the strict cutoff while the rest of the fillable book is excluded.

**Fix:** Add configurable `EXIT_DEPTH_SLIPPAGE_TOLERANCE` (default 2%) so the price cutoff includes levels slightly beyond VWAP.

## Acceptance Criteria Coverage

### AC-1: Tolerance band applied to depth cutoff (P0)

- [ ] 1.1 buy-close with 2% tolerance includes ask levels within band — VWAP=0.50, 2% band → cutoff 0.51, asks at 0.50 (qty 1) and 0.505 (qty 10) included → depth = 11
- [ ] 1.2 sell-close with 2% tolerance includes bid levels within band — VWAP=0.60, 2% band → cutoff 0.588, bids at 0.60 (qty 5) and 0.59 (qty 8) included → depth = 13
- [ ] 1.3 Levels beyond tolerance band are excluded — ask at 0.52 excluded when buy-close cutoff is 0.51
- [ ] 1.4 All levels within band accumulates total depth correctly — 3-level book with all within band, verify exact sum
- [ ] 1.5 Empty order book returns zero depth (regression — unchanged behavior)

### AC-2: Configurable via EngineConfig DB (P1)

- [ ] 2.1 `config-defaults.ts` includes `exitDepthSlippageTolerance` with envKey `EXIT_DEPTH_SLIPPAGE_TOLERANCE` and default 0.02
- [ ] 2.2 `settings-metadata.ts` has the setting in `SettingsGroup.ExitStrategy` group with type `'decimal'`, min 0, max 1
- [ ] 2.3 `update-settings.dto.ts` field validates range [0, 1] with `@IsNumber() @Min(0) @Max(1)`
- [ ] 2.4 Settings count is 74 (was 73)
- [ ] 2.5 `config-accessor.service.spec.ts` mock includes `exitDepthSlippageTolerance: 0.02`
- [ ] 2.6 Hot-reload updates `exitDepthSlippageTolerance` in ExitMonitorService via `CONFIG_SETTINGS_UPDATED` event — verify field value changes after reload

### AC-3: Backward compatibility at zero tolerance (P0)

- [ ] 3.1 tolerance=0.0 produces identical behavior to strict-VWAP cutoff — same book as 1.1 but tolerance=0 → only qty at exactly VWAP or better
- [ ] 3.2 Full `evaluatePositions()` cycle with 2% tolerance — C5 does NOT trigger when sufficient depth exists within band (integration)
- [ ] 3.3 Full `evaluatePositions()` cycle — C5 still triggers when depth is insufficient even with tolerance band (integration)

## Priority Distribution

| Priority | Count | Percentage |
|----------|-------|------------|
| P0 | 6 | 43% |
| P1 | 5 | 36% |
| P2 | 3 | 21% |
| **Total** | **14** | **100%** |

## Test Location Map

| Test Scenario | File | Describe Block |
|---|---|---|
| 1.1–1.5, 3.1 | `exit-monitor-depth-check.spec.ts` | `tolerance band (10-7-3)` |
| 3.2–3.3 | `exit-monitor-depth-check.spec.ts` | `tolerance band integration (10-7-3)` |
| 2.1–2.3 | `config-defaults.spec.ts` | Existing ordered-key / envKey / metadata tests |
| 2.4 | `settings.service.spec.ts` | Settings count assertion |
| 2.5 | `config-accessor.service.spec.ts` | `buildMockEffectiveConfig` helper |
| 2.6 | `exit-monitor-depth-check.spec.ts` | `tolerance band (10-7-3)` hot-reload |

## Red Phase Failure Reasons

Every test is designed to fail before implementation for a specific reason:

| Scenario | Why It Fails (Red Phase) |
|---|---|
| 1.1–1.4, 3.1 | `getAvailableExitDepth()` doesn't accept `slippageTolerance` parameter — TypeError or unchanged strict cutoff |
| 1.5 | Regression — should pass immediately (empty book = 0) |
| 2.1 | `exitDepthSlippageTolerance` key not in `config-defaults.ts` |
| 2.2 | Key not in `settings-metadata.ts` |
| 2.3 | Field not in `update-settings.dto.ts` |
| 2.4 | Count is still 73, not 74 |
| 2.5 | Key missing from mock config |
| 2.6 | Reload handler doesn't process `exitDepthSlippageTolerance` |
| 3.2–3.3 | Call sites don't pass tolerance → strict cutoff produces wrong depth |

## Next Steps (TDD Green Phase)

After implementing the feature:

1. Remove `it.skip()` from all test scenarios above
2. Run tests: `cd pm-arbitrage-engine && pnpm test`
3. Verify tests PASS (green phase)
4. If any tests fail:
   - Either fix implementation (feature bug)
   - Or fix test (test bug — incorrect expectation)
5. Run `pnpm lint` and commit

## Implementation Guidance

### Files to modify (production code)

| File | Change |
|---|---|
| `src/common/config/env.schema.ts` | Add `EXIT_DEPTH_SLIPPAGE_TOLERANCE` validator |
| `src/common/config/config-defaults.ts` | Add `exitDepthSlippageTolerance` entry |
| `src/common/config/settings-metadata.ts` | Add metadata under Exit Strategy group |
| `src/common/config/effective-config.types.ts` | Add `exitDepthSlippageTolerance: number` |
| `src/dashboard/dto/update-settings.dto.ts` | Add DTO field with validators |
| `src/dashboard/settings.service.ts` | Add to SERVICE_RELOAD_MAP + exit-monitor handler |
| `src/persistence/repositories/engine-config.repository.ts` | Add to resolve chain |
| `prisma/schema.prisma` | Add column to EngineConfig |
| `src/modules/exit-management/exit-monitor.service.ts` | Add field, constructor init, reloadConfig, modify `getAvailableExitDepth()`, update call sites |

### Key method signature change

```typescript
// Before
private async getAvailableExitDepth(
  connector: IPlatformConnector,
  contractId: string,
  closeSide: 'buy' | 'sell',
  closePrice: Decimal,
): Promise<Decimal>

// After
private async getAvailableExitDepth(
  connector: IPlatformConnector,
  contractId: string,
  closeSide: 'buy' | 'sell',
  closePrice: Decimal,
  slippageTolerance: number,  // NEW
): Promise<Decimal>
```

### Tolerance band math

```
Buy-close (consuming asks):  cutoff = closePrice × (1 + tolerance)
Sell-close (consuming bids): cutoff = closePrice × (1 - tolerance)
```
