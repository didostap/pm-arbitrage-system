# Story 9-21: UX Audit Findings

> Generated: 2026-03-15
> Pages audited: 7 (Dashboard, Positions Open/All, Position Detail, Matches Approved/Pending/Rejected, Match Detail, Performance, Stress Test)

## Summary

| Priority | Count | Description |
|----------|-------|-------------|
| **P0** | 13 | Misleading without explanation — could lead to incorrect operator decisions |
| **P1** | 42 | Unclear but not misleading — requires source code or domain knowledge to understand |
| **P2** | 4 | Nice-to-have polish |
| **Total** | 59 | |

---

## 1. Dashboard (Overview) Page

**Source:** `src/pages/DashboardPage.tsx`, `src/components/HealthComposite.tsx`, `src/components/ConnectionStatus.tsx`, `src/components/MetricDisplay.tsx`, `src/components/EditBankrollDialog.tsx`, `src/components/TopBar.tsx`

| # | Element | Current State | Recommended Change | Priority |
|---|---------|--------------|-------------------|----------|
| D1 | **Execution Quality** metric card | Shows "XX.X%" with no context | Add InfoTooltip: "Lifetime ratio of filled orders to total attempted. All-time aggregate, not a recent window." | **P0** |
| D2 | **Platform health status badges** (healthy/degraded/disconnected/initializing) in HealthComposite | Raw status badge, no meaning | Add InfoTooltip to "Platform Health" panel title: "healthy = API connected, data fresh (<60s). degraded = connected but data stale or high latency. disconnected = API unreachable. initializing = startup state (<30s)." | **P0** |
| D3 | **"Stale data"** label in HealthComposite | Appears without threshold context | Add InfoTooltip inline: "No update received in 60+ seconds. Prices and order books may be outdated." | **P0** |
| D4 | **Trailing 7d P&L** metric card | Label only | Add InfoTooltip: "Sum of expected edge for positions closed in the last 7 days." | P1 |
| D5 | **Active Alerts** metric card | Count only | Add InfoTooltip: "Active system alerts requiring attention. Currently tracks single-leg exposures." | P1 |
| D6 | **Total Bankroll** label in Capital Overview | Has edit button but no explanation of impact | Add InfoTooltip: "Total trading capital. Position sizing is capped at 3% of bankroll per pair." | P1 |
| D7 | **Deployed** label in Capital Overview | Label only | Add InfoTooltip: "Capital currently committed to open positions across both platforms." | P1 |
| D8 | **Available** label in Capital Overview | Color-coded (green/amber/red) with no threshold explanation | Add InfoTooltip: "Bankroll minus deployed and reserved. Color: green (>50%), amber (>20%), red (<20% of bankroll)." | P1 |
| D9 | **Reserved** label in Capital Overview | Label only | Add InfoTooltip: "Capital held for pending order execution (budget reservations). Released when orders fill or are cancelled." | P1 |
| D10 | **Mode badge** (LIVE/PAPER) per platform in HealthComposite | Badge only | Add to D2 tooltip text: "Mode: LIVE = real orders, PAPER = simulated execution with real market data." | P1 |
| D11 | **"API disconnected"** label in HealthComposite | Text only, no guidance | Add InfoTooltip: "Platform API unreachable. Check network connectivity and API credentials." | P1 |
| D12 | **ConnectionStatus** (WebSocket indicator) in TopBar | Dot + "connected/disconnected" label | Add InfoTooltip: "WebSocket for real-time updates. When disconnected, data may be stale — refresh manually." | P1 |
| D13 | **Open Positions** metric card | Count only | P2 — could show live/paper breakdown. No change needed now. | P2 |

---

## 2. Positions Page (Open / All tabs)

**Source:** `src/pages/PositionsPage.tsx`, `src/components/cells/StatusBadge.tsx`, `src/components/cells/ExitTypeBadge.tsx`

