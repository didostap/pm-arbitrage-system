---
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-03-27'
workflowType: 'testarch-atdd'
inputDocuments:
  - '_bmad-output/implementation-artifacts/10-9-4-calibration-report-sensitivity-analysis.md'
  - '_bmad-output/implementation-artifacts/10-9-0-design-doc.md'
  - '_bmad/tea/testarch/knowledge/data-factories.md'
  - '_bmad/tea/testarch/knowledge/test-quality.md'
  - '_bmad/tea/testarch/knowledge/test-levels-framework.md'
  - '_bmad/tea/testarch/knowledge/test-priorities-matrix.md'
  - '_bmad/tea/testarch/knowledge/test-healing-patterns.md'
  - '_bmad/tea/testarch/knowledge/ci-burn-in.md'
---

# ATDD Checklist - Epic 10-9, Story 10-9.4: Calibration Report Generation with Sensitivity Analysis

**Date:** 2026-03-27
**Author:** Arbi
**Primary Test Level:** Unit + Integration (backend)

---

## Story Summary

**As an** operator
**I want** backtest results presented as a calibration report with recommended parameter values, confidence intervals, sensitivity analysis, and out-of-sample validation
**So that** I can make informed parameter decisions with clear risk boundaries and confidence against overfitting

---

## Acceptance Criteria

1. Calibration report includes summary metrics: total trades, profit factor, net P&L, max drawdown, Sharpe ratio, win rate, average edge captured vs expected
2. Recommended parameter values identified — the parameter set that maximizes profit factor (primary) or Sharpe (secondary)
3. Bootstrap resampling (1000+ iterations) produces 95% CI for profit factor and Sharpe ratio
4. Sensitivity parameter sweeps compute profit factor, max drawdown, and Sharpe at each point: edge threshold 0.5%–5.0% in 0.1% steps, position sizing 1%–5% in 0.5% steps, max concurrent pairs 5–30 in steps of 5, trading window full-day vs top-performing UTC hour ranges
5. Degradation boundaries identify parameter values where profit factor drops below 1.0 (breakeven)
6. Walk-forward analysis trains on first N% of the date range and tests on remaining (100-N)% with configurable split ratio (default 70/30), reporting in-sample vs out-of-sample metrics separately. Parameters showing >30% degradation flagged as potential overfits.
7. Calibration report documents known limitations (10 items from design doc section 4.8)
8. Calibration report includes data quality summary: coverage gaps, excluded periods, pair count, total data points analyzed
9. Report persisted in BacktestRun record and sensitivity charts renderable by dashboard (JSON structure compatible)

---

## Failing Tests Created (RED Phase)

### Task 1: Prisma Schema Migration Tests (3 tests)

**File:** `src/modules/backtesting/dto/backtest-result.dto.spec.ts` (EXTEND existing, ~40 lines added)

- [ ] **Test:** [P1] should include `report` field as `Record<string, unknown> | null` in BacktestRunResponseDto
  - **Status:** RED — field not added to DTO
  - **Verifies:** AC #9 — report field in response
- [ ] **Test:** [P1] should include `walkForwardResults` field as `Record<string, unknown> | null` in BacktestRunResponseDto
  - **Status:** RED — field not added to DTO
  - **Verifies:** AC #9 — walk-forward field in response
- [ ] **Test:** [P1] should include `sensitivityResults` field as `Record<string, unknown> | null` in BacktestRunResponseDto
  - **Status:** RED — field not added to DTO
  - **Verifies:** AC #9 — sensitivity field in response

---

### Task 2: Report Types, Error Code, Events Tests (16 tests)

**File:** `src/modules/backtesting/types/calibration-report.types.spec.ts` (NEW, ~200 lines)

- [ ] **Test:** [P1] should construct CalibrationReport with summaryMetrics, confidenceIntervals, knownLimitations, dataQualitySummary, generatedAt
  - **Status:** RED — CalibrationReport interface does not exist
  - **Verifies:** AC #1, #3, #7, #8 — report type structure
- [ ] **Test:** [P1] should construct SummaryMetrics with totalTrades, profitFactor, netPnl, maxDrawdown, sharpeRatio, winRate, avgEdgeCapturedVsExpected
  - **Status:** RED — SummaryMetrics interface does not exist
  - **Verifies:** AC #1 — summary metrics shape
- [ ] **Test:** [P1] should construct BootstrapCIResult with iterations, confidence, profitFactor CI bounds, sharpeRatio CI bounds
  - **Status:** RED — BootstrapCIResult interface does not exist
  - **Verifies:** AC #3 — CI type structure
- [ ] **Test:** [P1] should construct WalkForwardResults with trainPct, testPct, date ranges, metrics, degradation, overfitFlags
  - **Status:** RED — WalkForwardResults interface does not exist
  - **Verifies:** AC #6 — walk-forward type structure
- [ ] **Test:** [P1] should construct SensitivityResults with sweeps array, degradationBoundaries, recommendedParameters, partial flag, counts
  - **Status:** RED — SensitivityResults interface does not exist
  - **Verifies:** AC #4, #5 — sensitivity type structure
- [ ] **Test:** [P1] should construct SweepConfig with optional range configs and timeoutSeconds
  - **Status:** RED — SweepConfig interface does not exist
  - **Verifies:** AC #4 — sweep configuration type
- [ ] **Test:** [P1] should export REPORT_DECIMAL_PRECISION = 10 and REPORT_DECIMAL_PRECISION_SHORT = 6
  - **Status:** RED — constants not defined
  - **Verifies:** Cross-cutting — decimal precision standardization
