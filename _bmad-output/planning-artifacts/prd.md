---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish', 'step-e-01-discovery', 'step-e-02-review', 'step-e-03-edit']
inputDocuments:
  - '_bmad-output/planning-artifacts/product-brief-pm-arbitrage-system-2026-02-09.md'
  - '_bmad-output/brainstorming/initial-brainstorming-session-with-claude.md'
  - '_bmad-output/planning-artifacts/prd-validation-report.md'
workflowType: 'prd'
workflow: 'edit'
briefCount: 1
researchCount: 0
brainstormingCount: 1
projectDocsCount: 0
classification:
  projectType: "api_backend"
  domain: "fintech"
  complexity: "high"
  projectContext: "greenfield"
lastEdited: '2026-02-10'
editHistory:
  - date: '2026-02-10'
    changes: 'Major PRD improvements - Added: Executive Summary, Functional Requirements section (60+ FRs), State Recovery, Deployment/Infrastructure, Concurrent Execution, Error Catalog, Alerting Fallback, Time Sync, Opportunity Baseline, Correlation Framework, Knowledge Base Schema, Price Normalization. Fixed: Uptime conflict, single-leg threshold conflict. Refined: Regulatory scanning, backtesting scope. Renamed: User Journeys → Operational Workflows. Removed: Vendor names (4 locations).'
---

# Product Requirements Document - pm-arbitrage-system

**Author:** Arbi
**Date:** 2026-02-10

## Executive Summary

### System Overview

Institutional-grade automated trading system exploiting cross-platform arbitrage opportunities in prediction markets (Polymarket ↔ Kalshi). The system capitalizes on structural market fragmentation - identical events priced differently across venues due to liquidity silos, differing user bases, and blockchain/exchange friction.

**Core Thesis:** Prediction market fragmentation will persist for 5-10 years before consolidation, creating durable arbitrage opportunities. Entry in 2026 is optimal - markets mature enough for liquidity, fragmented enough for edge, pre-institutional competition.

**Strategy:** Phase 1 (Months 1-12) = Pure arbitrage with operational autonomy. Phase 2 (Month 12+) = Layer news-velocity alpha signals if arbitrage data reveals patterns. Phase 3 (18-24 months) = Optional infrastructure productization or institutional scaling.

### Success Dashboard - Key Metrics

**MVP Validation (Months 1-3):**

| Metric | Target | Alert Threshold | Status |
|--------|--------|-----------------|---------|
| Completed Cycles | 100+ cycles | <20 cycles/month | Track |
| Profit Factor | >1.2 | <1.0 for 30 days | Track |
| Net Edge per Cycle | 0.4%+ after costs | <0.2% sustained | Track |
| Hit Rate | >65% | <50% sustained | Track |
| Contract Matching Errors | 0 (zero tolerance) | 1 error = halt | Critical |
| Single-Leg Events | <5/month | >1/week for 3 weeks | Track |

**Phase 1 Operational (Months 3-12):**

| Metric | Target | Alert Threshold | Status |
|--------|--------|-----------------|---------|
| System Uptime | 99% (active hours) | <98% sustained | Track |
| Daily Operator Time | 30-45 min | >60 min sustained | Track |
| Autonomy Ratio | 100:1 by Month 6 | <50:1 sustained | Track |
| Net Annualized Return | 15%+ | <10% on 90-day trail | Critical |
| Sharpe Ratio | >1.5 (target 2.0) | <1.5 for 2 months | Track |
| Max Drawdown | <15% target | >20% alert, 25% halt | Critical |
| Open Positions | 15-25 pairs | <10 sustained = underutilized | Track |
| Execution Quality Ratio | >0.7 (70% of edge captured) | <0.6 for 10 days | Alert |

**Phase 1 Success Gates (Month 6):**
- Capital at or near full deployment ($100K-$250K)
- 48-hour test passed at least twice (weekend away, system operates autonomously)
- Contract matching knowledge base covers 50+ validated pairs
- System handled multiple adverse scenarios autonomously (platform outage, risk limit approached, single-leg exposure)
- Operator spending time on Phase 2 research (not Phase 1 maintenance)

**12-Month Checkpoint (Proceed/Scale/Wind Down):**
- 12 consecutive months operation with no losing month after Q1
- Cumulative returns met 15% annualized target
- Max drawdown stayed <20% (within 25% hard limit)
- System adapted to at least one significant market change without redesign
- Expanded to at least one additional platform beyond initial Polymarket/Kalshi pair
- Phase 2 news-velocity layer in development OR concluded non-viable based on data (both acceptable)

### Architectural Pillars (Phase 1)

1. **Unified Cross-Platform Order Book** - Real-time normalized aggregation, sub-second refresh, graceful degradation
2. **Automated Contract Matching** - Semantic analysis with confidence scoring (95%+ auto-approve, <85% human review), accumulated knowledge base
3. **Near-Simultaneous Execution** - Coordinated submission across heterogeneous venues (on-chain + exchange API), intelligent leg sequencing, automatic leg-risk management
4. **Model-Driven Exit Framework** - Continuous edge recalculation based on five criteria (edge evaporation, model update, time decay, risk breach, liquidity deterioration)
5. **Portfolio-Level Risk Management** - Correlation-aware sizing, dynamic risk budgets, Monte Carlo stress testing, automatic trading halts

### Risk-Adjusted Decision Gates

**3-Month Gate (Is the Edge Real?):**
- **Proceed to Scale:** Profit factor >1.3 over 100+ cycles, execution within 40% of backtest → Scale capital to 25%
- **Extend Validation:** Profit factor 1.0-1.3 or <100 cycles → Continue at minimum capital 4-6 weeks
- **Shut Down:** Profit factor <1.0 over 60+ cycles, OR catastrophic matching failure, OR execution <50% of backtest

**6-Month Gate (Is the Edge Durable and Scalable?):**
- **Shift to Phase 2:** All three conditions met (8+ weeks stability, sufficient data for hypotheses, 30-45 min daily involvement) → Begin Phase 2 research parallel to Phase 1
- **Continue Phase 1:** Profitable but not operationally steady → Focus on hardening, reassess Phase 2 at month 9
- **Scale Down/Shut Down:** Returns <10% annualized on 90-day trail OR max drawdown >20% OR edge degrading

**12-Month Gate (Is This a Durable Business?):**
- **Expand & Evolve:** Phase 2 promising + arbitrage durable + competitive position strong → Scale capital, explore fund structure
- **Maintain & Harvest:** Arbitrage works but edge compressing, Phase 2 not viable → Continue at current scale as income stream
- **Wind Down:** Edge compressed, risk-adjusted returns no longer justify complexity → Close over 2-4 weeks, document learnings

## Success Criteria

### Core Philosophy: Process Over Outcomes

Success is measured through a hierarchy that deliberately separates execution quality from outcome quality:

1. **Operational Confidence** — System does what it's supposed to do with verifiable correct behavior
2. **Time Efficiency** — System frees operator for strategic thinking rather than tactical operations
3. **Returns** — Financial performance, measured with proper risk adjustment and statistical rigor
4. **Strategic Optionality** — Accumulated data and knowledge that enables future evolution

**Core Principle:** "A day with negative P&L but flawless execution is a successful day. A day with positive P&L but a mishandled single-leg event is a concerning day."

### User Success (Operator Experience)

**Primary Success Criteria:**

**The 48-Hour Test (Pass by end of Month 2)**
- Can go away for a weekend with phone alerts only
- Return to find system operated correctly, without anxiety
- This milestone indicates genuine operational autonomy achieved

**Autonomy Ratio Trajectory**
- Formula: Automated decisions ÷ manual interventions
- Month 1 target: 20:1
- Month 6 target: 100:1+
- Increasing ratio over time indicates system handling broader range of scenarios
- Declining ratio means encountering situations it can't handle — either market complexity increasing or decision framework has gaps

**Daily Time Investment**
- Target: 30-45 minutes at steady state (month 3+)
- Month 1: 2-3 hours (building trust phase)
- Transition indicates shift from monitoring whether system works → managing confirmed working system

**Critical Trust Milestone**
- The first time the system handles an adverse scenario correctly without operator intervention, discovered only during routine review the next day
- Examples: Platform API outage with graceful degradation and automatic recovery; single-leg exposure successfully managed within risk parameters
- Expected timing: Weeks 3-6 of live trading
- Operator's reaction shifts from "thank god it didn't blow up" to "good, that's what it's supposed to do"

**Supporting Indicators:**
- **Language shift:** From "the system did X" (describing individual actions) to "my trading operation generates Y" (describing aggregate outcomes)
- **Time allocation shift:** Spending more time on Phase 2 research than Phase 1 operations indicates system has become infrastructure rather than project

### Business Success

Business success is evaluated through three formal checkpoints with explicit decision gates:

#### 3-Month Checkpoint: Is the Edge Real?

**Primary Question:** Does the system demonstrate positive expected value that's statistically distinguishable from zero after all transaction costs?

**Success Criteria:**
- 100+ completed arbitrage cycles executed on real capital
- Average net edge per completed cycle: 0.4%+ after all costs
- Hit rate on executed opportunities: >65%
- Distribution of outcomes matches backtested projections within 40% tolerance
- Zero catastrophic failures (contract matching errors causing directional exposure on mismatched contracts)
- Fewer than 5 single-leg exposure events per month, all managed within acceptable loss parameters
- At least one risk limit approached (not breached) — confirms limits are calibrated at correct level

**Decision Outcomes:**
- **Proceed to scale:** Per-trade economics positive and statistically significant (profit factor >1.3 over 100+ cycles), execution quality within 40% of backtest. Scale capital to 25%, continue deployment plan.
- **Extend validation:** Per-trade economics positive but not yet statistically significant (profit factor 1.0-1.3, or fewer than 100 cycles). Continue at minimum capital for 4-6 additional weeks.
- **Shut down:** Per-trade economics negative (profit factor <1.0 over 60+ cycles), OR catastrophic contract matching failure occurred, OR execution quality <50% of backtest with no identifiable fixable cause.

#### 6-Month Checkpoint: Is the Edge Durable and Scalable?

**Primary Question:** Can the system generate target returns at full capital deployment with operational autonomy?

**Success Criteria:**
- Capital at or near full target deployment (scaled through 25% increments, each validated for 2+ weeks)
- Returns consistent with 15% annualized target on trailing 90-day basis (minimum acceptable: 10%+ annualized)
- Sharpe ratio >1.5 on rolling basis (target: 2.0)
- Daily operator involvement at 30-45 minute target
- System has handled multiple adverse scenarios autonomously
- 48-hour test passed at least twice
- Contract matching knowledge base covers 50+ validated cross-platform pairs
- System running 15-25 simultaneous open positions consistently
- Operator actively spending time on Phase 2 research rather than Phase 1 maintenance

**Decision Outcomes:**
- **Shift focus to Phase 2:** System meets all three Phase 2 gate conditions (8+ weeks operational stability, sufficient data for testable hypotheses, 30-45 min daily involvement achieved). Begin Phase 2 research as parallel workstream while Phase 1 continues generating returns.
- **Continue pure Phase 1:** System profitable but hasn't reached operational steady state (still intervening frequently, unresolved execution quality issues, insufficient data for Phase 2). Focus on hardening and optimization. Reassess Phase 2 readiness at month 9.
- **Scale down or shut down:** Returns below 10% annualized minimum on trailing 90 days at full capital, OR max drawdown exceeded 20%, OR edge clearly degrading based on leading indicators.

#### 12-Month Checkpoint: Is This a Durable Business?

**Primary Question:** Has the system operated profitably for a full market cycle and generated the strategic positioning for next-phase evolution?

**Success Criteria:**
- 12 consecutive months of operation (allowing individual losing weeks, but no losing month after first quarter)
- Cumulative returns met or exceeded 15% annualized target
- Maximum drawdown stayed below 20% (well within 25% hard limit)
- System adapted to at least one significant market change (platform fee adjustment, new competitor, liquidity shift) without fundamental redesign
- Expanded to at least one additional platform beyond initial Polymarket/Kalshi pair
- Operational infrastructure documented sufficiently for potential technical collaborator onboarding
- Phase 2 news-velocity alpha layer either in development or concluded non-viable based on data (both acceptable)

**Strategic Clarity Achieved:** Clear understanding of whether this is:
- $200K/year lifestyle business
- $1M+/year operation worth scaling
- Edge that's compressing and needs to evolve

**Decision Outcomes:**
- **Expand and evolve:** Phase 2 showing promising results, arbitrage system generating durable returns, competitive position strong. Begin serious Phase 2 development/deployment. Consider adding platforms, scaling capital, exploring fund structure.
- **Maintain and harvest:** Arbitrage system works but edge slowly compressing. Phase 2 not viable or not ready. Continue operating at current scale as profitable but potentially declining income stream.
- **Wind down:** Edge compressed to point where risk-adjusted returns no longer justify operational complexity. Close positions over 2-4 weeks, document learnings. This is a success outcome if system was profitable for 12 months and generated enough knowledge and capital to fund next venture.

**Critical Principle:** Default is "continue" unless specific, articulable reasons justify "expand" or "contract." Inertia toward current state is appropriate when operating within expected parameters.

### Technical Success

**System Reliability:**
- **Uptime:** 99%+ during active market hours (Mon-Fri 9am-5pm ET when prediction markets are most active), 95% overall including planned maintenance windows
- Each hour of downtime during active hours is lost opportunity and operational risk
- Below 98% sustained during active hours, priority shifts from alpha improvement to infrastructure hardening