| # | Element | Current State | Recommended Change | Priority |
|---|---------|--------------|-------------------|----------|
| P1 | **Init Edge** column header | "Init Edge" — jargon, no formula | Add InfoTooltip: "Initial Edge — net spread at entry after fees and gas. Formula: \|Price_A − Price_B\| − fees − gas. Min threshold: 0.8%." | **P0** |
| P2 | **Curr Edge** column header | "Curr Edge" — abbreviated jargon | Add InfoTooltip: "Current Edge — net spread using current VWAP close prices for the position size. May differ from Init Edge as order books change." | **P0** |
| P3 | **StatusBadge** (OPEN, SINGLE_LEG_EXPOSED, EXIT_PARTIAL, CLOSED, RECONCILIATION_REQUIRED) | Raw status text, no meaning | Add per-status tooltip to StatusBadge component. SINGLE_LEG_EXPOSED: "One leg executed, other failed — requires operator action (retry or close)." EXIT_PARTIAL: "Exit triggered but only one leg closed. Second leg pending." OPEN: "Both legs filled. Monitored for exit triggers." CLOSED: "Both legs closed. Terminal state." RECONCILIATION_REQUIRED: "State inconsistent after restart. Manual review needed." | **P0** |
| P4 | **Entry** column header | "Entry" only | Add InfoTooltip: "Fill prices at position entry on each platform (K = Kalshi, P = Polymarket)." | P1 |
| P5 | **Current** column header | "Current" only | Add InfoTooltip: "Current VWAP close prices for the position size. Prices with ~ prefix use best available price due to thin depth." | P1 |
| P6 | **P&L** column header | "P&L" only (PnlCell handles estimated indicator — do NOT add tooltip to PnlCell) | Add InfoTooltip to column header only: "Unrealized P&L for open positions; realized for closed. Values with ~ are estimated (thin order book)." | P1 |
| P7 | **Resolution** column header | "Resolution" only | Add InfoTooltip: "Time until contract resolves. Positions are auto-exited as resolution approaches." | P1 |
| P8 | **ExitTypeBadge** (stop_loss, take_profit, time_based, manual) | Labels only, no meaning explanation | Add per-type tooltip to ExitTypeBadge component. STOP_LOSS: "P&L hit stop-loss threshold." TAKE_PROFIT: "P&L hit take-profit threshold." TIME_BASED: "Resolution date approached." MANUAL: "Closed by operator." | P1 |

---

## 3. Position Detail Page

**Source:** `src/pages/PositionDetailPage.tsx`

| # | Element | Current State | Recommended Change | Priority |
|---|---------|--------------|-------------------|----------|
| PD1 | **Current Edge** label (Current State section) | "Current Edge" text only | Add InfoTooltip (same as P2 text above) | **P0** |
| PD2 | **Initial Edge** label (Current State section) | "Initial Edge" text only | Add InfoTooltip (same as P1 text above) | **P0** |
| PD3 | **Unrealized P&L** label (Current State section) | "Unrealized P&L" text only | Add InfoTooltip: "Estimated P&L if both legs closed at current prices. Includes entry fees and estimated exit fees." | P1 |
| PD4 | **Gross P&L** label (Exit section) | "Gross P&L" text only | Add InfoTooltip: "Profit/loss from price movement before fees are deducted." | P1 |
| PD5 | **Net P&L** label (Exit section) | "Net P&L" text only | Add InfoTooltip: "Profit/loss after all fees (entry + exit) are deducted. This is the actual economic result." | P1 |
| PD6 | **Slippage** column (Order History table) | "Slippage" header only | Add InfoTooltip: "Difference between requested and actual fill price. Lower is better." | P1 |
| PD7 | **Req. Price** column (Order History table) | Abbreviated header | Rename to "Requested" for clarity. No tooltip needed. | P1 |

---

## 4. Matches Page (Approved / Pending / Rejected tabs)

**Source:** `src/pages/MatchesPage.tsx`

| # | Element | Current State | Recommended Change | Priority |
|---|---------|--------------|-------------------|----------|
| M1 | **Confidence** column header | "Confidence" + number with no context | Add InfoTooltip: "LLM-assessed match quality (0–100). Evaluates whether both contracts refer to the same real-world event. ≥85 auto-approved; <85 requires operator review." | **P0** |
| M2 | **Est. APR** column header | "Est. APR" + number only | Add InfoTooltip: "Estimated Annualized Return. Formula: netEdge × (365 / daysToResolution). Min threshold: 15%. Updated each detection cycle." | **P0** |
| M3 | **Cluster** column header | Badge with cluster name only | Add InfoTooltip: "Correlation cluster — positions in the same cluster are correlated. If one loses, others likely lose too. Max 15% of bankroll per cluster." | P1 |
| M4 | **Primary Leg** column header | Badge with platform name only | Add InfoTooltip: "Platform where the first leg executes. The second leg follows on the other platform." | P1 |
| M5 | **Positions** column header | "X / Y" format, meaning not explained | Add InfoTooltip: "Active positions / total positions for this contract pair." | P1 |

---

## 5. Match Detail Page

**Source:** `src/pages/MatchDetailPage.tsx`

| # | Element | Current State | Recommended Change | Priority |
|---|---------|--------------|-------------------|----------|
| MD1 | **Criteria Hash** label (Resolution section) | Label + truncated hash | Add InfoTooltip: "Hash of resolution criteria text. Used to detect if settlement rules changed between platforms." | P1 |
| MD2 | **Diverged** badge (Resolution section) | "Yes/No" badge only | Add InfoTooltip: "Whether platforms resolved the same event differently. Divergence means one paid out and the other didn't — potential loss." | P1 |
| MD3 | **Total Cycles Traded** label (Trading Activity) | Number only | Add InfoTooltip: "Number of detection cycles where this pair was evaluated for trading." | P1 |
| MD4 | **Freshness** badge (Capital Efficiency) | "Fresh/Stale" with no threshold | Add InfoTooltip: "Based on last detection computation. Fresh = updated within 5 minutes. Stale = >5 minutes since last update." | P1 |
| MD5 | **Net Edge** label (Capital Efficiency) | Number only | Add InfoTooltip: "Current net spread between platforms after fees. Updated each detection cycle." | P1 |