- [ ] **Test:** [P1] should export KNOWN_LIMITATIONS as string array with exactly 10 items matching design doc section 4.8
  - **Status:** RED — constant not defined
  - **Verifies:** AC #7 — known limitations completeness

**File:** `src/common/errors/system-health-error.spec.ts` (EXTEND existing, ~20 lines added)

- [ ] **Test:** [P1] should define BACKTEST_REPORT_ERROR with code 4205
  - **Status:** RED — error code 4205 not defined
  - **Verifies:** AC #4, #5 — report error code
- [ ] **Test:** [P1] should have no duplicate error codes across all SYSTEM_HEALTH_ERROR_CODES (including 4205)
  - **Status:** GREEN (existing pattern) — verify 4205 integrated
  - **Verifies:** Cross-cutting — error code uniqueness

**File:** `src/common/events/backtesting.events.spec.ts` (EXTEND existing, ~80 lines added)

- [ ] **Test:** [P1] should construct BacktestReportGeneratedEvent with runId and summary snapshot
  - **Status:** RED — event class does not exist
  - **Verifies:** AC #9 — report event emission
- [ ] **Test:** [P1] should construct BacktestSensitivityCompletedEvent with runId, sweepCount, and recommendedParams
  - **Status:** RED — event class does not exist
  - **Verifies:** AC #4 — sensitivity event emission
- [ ] **Test:** [P1] should construct BacktestWalkForwardCompletedEvent with runId and overfit flag summary
  - **Status:** RED — event class does not exist
  - **Verifies:** AC #6 — walk-forward event emission
- [ ] **Test:** [P1] should register backtesting.report.generated in EVENT_NAMES catalog
  - **Status:** RED — event name not registered
  - **Verifies:** Cross-cutting — event catalog completeness
- [ ] **Test:** [P1] should register backtesting.sensitivity.completed in EVENT_NAMES catalog
  - **Status:** RED — event name not registered
  - **Verifies:** Cross-cutting — event catalog completeness
- [ ] **Test:** [P1] should register backtesting.walkforward.completed in EVENT_NAMES catalog
  - **Status:** RED — event name not registered
  - **Verifies:** Cross-cutting — event catalog completeness

---

### Task 3: CalibrationReportService Tests (24 tests)

**File:** `src/modules/backtesting/reporting/calibration-report.service.spec.ts` (NEW, ~400 lines)

**generateReport() — 10 tests:**

- [ ] **Test:** [P0] should load BacktestRun and positions from DB and produce CalibrationReport with all required sections
  - **Status:** RED — CalibrationReportService does not exist
  - **Verifies:** AC #1, #7, #8 — complete report generation
- [ ] **Test:** [P0] should calculate totalTrades equal to the number of closed positions
  - **Status:** RED — CalibrationReportService does not exist
  - **Verifies:** AC #1 — totalTrades metric
- [ ] **Test:** [P0] should calculate winRate as winCount / totalPositions (decimal 0.0–1.0)
  - **Status:** RED — CalibrationReportService does not exist
  - **Verifies:** AC #1 — win rate formula
- [ ] **Test:** [P0] should calculate avgEdgeCapturedVsExpected as mean of (realizedPnl/positionSizeUsd) vs entryEdge across positions
  - **Status:** RED — CalibrationReportService does not exist
  - **Verifies:** AC #1 — avg edge captured vs expected metric
- [ ] **Test:** [P1] should include profitFactor, netPnl, maxDrawdown, sharpeRatio from BacktestRun aggregate metrics
  - **Status:** RED — CalibrationReportService does not exist
  - **Verifies:** AC #1 — summary metrics from existing aggregate
- [ ] **Test:** [P0] should include all 10 KNOWN_LIMITATIONS verbatim from design doc section 4.8
  - **Status:** RED — CalibrationReportService does not exist
  - **Verifies:** AC #7 — known limitations completeness
- [ ] **Test:** [P1] should produce DataQualitySummary with pairCount, totalDataPoints, coverageGaps, excludedPeriods, dateRange
  - **Status:** RED — CalibrationReportService does not exist
  - **Verifies:** AC #8 — data quality summary structure
- [ ] **Test:** [P1] should detect coverage gaps from HistoricalPrice records (gap count per pair, total gap minutes)
  - **Status:** RED — CalibrationReportService does not exist
  - **Verifies:** AC #8 — gap detection
- [ ] **Test:** [P0] should persist report JSON to BacktestRun.report column
  - **Status:** RED — CalibrationReportService does not exist
  - **Verifies:** AC #9 — report persistence
- [ ] **Test:** [P0] should emit BacktestReportGeneratedEvent with runId and summary (expect.objectContaining)
  - **Status:** RED — CalibrationReportService does not exist
  - **Verifies:** AC #9 — event emission with payload

**bootstrapConfidenceIntervals() — 10 tests:**

- [ ] **Test:** [P0] should produce 95% CI for profit factor with 1000 iterations on fixture positions
  - **Status:** RED — CalibrationReportService does not exist
  - **Verifies:** AC #3 — bootstrap CI for profit factor
- [ ] **Test:** [P0] should produce 95% CI for Sharpe ratio with 1000 iterations on fixture positions
  - **Status:** RED — CalibrationReportService does not exist
  - **Verifies:** AC #3 — bootstrap CI for Sharpe