**Execution Quality:**
- **Execution Quality Ratio:** Realized edge ÷ expected edge at entry
- Target: >0.7 (capturing 70%+ of expected edge)
- Alert threshold: <0.6 sustained for rolling 10-day window
- Validates that actual execution matches backtested assumptions

**Contract Matching Accuracy:**
- **Zero catastrophic failures** — absolute threshold
- Any resolution divergence causing directional loss on "matched" contracts halts trading and triggers matching system audit
- Even one matching error means something fundamental is wrong with thesis

**Single-Leg Exposure Management:**
- **Target:** <5 events per month (success threshold)
- **Alert Threshold:** >1 per week sustained for 3+ consecutive weeks triggers investigation (indicates systematic execution reliability issues)
- **Measurement Standard:** <2 events per month for NFR compliance verification
- **Requirement:** All events managed within acceptable loss parameters (average loss <1% of position size)

**Slippage Control:**
- **Average Realized Slippage vs. Modeled:** Within 25% of modeled slippage
- Alert threshold: Excess of 25% for rolling 10-day window
- Validates execution assumptions from backtesting; excess slippage means market microstructure changed or model was miscalibrated

**Platform Relationship Health:**
- **Hard Constraint:** Zero adverse platform actions (trading pattern flags, API access restrictions, punitive terms changes)
- **Soft Metric:** API rate limit utilization <70% of published limits
- **Rationale:** Platform relationship issues are existential risk not captured by other metrics. Getting rate-limited or flagged kills strategy regardless of execution quality.

### Measurable Outcomes

#### Financial Performance Metrics (Hierarchy by Importance)

**1. Maximum Drawdown (Most Critical)**
- Hard limit: 25% (any breach triggers immediate review and trading halt)
- Target: <15% in any rolling 6-month period
- Capital preservation under adverse conditions is fundamental

**2. Sharpe Ratio (Edge Quality)**
- Target: 2.0+ over any rolling 6-month period
- Minimum acceptable: 1.5
- Alert threshold: Below 1.5 sustained for 2 months warrants strategy review
- Measures edge quality, not just magnitude

**3. Profit Factor (Edge Robustness)**
- Target: 1.5+ (gross wins ÷ gross losses)
- Minimum acceptable: 1.3
- Shutdown threshold: Below 1.0 for any rolling 30-day period after initial 3-month validation triggers automatic halt and full review

**4. Net Annualized Return (Output Metric)**
- Target: 15%+ annualized
- Minimum acceptable: 10%+ annualized after all costs
- Below 10%, risk/complexity/opportunity cost not justified

#### Leading Indicators for Edge Degradation

**Opportunity Frequency (Earliest Warning)**
- Baseline: 8-12 actionable opportunities per week (Month 1)
- Alert threshold: Sustained 30%+ decline in weekly opportunity frequency over 3-week window
- Before edge degrades in profitability, it degrades in availability

**Time-to-Convergence (Competition Indicator)**
- Baseline: Dislocations persist 4-6 hours historically
- Alert threshold: 40%+ compression in rolling 14-day median time-to-convergence
- When dislocations close in 30-60 minutes instead of hours, competitors have entered

**Order Book Depth at Execution (Extractable Edge)**
- Monitor: Liquidity available at best prices, spread width trends
- Alert: Sustained decline in average depth at execution points
- Thinning liquidity means practical extractable edge per trade shrinks

#### Strategic Metrics

**Data Accumulation**
- 12-month target: 100+ unique contract pairs traded, 500+ completed cycles, 75%+ resolution outcome data
- This dataset is the foundation for Phase 2 and is genuinely irreplaceable

**Phase 2 Readiness**
- Gate condition: Can formulate and backtest 3+ specific, data-supported hypotheses about news-driven dislocation patterns
- Assessed at 6 and 12 month checkpoints
- If can't identify testable patterns after 12 months data, Phase 2 may not be viable

## Product Scope

### MVP - Minimum Viable Product (Weeks 1-8)

**Philosophy:** The MVP exists to answer exactly one question: "Do actionable cross-platform dislocations exist at sufficient frequency and magnitude to be profitable after real transaction costs?" Every feature that doesn't directly contribute to answering this question is premature infrastructure.

The MVP is deliberately crude. It's a validation tool, not a production system. If the edge doesn't exist, beautiful infrastructure for a non-working strategy is worthless. If the edge does exist, the MVP will be replaced component-by-component by the full Phase 1 system while continuing to generate returns and collect data.

**Pre-MVP: Backtesting & Paper Trading Scope**

The product brief references Phase A (backtesting) and Phase B (paper trading) as prerequisites. This PRD scope begins at **Week 1 of live capital deployment** and assumes backtesting has been completed pre-development:

- **Backtesting (Phase A - Outside System Scope):** Historical data analysis validating arbitrage thesis, estimating edge magnitude, testing detection logic on past dislocations. Completed manually using historical Polymarket/Kalshi order book data before MVP development begins. Outputs inform MVP parameter selection (minimum edge threshold, position sizing, expected opportunity frequency).

- **Paper Trading (Phase B - 3-4 Weeks During MVP Development):** MVP system runs in paper trading mode during final development/testing phase (Weeks 3-4 of 4-week build timeline). System detects opportunities, simulates executions, tracks hypothetical P&L. Validates: Detection logic works on live data, platform API integration functional, execution timing feasible.

- **Live Trading (MVP Week 1+):** System begins real capital deployment at 10% of target ($10K). This PRD describes the live trading system, not the backtesting infrastructure.

**Core Features:**

**Platform Coverage:**
- One platform pair: Polymarket ↔ Kalshi only
- One contract category: U.S. political/economic binaries (highest volume, most obvious cross-platform matches)

**Contract Matching:**
- Manual curation: Personal verification of 20-30 high-volume contract pairs
- Curated pair table maintained in config file
- Zero automation — deliberately labor-intensive but eliminates matching risk entirely

**Execution:**
- Sequential execution: Place more liquid leg first (typically Kalshi), then immediately place second leg on Polymarket
- Accept leg risk: For slow-moving political contracts, prices don't move meaningfully in 10-15 seconds
- Order book depth verification before placing any order

**Exit Management:**
- Fixed thresholds only:
  - Take profit: 80% of initial edge captured
  - Stop loss: 2x initial edge
  - Time-based: 48 hours before contract resolution

**Risk Controls:**
- Position sizing: 3% of bankroll per arbitrage pair maximum
- Portfolio limit: Maximum 10 simultaneous open pairs
- Daily loss limit: 5% of bankroll enforced manually

**Monitoring & Alerting:**
- CSV logging: All trades, prices, fills, P&L logged to timestamped CSV files
- Telegram alerts: Opportunity identification, execution results, exit triggers, system errors
- Polling frequency: 30-second refresh of both platforms' order books
- Automated single-leg detection & alerting with full context for manual decision

**Build Timeline:** 3-4 weeks
- Week 1: Platform API integration
- Week 2: Arbitrage detection logic
- Week 3: Execution logic and exit monitoring
- Week 4: Testing, paper trading validation, operational setup

**MVP Success Gate - Proceed to Phase 1 Build When ALL of These Are True:**

1. **50+ completed arbitrage cycles on real capital**
2. **Aggregate profit factor >1.2 after all real transaction costs**
3. **Zero contract matching errors** (absolute threshold)
4. **Fewer than 3 single-leg exposure events requiring manual intervention with loss**
5. **Evidence that full system would capture meaningful additional edge** — manual tracking confirms opportunities missed due to MVP limitations represent material improvement opportunity

**MVP Failure - Any of These:**
- Profit factor below 1.0 after 50+ cycles
- Fewer than 20 actionable opportunities identified over 8 weeks
- Multiple contract matching errors despite manual curation
- Single-leg exposure events frequent (>1 per week) and costly (average loss >1% of position size)

**Transition:** If MVP validates edge, start building Phase 1 features immediately while continuing to run MVP in production. MVP becomes "legacy system" gradually replaced component-by-component as Phase 1 features come online. No downtime between MVP and Phase 1.

### Phase 1 - Growth Features (Month 6 Complete)

**Goal:** Full institutional-grade system with all five architectural pillars operational at full capital deployment with operational autonomy.

**Core Architectural Pillars:**

**1. Unified Cross-Platform Order Book**
- Real-time normalized aggregation of liquidity across Polymarket, Kalshi, and future venues
- Platform-agnostic abstraction layer: adding new venues is a connector implementation, not a system redesign
- Sub-second refresh rates with graceful degradation protocols

**2. Automated Contract Matching with Confidence Scoring**
- NLP-based semantic matching of contract descriptions, resolution criteria, and settlement dates
- Confidence scoring (0-100%) based on criteria alignment, with position sizing adjusted by matching confidence
- Human-in-the-loop for edge cases: 95%+ matches auto-approve, <85% matches require manual review
- Accumulated knowledge base of resolved matches to improve accuracy over time

**3. Near-Simultaneous Cross-Platform Execution**
- Coordinated order submission across heterogeneous venues (on-chain transactions + exchange API calls)
- Intelligent leg sequencing: execute more liquid/stable leg first, adapt to venue-specific latency profiles
- Graceful leg-risk management: if second leg fails to fill, automatically close or hedge first leg within risk parameters

**4. Model-Driven Exit Framework**
- Continuous recalculation of expected edge based on: fee/slippage updates, liquidity depth changes, contract matching confidence evolution, time to resolution
- Five-criteria exit logic: (1) edge evaporation, (2) model update, (3) time decay, (4) risk budget breach, (5) liquidity deterioration
- Captures remaining edge that fixed thresholds leave on the table

**5. Portfolio-Level Risk Management**
- Correlation-aware position sizing: contracts linked to same underlying event sized as portfolio, not independently
- Dynamic risk budgets: platform counterparty limits, maximum single-leg exposure, daily loss limits with automatic trading halts
- Monte Carlo stress testing against historical and synthetic scenarios

**Operational Infrastructure:**
- Lightweight web dashboard for daily 2-minute morning scan (system health, P&L, open positions, alerts)
- Telegram alerts for real-time notifications
- Full audit trails and compliance monitoring
- Automated regulatory horizon scanning

**Phase 1 Success Criteria:**
- System running at full capital deployment ($100K-$250K)
- Operational autonomy achieved (30-45 minute daily involvement)
- 50+ validated cross-platform contract pairs in knowledge base
- 15-25 simultaneous open positions consistently
- Returns consistent with 15% annualized target, Sharpe >1.5

### Phase 2+ - Vision (Month 12+)

**Strategic Evolution - Only When Phase 2 Gate Conditions Met:**

**Gate Conditions (ALL must be met):**
1. **Operational Stability:** Arbitrage system stable for 8+ consecutive weeks with no major incidents
2. **Data Sufficiency:** Enough live data (3+ months across multiple event categories) to formulate testable hypotheses about news-driven edge
3. **Freed Cognitive Bandwidth:** Operating arbitrage system in 30-45 minutes daily consistently

**News-Velocity Alpha Layer:**
- News ingestion pipeline monitoring feeds, social media, economic data releases
- Correlate news events with observed cross-platform price movements
- Pure analysis for first 4-6 weeks, no trading implications
- If patterns reveal actionable signals, build signal layer feeding into existing execution framework
- Arbitrage system gains "heads up" that dislocation is likely, enabling pre-positioning or faster reaction

**Third Platform Addition:**
- Decision depends on whether edge is real on two platforms and whether additional platforms show sufficient unique liquidity
- Requires validated additional fragmentation and liquidity depth

**Ring 2: Infrastructure Productization (18-24 Months - Optional)**
- Package system as deployable infrastructure for other systematic traders
- Clean documentation, configurable parameters, pluggable platform connectors
- Justifies architectural investments that seemed over-engineered for single-user MVP

**Ring 3: Institutional Scaling (24+ Months - Contingent)**
- Fund structure for managing external capital
- Multi-user access, investor reporting, institutional compliance frameworks
- Contingent on durable edge demonstration and regulatory clarity

**5-Year Speculative Vision:**
- Prediction market infrastructure provider ("Bloomberg Terminal for prediction markets")
- Cross-asset event-driven trading (prediction markets + traditional financial instruments)
- These shouldn't influence near-term decisions but provide strategic direction for "what comes after Phase 2?"

## Operational Workflows

### Journey 1: MVP Deployment Through Validation (Weeks 1-8)

**Persona: Arbi — Quantitative Independent Trader**

**Opening Scene:**

It's 6 AM on a Monday, Week 1 of live trading. Arbi has spent the last 4 weeks building the MVP, and it's been running in paper trading mode for 3 weeks with encouraging results. Today, he's deploying 10% of target capital — $10K — on real trades for the first time. The MVP is deliberately crude: manual contract matching from a curated 20-pair table, sequential execution with accepted leg risk, fixed exit thresholds, CSV logs and Telegram alerts.

He's watching the dashboard constantly. He knows he shouldn't need to, but he will — that's human psychology. First opportunity triggers at 9:47 AM: Polymarket and Kalshi showing a 1.2% spread on a Fed rate contract. The system places the Kalshi leg first (more liquid), fills at expected price. 8 seconds later, Polymarket leg goes out. Telegram pings: "Leg 2 submitted." Another ping 12 seconds later: "Leg 2 filled." Both legs filled, 1.1% net edge captured after fees. P&L tracking matches his mental calculation.

Arbi exhales. First trade done.

**Rising Action:**

Over the next 8 weeks, the system executes 56 arbitrage cycles. Most days are boring — which is exactly what Arbi wants. Morning routine crystallizes by Week 2: 15 minutes reviewing overnight activity, checking the daily summary in his CSV log, approving 2-3 contract matches that need manual verification. Evening routine: 20 minutes comparing week's metrics against backtested expectations.

