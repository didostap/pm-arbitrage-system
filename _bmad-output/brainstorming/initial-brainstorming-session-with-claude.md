# Prediction Market Cross-Platform Arbitrage System: Project Description

## Overview

This project delivers an automated trading system that exploits price dislocations for identical prediction market contracts across multiple platforms. The core thesis is simple: the same binary event — "Will the Fed cut rates in March?" — frequently trades at materially different prices on Polymarket, Kalshi, and other venues simultaneously. These dislocations exist because prediction markets are fragmented, settlement mechanisms differ, and participant bases don't fully overlap. The system identifies these dislocations in real time, executes simultaneous opposing positions to lock in risk-free or near-risk-free profit, and manages the resulting portfolio through a model-driven framework that replaces naive fixed-threshold exits.

The target is 0.5–2% profit per arbitrage cycle after all transaction costs, with dozens of actionable opportunities per week during high-volume event periods. The system is designed to be the primary income engine of a broader prediction market trading operation, with a later phase layering news-velocity alpha on top.

## System Architecture

### Data Infrastructure

The foundation is a unified order book aggregator that normalizes data from at least three prediction market platforms into a single representation. This involves maintaining persistent websocket connections to Polymarket (via Polygon chain event subscriptions), Kalshi (via their streaming API), and at least one additional venue. Each platform has different data formats, update frequencies, and latency profiles, so the aggregator must handle clock synchronization, deduplication, and schema normalization.

A critical subtask is contract matching — programmatically determining that "Will Biden win the 2028 Democratic nomination?" on Polymarket refers to the same real-world event as a similarly worded contract on Kalshi, despite potentially different resolution criteria, expiry dates, or wording. This requires a combination of NLP-based similarity matching and a manually curated mapping table for high-volume contracts. Incorrect matching is an existential risk — trading opposite sides of two contracts that aren't actually the same event produces directional exposure, not arbitrage.

The system stores all ingested data in a time-series database for both live trading and historical backtesting. Every order book snapshot, trade execution, and model decision is logged with microsecond timestamps.

### Arbitrage Detection Engine

The engine continuously computes the implied cost of a round-trip arbitrage for every matched contract pair. This is not simply comparing mid-prices. The calculation must account for the actual executable price at the desired size on each platform's order book, platform-specific fees (Kalshi's per-contract fee structure versus Polymarket's gas costs and AMM pool fees), settlement timing differences (capital lock-up cost between execution and resolution), and the bid-ask spread on each side.

A valid arbitrage opportunity exists when:

```
price_platform_A (buy) + fees_A + price_platform_B (sell equivalent) + fees_B + slippage_estimate + capital_cost < 1.00
```

The system only flags opportunities where the net expected profit after all costs exceeds a minimum threshold of 0.3% — below this, execution risk and model uncertainty eat the edge. Opportunities above 1.5% net are flagged for additional scrutiny, as they may indicate a contract matching error or a platform-specific issue rather than a genuine arbitrage.

### Execution Layer

Execution must be near-simultaneous across platforms to avoid leg risk — the danger that one side of the arbitrage fills while the other moves away. The system uses a parallel execution architecture that submits orders to both platforms within the same event loop cycle, with pre-signed transactions for on-chain venues to minimize confirmation latency.

For each execution, the system follows this sequence: verify opportunity still exists at executable prices, pre-compute exact order sizes accounting for minimum tick sizes and lot constraints on each platform, submit both legs simultaneously, monitor for fills with a configurable timeout (default 5 seconds), and if only one leg fills, immediately attempt to unwind the filled leg or hedge the resulting directional exposure.

Partial fills are handled by a residual position manager that either completes the arbitrage at a slightly worse price or exits the single-leg position using the model-driven exit framework described below.

## Model-Driven Exit Framework

Even in an arbitrage-focused strategy, positions sometimes become directional — due to partial fills, failed second legs, platform outages, or resolution timing mismatches. The system cannot rely on fixed take-profit or stop-loss thresholds. Instead, it evaluates open positions continuously against five exit criteria.

**Edge Evaporation Exit.** The system continuously recalculates the remaining expected profit on each open position pair. When the spread between platforms narrows to the point where remaining expected profit falls below transaction costs to close, the system exits. This prevents holding positions where the arbitrage has been closed by other market participants but the bot hasn't yet realized its gain.

**Model Update Exit.** If new information arrives that changes the fundamental probability of the underlying event, and both platform prices converge toward the updated probability, the original arbitrage thesis is no longer relevant. The system monitors for price convergence as a proxy and exits when both legs move in the same direction by more than a calibrated threshold.

**Time Decay Exit.** As contracts approach resolution, liquidity typically deteriorates and the cost of maintaining positions increases (wider spreads, higher slippage). The system enforces progressively tighter exit thresholds as time-to-resolution decreases. Within the final 24 hours before resolution, any position with less than 1% expected remaining edge is closed.