- [ ] **Test:** [P0] should return CI where lower < upper for both profit factor and Sharpe
  - **Status:** RED — CalibrationReportService does not exist
  - **Verifies:** AC #3 — CI ordering invariant
- [ ] **Test:** [P1] should narrow CI width as iteration count increases (1000 vs 100 comparison)
  - **Status:** RED — CalibrationReportService does not exist
  - **Verifies:** AC #3 — CI convergence behavior
- [ ] **Test:** [P0] should return null CI when positions.length < 2
  - **Status:** RED — CalibrationReportService does not exist
  - **Verifies:** AC #3 — edge case: too few positions
- [ ] **Test:** [P1] should return null CI when > 50% of bootstrap samples produce null metric
  - **Status:** RED — CalibrationReportService does not exist
  - **Verifies:** AC #3 — null metric dominance handling
- [ ] **Test:** [P0] should handle all-wins scenario (profitFactor null from 0 gross loss, Sharpe valid)
  - **Status:** RED — CalibrationReportService does not exist
  - **Verifies:** AC #3 — edge case: all wins
- [ ] **Test:** [P0] should handle all-losses scenario (profitFactor 0, Sharpe valid negative)
  - **Status:** RED — CalibrationReportService does not exist
  - **Verifies:** AC #3 — edge case: all losses
- [ ] **Test:** [P1] should handle single-position input (return null — < 2 positions)
  - **Status:** RED — CalibrationReportService does not exist
  - **Verifies:** AC #3 — edge case: single position
- [ ] **Test:** [P0] should handle zero-stddev returns (Sharpe null, profitFactor CI valid)
  - **Status:** RED — CalibrationReportService does not exist
  - **Verifies:** AC #3 — edge case: identical P&L across positions

**Edge cases — 4 tests:**

- [ ] **Test:** [P0] should handle 0 positions (empty report with null metrics)
  - **Status:** RED — CalibrationReportService does not exist
  - **Verifies:** AC #1, #3 — empty run edge case
- [ ] **Test:** [P1] should throw BACKTEST_REPORT_ERROR 4205 when BacktestRun not found
  - **Status:** RED — CalibrationReportService does not exist
  - **Verifies:** Cross-cutting — error handling
- [ ] **Test:** [P1] should throw BACKTEST_REPORT_ERROR 4205 when BacktestRun status is not COMPLETE
  - **Status:** RED — CalibrationReportService does not exist
  - **Verifies:** Cross-cutting — precondition validation
- [ ] **Test:** [P1] should use Decimal arithmetic throughout (no native JS operators on monetary values)
  - **Status:** RED — CalibrationReportService does not exist
  - **Verifies:** Cross-cutting — financial math precision

---

### Task 4: WalkForwardService Tests (16 tests)

**File:** `src/modules/backtesting/reporting/walk-forward.service.spec.ts` (NEW, ~280 lines)

**splitTimeSteps() — 6 tests:**

- [ ] **Test:** [P0] should split 100 time steps at 70% boundary into 70 train and 30 test
  - **Status:** RED — WalkForwardService does not exist
  - **Verifies:** AC #6 — chronological split default 70/30
- [ ] **Test:** [P0] should maintain chronological order (train steps before test steps, no shuffling)
  - **Status:** RED — WalkForwardService does not exist
  - **Verifies:** AC #6 — chronological ordering invariant
- [ ] **Test:** [P1] should handle custom split ratio (e.g., 80/20)
  - **Status:** RED — WalkForwardService does not exist
  - **Verifies:** AC #6 — configurable split ratio
- [ ] **Test:** [P1] should handle empty time steps (return empty train and test)
  - **Status:** RED — WalkForwardService does not exist
  - **Verifies:** AC #6 — edge case: no data
- [ ] **Test:** [P1] should handle single time step (all in train, empty test)
  - **Status:** RED — WalkForwardService does not exist
  - **Verifies:** AC #6 — edge case: minimal data
- [ ] **Test:** [P2] should floor boundary index (70 steps at 70% → index 49, train=49, test=21)
  - **Status:** RED — WalkForwardService does not exist
  - **Verifies:** AC #6 — boundary rounding behavior

**compareMetrics() — 10 tests:**

- [ ] **Test:** [P0] should compute degradation percentage for profitFactor between train and test
  - **Status:** RED — WalkForwardService does not exist
  - **Verifies:** AC #6 — degradation calculation
- [ ] **Test:** [P0] should compute degradation percentage for sharpeRatio between train and test
  - **Status:** RED — WalkForwardService does not exist
  - **Verifies:** AC #6 — degradation calculation
- [ ] **Test:** [P0] should compute degradation percentage for totalPnl between train and test
  - **Status:** RED — WalkForwardService does not exist
  - **Verifies:** AC #6 — degradation calculation
- [ ] **Test:** [P0] should flag metrics with >30% degradation as potential overfits in overfitFlags array
  - **Status:** RED — WalkForwardService does not exist
  - **Verifies:** AC #6 — overfit detection at 30% threshold
- [ ] **Test:** [P0] should not flag metrics with <=30% degradation
  - **Status:** RED — WalkForwardService does not exist
  - **Verifies:** AC #6 — threshold boundary (not overfit)
- [ ] **Test:** [P0] should flag exactly at 30.01% degradation but not at 30.00%
  - **Status:** RED — WalkForwardService does not exist
  - **Verifies:** AC #6 — boundary precision (>30%, not >=30%)