Week 3, Wednesday afternoon: Telegram alert fires while he's away from desk. "SINGLE-LEG EXPOSURE: Kalshi leg filled at 0.62, Polymarket leg failed to fill, current Polymarket price 0.64. Estimated loss if exit now: 0.8%. Hold or close?"

This is the moment. Arbi opens the dashboard on his phone. The alert has full context: what filled, what didn't, current prices, estimated P&L scenarios. He has two options: close the Kalshi position at a small loss, or wait 60 seconds and retry the Polymarket leg at slightly worse price. He chooses retry. 45 seconds later: "Leg 2 filled at 0.64, arbitrage complete, net edge 0.6%."

The system detected the problem instantly and gave him everything he needed to decide. It didn't panic, didn't make assumptions, didn't need him to dig through logs to understand what happened. That's the trust milestone.

**Climax:**

Week 8: Arbi opens his tracking spreadsheet. The numbers:
- 56 completed cycles
- Profit factor: 1.28 (comfortably above 1.2 threshold)
- Hit rate: 68% (above 65% target)
- Zero contract matching errors
- Two single-leg exposure events, both managed with <1% loss
- Execution quality: 73% of expected edge captured (manual tracking shows opportunities missed due to MVP's crude thresholds and sequential execution)

All five MVP success gate criteria are met. The edge is real. The system works.

**Resolution:**

Arbi starts building Phase 1 features that week — unified order book, NLP contract matching, model-driven exits — while the MVP continues running in production, generating returns and collecting data. The MVP isn't shut down; it's gradually replaced component-by-component as Phase 1 features come online. No downtime. No drama. Just a working system that proved what needed proving.

The transition from "experimental project" to "reliable infrastructure" has begun.

**Requirements Revealed:**
- Real-time alerting with full context (Telegram integration)
- Single-leg exposure detection and operator notification
- CSV-based logging for daily review
- Manual contract matching approval workflow
- Execution tracking and P&L reconciliation
- Success gate metrics dashboard (cycles, profit factor, hit rate, matching errors, single-leg events)

---

### Journey 2: Steady State Operations (Month 3+)

**Persona: Arbi — Three Months Into Live Trading**

**Opening Scene:**

Monday morning, 7:15 AM. Arbi pours coffee and opens the web dashboard on his laptop. The Phase 1 system is now fully operational — all five architectural pillars live, running at 50% of target capital ($50K deployed), managing 18 open arbitrage pairs across Polymarket and Kalshi.

The morning scan takes 2 minutes:
- **System Health:** Green. All APIs connected, data feeds fresh, execution engine operational.
- **Net P&L (trailing 7 days):** +$1,247 (+2.5% weekly). Slightly ahead of 15% annualized target.
- **Execution Quality Ratio:** 0.74 (above 0.7 target — system capturing 74% of expected edge at entry).
- **Open Positions:** 18 pairs, aggregate unrealized edge $892.
- **Active Alerts:** 1 alert — "Contract match confidence 82%, requires manual review."

Everything nominal except the one contract match that needs his judgment.

**The Daily Routine:**

Arbi clicks into the alert. Two contracts displayed side-by-side:
- Polymarket: "Fed cuts rates by 0.25% or more at March meeting"
- Kalshi: "Fed Funds rate 0.25% lower on March 20 than February 28"

The NLP matcher flagged 82% confidence (below the 85% auto-approval threshold) because of a subtle difference: Kalshi's contract resolves on March 20, but the Fed meeting is March 19. If the Fed cuts on March 19 but then some weird restatement happens on March 20, the contracts could resolve differently.

Decision time: 60 seconds. Arbi reads both resolution criteria. The probability of divergent resolution is <1%. He approves the match with a note: "Meeting date vs. resolution date difference, negligible risk." The system logs his decision and adds it to the contract matching knowledge base.

Midday, 12:30 PM: Arbi glances at the dashboard on his phone while grabbing lunch. System health still green. No new alerts. He doesn't open the full interface — the glance is habit, not necessity.

Evening, 7:00 PM: Arbi spends 20 minutes reviewing the week's performance. Key metrics:
- Weekly return: On track for 15% annualized
- Autonomy ratio: 94:1 (94 automated decisions, 1 manual intervention this week)
- Average slippage: 0.31% vs. 0.29% modeled (within 25% tolerance)
- Opportunity frequency: 9 actionable opportunities identified this week (within baseline of 8-12)

No red flags. He spends the next 10 minutes reviewing a Phase 2 research note he started yesterday — correlating news events with cross-platform price movements. The system freed up cognitive bandwidth for strategic work.

**Resolution:**

The day ends with no drama. The system executed 3 new arbitrage pairs, closed 2 positions at profit targets, managed 18 ongoing pairs, and required one 60-second decision from Arbi. Total operator involvement: 28 minutes.

The language has shifted: Arbi no longer thinks "the system executed trades today." He thinks "my trading operation generated $180 today." It's infrastructure.

**Requirements Revealed:**
- Lightweight web dashboard with 2-minute morning scan view (system health, P&L, execution quality, open positions, alerts)
- Contract matching approval workflow with side-by-side resolution criteria comparison
- NLP confidence scoring with auto-approval threshold (85%+)
- Manual decision logging and knowledge base accumulation
- Weekly performance summary with key metrics (autonomy ratio, slippage, opportunity frequency)
- Mobile-friendly dashboard for midday glances
- Phase 2 research workspace (nice-to-have, not core)

---

### Journey 3: Edge Case / Adverse Scenario Handling

**Persona: Arbi — Month 4, Wednesday 2:47 PM**

**Opening Scene:**

Arbi is away from his desk, working on Phase 2 research in another room. His phone buzzes with a Telegram alert:

"⚠️ HIGH PRIORITY: Platform API degradation detected. Polymarket websocket disconnected. Last data: 14:46:32 UTC (81 seconds ago). Graceful degradation protocol activated: All pending Polymarket orders cancelled, no new Polymarket arbitrage pairs initiated. 12 open positions on Polymarket monitored via polling (30-second refresh). Kalshi trading continues normally."

**The Problem:**

The system detected that Polymarket's real-time data feed died. It doesn't know why — could be Polymarket's infrastructure issue, could be network problem, could be rate limiting. What matters: the system can't trust real-time prices from Polymarket anymore.

The graceful degradation protocol kicked in automatically:
1. Cancelled all pending Polymarket orders (don't trade on stale data)
2. Stopped initiating new arbitrage pairs involving Polymarket
3. Switched existing Polymarket positions to polling mode (less precise, but functional)
4. Continues trading Kalshi positions normally

Arbi opens the dashboard. The system health indicator shows **Yellow** (degraded mode, not full failure). The alert log shows exactly what happened, when, and what actions were taken automatically.

**Decision Point:**

Arbi has three options:
1. **Let it run:** The system is handling it. Existing Polymarket positions are still monitored, just on slower polling. If the websocket comes back (often does within 5-10 minutes), system auto-recovers.
2. **Investigate:** Check if this is a known Polymarket issue (Twitter, their status page) or something specific to his connection.
3. **Manual intervention:** Close all Polymarket positions proactively to avoid exposure during degraded monitoring.

He checks Twitter: Polymarket posted 3 minutes ago acknowledging API issues, working on fix. This is a platform-wide problem, not specific to him. Expected resolution: 10-15 minutes.

Decision: Let it run. The system is doing exactly what it should. He sends a reply via Telegram: "Acknowledged. Monitor." The system logs his acknowledgment.

**Rising Action:**

8 minutes later, another Telegram alert:

"✅ RECOVERY: Polymarket websocket reconnected at 14:55:47 UTC. Data feed restored. Graceful degradation protocol deactivated. System returning to normal operations. No positions affected during outage. Ready to resume Polymarket trading."

The system health indicator turns **Green**. Total outage duration: 9 minutes 15 seconds. Impact on portfolio: Zero. The system detected the problem, handled it gracefully, and recovered automatically.

**Resolution:**

That evening, Arbi reviews the incident in detail. The system's audit log shows:
- Detection latency: 81 seconds (the websocket timeout threshold — reasonable)
- Actions taken: All correct per degradation protocol
- Recovery: Automatic, no manual intervention required
- Positions affected: None (monitoring continued via polling during outage)
- Trading impact: 9 minutes of foregone Polymarket opportunities (estimated 0-1 missed trades)

This is the second trust milestone: discovering after the fact that the system handled an adverse scenario correctly while he wasn't even watching. The reaction shifts from "thank god it didn't blow up" to "good, that's what it's supposed to do."

**Alternative Scenario: When Manual Intervention IS Required**

A different day: Alert fires indicating a risk limit approaching breach. Correlated exposure across 6 open positions (all related to Fed policy) is at 13.8% of bankroll, approaching the 15% hard limit. One more Fed-related position would breach the limit.

The system's action: Automatically prevented new Fed-related positions from opening. Flagged for manual review: "Should we close 1-2 existing positions to free up correlation budget, or wait for natural exits?"

Arbi reviews the 6 positions. Three are within 24 hours of resolution (will exit soon naturally). Two have strong remaining edge. One has thin remaining edge (0.3% expected profit, mostly captured already).

Decision: Close the thin-edge position now, freeing up correlation budget without sacrificing meaningful returns. He executes the manual close via the dashboard. The system logs the decision and resumes normal operation with freed correlation budget.

**Requirements Revealed:**
- Real-time platform API health monitoring with automatic degradation detection
- Graceful degradation protocols: cancel pending orders, stop new positions, maintain existing positions on degraded monitoring
- Automatic recovery when platform APIs restore
- High-priority alerting for adverse scenarios (platform issues, risk limits, single-leg exposure)
- Detailed incident audit logs for post-mortem review
- Manual intervention interface for operator decisions during incidents
- Correlation exposure tracking with automatic prevention of limit breaches
- Position-level edge calculation for manual triage decisions

---

### Journey 4: Legal Counsel Quarterly Review

**Persona: Sarah — Prediction Market Regulatory Attorney**

**Opening Scene:**

Sarah receives a quarterly email from Arbi with the subject line: "Q1 2026 Trading Activity — Quarterly Legal Review." Attached: Two files.

1. **`Q1-2026-audit-trail.csv`** — Complete trade log (347 trades across 3 months)
2. **`Q1-2026-compliance-report.pdf`** — 8-page automated compliance summary

Sarah has 30 minutes allocated for this review. She's not looking at individual trades (unless something flags). She's looking for patterns that could create regulatory risk.

**The Review Process:**

Sarah opens the compliance report first. Executive summary on page 1:

**Trading Activity Summary (Q1 2026)**
- Total trades executed: 347 (173 arbitrage pairs, 1 partial fill)
- Platforms: Polymarket (174 trades), Kalshi (173 trades)
- Contract categories: U.S. political events (89%), Economic indicators (11%)
- Total capital deployed: $50K average, peak $62K
- Regulatory alerts flagged: 0

**Platform Relationship Health:**
- API rate limit utilization: Polymarket 43% average, Kalshi 51% average (both well below 70% threshold)
- Platform communications: 2 routine fee change notifications (logged), 0 adverse actions
- Terms of service violations: 0

**Wash Trading Analysis:**
- Cross-platform opposite positions: 173 pairs (expected for arbitrage strategy)
- All cross-platform pairs documented with arbitrage rationale and timestamp correlation
- No same-platform wash trading patterns detected
- Average time between opposite leg placements: 8.3 seconds (consistent with arbitrage execution, not manipulation)

**Anti-Spoofing Compliance:**
- Order cancellation rate: 2.1% (low, consistent with execution-focused strategy)
- No rapid place-cancel patterns flagged
- All cancelled orders logged with cancellation rationale

**Regulatory Horizon Scan (Q1 2026):**
- CFTC filings mentioning prediction markets: 3 routine filings, 0 enforcement actions
- Congressional hearings: 0
- Platform regulatory status changes: Kalshi added new contract categories (no impact on trading strategy)
- Risk assessment: No material changes to regulatory landscape

**The Verification:**

Sarah spot-checks 5 random trades from the audit trail CSV. For each trade, she verifies:
- Arbitrage rationale documented (opposite positions on different platforms, near-simultaneous timing)
- Timestamps consistent with legitimate execution (not spoofing)
- Contract resolution criteria match across platforms (not manipulating divergent outcomes)

All spot checks pass. Nothing unusual.

She reviews the anti-spoofing section more carefully. Order cancellation rate of 2.1% is low (most orders fill) — consistent with an arbitrage strategy that only places orders when genuine edge exists, not a manipulative strategy placing/canceling rapidly to probe liquidity.

**The Edge Case:**

One item flags her attention: On February 18, a single Kalshi position was closed manually without a corresponding Polymarket close. The audit log shows: "Manual close by operator. Rationale: Correlation budget breach, thinning remaining edge. Polymarket leg exited naturally 6 hours later at profit target."

This isn't a violation, but she makes a note: "If manual single-leg closes become frequent (>5% of trades), revisit arbitrage documentation framework." This quarter: 1 out of 347 trades (0.3%) — well within normal.

**Resolution:**

Sarah sends her quarterly summary back to Arbi:

"Q1 review complete. No compliance concerns identified. Trading activity consistent with documented cross-platform arbitrage strategy. All regulatory monitoring indicators green. One note: If manual single-leg position management increases materially (>5% of activity), let's discuss documentation enhancement. Otherwise, continue as-is. Next review: Q2 end."

Total review time: 22 minutes. Sarah can confidently defend this trading activity if questioned. The automated compliance report gave her exactly what she needed to assess regulatory risk without digging through 347 individual trades.

**Requirements Revealed:**
- Automated quarterly compliance report generation
  - Trading activity summary (volume, platforms, categories)
  - Wash trading analysis with cross-platform rationale documentation
  - Anti-spoofing compliance (order cancellation patterns)
  - Platform relationship health (API usage, terms compliance)
  - Regulatory horizon scanning (CFTC filings, hearings, platform status)
- Complete audit trail export in standard CSV format
  - All trades with timestamps, platforms, prices, fills
  - Arbitrage rationale for each cross-platform pair
  - Manual intervention logging with operator rationale
- Audit trail designed for legal review (not just operational logs)
  - Timestamp correlation between opposite legs
  - Cancellation rationale for all non-filled orders
  - Documentation that maps to regulatory compliance frameworks

**Stakeholder Acknowledgment — Tax/Accounting Advisor:**

Tax advisor receives annual export: `2026-tax-report.csv` with complete trade log, P&L summaries by platform and quarter, cost basis tracking, and transaction categorization (on-chain vs. regulated exchange). Clean export enables accurate tax filing without manual reconstruction. This stakeholder does not require a full user journey — they need clean data export, not system interaction.

**Design Implication — Future Technical Collaborator:**

At 12-month checkpoint, if Arbi brings on technical help, the codebase must be well-structured and documented for onboarding. This is a design implication (code quality, documentation standards) rather than a user journey. The operational infrastructure should be documented in runbooks covering deployment, monitoring, common failure scenarios, and clear separation between trading logic and operational infrastructure. This enables eventual handoff without requiring a separate journey map at this stage.

---

### Journey Requirements Summary

These four journeys reveal the core capabilities needed across the system:

**From Journey 1 (MVP Deployment Through Validation):**
- Real-time alerting system (Telegram integration)
- Single-leg exposure detection with full context notifications
- Manual contract matching approval workflow
- CSV-based trade logging for daily review
- Success gate metrics tracking (cycles, profit factor, hit rate, errors)

**From Journey 2 (Steady State Operations):**
- Lightweight web dashboard (2-minute morning scan, mobile-friendly)
- Contract matching approval interface with side-by-side comparison
- NLP confidence scoring with auto-approval thresholds
- Manual decision logging and knowledge base accumulation
- Weekly performance summaries and metric tracking
- Autonomy ratio calculation and trending

**From Journey 3 (Edge Case / Adverse Scenario Handling):**
- Platform API health monitoring with automatic degradation detection
- Graceful degradation protocols (cancel orders, stop new positions, maintain monitoring)
- Automatic recovery when APIs restore
- High-priority alerting for adverse scenarios
- Detailed incident audit logs for post-mortem analysis
- Correlation exposure tracking with automatic limit enforcement
- Manual intervention interface for operator decisions

**From Journey 4 (Legal Counsel Quarterly Review):**
- Automated quarterly compliance report generation
- Complete audit trail export with arbitrage rationale documentation
- Wash trading analysis and anti-spoofing compliance checks
- Platform relationship health reporting
- Regulatory horizon scanning (CFTC, hearings, platform status)
- Audit logs designed for legal review (timestamp correlation, cancellation rationale)

**Cross-Cutting Capabilities:**
- Multi-platform integration (Polymarket, Kalshi)
- Real-time order book aggregation and normalization
- Execution engine with near-simultaneous cross-platform coordination
- Risk management (position sizing, correlation limits, daily loss limits)
- Model-driven exit framework (five-criteria continuous recalculation)
- Portfolio-level monitoring and optimization

## Functional Requirements

### Overview

Functional requirements define the capabilities the system must provide, organized by the five core modules. Each requirement is tagged for MVP or Phase 1 delivery and written as testable actor-capability statements.

### Data Ingestion Module

**FR-DI-01 [MVP]:** System shall maintain real-time connections to Polymarket and Kalshi platform APIs with automatic reconnection on disconnect (max reconnection delay: 60 seconds with exponential backoff).

**FR-DI-02 [MVP]:** System shall normalize heterogeneous platform data into unified internal order book representation within 500ms of platform event (95th percentile).

**FR-DI-03 [MVP]:** System shall detect platform API degradation within 81 seconds of websocket timeout and transition to polling mode automatically.

**FR-DI-04 [MVP]:** System shall publish platform health status updates every 30 seconds (healthy/degraded/offline) based on API response time, order book update frequency, and execution success rate.

**FR-DI-05 [Phase 1]:** System shall support adding new platform connectors without modifying core detection or execution modules (platform-agnostic abstraction layer).

### Arbitrage Detection Module

**FR-AD-01 [MVP]:** System shall identify cross-platform arbitrage opportunities by comparing normalized order book data from all active platforms, completing full detection cycle within 1 second.

**FR-AD-02 [MVP]:** System shall calculate expected edge for each opportunity accounting for platform fees, gas costs (Polymarket), and liquidity depth at execution prices.

**FR-AD-03 [MVP]:** System shall filter opportunities below minimum edge threshold (configurable, default: 0.8% net after all costs).

**FR-AD-04 [MVP]:** Operator can manually approve contract matches flagged by system as requiring human verification (confidence score <85%).

**FR-AD-05 [Phase 1]:** System shall score contract matching confidence (0-100%) using semantic analysis of contract descriptions, resolution criteria, and settlement dates.

**FR-AD-06 [Phase 1]:** System shall auto-approve contract matches with confidence score ≥85% and queue matches <85% for operator review.

**FR-AD-07 [Phase 1]:** System shall accumulate contract matching knowledge base with resolved matches to improve confidence scoring accuracy over time.

### Execution Module

**FR-EX-01 [MVP]:** System shall coordinate near-simultaneous order submission across platforms (both legs submitted within same event loop cycle, target: <100ms between submissions).

**FR-EX-02 [MVP]:** System shall execute more liquid leg first, then immediately execute second leg (sequential execution with accepted leg risk for MVP).

**FR-EX-03 [MVP]:** System shall verify order book depth before placing any order (minimum: size sufficient for target position at expected price).

**FR-EX-04 [MVP]:** System shall detect single-leg exposure within 5 seconds of incomplete arbitrage pair (one leg filled, other failed).

**FR-EX-05 [MVP]:** System shall alert operator immediately with full context when single-leg exposure detected (what filled, current prices, P&L scenarios, recommended actions).

**FR-EX-06 [MVP]:** Operator can choose to retry failed leg at worse price or close filled leg within loss parameters via dashboard interface.

**FR-EX-07 [Phase 1]:** System shall automatically close or hedge first leg if second leg fails to fill within configurable timeout (default: 5 seconds), keeping loss within acceptable parameters.

**FR-EX-08 [Phase 1]:** System shall adapt leg sequencing based on venue-specific latency profiles (execute faster platform first when latency difference >200ms).

### Risk Management Module

**FR-RM-01 [MVP]:** System shall enforce position sizing limit of 3% of bankroll per arbitrage pair maximum.

**FR-RM-02 [MVP]:** System shall enforce portfolio limit of maximum 10 simultaneous open pairs (MVP), 25 pairs (Phase 1).

**FR-RM-03 [MVP]:** System shall halt all trading when daily loss limit (5% of bankroll) is reached and alert operator via high-priority notification.

**FR-RM-04 [MVP]:** Operator can manually approve trades that would exceed normal position limits (override mechanism with explicit confirmation).

**FR-RM-05 [Phase 1]:** System shall calculate correlation exposure across open positions grouped by underlying event category (Fed Policy, Elections, Economic Indicators, Geographic Events).

**FR-RM-06 [Phase 1]:** System shall enforce correlation cluster limit of 15% of bankroll maximum exposure to any single event category.

**FR-RM-07 [Phase 1]:** System shall automatically prevent new positions that would breach correlation limits and alert operator with position-level triage recommendations.

**FR-RM-08 [Phase 1]:** System shall adjust position sizing based on contract matching confidence score (lower confidence = smaller position size, formula: base_size × confidence_score).

**FR-RM-09 [Phase 1]:** System shall run Monte Carlo stress testing against historical and synthetic scenarios to validate portfolio risk parameters.

### Monitoring & Alerting Module

**FR-MA-01 [MVP]:** System shall send Telegram alerts for all critical events (opportunity identification, execution results, exit triggers, single-leg exposure, system errors) with full context within 2 seconds of event.

**FR-MA-02 [MVP]:** System shall log all trades, prices, fills, P&L to timestamped CSV files with 7-year retention for regulatory compliance.

**FR-MA-03 [MVP]:** System shall provide daily summary of system health, P&L, open positions, and alerts accessible via CSV log review.

**FR-MA-04 [Phase 1]:** System shall provide lightweight web dashboard with 2-minute morning scan view showing system health, P&L (trailing 7 days), execution quality ratio, open positions, and active alerts.

**FR-MA-05 [Phase 1]:** System shall present contract matching approval interface with side-by-side resolution criteria comparison for operator review.

**FR-MA-06 [Phase 1]:** System shall log all manual operator decisions (contract approvals, risk overrides, manual closes) with rationale for audit trail and knowledge base accumulation.

**FR-MA-07 [Phase 1]:** System shall generate automated quarterly compliance reports including trading activity summary, wash trading analysis, anti-spoofing compliance checks, platform relationship health, and regulatory horizon scan.

**FR-MA-08 [Phase 1]:** System shall export complete audit trails in CSV format with arbitrage rationale, timestamp correlation, and cancellation rationale for legal review.

**FR-MA-09 [Phase 1]:** System shall calculate and display weekly performance metrics including autonomy ratio (automated decisions ÷ manual interventions), average slippage vs. modeled, and opportunity frequency trends.

### Exit Management

**FR-EM-01 [MVP]:** System shall monitor open positions continuously and trigger exits based on fixed thresholds: take profit at 80% of initial edge captured, stop loss at 2× initial edge, time-based exit 48 hours before contract resolution.

**FR-EM-02 [Phase 1]:** System shall continuously recalculate expected edge for open positions based on fee/slippage updates, liquidity depth changes, contract matching confidence evolution, and time to resolution.

**FR-EM-03 [Phase 1]:** System shall trigger exits based on five criteria: (1) edge evaporation, (2) model update reducing confidence, (3) time decay reducing expected value, (4) risk budget breach, (5) liquidity deterioration below acceptable threshold.

### Contract Matching & Knowledge Base

**FR-CM-01 [MVP]:** Operator can manually curate and verify 20-30 high-volume contract pairs maintained in configuration file (zero automation for MVP).

**FR-CM-02 [Phase 1]:** System shall perform semantic matching of contract descriptions, resolution criteria, and settlement dates to identify potential cross-platform pairs.

**FR-CM-03 [Phase 1]:** System shall store validated contract matches in knowledge base with platform IDs, resolution criteria hash, confidence score, operator approval timestamp, and final resolution outcome.

**FR-CM-04 [Phase 1]:** System shall use resolution outcome data from knowledge base as feedback to improve confidence scoring accuracy for future matches.

### Platform Integration & Compliance

**FR-PI-01 [MVP]:** System shall authenticate with Kalshi using API key-based authentication per platform requirements.

**FR-PI-02 [MVP]:** System shall authenticate with Polymarket using wallet-based authentication (private key signing) for on-chain transactions.

**FR-PI-03 [MVP]:** System shall enforce platform-specific rate limits with 20% safety buffer, queueing requests when approaching limits to prevent platform throttling.

**FR-PI-04 [MVP]:** System shall track API rate limit utilization in real-time and alert when exceeding 70% of published limits.

**FR-PI-05 [MVP]:** System shall validate all trades against compliance matrix (platform, jurisdiction, contract category restrictions) before execution, hard-blocking non-compliant trades with operator notification.

**FR-PI-06 [Phase 1]:** System shall retrieve API keys and wallet private keys from external secrets management service at startup (not stored in process memory long-term).

**FR-PI-07 [Phase 1]:** System shall support zero-downtime API key rotation for all platforms with <5 seconds degraded operation during switchover.

### Data Export & Reporting

**FR-DE-01 [MVP]:** System shall export trade logs in structured JSON format with CSV export capability for audit and tax reporting.

**FR-DE-02 [MVP]:** System shall generate annual tax report CSV with complete trade log, P&L summaries by platform and quarter, cost basis tracking, and transaction categorization (on-chain vs. regulated exchange).

**FR-DE-03 [Phase 1]:** System shall generate quarterly compliance reports in PDF format with standardized sections (trading activity, wash trading analysis, anti-spoofing compliance, platform health, regulatory horizon scan).

**FR-DE-04 [Phase 1]:** System shall export audit trails on demand for any time period within 7-year retention window with timestamp correlation, cancellation rationale, and legal review formatting.

## Domain-Specific Requirements

### Compliance & Regulatory

**Data Retention Requirements:**
- **Mandatory retention period:** 7 years for all trade logs, consistent with IRS record-keeping requirements and general financial regulatory expectations
- **Storage format:** Structured JSON with CSV export capability
- **Non-negotiable:** This is a hard system requirement, not optional
- **Scope:** All trades, executions, order placements, cancellations, manual interventions, risk events, and compliance reports

**KYC/AML Obligations:**
- **Platform-handled:** All KYC/AML compliance is managed by trading platforms (Kalshi regulated entity compliance, Polymarket wallet-based access)
- **System responsibility:** None. The system trades through pre-authenticated accounts and has no direct KYC obligations
- **Entity compliance:** Operator entities complete platform-level KYC during account setup, not at system runtime

**CFTC Reporting Thresholds:**
- **Current scale:** At $100K-$250K capital deployment, well below large trader reporting thresholds
- **Proactive monitoring:** System tracks cumulative position sizes per contract category
- **Alert threshold:** 50% of any known reporting threshold triggers soft alert (notification, not trading halt)
- **Rationale:** Safety margin to avoid inadvertent threshold breaches as capital scales

### Technical Constraints

**API Rate Limiting & Request Management:**
- **Automatic request throttling:** Exponential backoff when approaching rate limits
- **Proactive monitoring:** Track rolling request counts against known platform limits
- **Pre-emptive slowdown:** Reduce polling frequency before hitting limits (target: <70% utilization)
- **This is a functional requirement,** not just a metric - system must enforce rate limit compliance to prevent platform restrictions

**Wallet Security (On-Chain Execution):**
- **MVP standard:** Private keys stored in environment variables, never in code or config files
- **Phase 1 requirement:** Secrets management service supporting key rotation, audit logging, encryption at rest, and API-based credential retrieval
- **Hardware wallet consideration:** Ideal for security but adds execution latency - defer evaluation to Phase 1 based on performance requirements
- **Key rotation:** Support key rotation without system downtime (Phase 1)

**On-Chain Privacy:**
- **MVP approach:** Minimal concern at current capital scale ($100K-$250K)
- **Known limitation:** Polymarket wallet address publicly visible on Polygon blockchain
- **Trade-off accepted:** Privacy solutions add complexity not justified at current scale
- **Future consideration:** If scaling to multi-million dollar operations (Phase 2+), evaluate privacy solutions (fresh wallets per trade, mixers, privacy-preserving protocols)

**Cross-Border Trading Compliance:**
- **Per-platform restrictions:**
  - Kalshi: U.S.-only, requires U.S. entity/residency compliance
  - Polymarket: Global access with platform-specific geo-restrictions
- **System requirement:** Maintain per-platform compliance configuration specifying which contract types are tradeable from which entity
- **MVP implementation:** Hardcoded compliance rules in configuration file
- **Phase 1 implementation:** Configurable compliance matrix with validation before trade execution

### Integration Requirements

**Platform API Integration:**
- **Authentication:** Secure API key management with platform-specific authentication flows
- **Connection resilience:** Handle platform API outages, latency spikes, and version changes gracefully
- **Data normalization:** Transform heterogeneous platform data formats into unified internal representation

**Secrets Management Integration (Phase 1):**
- **External secrets service:** Integration with secrets management service supporting key rotation, audit logging, and encryption at rest
- **Runtime key retrieval:** Fetch private keys and API credentials at startup, not stored in process memory long-term
- **Audit logging:** All secrets access logged for security audit trail

**Regulatory Data Sources (Compliance Monitoring):**

**Scope Clarification:** This is automated *monitoring* and *alerting*, NOT automated legal analysis. System flags potentially relevant regulatory developments for operator review; operator (with legal counsel as needed) interprets impact and decides on response.

**Automated Monitoring (Phase 1):**
- **CFTC filings:** RSS feed monitoring of CFTC.gov public filings, keyword alerts for "prediction market", "event contract", "Kalshi", "Polymarket"
- **Platform status:** API polling of Kalshi/Polymarket status pages (hourly), email forwarding rules for platform regulatory announcements to system monitoring inbox
- **Google Alerts:** Configured for search terms: "prediction market regulation", "CFTC prediction market", "Kalshi regulatory", "Polymarket regulatory"
- **Congressional calendar:** Manual check (operator responsibility) - not automated due to complexity and low signal-to-noise ratio

**Alert Triggers:**
- Any CFTC filing containing prediction market keywords: Immediate alert to operator with filing link and matched keywords
- Platform service disruption >2 hours: High-priority alert (potential regulatory action or compliance issue)
- Google Alert match on regulatory keywords: Daily digest sent to operator for review
- Platform email announcements with subject containing "regulatory", "compliance", "terms": Forward to operator inbox immediately

**No AI/NLP Analysis Required:** All monitoring uses simple keyword matching, RSS parsing, and API polling - implementable with standard tools without machine learning or natural language understanding.

### Risk Mitigations

**Platform Adverse Action Detection:**
- **Challenge:** System cannot directly know if trading activity has been flagged by platform compliance
- **Indirect signal monitoring:**
  - Unexpected API errors (403 Forbidden, new error codes not in documentation)
  - Rate limit reductions (previously 1000 req/min, now 500 req/min without announcement)
  - Delayed trade fills (execution latency suddenly 10x slower)
  - Account restriction emails (forwarded to system monitoring inbox)
- **Anomalous pattern detection:** Log all API response codes, alert when error rate exceeds 5% of requests or new error types appear
- **Manual escalation:** High-severity alert to operator for investigation, potential pause on affected platform

**Compliance Configuration Management:**
- **Per-platform rules:** Maintain compliance configuration specifying which contract categories are tradeable based on entity domicile and platform restrictions
- **Validation before execution:** Before placing any order, validate contract category against compliance matrix for that platform
- **Reject non-compliant trades:** Hard block on trades that violate compliance rules, with clear operator notification of why trade was rejected

**Data Retention & Audit Readiness:**
- **7-year retention enforced:** Automated retention policy prevents deletion of required records
- **Tamper-evident logging:** Trade logs cryptographically signed or stored in append-only structure
- **Export on demand:** Ability to generate compliant audit trail exports (CSV, JSON) for any time period within retention window
- **Legal review optimization:** Audit trail format designed for legal review, not just operational debugging

**Regulatory Horizon Scanning:**
- **Automated monitoring:** Track CFTC filings, congressional hearings, platform regulatory status changes
- **Risk severity categorization:** Low/Medium/High severity alerts based on potential impact
- **Response playbooks:** Pre-defined actions for different regulatory scenarios (e.g., major adverse ruling → 50% exposure reduction within 24 hours)

### Opportunity Frequency Baseline

**Baseline Definition:**
"8-12 actionable opportunities per week" serves as the success metric for validating the arbitrage thesis. This baseline requires precise definition to enable meaningful tracking and edge degradation detection.

**Active Trading Week Conditions:**
An "active trading week" is defined as a 7-day period meeting all of the following conditions:
- **Both platforms operational:** Polymarket and Kalshi APIs available with <5% downtime during active market hours (Mon-Fri 9am-5pm ET)
- **Normal market conditions:** No extraordinary events disrupting prediction market activity (platform outages >4 hours, major regulatory announcements, extreme volatility events)
- **Sufficient liquidity:** Average order book depth at best prices >$500 equivalent per side across tracked contract categories
- **System operational:** Trading system uptime >95% during the week, no manual trading halts or testing modes

**Actionable Opportunity Criteria:**
An opportunity qualifies as "actionable" if it meets ALL of the following:
- **Edge threshold:** Net expected edge >0.8% after all transaction costs (fees, gas, slippage)
- **Liquidity requirement:** Order book depth sufficient to execute target position size (3% of bankroll) at expected prices
- **Risk budget availability:** Execution would not breach any risk limits (correlation cluster <15%, position count <10 for MVP/<25 for Phase 1, daily capital deployment within target)
- **Contract matching confidence:** Manual verification (MVP) or confidence score >threshold (Phase 1: 85%+)
- **Timing validity:** Opportunity persists for minimum 10 seconds (filters out fleeting noise, ensures genuine dislocation)

**Baseline Rationale:**
- **8 opportunities/week = minimum viable:** Indicates edge exists but barely sufficient for target returns (15% annualized)
- **12 opportunities/week = healthy:** Comfortable margin above minimum, indicates robust arbitrage environment
- **<6 opportunities/week sustained for 3 weeks:** Alert threshold - edge may be compressing, triggers investigation
- **<4 opportunities/week sustained for 3 weeks:** Critical threshold - strategy viability questionable, consider scaling down or pausing

**Measurement & Tracking:**
- Log all detected opportunities (actionable + filtered) with reasons for filtering
- Weekly summary: Total opportunities detected, actionable count, filter reasons breakdown
- Trend analysis: 4-week rolling average to smooth weekly variance, alert if below baseline
- Market condition context: Correlate opportunity frequency with platform uptime, news event calendar, volatility measures

### Correlation Management Framework

**Purpose:**
Prevent concentrated exposure to single underlying events that could cause correlated losses across multiple arbitrage pairs. For example, 6 open Fed policy contracts are not 6 independent positions - they're a single $40K exposure to Fed decision outcomes.

**Contract Correlation Clusters:**

Arbitrage pairs grouped into correlation clusters based on underlying event category:

1. **Fed Policy Cluster**
   - Events: Fed rate decisions, FOMC meeting outcomes, inflation data releases, Fed chair statements
   - Examples: "Fed cuts rates March meeting" (Polymarket) ↔ "Fed Funds rate lower March 20" (Kalshi)
   - Correlation assumption: 0.9+ (extremely high - all resolve based on same Fed action)

2. **Election Outcomes Cluster**
   - Events: Presidential election, Senate races, House races, gubernatorial elections
   - Examples: "Trump wins 2024" ↔ "Republican presidential victory 2024"
   - Correlation assumption: 0.7-0.9 (high - many resolve on same election night, some cross-correlation between races)

3. **Economic Indicators Cluster**
   - Events: GDP growth, unemployment rate, CPI, jobless claims, consumer sentiment
   - Examples: "Q1 GDP >2%" ↔ "Positive GDP growth Q1"
   - Correlation assumption: 0.5-0.7 (moderate - related to same economy but different indicators)

4. **Geographic Events Cluster**
   - Events: Natural disasters, geopolitical conflicts, regional referendums, state-level policy
   - Examples: "California wildfire severity >X" ↔ "Western US air quality alert"
   - Correlation assumption: 0.3-0.6 (low-moderate - geographic proximity creates correlation)

5. **Uncategorized/Independent**
   - Events not fitting above clusters, assumed independent
   - Each contract pair treated as its own cluster (correlation 0.0 with others)

**Portfolio Correlation Calculation:**

For each cluster, calculate total exposure:
```
Cluster Exposure = Sum of (Position Size × Entry Price) for all open pairs in cluster
Cluster Exposure % = (Cluster Exposure ÷ Total Bankroll) × 100%
```

**Risk Limits:**
- **Hard limit:** No single cluster can exceed 15% of bankroll
- **Soft limit:** Alert if any cluster exceeds 12% (warning - approaching limit)
- **Aggregate limit:** Sum of all cluster exposures should not exceed 50% of bankroll (prevents over-concentration even if no single cluster breaches)

**Position Sizing Adjustment:**

When opening new position in cluster already >8% exposure:
```
Adjusted Position Size = Base Size × (1 - (Current Cluster % ÷ 15%))
```

Example:
- Fed Policy cluster currently at 10% of bankroll
- New Fed opportunity detected, base size would be 3% of bankroll
- Adjusted size = 3% × (1 - (10% ÷ 15%)) = 3% × 0.33 = 1% of bankroll
- Rationale: Reduce new position size as cluster exposure approaches limit

**Enforcement:**
- Before executing any trade, check cluster classification for both contracts
- Calculate cluster exposure with new position
- If new exposure would breach 15% hard limit: Reject trade, log as "filtered by correlation limit"
- If new exposure 12-15%: Allow trade but alert operator with triage recommendations ("Consider closing position X in Fed cluster to free budget")

**Operator Triage Interface (Phase 1):**
When correlation limit approached, dashboard displays:
- Current positions in affected cluster
- Remaining edge for each position (calculated by model-driven exit framework)
- Recommendation: Close position(s) with lowest remaining edge to free correlation budget
- One-click close action for operator decision

**Knowledge Base:**
- System maintains cluster classification for all known contract pairs
- Operator can override cluster assignment if domain knowledge indicates lower/higher correlation
- Overrides logged to audit trail with rationale

### Contract Matching Knowledge Base Schema

**Purpose:**
The knowledge base is a strategic asset accumulating validated contract matches and resolution outcomes. This data drives three capabilities:
1. **Confidence scoring improvement:** Resolution outcomes validate/invalidate semantic matching logic, feedback loop improves Phase 1 NLP accuracy
2. **Operator efficiency:** Recurring contracts (monthly Fed meetings, quarterly GDP) auto-approved based on historical validation
3. **Risk management:** Tracks divergent resolutions (matches that should have converged but didn't) to refine matching criteria

**Storage Format:**
- **Technology:** SQLite database (simple, serverless, file-based, 7-year retention compatible)
- **Table:** `contract_matches` with following schema

**Schema Fields:**

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| match_id | INTEGER PRIMARY KEY | Auto-increment unique identifier | 1 |
| polymarket_contract_id | TEXT | Polymarket contract identifier | "0x3a4b..." |
| kalshi_contract_id | TEXT | Kalshi contract ticker | "FEDRATE-23DEC-T0.25" |
| polymarket_description | TEXT | Full contract description from Polymarket | "Fed cuts rates by 0.25% or more at December meeting" |
| kalshi_description | TEXT | Full contract description from Kalshi | "Fed Funds rate 0.25% lower on Dec 20 than Nov 30" |
| resolution_criteria_hash | TEXT | SHA-256 hash of normalized resolution criteria (both platforms) | "a3f2..." |
| confidence_score | REAL | NLP confidence score 0-100% (NULL for MVP manual matches) | 87.5 |
| operator_approved | BOOLEAN | Human verification flag | TRUE |
| operator_approval_timestamp | TEXT | ISO 8601 timestamp of approval | "2026-02-15T14:32:00Z" |
| operator_rationale | TEXT | Approval notes/concerns | "Meeting date vs resolution date difference, negligible risk" |
| first_traded_timestamp | TEXT | First time this pair was traded | "2026-02-16T09:15:00Z" |
| total_cycles_traded | INTEGER | How many times this pair was arbitraged | 12 |
| polymarket_resolution | TEXT | Final resolution outcome ("YES", "NO", "INVALID", NULL if unresolved) | "YES" |
| kalshi_resolution | TEXT | Final resolution outcome | "YES" |
| resolution_timestamp | TEXT | When contracts resolved | "2026-12-20T14:00:00Z" |
| resolution_diverged | BOOLEAN | Did resolutions differ? Critical flag for matching error detection | FALSE |
| divergence_notes | TEXT | If diverged, why? Root cause analysis | NULL |

**Feedback Loop into Confidence Scoring (Phase 1):**
- After contract resolution, compare `polymarket_resolution` to `kalshi_resolution`
- If both "YES" or both "NO": Positive validation, increase future confidence for similar semantic patterns
- If diverged: Negative signal, analyze `divergence_notes` to identify failure pattern, reduce confidence for similar patterns, alert operator
- Quarterly batch analysis: Review all resolved matches, retrain/calibrate NLP confidence model based on outcomes

**Operator Interface (Phase 1):**
- Dashboard displays pending matches requiring approval (confidence <85%)
- Side-by-side view: Both contract descriptions, resolution criteria, confidence score, similar historical matches
- Approval action logs `operator_rationale` to knowledge base
- Resolved contracts view: Filterable by divergence flag to review matching errors

### Price Normalization Logic

**Problem:**
Polymarket uses decimal probabilities (0.00 to 1.00), Kalshi uses cents (0¢ to 99¢). Cross-platform arbitrage detection requires unified pricing to calculate edge and compare opportunities.

**Normalization Standard:**
All internal calculations use **decimal probability format (0.00 to 1.00)**, matching Polymarket convention.

**Kalshi → Internal Conversion:**
```
Internal Price = Kalshi Price (¢) ÷ 100
Example: Kalshi showing 62¢ → Internal representation 0.62
```

**Internal → Kalshi Conversion (for order submission):**
```
Kalshi Price (¢) = Internal Price × 100, rounded to nearest cent
Example: Internal 0.625 → Kalshi 62¢ or 63¢ (rounding decision: round to nearest)
```

**Edge Calculation Formula:**
```
Net Edge = |Polymarket Price - Kalshi Price| - Total Fees - Gas Estimate

Where:
  Polymarket Price: Already in decimal format (0.00-1.00)
  Kalshi Price: Converted to decimal (¢ ÷ 100)
  Total Fees: (Polymarket taker fee + Kalshi taker fee) in decimal
  Gas Estimate: Polymarket gas cost in dollar terms ÷ position size, converted to decimal

Example:
  Polymarket: 0.58 (buy YES at 58%)
  Kalshi: 62¢ → 0.62 (sell YES at 62%, equivalent to buy NO at 38%)
  Polymarket fee: 2% = 0.02
  Kalshi fee: 1.5% = 0.015
  Gas: $0.50 for $300 position = 0.0017

  Gross Edge = |0.58 - (1 - 0.62)| = |0.58 - 0.38| = 0.20 (20%)
  Net Edge = 0.20 - 0.02 - 0.015 - 0.0017 = 0.1633 (16.33% net profit potential)
```

**Rounding Considerations:**
- Kalshi only accepts integer cent prices (no fractional cents)
- When converting internal price to Kalshi for order submission: Round to nearest cent (0.625 → 63¢)
- Rounding can introduce ±0.5¢ (±0.005) variance in executed price vs. calculated edge
- This variance is acceptable: Edge threshold (0.8% minimum) provides >10× margin over rounding error

**Fee Normalization:**
Both platforms charge percentage fees, already in compatible format:
- Polymarket: 2% taker fee → 0.02 multiplier
- Kalshi: 1.5% taker fee → 0.015 multiplier
- Gas (Polymarket only): Convert dollar cost to percentage of position size

**Validation:**
- After normalization, sanity check: All prices should be 0.00 ≤ price ≤ 1.00
- If any price outside range: Log error, reject opportunity, alert operator (likely data corruption or API change)

## API Backend Specific Requirements

### System Architecture

**Module Boundaries:**

The system is composed of five core modules with defined interfaces:

1. **Data Ingestion Module**
   - Responsibility: Maintain connections to platform APIs, normalize heterogeneous data into unified internal format
   - Output: Normalized order book snapshots, platform health status
   - Interface: Publishes order book updates and platform status to Detection Module

2. **Arbitrage Detection Module**
   - Responsibility: Identify actionable cross-platform arbitrage opportunities
   - Input: Normalized order book data from Data Ingestion
   - Output: Opportunity signals with expected edge, confidence scores, and execution parameters
   - Interface: Publishes opportunities to Execution Module, queries Risk Module for position constraints

3. **Execution Module**
   - Responsibility: Coordinate near-simultaneous order placement across platforms, manage leg risk
   - Input: Opportunity signals from Detection, position constraints from Risk
   - Output: Execution results, single-leg exposure events, fill confirmations
   - Interface: Sends execution commands to platform APIs via Data Ingestion, reports results to Risk and Monitoring

4. **Risk Management Module**
   - Responsibility: Enforce position sizing, correlation limits, daily loss limits, portfolio-level constraints
   - Input: Position requests from Execution, current portfolio state
   - Output: Approved/rejected position decisions, risk limit alerts
   - Interface: Provides constraint validation to Execution, alerts to Monitoring

5. **Monitoring & Alerting Module**
   - Responsibility: Dashboard data aggregation, alert generation, compliance reporting, audit log management
   - Input: Events from all modules (executions, risks, opportunities, platform health)
   - Output: Dashboard API, Telegram alerts, compliance reports, audit logs
   - Interface: Consumes events from all modules, exposes dashboard API, generates exports

**Implementation Flexibility:**

The PRD specifies module boundaries and interfaces. Whether these are in-process modules (MVP) or separate services (Phase 1+) is an implementation decision. The key requirement: modules communicate through defined interfaces that enable future decomposition if needed.

### Authentication & Authorization

**Dashboard Authentication:**

- **MVP Standard:** Basic authentication or API token for single operator access
- **Context:** Single-user system on private network, security model optimized for operational simplicity
- **Phase 1 Enhancement:** Token-based authentication with session management
- **Not Required:** Multi-user access control, OAuth, complex permission systems

**Platform API Authentication:**

- **Kalshi:** API key-based authentication per Kalshi platform requirements
- **Polymarket:** Wallet-based authentication (private key signing) for on-chain transactions
- **Key Rotation:** Quarterly rotation of platform API keys (operational procedure, not automated system feature)
- **Secrets Management:** Environment variables (MVP), external secrets manager (Phase 1)

### Data Formats & Schemas

**Normalized Internal Order Book Representation:**

The contract between Data Ingestion and Detection modules. Each order book snapshot must include:

```
{
  platform: string           // "polymarket" | "kalshi"
  contract_id: string        // Platform-specific contract identifier
  contract_description: string
  resolution_date: timestamp
  best_bid: {
    price: decimal (0-1)     // Normalized probability
    size: decimal            // Executable size at this price
    liquidity_depth: decimal // Total liquidity within 1% of best price
  }
  best_ask: {
    price: decimal (0-1)
    size: decimal
    liquidity_depth: decimal
  }
  fees: {
    taker_fee: decimal       // Platform fee for immediate execution
    maker_fee: decimal       // Platform fee for posted orders
    gas_estimate: decimal    // Gas cost estimate (Polymarket only)
  }
  timestamp: timestamp       // Order book snapshot time
  platform_health: enum      // "healthy" | "degraded" | "offline"
}
```

This normalized format enables the Detection Module to perform cross-platform comparison without platform-specific logic.

**Export Formats:**

- **Trade Logs:** Structured JSON with CSV export capability (7-year retention)
- **Compliance Reports:** PDF format with structured sections (trading activity summary, wash trading analysis, regulatory horizon scan)
- **Audit Trails:** CSV with standardized columns (timestamp, platform, contract, action, rationale, outcome)
- **Tax Reports:** CSV with transaction categorization (on-chain vs. regulated exchange)

**Dashboard API:**

- **Protocol:** RESTful JSON for state queries, WebSocket for real-time updates (execution events, alerts)
- **Endpoints:** System health, P&L summary, open positions, alert queue, contract match approval queue
- **Update Frequency:** WebSocket push for events, REST polling for state (max 1 req/sec)

### Platform API Integration

**API Version Compatibility:**

- **Behavior on version change:** Alert operator, graceful degradation (continue with last known good behavior, halt new trade execution until operator reviews)
- **Detection:** Monitor API response schemas for unexpected fields or missing expected fields
- **Fallback:** System continues monitoring existing positions but does not initiate new trades on platforms with unrecognized API behavior

**Error Handling & Retry Logic:**

- **Retry strategy:** Exponential backoff (1s, 2s, 4s), maximum 3 retries per request
- **Permanent failure:** After 3 failed retries, alert operator and transition to degraded mode for that platform
- **Transient errors:** Distinguish between retriable errors (503 Service Unavailable, timeout) and permanent errors (401 Unauthorized, 403 Forbidden)
- **Rate limit errors:** If 429 Too Many Requests received, back off exponentially and alert if rate limit utilization exceeds safety threshold

**Data Normalization:**

- **Target format:** Normalized internal order book representation (specified above)
- **Mapping responsibility:** Data Ingestion Module transforms platform-specific formats to normalized schema
- **Graceful degradation:** If platform introduces new fields or changes schema, log warning, attempt to continue with available data, alert operator

**Connection Resilience:**

- **Polymarket:** WebSocket connection with automatic reconnection on disconnect, fallback to polling if WebSocket unavailable
- **Kalshi:** Maintain persistent connection, handle API rate limits proactively (70% utilization threshold)
- **Health monitoring:** Continuous tracking of API response times, error rates, and connection stability
- **Degradation protocol:** Defined in Domain-Specific Requirements (Risk Mitigations section)

### Implementation Considerations

**Development Priorities:**

1. **MVP Focus:** Prove the edge exists (manual contract matching, sequential execution, fixed thresholds)
2. **Phase 1 Investment:** Build sophistication (NLP matching, model-driven exits, correlation-aware sizing)
3. **Phase 2+ Evolution:** Layer additional alpha sources (news-velocity signals)

**Technology Constraints:**

- **Single long-running process (MVP):** Continuous operation, no scheduled batch jobs
- **Stateful operation:** Maintains open position state, risk budget state, contract matching knowledge base
- **Real-time requirements:** Sub-second order book processing, 30-second polling frequency minimum
- **Reliability over features:** 99%+ uptime more important than feature richness

**Operational Requirements:**

- **Deployment:** Single-server deployment (MVP), can scale to distributed if needed (Phase 1+)
- **Monitoring:** Operator dashboard + Telegram alerts sufficient for single-user operation
- **Maintenance window:** Must support deployment updates without data loss (save state, restart, restore)

### State Recovery & Crash Handling

**State Persistence:**
- **What to persist:** Open positions (platform IDs, entry prices, sizes, timestamps), risk budgets (daily loss, correlation exposure by cluster, position count), pending orders (order IDs, submission timestamps, expected fills), contract matching knowledge base
- **When to persist:** After each state change (position opened/closed, order submitted, risk budget updated), maximum 5-second intervals for periodic snapshots
- **Where to persist:** Local SQLite database for structured data (positions, orders, risk state) + JSON files for configuration (contract pairs, compliance rules) with atomic write-rename pattern to prevent corruption

**Recovery Scenarios:**

1. **Process crash before order submission:** No action required - no state changed, system restarts cleanly
2. **Crash after first leg submitted but before state written:** Startup reconciliation queries both platform APIs for fills in last 60 seconds, compares against local state file, flags any discrepancies (orphan fills, missing positions) for immediate operator review via high-priority alert
3. **Crash after state written with open positions:** Restore positions from SQLite, re-subscribe to platform feeds, resume monitoring and exit logic for all open pairs
4. **Crash during state write (partial corruption):** SQLite rollback journal ensures atomicity; JSON config uses write-to-temp + atomic rename to prevent corruption

**Startup Reconciliation Procedure:**
1. Load last known state from SQLite (timestamp of last write)
2. Query Polymarket and Kalshi APIs for all fills/orders in time window: [last_state_timestamp - 60s, current_time]
3. Match API-reported fills against local state file
4. If discrepancy detected (fill reported by API but not in local state): Create high-priority alert with full details (platform, contract, price, size, timestamp), flag position as "RECONCILIATION REQUIRED", halt new trading until operator confirms corrective action
5. Log reconciliation results to audit trail (positions matched, discrepancies found, operator actions taken)

### Deployment & Infrastructure Requirements

**Deployment Target:**
- **Host:** Single Linux server (cloud VM or bare metal), Ubuntu 20.04+ or Debian 11+
- **Minimum specifications:** 2 vCPU, 4GB RAM, 50GB SSD storage (logs and state data), stable internet with <50ms latency to major cloud regions
- **Network requirements:** Outbound HTTPS (443) for platform APIs, outbound access to Polygon RPC nodes (Polymarket), inbound access for dashboard (port 8080, localhost only for MVP)

**Host Failure Handling:**
- **MVP:** Manual restart required - operator receives alert (via external monitoring service or platform API errors), investigates failure, restarts process manually, reviews startup reconciliation for data integrity
- **Phase 1:** Automated failover to standby host - health check service detects primary failure (missed 3 consecutive heartbeats over 90 seconds), triggers standby activation, standby host loads state from shared storage (NFS or S3), resumes operation, alerts operator of failover event

**Backup & Restore:**
- **Backup scope:** Stateful data (open positions SQLite database, contract matching knowledge base, audit logs, configuration files)
- **Backup frequency:** Hourly automated snapshots to local backup directory + cloud storage (S3 or equivalent), retained for 7 days rolling window
- **Backup verification:** Weekly automated restore test to separate environment, validates backup integrity and restore procedure
- **Restore procedure:** (1) Stop trading process, (2) Restore SQLite database from most recent backup, (3) Verify data integrity (row counts, timestamp ranges), (4) Start process with reconciliation mode enabled, (5) Review reconciliation results before resuming trading

**Deployment Without Data Loss:**
- **Blue/Green deployment approach:**
  1. Start new process version (green) in standby mode (connects to APIs for data feeds but does not trade)
  2. Verify green connectivity and health (all platform APIs connected, data feeds operational, no errors for 60 seconds)
  3. Transfer state file from blue (current) to green via atomic file copy
  4. Activate green for trading (begin accepting opportunities, executing trades)
  5. Graceful shutdown of blue (complete any in-flight order submissions, finalize state writes, disconnect from APIs)
  6. Monitor green for 5 minutes post-activation, rollback to blue if errors detected
- **Rollback procedure:** If green encounters errors within 5-minute observation window, reverse activation (shut down green, restart blue with restored state, investigate green failure in offline environment)

### Concurrent Execution Conflict Handling

**Problem Definition:**
Two or more arbitrage opportunities detected simultaneously (within same detection cycle) that would individually be acceptable, but combined would breach risk limits. Examples:
- Two Fed policy contracts detected, each using 8% correlation budget, combined 16% exceeds 15% cluster limit
- Three opportunities detected when portfolio already has 8 open pairs, accepting all three would breach 10-pair maximum
- Multiple opportunities totaling 12% capital when daily deployed capital already at 90% of target

**Solution: Sequential Execution Locking with Atomic Risk Budget Reservation**

**Design:**
1. **Detection:** Arbitrage detection module identifies all opportunities in current cycle, scores and ranks by expected edge
2. **Reservation:** For each opportunity in rank order (highest edge first):
   - Attempt atomic risk budget reservation (correlation exposure, position count, daily capital)
   - Reservation checks: Does this opportunity + current portfolio breach any limit?
   - If reservation succeeds: Mark opportunity as "reserved", proceed to execution queue
   - If reservation fails: Skip opportunity, log as "filtered by risk limits", continue to next opportunity
3. **Execution:** Execution module processes reserved opportunities sequentially (one at a time)
4. **Release:** After execution completes (both legs filled OR opportunity abandoned), release or commit reservation:
   - If execution succeeded: Commit reservation (update actual risk budgets with new position)
   - If execution failed: Release reservation (return risk budget to available pool)

**Atomic Reservation Implementation:**
- **Lock-based approach (MVP):** Global execution lock ensures only one opportunity processed at a time, reservation check + execution happens atomically within lock
- **Optimistic concurrency (Phase 1):** Risk budget tracked with version counter, reservation attempts increment version, conflicts detected via version mismatch and retried

**Logging & Observability:**
- All filtered opportunities logged with reason: "Filtered: correlation limit (Fed Policy cluster at 14%, opportunity requires 3%, limit 15%)"
- Daily summary includes filtered opportunity count and reasons, alerts operator if >20% of opportunities filtered (indicates risk limits may be too conservative)

### Error Code Catalog

Centralized error taxonomy covering all system failure modes with standardized codes, descriptions, severity, retry strategies, and operator actions.

**Platform API Errors (1000-1999):**

| Code | Description | Severity | Retry Strategy | Operator Action |
|------|-------------|----------|----------------|-----------------|
| 1001 | 401 Unauthorized - API key invalid/expired | Critical | No retry | Verify API key, rotate if needed, check platform status |
| 1002 | 403 Forbidden - Trading restricted | Critical | No retry | Contact platform support, review ToS compliance, check for account flags |
| 1003 | 429 Rate Limit Exceeded | Warning | Exponential backoff (2s, 4s, 8s) | Review rate limit utilization, reduce polling frequency if sustained |
| 1004 | 503 Service Unavailable | Warning | Exponential backoff (1s, 2s, 4s), max 3 retries | Monitor platform status, activate degradation protocol if >3 failures |
| 1005 | Timeout (>10s) | Warning | Retry once immediately | Check network latency, platform status |
| 1006 | WebSocket Disconnect | Warning | Auto-reconnect with backoff | Monitor connection stability, switch to polling if frequent disconnects |
| 1007 | Unexpected API Response Schema | Critical | No retry, halt trading | Log full response, notify operator, wait for investigation |

**Execution Failures (2000-2999):**

| Code | Description | Severity | Retry Strategy | Operator Action |
|------|-------------|----------|----------------|-----------------|
| 2001 | Insufficient Liquidity - Order size > available depth | Info | No retry | Log opportunity as missed, adjust min liquidity threshold if frequent |
| 2002 | Price Moved - Expected price no longer available | Info | No retry | Log slippage, review edge threshold if frequent |
| 2003 | Order Rejected - Platform declined order | Warning | Retry once with fresh price | Investigate rejection reason, check platform status |
| 2004 | Second Leg Failed After First Filled | Critical | Execute single-leg protocol | Alert operator immediately with P&L scenarios, await decision |
| 2005 | Gas Estimation Failed (Polymarket) | Warning | Retry with +50% buffer | Monitor gas prices, adjust buffer if sustained failures |
| 2006 | Transaction Reverted (Polymarket on-chain) | Warning | Retry once, check chain status | Review transaction details, check for contract issues |

**Risk Limit Breaches (3000-3999):**

| Code | Description | Severity | Retry Strategy | Operator Action |
|------|-------------|----------|----------------|-----------------|
| 3001 | Daily Loss Limit Exceeded | Critical | Halt all trading | Review daily performance, investigate if loss due to errors vs. normal variance |
| 3002 | Correlation Cluster Limit Breach | Warning | Skip opportunity, continue monitoring | Review correlation exposure, consider closing positions in cluster |
| 3003 | Position Count Limit Reached | Info | Skip opportunity | Normal - wait for positions to exit |
| 3004 | Position Size Exceeds Maximum | Warning | Reduce size, retry | Investigate if error in size calculation |
| 3005 | Max Drawdown Approaching Threshold | Critical | Reduce position sizes by 50% | Immediate review of portfolio risk, consider halting trading |

**System Health Issues (4000-4999):**

| Code | Description | Severity | Retry Strategy | Operator Action |
|------|-------------|----------|----------------|-----------------|
| 4001 | State File Corruption Detected | Critical | Halt, attempt rollback | Restore from backup, investigate corruption cause |
| 4002 | Data Staleness - No updates >60s | Critical | Activate degradation protocol | Check platform APIs, network connectivity |
| 4003 | Memory Usage >90% | Warning | Continue, log alert | Investigate memory leak, restart if sustained |
| 4004 | Disk Space <10% Free | Warning | Continue, cleanup old logs | Archive old logs to external storage |
| 4005 | Startup Reconciliation Discrepancy | Critical | Halt, flag positions | Operator must manually verify positions before resuming |

### Alerting Channels & Fallback

**Primary Alerting (MVP): Telegram**
- **Coverage:** All alerts (info, warning, critical)
- **Delivery SLA:** <2 seconds for critical alerts
- **Format:** Rich text with action buttons for operator decisions (retry, close, acknowledge)
- **Failure detection:** If Telegram API returns error 3 consecutive times, escalate to secondary channel

**Secondary Alerting (Phase 1): Email**
- **Coverage:** High-severity and critical alerts only (platform degradation, risk limit breach, system crash, single-leg exposure)
- **Delivery SLA:** <30 seconds
- **Format:** Plain text with full context (timestamps, affected contracts, P&L impact, recommended actions)
- **Activation:** Automatic if Telegram fails OR for alerts requiring audit trail (compliance, regulatory)

**Tertiary Alerting (Phase 1): SMS**
- **Coverage:** Critical alerts only (daily loss limit exceeded, system crash, catastrophic failure)
- **Delivery SLA:** <60 seconds
- **Format:** Plain text, max 160 characters with alert code and critical summary
- **Activation:** Automatic if both Telegram and Email fail OR for maximum-severity events

**Alerting Health Monitoring:**
- System sends test alert daily at configurable time (default: 8am local)
- Test alert sent to all channels, operator confirms receipt
- If test fails for any channel: Alert via remaining functional channels, log failure for investigation
- If all channels fail: System logs locally and continues operation (cannot halt trading due to alerting failure)

### Time Synchronization Requirements

**Requirement Rationale:**
Cross-platform arbitrage depends on accurate timestamp correlation for:
- Audit trails proving near-simultaneous execution (regulatory compliance)
- Opportunity detection timing (did price dislocation exist when detected?)
- Performance analytics (actual execution latency vs. target)
- Startup reconciliation (query platform APIs for fills in specific time window)

**Implementation:**

**NTP Synchronization:**
- System must sync with NTP pool servers (pool.ntp.org or equivalent) at startup and every 6 hours
- Acceptable clock drift: <100ms from NTP reference
- Alert threshold: Clock drift >100ms detected during sync check

**Clock Drift Monitoring:**
- Every 30 minutes, compare system clock to NTP reference
- If drift >100ms: Log warning alert to operator
- If drift >500ms: Critical alert, recommend investigation (system clock hardware issue, NTP server unreachable)
- If drift >1000ms: Halt trading until clock drift resolved (timestamps unreliable for audit compliance)

**Timestamp Precision:**
- Audit trail timestamps: Millisecond precision (sufficient for demonstrating near-simultaneous execution)
- Performance metrics: Millisecond precision (order book latency, execution speed)
- Not required: Microsecond or nanosecond precision (overkill for this strategy, adds complexity)

**Platform API Timestamp Handling:**
- Platform-provided timestamps (order fill times) used as authoritative source for that platform
- System timestamps used for internal event correlation (opportunity detected, order submitted)
- Timestamp reconciliation: If platform fill timestamp differs from system submission timestamp by >10 seconds, flag for investigation (network latency issue, clock drift, or platform delay)

## Risk Mitigation Strategy

### Technical Risks & Mitigations

**Contract Matching Failures**
- **Risk:** Trading opposite sides of contracts that aren't actually the same event, creating directional exposure instead of arbitrage
- **Likelihood:** Low (with proper validation), **Impact:** Catastrophic (position loss on both legs)
- **Mitigation:**
  - MVP: Manual curation of 20-30 verified contract pairs (zero automation = zero matching errors)
  - Phase 1: NLP-based matching with confidence scoring, human-in-the-loop for <85% confidence matches
  - Accumulated knowledge base of resolved matches to improve accuracy over time
  - **Hard constraint:** Zero tolerance policy - any matching error triggers system halt and audit
- **Detection:** Post-resolution verification of contract outcomes; any divergence triggers immediate review
- **Success Metric:** Zero catastrophic matching failures across all phases

**Single-Leg Exposure Events**
- **Risk:** One leg fills, other doesn't, creating unwanted directional position
- **Likelihood:** Medium (platform latency, volatility), **Impact:** Medium (1-2% position loss typically)
- **Mitigation:**
  - Automated detection within seconds (not minutes)
  - Immediate alert to operator with full context (what filled, current prices, P&L scenarios)
  - Decision framework: retry second leg at worse price, or close first leg within loss parameters
  - **Target:** <5 events per month, all managed within acceptable loss parameters
- **Detection:** Real-time monitoring of execution state, alert on incomplete arbitrage pairs
- **Success Metric:** <1 event per week, average loss <1% of position size

**Platform API Outages & Degradation**
- **Risk:** Loss of real-time data, inability to execute or monitor positions
- **Likelihood:** Medium (platform infrastructure issues), **Impact:** High (trading halt, position risk)
- **Mitigation:**
  - Graceful degradation protocol: cancel pending orders, halt new trades, maintain monitoring via polling
  - Automatic recovery when platform APIs restore
  - Connection resilience (WebSocket with reconnection, fallback to polling)
  - Multiple platform support (if one fails, others continue)
- **Detection:** WebSocket timeout (81 seconds), unexpected API errors, response latency spikes
- **Success Metric:** 99%+ uptime during active market hours, graceful handling of platform outages

**Slippage Exceeding Modeled Assumptions**
- **Risk:** Actual execution costs exceed backtested projections, eroding edge
- **Likelihood:** Medium (market microstructure changes), **Impact:** Medium (edge compression)
- **Mitigation:**
  - Continuous tracking of realized slippage vs. modeled (target: within 25%)
  - Automatic widening of minimum edge threshold if slippage drifts >25%
  - Order book depth verification before execution (don't trade if insufficient liquidity)
- **Detection:** Rolling 10-day slippage comparison, alert on 25% excess
- **Success Metric:** Average realized slippage within 25% of modeled

**API Version Compatibility Issues**
- **Risk:** Platform API changes break integration, causing failed executions or data loss
- **Likelihood:** Low-Medium (platforms evolve), **Impact:** High (trading halt until fixed)
- **Mitigation:**
  - Monitor API response schemas for unexpected changes
  - Graceful degradation: continue monitoring existing positions, halt new trades until operator reviews
  - Alert operator immediately on unrecognized API behavior
- **Detection:** Schema validation on API responses, unexpected field presence/absence
- **Success Metric:** No data loss or incorrect trades due to API version changes

### Market & Edge Degradation Risks

**Edge Compressing Faster Than Expected**
- **Risk:** Prediction market fragmentation resolves faster than 5-10 year thesis, institutional competition enters
- **Likelihood:** Medium (market maturation), **Impact:** High (strategy becomes unprofitable)
- **Mitigation:**
  - Leading indicator hierarchy: Opportunity frequency (earliest) → Time-to-convergence → Order book depth → Execution quality ratio
  - Automated monitoring with alert thresholds:
    - Opportunity frequency: 30%+ decline over 3 weeks
    - Time-to-convergence: 40%+ compression in 14-day median
    - Order book depth: Sustained decline in average execution depth
  - Clear decision gates at 3/6/12-month checkpoints with proceed/adapt/wind-down outcomes
- **Detection:** Weekly tracking of leading indicators, monthly deep dive analysis
- **Success Metric:** Edge remains durable 12+ months post-deployment per success criteria
- **Contingency:** Timing thesis is explicitly being validated; if edge compresses in 2-3 years instead of 5-10, this is a successful learning outcome (system was profitable while it lasted)

**Opportunity Frequency Declining**
- **Risk:** Fewer actionable arbitrage opportunities, reducing revenue potential
- **Likelihood:** Medium (competition, market efficiency), **Impact:** High (below minimum viable returns)
- **Mitigation:**
  - Baseline: 8-12 opportunities per week (Month 1)
  - Alert threshold: Sustained 30%+ decline over 3-week window
  - Contingency: Add third platform to expand opportunity set, or layer Phase 2 alpha (news-velocity)
- **Detection:** Automated weekly opportunity counting and trend analysis
- **Success Metric:** Opportunity frequency remains above minimum threshold for target returns

**Liquidity Deterioration**
- **Risk:** Order book depth declines, reducing extractable edge per trade
- **Likelihood:** Low-Medium (market evolution), **Impact:** Medium (smaller position sizes, lower returns)
- **Mitigation:**
  - Monitor liquidity at execution points (best price depth, 1% depth)
  - Order book depth verification before execution (don't trade if insufficient liquidity)
  - Position sizing adjusted by available liquidity
- **Detection:** Sustained decline in average liquidity depth over 30 days
- **Success Metric:** Sufficient liquidity to support target capital deployment ($100K-$250K)

### Regulatory & Compliance Risks

**CFTC Regulatory Action**
- **Risk:** Regulatory ruling restricts prediction market trading or creates compliance burden
- **Likelihood:** Low-Medium (regulatory uncertainty), **Impact:** Potentially Catastrophic (strategy shutdown)
- **Mitigation:**
  - Automated regulatory horizon scanning (CFTC filings, congressional hearings, platform status)
  - Risk severity categorization (Low/Medium/High) with response playbooks
  - Major adverse ruling → 50% exposure reduction within 24 hours, full exit within 1 week if ruling stands
  - Legal counsel quarterly review (compliance reports, audit trails)
  - Entity structure designed for regulatory compliance (U.S. entity for Kalshi, separate entity for Polymarket)
- **Detection:** Automated monitoring of regulatory sources, manual legal counsel review quarterly
- **Success Metric:** No trading activity challenged by regulators; proactive compliance positioning

**Platform Adverse Actions**
- **Risk:** Platform flags trading activity, restricts API access, changes terms unfavorably
- **Likelihood:** Low (well-behaved trading), **Impact:** High (loss of platform access)
- **Mitigation:**
  - Platform relationship health metrics (API rate limit <70%, zero adverse actions)
  - Indirect signal monitoring (403 errors, rate limit reductions, delayed fills, restriction emails)
  - Anomalous pattern detection (error rate >5%, new error types)
  - Compliance automation (wash trading documentation, anti-spoofing compliance, audit trails)
  - Platform diversification (40% single-platform capital cap) reduces impact of losing one platform
- **Detection:** API response code logging, error pattern analysis, manual escalation on anomalies
- **Success Metric:** Zero adverse platform actions, <70% API rate limit utilization

**Cross-Border Compliance Issues**
- **Risk:** Trading contracts restricted by entity domicile or jurisdictional limitations
- **Likelihood:** Low (with proper configuration), **Impact:** Medium (contract category restrictions)
- **Mitigation:**
  - Per-platform compliance configuration specifying tradeable contract types by entity
  - Validation before execution (hard block on non-compliant trades)
  - Kalshi: U.S.-only, requires U.S. entity compliance
  - Polymarket: Global access with platform-specific geo-restrictions
- **Detection:** Pre-execution validation against compliance matrix
- **Success Metric:** Zero trades executed in violation of jurisdictional restrictions

**Data Retention Compliance Failures**
- **Risk:** Failure to maintain 7-year trade logs, creating audit liability
- **Likelihood:** Very Low (automated enforcement), **Impact:** High (IRS/regulatory penalties)
- **Mitigation:**
  - Automated retention policy prevents deletion of required records
  - Structured JSON + CSV export capability
  - Tamper-evident logging (cryptographic signing or append-only storage)
  - Export on demand for audit trail generation
- **Detection:** Automated retention monitoring, quarterly legal review
- **Success Metric:** 100% retention compliance for 7-year window

### Operational & Platform Risks

**Platform Counterparty Risk**
- **Risk:** Platform experiences smart contract exploit, regulatory shutdown, or insolvency
- **Likelihood:** Low (established platforms), **Impact:** High (capital loss on that platform)
- **Mitigation:**
  - Hard limit: Maximum 40% of capital on any single platform
  - Sweep excess capital to central treasury between trades (minimize idle capital on platforms)
  - Diversification across platforms with different risk profiles (Polymarket on-chain, Kalshi regulated)
  - Platform health monitoring (operational stability, regulatory status)
- **Detection:** Platform status monitoring, regulatory horizon scanning
- **Success Metric:** Maximum capital at risk bounded to 40% if single platform fails

**Wallet Security & Key Management**
- **Risk:** Private key compromise leading to capital loss
- **Likelihood:** Very Low (with proper security), **Impact:** Catastrophic (total capital loss)
- **Mitigation:**
  - MVP: Private keys in environment variables, never in code/config
  - Phase 1: External secrets management service with key rotation and audit logging capabilities
  - Quarterly key rotation (operational procedure)
  - Hardware wallet consideration for Phase 1 (security vs. latency trade-off)
- **Detection:** Unauthorized transactions would appear in on-chain monitoring
- **Success Metric:** Zero unauthorized access to private keys or wallet funds

**System Downtime & Operational Reliability**
- **Risk:** System crashes or becomes unavailable, missing opportunities or creating position risk
- **Likelihood:** Low (with proper engineering), **Impact:** Medium (missed opportunities, monitoring gaps)
- **Mitigation:**
  - Target: 99%+ uptime during active market hours
  - Stateful operation with graceful restart (save state, restore positions)
  - Deployment updates without data loss (maintenance window support)
  - Alerting on system health degradation (Telegram + dashboard)
- **Detection:** System health monitoring, automated alerts on process failures
- **Success Metric:** 99%+ uptime sustained, <1 hour downtime per month

**Resource Constraints (Team/Capital)**
- **Risk:** Insufficient resources to complete development or operate at target scale
- **Likelihood:** Low (single-user project, modest capital), **Impact:** Medium (delayed timeline, reduced scope)
- **Mitigation:**
  - MVP validates edge with minimal capital ($10K)
  - Phased capital scaling (10% → 25% → 50% → 100%) based on validation
  - Single-operator design (no team dependency)
  - Clearly defined success gates prevent throwing good money after bad
- **Detection:** 3-month checkpoint explicitly evaluates whether to proceed, extend, or shut down
- **Success Metric:** Capital scaled only after validation at each increment
- **Contingency:** If MVP fails validation (profit factor <1.0), wind down with minimal capital loss

## Non-Functional Requirements

### Performance

**NFR-P1: Order Book Update Latency**
- Order book data from all platforms processed and normalized within 500ms of platform event
- Rationale: Arbitrage opportunities can disappear in seconds. Stale data leads to failed executions and single-leg exposure.
- Measurement: 95th percentile latency from platform websocket event to internal normalized representation

**NFR-P2: Arbitrage Detection Cycle Time**
- Complete arbitrage detection cycle (all matched contract pairs evaluated) completes within 1 second
- Rationale: Detection delays reduce available execution time, increasing leg risk
- Measurement: Time from order book update to opportunity flag in logs

**NFR-P3: Execution Submission Speed**
- Both legs of arbitrage submitted to platforms within same event loop cycle (target: <100ms between submissions)
- Rationale: Leg risk increases with time delta between order submissions. Core execution assumption.
- Measurement: Timestamp delta between first and second order submission in execution logs

**NFR-P4: Dashboard Responsiveness**
- Dashboard UI updates within 2 seconds of data change for all monitoring views
- Rationale: Operator needs real-time visibility during manual interventions
- Measurement: Time from backend state change to frontend render

### Security

**NFR-S1: Credential Storage**
- **MVP**: Platform API keys and wallet private keys stored in environment variables, never in code or version control
- **Phase 1**: Migration to secrets management service supporting API-based credential retrieval, automatic key rotation, and encrypted storage
- Rationale: Compromise of credentials = loss of all deployed capital. Secrets manager provides rotation, audit trails, and access control.
- Measurement: Zero credential exposure events (credentials found in logs, repos, or unencrypted storage)

**NFR-S2: API Key Rotation Support**
- System supports zero-downtime API key rotation for all platforms
- Rationale: Regulatory or security incident may require immediate key rotation. System must continue operating.
- Measurement: Successful rotation with <5 seconds of degraded operation during switchover

**NFR-S3: Transaction Logging**
- All trade executions, order submissions, and wallet transactions logged with complete audit trail
- Logs include: timestamp, arbitrage opportunity rationale, execution prices, order IDs, transaction hashes
- Retention: 7 years (IRS compliance requirement)
- Rationale: Regulatory compliance, debugging, performance analysis, dispute resolution
- Measurement: 100% of trades have complete audit records

**NFR-S4: Access Control**
- Dashboard and API endpoints require authentication (MVP: basic auth or API token; Phase 1: proper session management)
- No unauthenticated access to system state, logs, or controls
- Rationale: Prevent unauthorized trading operations or exposure of strategy details
- Measurement: Zero successful unauthorized access attempts in penetration testing

### Reliability

**NFR-R1: System Uptime**
- 99% uptime during active market hours (Mon-Fri 9am-5pm ET), 95% overall including planned maintenance windows
- Planned maintenance windows announced 24 hours in advance, scheduled outside active market hours
- Rationale: Downtime during active hours = missed opportunities and inability to manage open positions; maintenance windows acceptable during low-activity periods
- Measurement: Uptime percentage calculated from system health check logs, tracked separately for active hours and overall

**NFR-R2: Graceful Degradation**
- When data feed from one platform fails:
  - Cancel all pending orders on that platform within 10 seconds
  - Continue operating on remaining healthy platforms
  - Widen opportunity thresholds by 1.5x (configurable) on remaining platforms
  - Alert operator via Telegram and dashboard
- System never trades "blind" (without current order book data)
- Rationale: Single platform failure should not cause total system failure or create dangerous exposure
- Measurement: Zero instances of trading without current data, 100% of degradation events properly logged and alerted

**NFR-R3: Single-Leg Exposure Handling**
- Execution timeout: 5 seconds (configurable) from first leg submission to second leg confirmation
- If timeout exceeded: Immediate attempt to unwind filled leg OR hedge exposure using model-driven exit framework
- Target: <5 events per month (success threshold), <2 events per month (compliance measurement standard)
- Alert: >1 per week sustained for 3+ consecutive weeks triggers systematic investigation
- Rationale: Single-leg exposure converts arbitrage into directional bet, violating core strategy
- Measurement: Count and severity of single-leg events in monthly performance reports, tracked weekly for alert threshold

**NFR-R4: Platform Health Detection**
- Platform health status (healthy/degraded/offline) updated every 30 seconds
- Health determined by: API response time, order book update frequency, execution success rate
- Degradation detection triggers alert within 60 seconds
- Rationale: Early detection prevents execution failures and capital lock-up
- Measurement: Zero undetected API degradation events >5 minutes

**NFR-R5: Data Persistence**
- All order book snapshots, executions, and model decisions logged with microsecond timestamps
- Storage: Time-series database suitable for historical replay
- Retention: 7 years minimum (regulatory requirement)
- Rationale: Historical data enables backtesting validation, strategy refinement, regulatory compliance
- Measurement: 100% of trading days have complete, replayable data

### Integration

**NFR-I1: Platform API Compatibility**
- Support specific API versions for each platform (version pinned in configuration)
- Defensive parsing: Handle unexpected API responses without crashing
- Version upgrade path: Test against new API versions in isolated environment before production deployment
- Rationale: Platform API changes are outside our control but can break execution
- Measurement: Zero production incidents caused by unexpected API responses

**NFR-I2: Rate Limit Compliance**
- Automatic enforcement of platform-specific rate limits with 20% safety buffer
- Rate limit tracking: Monitor consumption in real-time, alert at 70% utilization
- Graceful handling: Queue requests when approaching limits, never exceed and trigger platform throttling
- Rationale: Rate limit violations can result in API access suspension (platform counterparty risk)
- Measurement: Zero rate limit violations, zero API suspensions due to excessive requests

**NFR-I3: Connection Resilience**
- Websocket connections automatically reconnect with exponential backoff (max 60 seconds between attempts)
- Missed data detection: System recognizes gaps in order book updates and marks platform as degraded
- Connection state clearly indicated in dashboard and logs
- Rationale: Transient network failures should not require manual operator intervention
- Measurement: 95% of connection failures recover automatically within 2 minutes

**NFR-I4: Transaction Confirmation Handling**
- On-chain transactions (Polymarket): Monitor for confirmation with timeout (default 30 seconds)
- Handle chain reorganizations: Detect and respond to transaction reversals
- Gas estimation: Pre-compute with 20% buffer to avoid failed transactions
- Rationale: On-chain execution has unique failure modes (gas estimation, confirmation delays, reorgs)
- Measurement: <5% transaction failure rate, 100% of failures properly detected and handled