---

## 6. Performance Page

**Source:** `src/pages/PerformancePage.tsx`, `src/components/TrendsSummary.tsx`

| # | Element | Current State | Recommended Change | Priority |
|---|---------|--------------|-------------------|----------|
| PE1 | **Opps (D/F/E)** column header | Cryptic abbreviation | Add InfoTooltip: "Opportunities: Detected (found) / Filtered (passed risk checks) / Executed (orders submitted). The funnel from detection to execution." | **P0** |
| PE2 | **Trades** column header | "Trades" only | Add InfoTooltip: "Total orders submitted during the week (entry + exit across both platforms)." | P1 |
| PE3 | **Hit Rate** column header | "Hit Rate" only | Add InfoTooltip: "Percentage of positions closed profitably during the week." | P1 |
| PE4 | **Slippage** column header | "Slippage" header only | Add InfoTooltip: "Average difference between requested and fill prices for the week." | P1 |
| PE5 | **AR** column header | Existing tooltip says only "Autonomy Ratio" | Enhance existing tooltip text to: "Autonomy Ratio — automated decisions vs operator interventions. Higher = more autonomous operation." (Do NOT add separate InfoTooltip — already has a tooltip trigger on the header) | P1 |
| PE6 | **Opportunities / wk** trend metric | Label only | Add InfoTooltip: "Rolling average of arbitrage opportunities detected per week." | P1 |
| PE7 | **Edge / wk** trend metric | Label only | Add InfoTooltip: "Rolling average of total edge captured (USD) per week." | P1 |
| PE8 | **Avg Slippage** trend metric | Label only | Add InfoTooltip: "Rolling average slippage across all trades in the lookback window." | P1 |
| PE9 | **Edge Trend** indicator | "Improving/Stable/Declining" with arrow | Add InfoTooltip: "Direction of weekly edge captured over the lookback window." | P1 |
| PE10 | **Opp Baseline** indicator | "Below baseline" / "On track" | Add InfoTooltip: "Minimum 8 opportunities/week expected. Below baseline may indicate platform or market issues." | P1 |

---

## 7. Stress Test Page

**Source:** `src/pages/StressTestPage.tsx`

| # | Element | Current State | Recommended Change | Priority |
|---|---------|--------------|-------------------|----------|
| ST1 | **VaR (95%)** metric card | Label + dollar value | Add InfoTooltip: "Value at Risk (95%) — max expected loss at 95% confidence via Monte Carlo (1000+ scenarios). 5% chance losses exceed this." | **P0** |
| ST2 | **VaR (99%)** metric card | Label + dollar value | Add InfoTooltip: "Value at Risk (99%) — max expected loss at 99% confidence. 1% chance losses exceed this." | **P0** |
| ST3 | **Worst-Case Loss** metric card | Label + dollar value | Add InfoTooltip: "Single worst outcome across all simulated scenarios (random + synthetic)." | P1 |
| ST4 | **Drawdown Probabilities** section title | Section with bar charts, dashed 5% line unexplained | Add InfoTooltip to section title: "Probability of portfolio falling by these percentages (Monte Carlo). Dashed line = 5% alert threshold." | P1 |
| ST5 | **P&L Distribution** section title | Percentile table (p5, p10...) with no explanation | Add InfoTooltip to section title: "P&L across all scenarios. p5 = 5th percentile (95% of scenarios are better). p95 = only 5% are better." | P1 |
| ST6 | **Synthetic Scenarios** section title | "Scenario" + P&L, no explanation of what synthetic means | Add InfoTooltip to section title: "Predefined worst-case scenarios (cluster blowup, correlated losses) tested alongside random Monte Carlo scenarios." | P1 |
| ST7 | **Vol** column header | Existing tooltip says only "Volatility" | Enhance existing tooltip: "Estimated price volatility used in Monte Carlo simulation. Higher = wider range of simulated outcomes." (Do NOT add separate InfoTooltip — already has a tooltip trigger) | P1 |
| ST8 | **Run Stress Test** button | Button text only | Add InfoTooltip next to button: "Runs 1000+ Monte Carlo scenarios plus synthetic stress tests against the current portfolio. Takes a few seconds." | P1 |
| ST9 | **Bankroll** metric card on stress test page | Label + dollar value, no context | P2 — self-evident in context. No change. | P2 |
| ST10 | **Scenario count subtitle** | "X scenarios · Y positions" | P2 — contextual enough. No change. | P2 |
| ST11 | **Data insufficiency alert** (in trends) | Already has explanation text | P2 — already adequate. No change. | P2 |

---

## P2 Items — Backlog for Future Stories

| # | Page | Element | Recommendation |
|---|------|---------|---------------|
| D13 | Dashboard | Open Positions count | Show live/paper breakdown inline |
| ST9 | Stress Test | Bankroll card | Add link back to dashboard bankroll edit |
| ST10 | Stress Test | Scenario count subtitle | Could show Monte Carlo vs synthetic breakdown |
| ST11 | Performance | Data insufficiency alert | Already adequate |