- [ ] **Test:** [P1] should return null degradation when train metric is null (e.g., null Sharpe from zero stddev)
  - **Status:** RED — WalkForwardService does not exist
  - **Verifies:** AC #6 — null metric handling
- [ ] **Test:** [P1] should return null degradation when test metric is null
  - **Status:** RED — WalkForwardService does not exist
  - **Verifies:** AC #6 — null metric handling
- [ ] **Test:** [P1] should handle negative improvement (test better than train) as negative degradation, not flagged
  - **Status:** RED — WalkForwardService does not exist
  - **Verifies:** AC #6 — improvement direction
- [ ] **Test:** [P1] should handle train metric = 0 (division by zero → null degradation)
  - **Status:** RED — WalkForwardService does not exist
  - **Verifies:** AC #6 — zero divisor edge case

---

### Task 4 (continued): BacktestEngineService Walk-Forward Pipeline Tests (10 tests)

**File:** `src/modules/backtesting/engine/backtest-engine.service.spec.ts` (EXTEND existing, ~150 lines added)

**runHeadlessSimulation() — 4 tests:**

- [ ] **Test:** [P0] should run simulation loop, close remaining positions, and return AggregateMetrics without state machine
  - **Status:** RED — runHeadlessSimulation method does not exist
  - **Verifies:** AC #6 — headless simulation execution
- [ ] **Test:** [P0] should create temporary runId and clean up via portfolioService.destroyRun in finally block
  - **Status:** RED — runHeadlessSimulation method does not exist
  - **Verifies:** Cross-cutting — collection lifecycle (cleanup guaranteed)
- [ ] **Test:** [P1] should not emit state change events during headless run
  - **Status:** RED — runHeadlessSimulation method does not exist
  - **Verifies:** AC #6 — headless runs are invisible to event subscribers
- [ ] **Test:** [P1] should not persist results to DB during headless run
  - **Status:** RED — runHeadlessSimulation method does not exist
  - **Verifies:** AC #6 — headless runs leave no persistence side effects

**Walk-forward pipeline integration — 6 tests:**

- [ ] **Test:** [P0] should run 3 simulation passes (train, test, full) when walkForwardEnabled=true
  - **Status:** RED — walk-forward pipeline not implemented
  - **Verifies:** AC #6 — 3-pass execution
- [ ] **Test:** [P0] should persist canonical aggregate metrics from full-range simulation (not train-only or test-only)
  - **Status:** RED — walk-forward pipeline not implemented
  - **Verifies:** AC #6 — canonical metrics from full range
- [ ] **Test:** [P0] should persist WalkForwardResults to BacktestRun.walkForwardResults column
  - **Status:** RED — walk-forward pipeline not implemented
  - **Verifies:** AC #6, #9 — walk-forward persistence
- [ ] **Test:** [P0] should emit BacktestWalkForwardCompletedEvent with runId and overfit summary
  - **Status:** RED — walk-forward pipeline not implemented
  - **Verifies:** AC #6 — event emission
- [ ] **Test:** [P1] should reset portfolio between train and test passes
  - **Status:** RED — walk-forward pipeline not implemented
  - **Verifies:** AC #6 — portfolio isolation between phases
- [ ] **Test:** [P1] should log INFO warning about 3x cost when walk-forward is enabled
  - **Status:** RED — walk-forward pipeline not implemented
  - **Verifies:** AC #6 — performance documentation

---

### Task 5: SensitivityAnalysisService Tests (24 tests)

**File:** `src/modules/backtesting/reporting/sensitivity-analysis.service.spec.ts` (NEW, ~450 lines)

**runSweep() — 8 tests:**

- [ ] **Test:** [P0] should execute one-dimensional sweeps for all 4 parameter dimensions (edge, position size, max pairs, trading window)
  - **Status:** RED — SensitivityAnalysisService does not exist
  - **Verifies:** AC #4 — parameter sweep execution
- [ ] **Test:** [P0] should use default sweep ranges when no SweepConfig provided (46 + 9 + 6 + 5 = ~66 points)
  - **Status:** RED — SensitivityAnalysisService does not exist
  - **Verifies:** AC #4 — default ranges
- [ ] **Test:** [P0] should collect profitFactor, maxDrawdown, sharpeRatio, totalPnl at each sweep point
  - **Status:** RED — SensitivityAnalysisService does not exist
  - **Verifies:** AC #4 — metrics per sweep point
- [ ] **Test:** [P0] should load data ONCE and reuse across all sweep iterations (not reload per sweep)
  - **Status:** RED — SensitivityAnalysisService does not exist
  - **Verifies:** AC #4 — performance: data loaded once
- [ ] **Test:** [P0] should hold all other params at base config values during each sweep dimension
  - **Status:** RED — SensitivityAnalysisService does not exist
  - **Verifies:** AC #4 — one-dimensional sweep correctness
- [ ] **Test:** [P0] should persist SensitivityResults to BacktestRun.sensitivityResults column
  - **Status:** RED — SensitivityAnalysisService does not exist
  - **Verifies:** AC #9 — sensitivity persistence
- [ ] **Test:** [P0] should emit BacktestSensitivityCompletedEvent with runId, sweepCount, recommendedParams
  - **Status:** RED — SensitivityAnalysisService does not exist
  - **Verifies:** AC #4 — event emission
- [ ] **Test:** [P1] should run sensitivity on full dataset regardless of walk-forward mode
  - **Status:** RED — SensitivityAnalysisService does not exist
  - **Verifies:** AC #4 — sensitivity always uses full data