**Risk Budget Exit.** If a single position or correlated group of positions exceeds its allocated share of portfolio variance, the system reduces exposure regardless of remaining edge. This is the portfolio-level override that prevents concentration, detailed further in the risk architecture section.

**Liquidity Exit.** The system estimates real-time exit slippage based on current order book depth. When estimated slippage to close a position exceeds the remaining expected profit, the system exits immediately at the best available price rather than waiting for conditions that may never improve.

## Risk Architecture

### Position-Level Controls

No single arbitrage pair can exceed 5% of total deployed capital. This limit accounts for the worst case: one platform's contract resolves at 0 while the other resolves at 1 due to differing resolution criteria (a contract matching failure). Even in this catastrophic scenario, the portfolio survives.

Minimum net edge to initiate any trade is 0.3% after all fees. This prevents overtrading on marginal opportunities that look profitable in theory but are fee-negative in practice.

### Portfolio-Level Controls

Maximum correlated exposure is capped at 15% of bankroll. Correlation here means positions whose outcomes are driven by the same underlying event or closely linked events. Fifteen contracts on different aspects of the same election are one correlated cluster, not fifteen independent bets.

Daily loss limit is 8% of current portfolio value. If breached, all trading halts automatically and no new positions are initiated until the next trading day. Weekly loss limit is 12%, triggering a mandatory 48-hour review period with manual override required to resume.

Maximum simultaneous open position pairs is 30. This ensures sufficient diversification while keeping monitoring manageable.

### Dynamic Position Sizing

Position size for each arbitrage pair is calculated as:

```
size = (net_edge / max_loss_scenario) × bankroll × confidence_scalar / correlation_penalty
```

Where net_edge is the expected profit after all costs, max_loss_scenario is the worst-case loss if the arbitrage breaks (typically the full notional of one leg), confidence_scalar ranges from 0.25 to 0.50 (never higher — this is the fractional Kelly dampener), and correlation_penalty increases with the number and strength of correlations to existing positions.

### Platform Counterparty Risk

No more than 40% of total capital is deployed on any single platform at any time. This is a hard limit enforced at the portfolio level. If Polymarket experiences a smart contract exploit or Kalshi faces a regulatory shutdown, the maximum loss is bounded. Idle capital on each platform is minimized by sweeping excess to a central treasury position between trades.

## Backtesting & Validation Pipeline

### Historical Data Collection

Polymarket's on-chain transaction history is public and permanent on Polygon. The system includes a historical data scraper that reconstructs order book states and trade histories for all resolved contracts dating back to 2021. For Kalshi, historical data is obtained through their API's historical endpoints where available, supplemented by the system's own data collection going forward.

All historical data is stored in a standardized schema that allows the backtesting engine to replay market conditions as they occurred.

### Simulation Engine

The backtesting engine replays historical cross-platform price data and simulates the arbitrage detection and execution pipeline against it. Critically, this does not assume mid-price fills. The simulator models execution against the reconstructed order book with realistic fill assumptions: partial fills, queue position estimation, and latency-adjusted prices. Gas costs are modeled using historical Polygon gas price data, and Kalshi fees use their published schedule.

The simulator also models failed second legs, platform downtime periods (injected from historical outage logs), and settlement timing mismatches.

### Validation Protocol

The strategy is trained and tuned on 2021–2023 data. It is then validated on 2024 data with no parameter changes. If the strategy does not show positive expected value on the out-of-sample period with realistic transaction costs, it does not deploy. There is no exception to this rule.

Additionally, Monte Carlo stress testing generates 10,000 simulated portfolio paths using randomized event outcomes, varying liquidity conditions, and injected stress scenarios (simultaneous platform outages, sudden fee changes, contract matching errors). The system must demonstrate a maximum drawdown below 25% and a positive expected return at the 10th percentile of simulated outcomes.

### Ongoing Performance Monitoring

Post-deployment, the system tracks hit rate, net edge per dollar deployed, maximum drawdown, Sharpe ratio (annualized target above 2.0), profit factor (gross wins divided by gross losses, target above 1.5), and the frequency and severity of single-leg exposure events. Any metric falling below threshold for two consecutive weeks triggers an automated reduction in position sizes and a manual strategy review.

## Regulatory Risk Management

### Entity Structure

Trading operations are conducted through a legal entity structured to comply with the regulatory requirements of each platform. For Kalshi, this means operating through a U.S.-compliant entity in accordance with CFTC regulations governing designated contract markets. For Polymarket and other offshore or decentralized venues, a separate entity domiciled in a jurisdiction with clear legal frameworks for prediction market participation is used.

Legal counsel with specific prediction market regulatory expertise is engaged before deployment, not after.

### Compliance Automation