**SweepConfig validation — 5 tests:**

- [ ] **Test:** [P1] should reject inverted range (min > max) with BACKTEST_REPORT_ERROR 4205
  - **Status:** RED — SensitivityAnalysisService does not exist
  - **Verifies:** AC #4 — input validation
- [ ] **Test:** [P1] should reject zero step with BACKTEST_REPORT_ERROR 4205
  - **Status:** RED — SensitivityAnalysisService does not exist
  - **Verifies:** AC #4 — input validation
- [ ] **Test:** [P1] should reject negative values with BACKTEST_REPORT_ERROR 4205
  - **Status:** RED — SensitivityAnalysisService does not exist
  - **Verifies:** AC #4 — input validation
- [ ] **Test:** [P1] should reject pct fields > 1.0 with BACKTEST_REPORT_ERROR 4205
  - **Status:** RED — SensitivityAnalysisService does not exist
  - **Verifies:** AC #4 — input validation
- [ ] **Test:** [P1] should reject timeoutSeconds > 7200 or <= 0 with BACKTEST_REPORT_ERROR 4205
  - **Status:** RED — SensitivityAnalysisService does not exist
  - **Verifies:** AC #4 — timeout validation

**Degradation boundary detection — 4 tests:**

- [ ] **Test:** [P0] should find breakeven value where profitFactor crosses below 1.0 via linear interpolation
  - **Status:** RED — SensitivityAnalysisService does not exist
  - **Verifies:** AC #5 — degradation boundary detection
- [ ] **Test:** [P0] should return null breakeven when profitFactor never crosses 1.0 (always profitable)
  - **Status:** RED — SensitivityAnalysisService does not exist
  - **Verifies:** AC #5 — no crossing edge case
- [ ] **Test:** [P1] should return null breakeven when profitFactor is always below 1.0 (always unprofitable)
  - **Status:** RED — SensitivityAnalysisService does not exist
  - **Verifies:** AC #5 — always-unprofitable edge case
- [ ] **Test:** [P1] should skip null profitFactor points in interpolation
  - **Status:** RED — SensitivityAnalysisService does not exist
  - **Verifies:** AC #5 — null handling in boundary detection

**Recommended parameters — 3 tests:**

- [ ] **Test:** [P0] should identify parameter values maximizing profitFactor (primary recommendation)
  - **Status:** RED — SensitivityAnalysisService does not exist
  - **Verifies:** AC #2 — recommended by profit factor
- [ ] **Test:** [P0] should identify parameter values maximizing Sharpe (secondary recommendation)
  - **Status:** RED — SensitivityAnalysisService does not exist
  - **Verifies:** AC #2 — recommended by Sharpe
- [ ] **Test:** [P1] should handle all-null profitFactor or Sharpe gracefully (empty recommendation)
  - **Status:** RED — SensitivityAnalysisService does not exist
  - **Verifies:** AC #2 — edge case: no valid metrics

**Timeout and concurrency — 4 tests:**

- [ ] **Test:** [P0] should persist partial results and abort with BACKTEST_REPORT_ERROR when timeout exceeded
  - **Status:** RED — SensitivityAnalysisService does not exist
  - **Verifies:** AC #4 — timeout with partial results
- [ ] **Test:** [P0] should set `partial: true` flag in results JSON when timeout interrupts
  - **Status:** RED — SensitivityAnalysisService does not exist
  - **Verifies:** AC #4 — partial flag correctness
- [ ] **Test:** [P0] should reject concurrent sweep for same runId with BACKTEST_REPORT_ERROR 4205
  - **Status:** RED — SensitivityAnalysisService does not exist
  - **Verifies:** AC #4 — concurrency guard
- [ ] **Test:** [P1] should clear concurrency flag in finally block (allow retry after failure)
  - **Status:** RED — SensitivityAnalysisService does not exist
  - **Verifies:** Cross-cutting — collection lifecycle (Map cleanup in finally)

---

### Task 5 (continued): Trading Window Sweep Edge Case (1 test)

**File:** `src/modules/backtesting/reporting/sensitivity-analysis.service.spec.ts` (same file)

- [ ] **Test:** [P1] should handle wrap-around trading window in sweep (startHour: 21, endHour: 4 — verify isInTradingWindow returns true for hour 23)
  - **Status:** RED — SensitivityAnalysisService does not exist
  - **Verifies:** AC #4 — wrap-around trading window correctness

---

### Task 6: ReportingModule + Pipeline Integration Tests (6 tests)

**File:** `src/modules/backtesting/reporting/reporting.module.spec.ts` (NEW, ~60 lines)

- [ ] **Test:** [P1] should register CalibrationReportService, WalkForwardService, SensitivityAnalysisService as providers
  - **Status:** RED — ReportingModule does not exist
  - **Verifies:** AC #9 — module DI wiring (3 providers, ≤8 limit)
- [ ] **Test:** [P1] should be importable from BacktestingModule
  - **Status:** RED — ReportingModule not imported yet
  - **Verifies:** AC #9 — module composition
- [ ] **Test:** [P1] should resolve CalibrationReportService via DI
  - **Status:** RED — ReportingModule does not exist
  - **Verifies:** AC #9 — DI resolution

**File:** `src/modules/backtesting/engine/backtest-engine.service.spec.ts` (EXTEND existing, ~40 lines added)