The system includes automated compliance monitoring that flags potential wash trading patterns (the arbitrage strategy naturally creates opposite positions on different platforms, which must be clearly documented as cross-platform arbitrage, not manipulation), any behavior that could be construed as spoofing (rapidly placing and canceling orders), and concentration levels that might trigger reporting requirements on regulated platforms.

All trading activity is logged with complete audit trails, including the arbitrage rationale for each trade pair, timestamps, execution prices, and the state of the opportunity at the time of execution.

### Regulatory Horizon Scanning

An automated monitoring pipeline tracks CFTC filings, federal court dockets related to prediction market cases, congressional hearing schedules mentioning prediction markets or event contracts, and platform-specific announcements about regulatory status changes. Each alert is categorized by severity, and pre-defined response playbooks specify portfolio adjustments: a major adverse ruling triggers an immediate 50% exposure reduction across affected platforms within 24 hours, with full exit within one week if the ruling stands.

### Platform Diversification as Regulatory Hedge

The 40% single-platform capital cap described in the risk architecture serves double duty as a regulatory hedge. If any single platform is forced to cease operations, the maximum capital at risk is bounded and the system continues operating on remaining venues.

## Operational Edge Layer

### Capital Efficiency

Capital not actively deployed in open positions does not sit idle. On-platform balances are minimized to the amount needed for near-term execution. Excess capital is held in short-duration, highly liquid instruments — stablecoin lending protocols with proven security track records or tokenized T-bill products yielding 4–5% annualized. This yield on idle capital meaningfully improves total portfolio returns given that the average capital utilization of an arbitrage strategy is typically 30–60%.

### Transaction Cost Optimization

On Polymarket, gas costs are minimized by batching transactions where possible, timing executions to low-gas periods when opportunities are not time-critical, and using limit orders instead of market orders to avoid taker fees on AMM pools. On Kalshi, the system optimizes order types and sizes to minimize per-contract fee impact. A running cost tracker attributes realized transaction costs to each trade and alerts if average costs drift above modeled assumptions.

### Monitoring and Alerting

A real-time operational dashboard displays current P&L (daily, weekly, all-time), all open positions with current mark-to-market and estimated exit cost, platform API health and latency metrics, arbitrage opportunity pipeline (identified, executing, completed), risk limit utilization across all dimensions, and anomaly detection alerts for unusual patterns in execution quality, fill rates, or market behavior.

Alerts are configured for platform API degradation or disconnection, execution failures or abnormal slippage, risk limit breaches at any level, and single-leg exposure events exceeding 60 seconds.

### Graceful Degradation

If a data feed from one platform fails, the system immediately cancels all pending orders on that platform, prevents new arbitrage pairs involving that platform, maintains existing positions on other platforms under the model-driven exit framework, and widens all thresholds on remaining platforms by a configurable factor (default 1.5x) to account for reduced visibility. The system does not continue trading blind. Degraded operation is logged and an alert is sent for manual review.

## Development Phases

**Phase 1 (Weeks 1–6): Data infrastructure and contract matching.** Build the unified aggregator, establish connections to Polymarket and Kalshi, develop the contract matching system, and begin accumulating historical data. Deliverable: live cross-platform price feed with matched contracts.

**Phase 2 (Weeks 7–12): Backtesting pipeline and strategy validation.** Build the simulation engine, replay historical data, validate the arbitrage detection logic, and tune parameters on in-sample data. Validate on out-of-sample data. Deliverable: backtested strategy with documented performance metrics meeting minimum thresholds.

**Phase 3 (Weeks 13–16): Execution layer and risk framework.** Build the parallel execution system, implement all risk controls and position sizing logic, and develop the model-driven exit framework. Deliverable: paper trading system executing simulated arbitrage on live data.

**Phase 4 (Weeks 17–20): Paper trading and operational hardening.** Run the full system in paper trading mode for a minimum of four weeks. Identify and fix execution issues, calibrate slippage models against real order book behavior, and build the monitoring dashboard. Deliverable: four weeks of paper trading results demonstrating positive expected value.

**Phase 5 (Weeks 21–24): Live deployment at minimum scale.** Deploy with 10% of target capital. Monitor all metrics against backtested expectations. Scale capital in 25% increments only after each increment demonstrates performance consistent with backtested projections for a minimum of two weeks. Deliverable: live system at full target capital allocation.

## Success Criteria

The system is considered successful if it achieves a net annualized return above 15% after all fees, slippage, and operational costs, maintains a Sharpe ratio above 2.0 over any rolling 6-month period, never breaches the 25% maximum drawdown threshold, operates with fewer than 2 material single-leg exposure events per month, and demonstrates consistent performance between backtested projections and live results (within 30% variance). Failure to meet any of these criteria for two consecutive months triggers a mandatory strategy review and potential suspension of live trading.