- [ ] **Test:** [P0] should call CalibrationReportService.generateReport(runId) in GENERATING_REPORT phase
  - **Status:** RED — report integration not implemented
  - **Verifies:** AC #9 — auto-generation on run completion
- [ ] **Test:** [P0] should persist walkForwardResults to BacktestRun when walkForwardEnabled
  - **Status:** RED — walk-forward persistence not implemented
  - **Verifies:** AC #6, #9 — walk-forward result persistence
- [ ] **Test:** [P1] should still complete run successfully if report generation fails (log error, don't halt)
  - **Status:** RED — error handling not implemented
  - **Verifies:** AC #9 — graceful degradation

---

### Task 7: Controller Endpoints + DTO Tests (16 tests)

**File:** `src/modules/backtesting/dto/calibration-report.dto.spec.ts` (NEW, ~100 lines)

- [ ] **Test:** [P1] should construct CalibrationReportResponseDto with summaryMetrics, confidenceIntervals, knownLimitations, dataQualitySummary
  - **Status:** RED — DTO does not exist
  - **Verifies:** AC #1 — response DTO shape
- [ ] **Test:** [P1] should construct SensitivityResultsResponseDto with sweeps, degradationBoundaries, recommendedParameters, partial flag
  - **Status:** RED — DTO does not exist
  - **Verifies:** AC #4 — response DTO shape
- [ ] **Test:** [P1] should construct WalkForwardResultsResponseDto with trainMetrics, testMetrics, degradation, overfitFlags
  - **Status:** RED — DTO does not exist
  - **Verifies:** AC #6 — response DTO shape

**File:** `src/modules/backtesting/controllers/backtest.controller.spec.ts` (EXTEND existing, ~200 lines added)

- [ ] **Test:** [P0] should GET /api/backtesting/runs/:id/report and return 200 with CalibrationReport data
  - **Status:** RED — endpoint does not exist
  - **Verifies:** AC #9 — report retrieval endpoint
- [ ] **Test:** [P0] should return 404 when report not yet generated for GET /api/backtesting/runs/:id/report
  - **Status:** RED — endpoint does not exist
  - **Verifies:** AC #9 — 404 for missing report
- [ ] **Test:** [P0] should POST /api/backtesting/runs/:id/sensitivity and return 202 Accepted
  - **Status:** RED — endpoint does not exist
  - **Verifies:** AC #4 — sensitivity trigger endpoint
- [ ] **Test:** [P0] should GET /api/backtesting/runs/:id/sensitivity and return 200 with SensitivityResults data
  - **Status:** RED — endpoint does not exist
  - **Verifies:** AC #4 — sensitivity retrieval endpoint
- [ ] **Test:** [P0] should return 404 when sensitivity not yet generated for GET /api/backtesting/runs/:id/sensitivity
  - **Status:** RED — endpoint does not exist
  - **Verifies:** AC #4 — 404 for missing sensitivity
- [ ] **Test:** [P0] should GET /api/backtesting/runs/:id/walk-forward and return 200 with WalkForwardResults data
  - **Status:** RED — endpoint does not exist
  - **Verifies:** AC #6 — walk-forward retrieval endpoint
- [ ] **Test:** [P0] should return 404 when walk-forward not available for GET /api/backtesting/runs/:id/walk-forward
  - **Status:** RED — endpoint does not exist
  - **Verifies:** AC #6 — 404 for missing walk-forward
- [ ] **Test:** [P1] should return 400 when run status is not COMPLETE for POST sensitivity
  - **Status:** RED — endpoint does not exist
  - **Verifies:** AC #4 — precondition: run must be complete
- [ ] **Test:** [P1] should return 409 Conflict when sensitivity sweep already in progress for same runId
  - **Status:** RED — endpoint does not exist
  - **Verifies:** AC #4 — concurrency rejection at HTTP level
- [ ] **Test:** [P1] should accept optional SweepConfigDto body on POST sensitivity with class-validator decorators
  - **Status:** RED — endpoint does not exist
  - **Verifies:** AC #4 — sweep config validation at DTO level
- [ ] **Test:** [P1] should wrap all responses in { data: T, timestamp: string } format
  - **Status:** RED — endpoint does not exist
  - **Verifies:** AC #9 — standard response wrapper
- [ ] **Test:** [P2] should use ParseUUIDPipe on :id parameter for all 4 new endpoints
  - **Status:** RED — endpoint does not exist
  - **Verifies:** Cross-cutting — input validation
- [ ] **Test:** [P2] should return error response in { error: { code, message, severity }, timestamp } format on failures
  - **Status:** RED — endpoint does not exist
  - **Verifies:** AC #9 — standard error response

---

### Task 8: Integration Tests + Report Fixtures (14 tests)

**File:** `src/modules/backtesting/reporting/calibration-report.integration.spec.ts` (NEW, ~350 lines)

**Full pipeline integration — 3 tests:**

- [ ] **Test:** [P0] FIXTURE: profitable-with-ci — should auto-generate report on run completion with CIs present, known limitations complete (10 items)
  - **Status:** RED — reporting pipeline not integrated
  - **Verifies:** AC #1, #3, #7 — full report auto-generation
  - **Fixture data:** Profitable scenario from 10-9-3 fixtures with 20+ positions for meaningful CI
- [ ] **Test:** [P0] FIXTURE: unprofitable-degradation — should produce report with profitFactor < 1.0, CI lower bound < 1.0
  - **Status:** RED — reporting pipeline not integrated
  - **Verifies:** AC #1, #3, #5 — unprofitable scenario reporting
- [ ] **Test:** [P1] should include data quality summary with coverage gaps and pair count from fixture data
  - **Status:** RED — data quality summary not implemented
  - **Verifies:** AC #8 — data quality integration

**Walk-forward integration — 3 tests:**

- [ ] **Test:** [P0] FIXTURE: walk-forward-overfit — run with walkForwardEnabled=true, verify >30% degradation flagged as overfit
  - **Status:** RED — walk-forward pipeline not integrated
  - **Verifies:** AC #6 — overfit detection end-to-end
  - **Fixture data:** Train period with strong edge, test period with collapsed edge (simulates overfit)
- [ ] **Test:** [P0] FIXTURE: walk-forward-robust — run with walkForwardEnabled=true, verify <=30% degradation NOT flagged
  - **Status:** RED — walk-forward pipeline not integrated
  - **Verifies:** AC #6 — robust strategy validation
  - **Fixture data:** Consistent edge across both periods
- [ ] **Test:** [P1] should report train and test metrics separately in WalkForwardResults
  - **Status:** RED — walk-forward pipeline not integrated
  - **Verifies:** AC #6 — separate metric reporting

**Sensitivity integration — 4 tests:**

- [ ] **Test:** [P0] should trigger sweep on completed run and produce results with all 4 parameter dimensions
  - **Status:** RED — sensitivity not integrated
  - **Verifies:** AC #4 — sweep execution end-to-end
- [ ] **Test:** [P0] should identify degradation boundaries where profitFactor drops below 1.0
  - **Status:** RED — sensitivity not integrated
  - **Verifies:** AC #5 — degradation boundary identification
- [ ] **Test:** [P0] should identify recommended params maximizing profitFactor and Sharpe
  - **Status:** RED — sensitivity not integrated
  - **Verifies:** AC #2 — recommended parameter identification
- [ ] **Test:** [P1] should emit progress events every ~10 sweeps during sensitivity analysis
  - **Status:** RED — sensitivity not integrated
  - **Verifies:** AC #4 — progress tracking for dashboard UX

**Dashboard compatibility — 1 test:**

- [ ] **Test:** [P0] should verify report, sensitivity, and walk-forward JSON structures are JSON-serializable and round-trip cleanly
  - **Status:** RED — JSON structures not defined
  - **Verifies:** AC #9 — dashboard charting compatibility

---

### Event Wiring Integration Tests (3 tests)

**File:** `src/common/testing/event-wiring-audit.spec.ts` (EXTEND existing)

- [ ] **Test:** [P1] should wire BacktestReportGeneratedEvent handler via real EventEmitter2
  - **Status:** RED — handler not implemented
  - **Verifies:** Cross-cutting — event wiring verification
- [ ] **Test:** [P1] should wire BacktestSensitivityCompletedEvent handler via real EventEmitter2
  - **Status:** RED — handler not implemented
  - **Verifies:** Cross-cutting — event wiring verification
- [ ] **Test:** [P1] should wire BacktestWalkForwardCompletedEvent handler via real EventEmitter2
  - **Status:** RED — handler not implemented
  - **Verifies:** Cross-cutting — event wiring verification

---

### Metrics Extraction Utility Tests (6 tests)

**File:** `src/modules/backtesting/utils/metrics-calculation.utils.spec.ts` (NEW, ~120 lines)

- [ ] **Test:** [P0] should calculate profitFactor as sum(winPnl) / abs(sum(lossPnl)) using Decimal arithmetic
  - **Status:** RED — calculateProfitFactor does not exist
  - **Verifies:** AC #1, #3 — reusable profit factor function
- [ ] **Test:** [P0] should return null profitFactor when gross loss is 0 (no losing trades)
  - **Status:** RED — calculateProfitFactor does not exist
  - **Verifies:** AC #1, #3 — profitFactor null edge case
- [ ] **Test:** [P0] should calculate Sharpe ratio as mean(dailyReturns) / stddev(dailyReturns) * sqrt(252) using Decimal arithmetic
  - **Status:** RED — calculateSharpeRatio does not exist
  - **Verifies:** AC #1, #3 — reusable Sharpe function
- [ ] **Test:** [P0] should return null Sharpe when stddev of daily returns is 0
  - **Status:** RED — calculateSharpeRatio does not exist
  - **Verifies:** AC #1, #3 — Sharpe null edge case
- [ ] **Test:** [P1] should produce identical results to BacktestPortfolioService.getAggregateMetrics() for same input
  - **Status:** RED — extracted functions not yet created
  - **Verifies:** Cross-cutting — financial math reuse consistency
- [ ] **Test:** [P1] should handle empty positions array (profitFactor null, Sharpe null)
  - **Status:** RED — extracted functions not yet created
  - **Verifies:** AC #1 — empty input edge case

---

## Test Summary

| Category | P0 | P1 | P2 | Total |
|----------|----|----|-----|-------|
| DTO/Schema (Task 1) | 0 | 3 | 0 | 3 |
| Report Types (Task 2) | 0 | 8 | 0 | 8 |
| Error Codes (Task 2) | 0 | 2 | 0 | 2 |
| Domain Events (Task 2) | 0 | 6 | 0 | 6 |
| CalibrationReportService (Task 3) | 12 | 12 | 0 | 24 |
| WalkForwardService (Task 4) | 6 | 9 | 1 | 16 |
| Headless + Walk-Forward Pipeline (Task 4) | 4 | 6 | 0 | 10 |
| SensitivityAnalysisService (Task 5) | 11 | 13 | 0 | 24 |
| Trading Window Edge Case (Task 5) | 0 | 1 | 0 | 1 |
| ReportingModule + Pipeline (Task 6) | 2 | 4 | 0 | 6 |
| DTOs (Task 7) | 0 | 3 | 0 | 3 |
| Controller Endpoints (Task 7) | 7 | 4 | 2 | 13 |
| Integration + Fixtures (Task 8) | 7 | 4 | 0 | 11 |
| Dashboard Compatibility (Task 8) | 1 | 0 | 0 | 1 |
| Event Wiring (cross-cutting) | 0 | 3 | 0 | 3 |
| Metrics Extraction Utils | 4 | 2 | 0 | 6 |
| **TOTAL** | **54** | **80** | **3** | **137** |

---

## Test File Map

| File Path | Task | Tests | New/Extend |
|-----------|------|-------|------------|
| `src/modules/backtesting/dto/backtest-result.dto.spec.ts` | 1 | 3 | EXTEND |
| `src/modules/backtesting/types/calibration-report.types.spec.ts` | 2 | 8 | NEW |
| `src/common/errors/system-health-error.spec.ts` | 2 | 2 | EXTEND |
| `src/common/events/backtesting.events.spec.ts` | 2 | 6 | EXTEND |
| `src/modules/backtesting/reporting/calibration-report.service.spec.ts` | 3 | 24 | NEW |
| `src/modules/backtesting/reporting/walk-forward.service.spec.ts` | 4 | 16 | NEW |
| `src/modules/backtesting/engine/backtest-engine.service.spec.ts` | 4, 6 | 16 | EXTEND |
| `src/modules/backtesting/reporting/sensitivity-analysis.service.spec.ts` | 5 | 25 | NEW |
| `src/modules/backtesting/reporting/reporting.module.spec.ts` | 6 | 3 | NEW |
| `src/modules/backtesting/dto/calibration-report.dto.spec.ts` | 7 | 3 | NEW |
| `src/modules/backtesting/controllers/backtest.controller.spec.ts` | 7 | 13 | EXTEND |
| `src/modules/backtesting/reporting/calibration-report.integration.spec.ts` | 8 | 11 | NEW |
| `src/common/testing/event-wiring-audit.spec.ts` | cross | 3 | EXTEND |
| `src/modules/backtesting/utils/metrics-calculation.utils.spec.ts` | cross | 6 | NEW |

---

## TDD Implementation Order (Recommended)

1. **Task 1** (Prisma schema migration) — 3 tests, run baseline verification after migration
2. **Task 2** (Report types + error code + events) — 16 tests, foundational types needed by all other tasks
3. **Metrics extraction utils** — 6 tests, pure functions reused by report and bootstrap
4. **Task 3** (CalibrationReportService) — 24 tests, core report generation + bootstrap CIs
5. **Task 4** (WalkForwardService + headless simulation) — 26 tests, pure logic + engine integration
6. **Task 5** (SensitivityAnalysisService) — 25 tests, sweep execution + degradation + concurrency
7. **Task 6** (ReportingModule + pipeline) — 6 tests, module wiring + auto-generation
8. **Task 7** (Controller endpoints + DTOs) — 16 tests, HTTP layer
9. **Task 8** (Integration tests + fixtures) — 14 tests, end-to-end validation + event wiring

---

## Fixture Data Requirements

**Directory:** `src/modules/backtesting/__fixtures__/report-scenarios/`

| Fixture File | Description |
|-------------|-------------|
| `profitable-with-ci.fixture.json` | 20+ positions with mixed wins/losses, enough for meaningful CI |
| `unprofitable-degradation.fixture.json` | Positions with profitFactor < 1.0, net losses |
| `walk-forward-overfit.fixture.json` | Train period strong edge, test period collapsed edge (>30% degradation) |
| `walk-forward-robust.fixture.json` | Consistent edge across both periods (<=30% degradation) |

---

## Key Design Decisions for Test Authors

1. **All financial assertions use Decimal comparison** — never `toBe(0.03)`, always `expect(result.toString()).toBe('0.03')` or `expect(result.equals(new Decimal('0.03'))).toBe(true)`
2. **Factory functions inline per spec file** (project pattern) — use `createSimulatedPosition()` from `simulation.types.ts`
3. **Mock PrismaService** for unit tests, real EventEmitter2 for event wiring tests
4. **`vi.useFakeTimers()` for timeout tests** with `vi.advanceTimersByTimeAsync()`
5. **Priority markers in test names** — `[P0]`, `[P1]`, `[P2]` for CI prioritization
6. **AC traceability** — every test description maps to specific AC numbers
7. **Payload verification** — all event emission tests use `expect.objectContaining({...})`, never bare `toHaveBeenCalled()`
8. **Use REPORT_DECIMAL_PRECISION** for all `toFixed()` calls in report math — never hardcode precision
9. **Bootstrap determinism** — seed `Math.random` in tests for reproducible CI bounds (e.g., using a seeded PRNG or mocking `Math.random`)
10. **SIZE GATE** — if `sensitivity-analysis.service.spec.ts` exceeds ~400 lines, split sweep tests from degradation/recommendation tests
11. **Metrics reuse** — use extracted `calculateProfitFactor` and `calculateSharpeRatio` from `metrics-calculation.utils.ts`, do NOT reimplement
