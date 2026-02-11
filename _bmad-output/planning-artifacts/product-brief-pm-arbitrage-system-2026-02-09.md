---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - "_bmad-output/brainstorming/initial-brainstorming-session-with-claude.md"
date: 2026-02-09
author: Arbi
---

# Product Brief: pm-arbitrage-system

## Executive Summary

The Prediction Market Cross-Platform Arbitrage System is an institutional-grade algorithmic trading system designed to systematically harvest persistent price dislocations across fragmented prediction market venues. Unlike traditional financial arbitrage where inefficiencies are competed away in milliseconds by HFT firms, prediction markets exhibit structural fragmentation that creates durable, exploitable opportunities.

The system targets 15%+ annualized returns through automated cross-platform arbitrage between venues with fundamentally different settlement mechanisms (on-chain AMM pools vs. regulated centralized order books), participant bases (crypto-native traders vs. CFTC-regulated retail), and no unified clearing infrastructure. Current opportunity size: 20-30 actively tradeable contract categories across Polymarket, Kalshi, and emerging platforms, with sufficient liquidity to support $100K-$250K deployed capital.

**Strategic Timing:** 2026 represents the optimal entry window. Platform infrastructure has matured, liquidity has reached critical mass following the 2024 election cycle, and regulatory ambiguity keeps institutional capital on the sidelines. The approaching 2026 U.S. midterm cycle provides maximum validation and revenue opportunity. The system is designed for sustainable operation over 5-10+ years as market fragmentation persists structurally rather than resolving quickly through consolidation.

**Success Metrics:** (1) Durability — the system continues to generate edge 12+ months post-deployment as market conditions evolve. (2) Operational reliability — autonomous operation with graceful degradation, minimal single-leg exposure, and <1 hour daily management requirement. (3) Strategic positioning — accumulated data, operational knowledge, and infrastructure enable layering additional alpha sources (news-velocity trading) before market maturation increases competition.

---

## Core Vision

### Problem Statement

Prediction markets are structurally inefficient in ways that persist over timescales measured in hours or days rather than milliseconds. The "same" event — identical resolution criteria and settlement date — routinely trades at materially different prices across platforms due to:

- **Fragmented liquidity** across venues with no consolidated tape or unified clearing
- **Heterogeneous settlement mechanisms** (on-chain smart contracts vs. regulated exchange infrastructure) creating execution asymmetries
- **Divergent participant bases** (DeFi-native users vs. CFTC-regulated retail) with different capital costs, risk tolerances, and information access
- **Absent market-making infrastructure** connecting venues, unlike traditional financial markets where cross-exchange arbitrageurs enforce price convergence

These structural factors create a durable arbitrage opportunity: systematically identifying equivalent contracts across platforms, executing near-simultaneous positions on both sides, and capturing the spread as prices converge — all while managing the execution, matching, and operational risks that make this significantly harder than traditional arbitrage.

### Problem Impact

**For the market:** Persistent price dislocations undermine the core value proposition of prediction markets as accurate probability signals for real-world events. When "Will event X occur?" trades at 60¢ on one platform and 68¢ on another, journalists, researchers, and decision-makers citing "the prediction market" are receiving unreliable information. Arbitrageurs improve market quality by forcing price convergence across fragmented liquidity — this system provides a public good while extracting private value.

**For sophisticated traders:** Current approaches fail in predictable ways. Manual arbitrageurs (spreadsheet comparison across browser tabs) capture occasional wide dislocations on slow-moving markets but miss systematic opportunities and frequently execute fee-negative "arbitrages." Simple bot operators run single-pair, hardcoded-threshold systems that break on contract matching, lack portfolio-level risk management, and fail when platform conditions change. Market makers on individual platforms capture spread but take directional exposure without cross-platform hedges.

**The strategic opportunity:** This is a time-limited window. As prediction markets mature, institutional players will enter, infrastructure will consolidate, and spreads will compress. The opportunity isn't just current revenue — it's establishing infrastructure, accumulating proprietary data, and building operational expertise during the market's "Wild West" phase before competition arrives. Waiting 18 months means competing against better-capitalized players who've already solved the hard problems.

### Why Existing Solutions Fall Short

No commercial cross-platform prediction market arbitrage system exists. Partial solutions fail on critical capabilities:

**Informational aggregators** (Oddschecker-style comparison sites) display prices across platforms but provide no execution capability, fee-adjusted spread calculation, or trading infrastructure. Useful for manual traders; irrelevant for systematic operations.

**Platform-specific APIs and SDKs** enable single-venue trading but provide no unified abstraction layer. Building cross-platform systems requires solving integration from scratch — different authentication, rate limits, order types, and data formats for each venue.

**Simple bot implementations** (the current state-of-the-art among technically capable traders) fail in a predictable sequence:
1. **Contract matching breaks first:** Discovering that "Fed cuts rates at or before March meeting" on Platform A and "Fed Funds rate lower on March 20 than February 28" on Platform B are *almost* the same but have different edge case outcomes. Most operators discover matching failures when contracts resolve differently and "risk-free" trades lose money on both legs.
2. **Execution simultaneity breaks second:** On-chain transaction confirmation times vs. centralized matching engine latency creates leg risk — one side fills, the other moves away, turning "arbitrage" into "unwanted directional position."
3. **Risk management breaks third:** Running 20 open arbitrage pairs with no understanding of correlation, then discovering during a major news event that 15 are effectively bets on the same underlying outcome. A single surprise generates a 20% portfolio drawdown.

**Why the gap persists:** Four reinforcing factors prevent sophisticated solutions from existing:
- **Technical complexity:** Building reliable cross-platform execution (on-chain + regulated exchange), contract matching with NLP, and institutional-grade risk management is a 6-month engineering undertaking — beyond weekend-project scope.
- **Regulatory uncertainty:** The CFTC's evolving stance and legal ambiguity deters institutional capital from deploying compliance resources into a market that might face regulatory action.
- **Market immaturity:** Total prediction market volume is too small to interest large quant funds ($500K-$2M annual returns) but highly attractive to focused small operations. Big players ignore it, small players lack sophistication.
- **Structural fragmentation:** The inefficiency exists *because* of fragmentation, and fragmentation persists because platforms serve different regulatory jurisdictions and user bases. Polymarket cannot become CFTC-regulated without losing its global crypto-native users; Kalshi cannot go on-chain without losing regulatory status. This isn't resolving through consolidation.

### Proposed Solution

An institutional-grade algorithmic trading system with five architectural pillars that address the failure modes of existing approaches:

**1. Unified Cross-Platform Order Book**
- Real-time normalized aggregation of liquidity across Polymarket (on-chain AMM), Kalshi (regulated CLOB), and future venues
- Platform-agnostic abstraction layer: adding new venues is a connector implementation, not a system redesign
- Sub-second refresh rates with graceful degradation protocols for platform outages or API latency spikes

**2. Automated Contract Matching with Confidence Scoring**
- NLP-based semantic matching of contract descriptions, resolution criteria, and settlement dates across platforms
- Confidence scoring (0-100%) based on criteria alignment, with position sizing adjusted by matching confidence
- Human-in-the-loop for edge cases: 95%+ matches auto-approve, <85% matches require manual review
- Accumulated knowledge base of resolved matches to improve matching accuracy over time

**3. Near-Simultaneous Cross-Platform Execution**
- Coordinated order submission across heterogeneous venues (on-chain transactions + exchange API calls)
- Intelligent leg sequencing: execute more liquid/stable leg first, adapt to venue-specific latency profiles
- Graceful leg-risk management: if second leg fails to fill, automatically close or hedge first leg within risk parameters

**4. Model-Driven Exit Framework (vs. Fixed Thresholds)**
- Continuous recalculation of expected edge based on: fee/slippage updates, liquidity depth changes, contract matching confidence evolution, time to resolution
- Five-criteria exit logic: (1) edge evaporation, (2) model update, (3) time decay, (4) risk budget breach, (5) liquidity deterioration
- Captures remaining edge that fixed thresholds leave on the table; avoids forced exits from temporarily adverse but positive-EV positions

**5. Portfolio-Level Risk Management**
- Correlation-aware position sizing: contracts linked to the same underlying event (Fed policy, election outcome, geopolitical risk) sized as a portfolio, not independently
- Dynamic risk budgets: platform counterparty limits, maximum single-leg exposure, daily loss limits with automatic trading halts
- Monte Carlo stress testing against historical and synthetic scenarios (platform outage during high volatility, simultaneous adverse movement of correlated positions)

**Minimum Viable Implementation (v0.1 — 3-4 week build):**
- Polymarket ↔ Kalshi only, U.S. political/economic binaries only
- Manual contract matching (curated table of 20-30 verified pairs)
- Sequential execution (accept some leg risk on slow-moving markets)
- Fixed exit thresholds (80% profit target, 2x loss stop, 48hr time-based)
- Basic risk controls (3% position cap, 10 max pairs, 5% daily loss limit)
- Validates core thesis before building full infrastructure

**Development Timeline:** 6-month phased implementation (Phase 1: Core system, Phase 2: Model-driven exits & correlation-aware sizing, Phase 3: Multi-platform expansion + news-velocity alpha).

### Key Differentiators

**Institutional-grade systems against Wild West markets:** The core asymmetry is applying quantitative finance rigor (portfolio construction, Kelly criterion, correlation modeling, out-of-sample backtesting) to a market where most participants trade on intuition and most bots use hardcoded thresholds. This isn't a marginal edge — it's a structural advantage.

**Model-driven exits:** The five-criteria continuous recalculation framework captures materially more edge than fixed thresholds by staying in positions with remaining positive EV and exiting when edge actually evaporates rather than when price hits an arbitrary level.

**Correlation-aware portfolio construction:** Treating the arbitrage book as a portfolio rather than independent pairs enables running more positions with less risk. Standard in institutional quant finance; essentially absent in prediction market trading.

**Contract matching confidence scoring:** Position sizing adjusted by matching confidence (99% match → full size; 85% match with resolution criteria differences → reduced size, tighter stops) captures edge from imperfect matches that conservative systems would skip entirely.

**Unfair advantage — the rare intersection:** Quantitative finance expertise + blockchain/DeFi technical fluency + willingness to operate in regulatory ambiguity. Institutional players have the first but wait for regulatory clarity. Crypto builders have the second but lack portfolio management sophistication. The combination, applied now, is the edge.

**Defensibility through accumulated data:** After 6-12 months of live operation, the system possesses proprietary data on actual execution latencies, slippage profiles, platform fill rates, and calibrated contract matching heuristics refined by real resolutions. This operational knowledge cannot be acquired — it must be earned through live trading. Competitors starting from scratch face the same learning curve while market conditions evolve.

**Non-consensus belief:** Prediction market fragmentation is structural and will persist 5-10+ years, not 2-3 years as consensus assumes. Polymarket and Kalshi serve fundamentally different user bases with mutually exclusive regulatory statuses — neither can become the other. New entrants add fragmentation rather than resolving it. This means the edge is durable enough to justify building sophisticated infrastructure rather than quick scripts, and the window isn't closing as fast as most people think.

**Why 2026 is the optimal entry point:**
- Liquidity has reached critical mass (post-2024 election cycle volume growth)
- Platform infrastructure has matured (stable APIs, reliable on-chain infrastructure)
- Regulatory clarity has increased but not resolved (sweet spot: operational confidence without institutional competition)
- 2026 U.S. midterm cycle approaching (system operational and validated before highest-volume period)

In 2024, it was too early — infrastructure wasn't ready. In 2028, it will likely be too late — institutional competition will have arrived. 2026 is the window.

---

## Target Users

### Primary User: The Quantitative Independent Trader

**Persona: "Arbi"**

**Background & Context:**
- Software engineer by training (4+ years building backend systems at fintech company)
- Transitioned to independent crypto trading 2020-2021: systematic DeFi yield farming and DEX arbitrage
- Self-taught quantitative portfolio management through canonical texts (Taleb, Thorpe, Kelly, Lopez de Prado) and expensive real-world lessons
- Formative experience: 2022 crypto drawdown — had a working strategy but no risk framework, gave back significant gains due to correlated exposure and absent drawdown controls
- Discovery path: Manual Polymarket trading during 2024 primaries → noticed cross-platform dislocations with Kalshi → 6 months manual arbitrage and spreadsheet tracking → recognized opportunity requires purpose-built infrastructure

**Technical Profile:**
- Comfortable with command-line interfaces, config files, Python/TypeScript, blockchain infrastructure
- Builds his own tools — wants well-structured, extensible codebases, not polished GUIs
- Thinks in systems, not trades — cares about portfolio statistical properties over 100 trades, not individual trade outcomes
- Values operational reliability over feature richness: 5 features that work flawlessly > 20 features at 90% reliability

**Problem Experience:**
"I can see the cross-platform dislocations happening in real-time, but I don't have the infrastructure to capture them systematically. Manual trading is too slow and leaves edge on the table. The crude bots I could build quickly would break in predictable ways — contract matching failures, execution leg risk, no portfolio-level correlation management. I need institutional-grade infrastructure without institutional bureaucracy."

**Risk Philosophy:**
Risk controls are non-negotiable. Will never override risk limits "just this once" because he's learned what happens when you negotiate with risk management. The 2022 drawdown created permanent scar tissue — this system's risk architecture reflects that experience.

**Success Vision:**

*Daily Life (Steady State):* Spends 30-45 minutes reviewing system performance over coffee, approves edge-case contract matches requiring human judgment, monitors for anomalies. The rest of the day is free for strategic work (Phase 2 alpha development) or unrelated activities. The daily check-in is by choice, not necessity — the system can run 48+ hours without human interaction.

*Operational Confidence:* "I trust this system. It handles normal operations autonomously, degrades gracefully under stress, and escalates intelligently when human judgment is genuinely needed. I've seen it handle adverse scenarios correctly."

*Strategic Positioning:* "This system generates returns AND accumulates the proprietary data and operational knowledge I'll need for the next layer of edge. It's infrastructure, not just a trading bot."

**Decision-Making Style:**

When the system escalates an edge case (e.g., 78% confidence contract match), decision process takes 60-90 seconds:

*Information Required (single screen):*
- Exact contract titles and descriptions from both platforms, side by side
- Resolution criteria from each platform with differences highlighted
- NLP matcher's reasoning — which terms matched, which diverged, why confidence isn't higher
- Historical precedent — resolution concordance rate for similar contract categories on these platforms
- Current spread and estimated edge — how much money is at stake
- Risk scenario — maximum loss if contracts resolve differently

*Decision Logic:*
1. Read both resolution criteria carefully — do they describe the same observable outcome?
2. Identify the divergence that dropped confidence below auto-approval threshold — semantic (different wording, same meaning) or substantive (genuinely different conditions)?
3. If semantic → approve, possibly add pattern to matching heuristics
4. If substantive → assess probability the difference matters for this specific event
5. If >5% chance of divergent resolution → reject match
6. If <5% → approve with reduced position sizing (manual confidence override)

After reviewing 50+ edge cases, most fall into recognizable categories. The system should learn from approve/reject decisions and present categorized edge cases with historical context.

**Interaction Patterns by Phase:**

*Month 1 (Building Trust):*
- Daily: 2-3 hours — detailed operational review, close monitoring of every execution
- Morning (15-20 min): Review overnight activity, check daily performance summary, approve contract matches, scan regulatory monitoring
- Midday (5 min via phone): Glance at dashboard, verify API health, check for alerts
- Evening (20-30 min): Deep review comparing week's metrics against backtest, analyze slippage tracking, review single-leg exposure events in detail
- Weekly (1-2 hours): Full performance review, statistical comparison against backtest benchmark, identify parameter drift

*Month 3+ (Steady State):*
- Daily: 20-30 minutes — strategic review, not operational monitoring
- Weekly (1 hour): Performance analysis, optimization opportunities, parameter tuning
- Focus shifts from "does it work?" to "how can I improve it?" and "what can I build on top of it?"
- System runs 15-25 open pairs at any given time, executes 5-15 new pairs per week, generates steady returns

**Intervention Thresholds:**

*Let it run:* Normal arbitrage execution, routine exits, standard contract matching above auto-approval threshold, temporary platform latency handled by graceful degradation

*Review but don't override:* Contract matches below auto-approval threshold, positions approaching time-decay exit window, positions where realized P&L diverges significantly from expected

*Active intervention:* Risk limit approaching breach, high-severity regulatory alert, platform announcing significant fee/rule changes, any behavior unexplainable after 5 minutes of investigation

### Secondary User Segments (Future Optionality)

**Ring 2: Other Systematic Traders**
- Profile: Individuals similar to primary user who want to run their own instance
- Timeframe: Not designed for in Phase 1, but architectural decisions preserve optionality
- Product evolution required: Packaging as deployable infrastructure with clean documentation, configurable parameters, pluggable platform connectors
- Influence on Phase 1 design: Justifies modular architecture (unified order book abstraction, platform-agnostic connectors) that might seem over-engineered for single-user deployment but pays off enormously for this segment

**Ring 3: Institutional / Fund Structures**
- Profile: Market-making firms or fund structures managing external capital
- Timeframe: Long-term vision only, explicitly out of scope for Phase 1-2
- Requirements: Multi-user access, investor reporting, institutional compliance frameworks, audit trails for external capital management
- Influence on Phase 1 design: Zero. Including prematurely would delay validation of core edge.

### Supporting Roles

**Legal Counsel**
- Interaction: Periodic (quarterly review or on-demand for regulatory events)
- Needs: Complete audit trails, compliance reports, regulatory scan results, documentation of entity structure and trading rationale
- Interaction mode: Receives exported reports and data, does NOT interact with system directly
- Value received: Can confidently defend trading activity if challenged, provides proactive regulatory guidance based on system-generated intelligence
- Design implication: Audit trail and compliance logging must be clear, complete, exportable, and organized to map to regulatory frameworks legal counsel understands

**Tax/Accounting Advisor**
- Interaction: Annual or quarterly
- Needs: Complete trade log exports in standard formats, P&L summaries by platform and time period, cost basis tracking, categorization of transaction types
- Value received: Clean tax filing without manual reconstruction of trading activity
- Design implication: Cross-platform prediction market trading creates complex tax situations (on-chain transactions vs. regulated exchange fills); system must capture sufficient detail for accurate tax reporting

**Platform Providers (Polymarket, Kalshi, Future Venues)**
- Relationship: Dependency, not user relationship
- Interaction: System interacts with platforms via APIs; platforms may occasionally inquire about trading patterns
- Needs from us: Compliant trading behavior, no API abuse, reasonable request volumes, proper documentation if inquiries arise
- We need from them: Reliable APIs, clear fee schedules, timely settlement, advance notice of platform changes
- Value to platforms: Well-behaved arbitrage systems improve price efficiency and add liquidity — this is a service to prediction market platforms
- Design implication: Compliance monitoring (anti-spoofing checks, wash trading avoidance documentation) partially serves this stakeholder; maintaining good platform relationships is operationally critical

**Technical Infrastructure / DevOps**
- In Phase 1: Also the primary user, but documented as separate role for clarity
- Needs: Deployment documentation, runbooks for common failure scenarios, infrastructure monitoring separate from trading monitoring, clear separation between trading logic and operational infrastructure
- Importance: Clarifies that the system needs operational tooling beyond trading logic; makes eventual handoff easier if infrastructure management is delegated while operator focuses on strategy

### User Journey

**Phase A: Pre-Launch — Backtesting Validation (Weeks 7-12)**

*Objective:* Validate strategy produces positive expected value on out-of-sample historical data with realistic transaction cost modeling

*Success Criteria:*
- Positive expectancy on out-of-sample data
- Profit factor >1.3
- Maximum simulated drawdown <20%
- At least 200 simulated trade pairs for statistical significance
- Distribution analysis: Median trade profitable without fat left tail of large losses
- Edge is systematic, not driven by small number of large wins

*Key Insight:* Not just looking at aggregate returns — examining per-trade outcome distributions to ensure risk framework is sound

**Phase B: Paper Trading (Weeks 17-20)**

*Objective:* Validate backtested assumptions hold against live market data without capital risk

*Duration:* Four weeks minimum of full system running against real-time prices, executing simulated trades

*Validation Focus:*
- Fill rate on both legs — does simulator's partial fill model match reality?
- Actual slippage vs. modeled slippage
- Platform API reliability under real conditions
- Contract matching system performance on live data (checking for false positives)
- System operational stability — can it run 7+ consecutive days without manual intervention for operational issues?

*Success Criteria:*
- Paper trading results within 30% of backtested projections
- Zero contract matching errors (false positives where approved match would have resolved differently)
- Seven consecutive days without requiring manual intervention for operational issues

**Phase C: Minimum Capital Deployment (Weeks 21-24)**

*Objective:* Validate system with real capital at reduced risk; verify operator doesn't intervene emotionally

*Capital:* 10% of target capital — real money, real psychology

*Critical Insight:* "The system monitors me as much as I monitor it during this phase." Need to verify operator doesn't manually override when system operates correctly but position is temporarily adverse.

*Success Criteria:*
- Four weeks of positive returns at minimum capital
- No risk limit breaches
- No single-leg exposure events lasting >5 minutes
- **Most critical:** Operator hasn't manually overridden system's decisions. If overrides occur, either the system is wrong (fix it) or operator doesn't trust it (understand why). Don't scale until resolved.

**Day 1 Live: Real Capital Deployment**

*Psychological Reality:* "First day with real capital, I'm watching constantly. Not because I should be, but because I will be — let's be honest about human psychology."

*Behavior:*
- Dashboard on second monitor all day
- Every execution checked: Did both legs fill? Prices vs. expected? Realized slippage?
- Every alert read immediately
- Personal observation log maintained alongside system logs
- Expect 10+ hour attention day — this is an investment in calibrating trust

*Confidence Builders:*
- System successfully executes first 2-3 arbitrage pairs
- Both legs fill within expected parameters
- P&L tracking matches manual calculation
- Risk controls accurately reflect position sizing and portfolio exposure
- **Key moment:** First time only one leg fills and system must manage single-leg exposure. How system handles this — completing second leg at worse price or exiting single leg within acceptable loss — is the highest-anxiety scenario and biggest trust milestone.

**First Month: Establishing Operational Rhythm**

*Week 2: Daily Pattern Crystallizes*

Morning (15-20 minutes):
- Review overnight activity
- Check daily performance summary (new pairs opened, pairs closed, net P&L, alerts)
- Review contract matching queue for approvals
- Scan regulatory monitoring

Midday (5 minutes, phone):
- Glance at real-time dashboard
- Verify API connections healthy, no open alerts
- Habit check, not operational necessity

Evening (20-30 minutes):
- Compare week's running metrics against backtested expectations
- Analyze slippage tracking — realized costs matching modeled costs?
- Review single-leg exposure events in detail (even if auto-resolved)
- Update personal log with observations and potential improvements

Weekly (1-2 hours, typically Sunday):
- Generate full performance report: returns, Sharpe ratio, hit rate, average edge captured, cost analysis, risk utilization, correlation analysis
- Compare against backtested benchmark for statistical significance
- Identify parameter drift (spreads narrowing, execution quality changing) requiring adjustment

*Intervention Decision Framework:*
- **Let it run:** Normal arbitrage execution, routine exits, standard contract matching above auto-approval threshold, temporary platform latency handled by graceful degradation
- **Review but don't override:** Contract matches below auto-approval threshold, positions approaching time-decay exit, realized P&L diverging significantly from expected
- **Active intervention:** Risk limit approaching breach, high-severity regulatory alert, platform announcing significant changes, any behavior unexplainable after 5 minutes of investigation

**Month 3+: Steady State Operation**

*Relationship Shift:* From monitoring whether system works → managing and optimizing confirmed working system

*Focus Areas:*
- **Optimization:** Parameter tuning based on realized performance — is minimum edge threshold too conservative/aggressive? Should correlation penalty adjust based on observed portfolio behavior?
- **Expansion:** Adding new contract categories, adding third platform if mature enough, expanding capital base if performance justifies
- **Data Analysis:** Mining live trading dataset for Phase 2 insights — which contract categories show most persistent dislocations? Time-of-day patterns? Dislocation correlation with news events?

*Normal Operation:*
- 20-30 minutes daily
- 1 hour weekly review
- Occasional deeper dives when interesting patterns emerge in data
- System runs 15-25 open pairs at any given time
- Executes 5-15 new pairs per week
- Generates steady, undramatic returns
- Excitement shifts from "will it work?" to "what can I build on top of it?"

**Strategic Evolution: Phase 2 Decision**

*Gate Conditions (ALL must be met):*

**Condition 1: Operational Stability**
- Arbitrage system stable for 8+ consecutive weeks
- No major incidents, no parameter changes required, no manual interventions beyond routine contract match approvals
- System in genuine steady state, not fragile equilibrium requiring constant attention

**Condition 2: Data Sufficiency**
- Enough live data (3+ months across multiple event categories) to formulate testable hypotheses about news-driven edge
- Observed pattern example: "When major economic indicator surprises, spread between Platform A and Platform B on related contracts widens by X% for average of Y minutes before arbitrageurs close it"
- Can quantify relationship between news events and cross-platform dislocations

**Condition 3: Freed Cognitive Bandwidth**
- If still spending 2+ hours daily on arbitrage system at month 3, something is wrong — Phase 2 is premature
- Priority is fixing the foundation, not building on shaky ground
- Whole point of robust automation: free up cognitive bandwidth for next strategic layer

*Phase 2 Development Approach:*
- Starts as research project running alongside live arbitrage system
- Add news ingestion pipeline — monitor feeds, social media, economic data releases
- Correlate news events with observed cross-platform price movements
- Pure analysis for first 4-6 weeks, no trading implications
- If analysis reveals actionable patterns, build signal layer that feeds into existing execution framework
- System gains "heads up" that dislocation is likely, enabling pre-positioning or faster reaction
- Arbitrage system doesn't change; it gains an additional input source

---

## Success Metrics

### Philosophy: Process Over Outcomes

Success is measured through a hierarchy of priorities that deliberately separates execution quality from outcome quality, especially during early operation when sample sizes are small:

1. **Operational Confidence** — System does what it's supposed to do with verifiable correct behavior
2. **Time Efficiency** — System frees operator for strategic thinking rather than tactical operations
3. **Returns** — Financial performance, measured with proper risk adjustment and statistical rigor
4. **Strategic Optionality** — Accumulated data and knowledge that enables future evolution

**Core Principle:** "A day with negative P&L but flawless execution is a successful day. A day with positive P&L but a mishandled single-leg event is a concerning day."

### User Success Indicators

**Daily Confidence Signals (Primary Dashboard — 2-minute morning scan):**

- **System Health Status** — Composite green/yellow/red indicator: API connectivity, execution engine operational, data feeds fresh
- **Net P&L (trailing 7 days)** — Immediate performance summary showing weekly trend
- **Execution Quality Ratio (trailing 7 days)** — Realized edge ÷ expected edge at entry. Target: >0.7. Investigation threshold: <0.6 sustained
- **Open position count + aggregate unrealized edge** — Portfolio utilization and forward-looking expected returns
- **Active alerts count** — Unresolved alerts requiring attention. Normal: 0-2. Unusual: 5+

**Behavioral Success Indicators:**

- **Time allocation shift** — Spending more time on Phase 2 research than Phase 1 operations indicates system has become infrastructure rather than project
- **Intervention frequency trending toward zero** — Week 1: 2-3 manual interventions daily. Month 2: 2-3 per week. Month 3+: rare (once weekly for novel decisions, operational interventions only for genuine edge cases)
- **The 48-hour test passed** — Can go away for a weekend with phone alerts only, return to find system operated correctly, without anxiety. Target: pass by end of month 2
- **Language shift** — From "the system did X" (describing individual actions, still evaluating) to "my trading operation generates Y" (describing aggregate outcomes, system is assumed infrastructure)

**Critical Trust Milestone:**

The transition from "experimental" to "reliable" occurs at a specific, observable moment: **The first time the system handles an adverse scenario correctly without operator intervention, discovered only during routine review the next day.**

Examples: Platform API outage triggering graceful degradation and automatic recovery. Single-leg exposure event successfully managed within risk parameters. The operator's reaction shifts from "thank god it didn't blow up" to "good, that's what it's supposed to do."

Expected timing: Weeks 3-6 of live trading (adverse scenarios occur naturally with sufficient frequency).

### Business Objectives

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
- **Shut down:** Per-trade economics negative (profit factor <1.0 over 60+ cycles), OR catastrophic contract matching failure occurred, OR execution quality <50% of backtest with no identifiable fixable cause. Return to backtesting with real-world data, determine if strategy is flawed or needs recalibration.

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

**Strategic Assessment:**
- Preliminary assessment of Phase 2 news-velocity alpha viability based on 6 months correlated data
- Clear view of whether third platform addition makes sense
- Sufficient performance history to begin conversations with legal counsel about fund structure exploration

**Decision Outcomes:**
- **Shift focus to Phase 2:** System meets all three Phase 2 gate conditions (8+ weeks operational stability, sufficient data for testable hypotheses, 30-45 min daily involvement achieved). Begin Phase 2 research as parallel workstream while Phase 1 continues generating returns.
- **Continue pure Phase 1:** System profitable but hasn't reached operational steady state (still intervening frequently, unresolved execution quality issues, insufficient data for Phase 2). Focus on hardening and optimization. Reassess Phase 2 readiness at month 9.
- **Scale down or shut down:** Returns below 10% annualized minimum on trailing 90 days at full capital, OR max drawdown exceeded 20% (approaching 25% hard limit), OR edge clearly degrading based on leading indicators (opportunity frequency down 50%+, time-to-convergence dramatically compressed). Assess whether edge was competed away or never as large as backtested.

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
- **Maintain and harvest:** Arbitrage system works but edge slowly compressing. Phase 2 not viable or not ready. Continue operating at current scale as profitable but potentially declining income stream. Explore other opportunities where infrastructure and skills transfer.
- **Wind down:** Edge compressed to point where risk-adjusted returns no longer justify operational complexity. Close positions over 2-4 weeks, document learnings. This is a success outcome if system was profitable for 12 months and generated enough knowledge and capital to fund next venture.

**Critical Principle:** Default is "continue" unless specific, articulable reasons justify "expand" or "contract." Inertia toward current state is appropriate when operating within expected parameters. Changes driven by data, not emotion or impatience.

### Key Performance Indicators

#### Financial Performance Metrics (Hierarchy by Importance)

**1. Maximum Drawdown (Most Critical)**
- Hard limit: 25% (any breach triggers immediate review and trading halt)
- Target: <15% in any rolling 6-month period
- Rationale: Capital preservation under adverse conditions is fundamental. Drawdown beyond 25% creates both practical problems (reduced capital base makes recovery harder) and psychological problems (loss of confidence leads to decision errors)

**2. Sharpe Ratio (Edge Quality)**
- Target: 2.0+ over any rolling 6-month period
- Minimum acceptable: 1.5
- Alert threshold: Below 1.5 sustained for 2 months warrants strategy review
- Rationale: Captures edge quality, not just magnitude. Consistent 15% return with Sharpe 3.0 superior to volatile 30% return with Sharpe 0.8

**3. Profit Factor (Edge Robustness)**
- Target: 1.5+ (gross wins / gross losses)
- Minimum acceptable: 1.3
- Shutdown threshold: Below 1.0 for any rolling 30-day period after initial 3-month validation triggers automatic halt and full review
- Rationale: Measures robustness — profit factor 1.3 means 30% margin where moderate cost increases or edge decreases don't flip strategy to negative

**4. Net Annualized Return (Output Metric)**
- Target: 15%+ annualized
- Minimum acceptable: 10%+ annualized after all costs
- Rationale: Returns are output of well-functioning system with real edge and proper risk management. Below 10%, risk/complexity/opportunity cost of operating system not justified vs. risk-free rate

#### Leading Indicators for Edge Degradation

**Opportunity Frequency (Earliest Warning)**
- Baseline: 8-12 actionable opportunities per week (Month 1)
- Alert threshold: Sustained 30%+ decline in weekly opportunity frequency over 3-week window
- Rationale: Before edge degrades in profitability, it degrades in availability. Measures raw supply of edge before execution or risk filtering. Probable earliest indicator that structural inefficiency is compressing.

**Time-to-Convergence (Competition Indicator)**
- Baseline: Dislocations persist 4-6 hours historically
- Alert threshold: 40%+ compression in rolling 14-day median time-to-convergence
- Rationale: When dislocations close in 30-60 minutes instead of hours, competitors have entered. Even if capturing edge per trade, window is shrinking and operating margin thinning.

**Order Book Depth at Execution (Extractable Edge)**
- Monitor: Liquidity available at best prices, spread width trends
- Alert: Sustained decline in average depth at execution points
- Rationale: Thinning liquidity means practical extractable edge per trade shrinks even if quoted mid-price dislocation looks the same. Affects strategy scalability.

**Execution Quality Ratio (Capture Efficiency)**
- Formula: Realized edge ÷ expected edge at entry
- Target: >0.7 (capturing 70%+ of expected edge)
- Alert threshold: <0.6 sustained
- Rationale: Downstream confirmation of the above leading indicators. By the time this degrades, edge degradation already underway.

**Leading Indicator Hierarchy:** Opportunity frequency (earliest, measures edge supply) → Time-to-convergence (measures competition) → Order book depth (measures extractable edge) → Execution quality ratio (measures realized capture) → Returns and Sharpe (lagging confirmation)

#### Operational Metrics

**System Uptime**
- Target: 99%+ during active market hours
- Rationale: Each hour of downtime is lost opportunity and operational risk (open positions may not be manageable). Drives infrastructure investment decisions. Below 98% sustained, priority shifts from alpha improvement to infrastructure hardening.

**Autonomy Ratio**
- Formula: Automated decisions ÷ manual interventions
- Trajectory target: Month 1: 20:1. Month 6: 100:1+
- Rationale: Increasing ratio over time indicates system handling broader range of scenarios. Declining ratio means encountering more situations it can't handle — either market complexity increasing or system decision framework has gaps.

**Average Realized Slippage vs. Modeled**
- Target: Within 25% of modeled slippage
- Alert threshold: Excess of 25% for rolling 10-day window
- Rationale: Validates execution assumptions from backtesting. Excess slippage either means market microstructure changed or model was miscalibrated.

#### Strategic Metrics

**Data Accumulation**
- 12-month target: 100+ unique contract pairs traded, 500+ completed cycles, 75%+ resolution outcome data
- Rationale: This dataset is the foundation for Phase 2 and is genuinely irreplaceable. Measures the strategic asset being built.

**Phase 2 Readiness**
- Gate condition: Can formulate and backtest 3+ specific, data-supported hypotheses about news-driven dislocation patterns
- Timeframe: Assessed at 6 and 12 month checkpoints
- Rationale: Leading indicator that strategic evolution is viable. If can't identify testable patterns after 12 months data, Phase 2 may not be viable — important to know.

**Competitive Positioning (Qualitative, Quarterly Assessment)**
- Questions: Has contract matching knowledge base grown? Platform coverage expanded? Relationships with platform teams developed? Operational knowledge accumulated that new competitor would take months to develop? Regulatory landscape still favorable?
- Rationale: Forces honest evaluation of whether compounding advantage thesis is playing out or competition catching up faster than expected.

### Automated Triggers

**Soft Triggers** — Create awareness, adjust behavior conservatively, fire early and often:

- **Autonomy ratio decline:** If automated:manual decision ratio decreases for 2 consecutive weeks, generate structured review prompt with top intervention categories, most common trigger, and suggested investigation hypothesis
- **Slippage drift:** If average realized slippage exceeds modeled by >25% for rolling 10-day window, automatically widen minimum edge threshold by excess amount and alert operator. Self-correcting while flagging model recalibration need.
- **Correlation concentration:** If portfolio correlated exposure exceeds 70% of 15% cap (i.e., 10.5%) for >48 hours, flag and prevent new positions in same correlation cluster
- **Platform concentration drift:** If capital on any single platform exceeds 30% of total (limit is 40%), alert and prevent new positions until rebalanced
- **Opportunity quality degradation:** If median identified edge declines >20% over rolling 14 days vs. trailing 60-day average, generate report analyzing temporary vs. structural causes

**Hard Triggers** — Halt activity, require explicit decisions to resume:

- **Shutdown threshold:** Profit factor below 1.0 for any rolling 30-day period after initial 3-month validation halts trading automatically, triggers full review
- **Maximum drawdown breach:** Exceeding 25% drawdown triggers immediate trading halt and risk framework review
- **Catastrophic contract matching failure:** Any resolution divergence causing directional loss on "matched" contracts halts trading, triggers matching system audit

**Design Principle:** Soft triggers provide continuous diagnostic stream. Hard triggers are rare and serious.

### Weekly Review Metrics (15-minute review, not daily noise)

- Rolling 30-day Sharpe ratio, profit factor, hit rate, maximum drawdown
- Opportunity frequency (weekly count of identified actionable opportunities)
- Average realized slippage vs. modeled slippage
- Autonomy ratio trend

### Monthly/Quarterly Deep Dive Metrics

- Correlation analysis across position book
- Platform concentration trends
- Contract matching knowledge base growth
- Time-to-convergence trends
- Order book depth analysis
- Per-platform cost attribution
- Comparison of live results to backtested projections

**Rule of thumb:** If checking a monthly/quarterly metric daily, either anxious about something specific (investigate and resolve) or metric should be promoted to daily/weekly tier.

---

## MVP Scope

### Philosophy: Validation Over Infrastructure

The MVP exists to answer exactly one question: **"Do actionable cross-platform dislocations exist at sufficient frequency and magnitude to be profitable after real transaction costs?"** Every feature that doesn't directly contribute to answering this question is premature infrastructure.

**Design Principle:** The MVP is deliberately crude. It's a validation tool, not a production system. If the edge doesn't exist, beautiful infrastructure for a non-working strategy is worthless. If the edge does exist, the MVP will be replaced component-by-component by the full Phase 1 system while continuing to generate returns and collect data.

### Core Features

**MVP = Option A (3-4 Week Build) + Two Critical Enhancements**

**Platform Coverage:**
- **One platform pair:** Polymarket ↔ Kalshi only
- **One contract category:** U.S. political/economic binaries (highest volume, most obvious cross-platform matches, widest historical dislocations)

**Contract Matching:**
- **Manual curation:** Personal verification of 20-30 high-volume contract pairs where resolution criteria alignment has been confirmed
- **Zero automation:** Deliberately labor-intensive but eliminates matching risk entirely for MVP
- **Curated pair table:** Hardcoded mapping maintained in config file

**Execution:**
- **Sequential execution:** Place more liquid leg first (typically Kalshi), then immediately place second leg on Polymarket
- **Accept leg risk:** For slow-moving political contracts, prices don't move meaningfully in 10-15 seconds outside event announcement windows
- **No parallel coordination:** Simpler implementation, adequate for MVP contract universe

**Exit Management:**
- **Fixed thresholds only:**
  - Take profit: 80% of initial edge captured
  - Stop loss: 2x initial edge (if entered expecting 1% profit, exit if position down 2%)
  - Time-based: 48 hours before contract resolution
- **No model-driven optimization:** Adequate for validating whether edge exists; refinement comes in Phase 1

**Risk Controls:**
- **Position sizing:** 3% of bankroll per arbitrage pair maximum
- **Portfolio limit:** Maximum 10 simultaneous open pairs
- **Daily loss limit:** 5% of bankroll enforced manually
- **No correlation management:** With max 10 pairs from 20-30 contract universe, correlation manageable mentally

**Monitoring & Alerting:**
- **CSV logging:** All trades, prices, fills, P&L logged to timestamped CSV files
- **Telegram alerts:** Opportunity identification, execution results, exit triggers, system errors
- **Polling frequency:** 30-second refresh of both platforms' order books for curated pairs
- **No dashboard:** CSV review and Telegram notifications sufficient for 10 pairs

**Two Critical Enhancements Beyond Baseline:**

**Enhancement 1: Order Book Depth Verification (Development: Few Hours)**
- Before placing any order, query full order book on both platforms
- Verify desired position size can be filled within modeled slippage tolerance
- If insufficient depth at expected prices, skip opportunity
- **Rationale:** Without this, execute "arbitrages" profitable at $100 that lose money at $2,000 actual position size. Cheap to build, prevents expensive mistakes.

**Enhancement 2: Automated Single-Leg Detection & Alerting (Development: One Day)**
- If first leg fills and second leg fails or fills at materially worse price than expected, immediate Telegram alert with full context: what filled, what didn't, current price on failed leg, estimated loss if exit now vs. hold
- MVP response: Manual intervention by operator (system detects, human decides)
- **Rationale:** Single-leg situation undetected for 30 minutes could produce loss invalidating entire MVP test. Instant detection with decision-ready information is the single most important safety feature.

**Build Timeline: 3-4 Weeks**
- **Week 1:** Platform API integration (authentication, order placement, order book queries for Polymarket and Kalshi)
- **Week 2:** Arbitrage detection logic (spread calculation including fees, opportunity identification against curated pair table, order book depth verification)
- **Week 3:** Execution logic (sequential order placement, fill monitoring, single-leg detection and alerting, fixed exit threshold monitoring)
- **Week 4:** Testing, paper trading validation, operational setup (Telegram bot, CSV logging, deployment)

### Out of Scope for MVP

**Deferred to Phase 1 (Month 6):**
- **Model-driven exit framework** — Fixed thresholds adequate for validating edge existence. Optimizing exit timing is refinement that only matters once positions worth optimizing exist.
- **Correlation-aware portfolio sizing** — With max 10 simultaneous pairs from curated 20-30 contracts, correlation manageable mentally. Portfolio-level correlation math necessary at 20+ pairs, not 10.
- **NLP-based contract matching** — Manual curation for 20-30 pairs is fast, reliable, eliminates matching risk entirely. NLP needed when scaling to 100+ pairs where manual verification becomes bottleneck.
- **Unified order book abstraction** — For two platforms, can write direct integrations without abstraction layer. Polymarket integration is hardcoded, Kalshi integration is hardcoded, comparison logic takes both as inputs. Ugly but functional. Proper abstraction justified when adding platform 3 or packaging for other users (Ring 2). If edge doesn't exist on two platforms, beautiful unified order book for five platforms is worthless.
- **Platform-agnostic connector architecture** — Same reasoning as unified order book. Hardcode Polymarket and Kalshi. Keep code reasonably clean for eventual refactoring, but don't build plugin system yet.
- **Full graceful degradation protocols** — MVP-grade degradation: if API call fails, retry once. If retry fails, Telegram alert and stop all new activity. Manual assessment and decision. Adequate for actively monitored system with 10 or fewer open pairs. Not adequate for 25-pair autonomous system while operator sleeps — but that's Phase 1, not MVP.
- **Historical data scraping and backtesting engine** — MVP is about live validation, not backtesting. Build backtesting pipeline for Phase 1 using data MVP collects. Spending 3 weeks building historical scraper before live system is procrastination disguised as rigor.
- **Monitoring dashboard** — CSV logs and Telegram alerts are ugly but sufficient for 10 pairs. Proper dashboard is Phase 1 investment.
- **Transaction cost optimization** (gas batching, execution timing) — Premature optimization. First prove edge exists, then optimize costs to improve it. Trying to save 0.05% on gas before knowing whether 0.5% edge exists is backwards.
- **Automated compliance monitoring and audit trails** — CSV logs and personal records adequate for 4-week MVP at minimum capital. Automated compliance monitoring is Phase 1 requirement for full-scale operation.

**Deferred to Phase 2 (Month 12+):**
- **Third platform** — Decision depends on whether edge is real on two platforms and whether additional platforms show sufficient unique liquidity
- **News-velocity alpha layer** — Requires 6+ months of correlated data from Phase 1 arbitrage system to identify actionable patterns
- **Multi-platform expansion beyond 3** — Contingent on Phase 2 success and market conditions

**Explicitly Out of Scope (Ring 3 / Long-term Vision):**
- **Multi-user access and permissions**
- **Investor reporting and fund management infrastructure**
- **Institutional compliance frameworks for external capital**

**Gray Area: Common Internal Data Structures**
- Even without formal abstraction, both platforms' data transformed into consistent internal format (price, size, side, timestamp, fee estimate) before arbitrage detection logic processes it
- This isn't an "abstraction layer" — it's not writing spaghetti code
- Takes an extra hour, makes eventual Phase 1 refactoring 10x easier
- **Included in MVP** as basic code hygiene

### MVP Success Criteria

**MVP Deployment Timeline: Weeks 1-4 (build) + Weeks 5-8 (paper trade & minimum capital validation)**

**The MVP has graduated — edge is validated, proceed to Phase 1 investment — when ALL of the following are true:**

1. **50+ completed arbitrage cycles on real capital** (lower than Phase C criterion of 100+ because MVP runs at minimum capital on smaller contract universe)

2. **Aggregate profit factor >1.2 after all real transaction costs** (slightly lower bar than Phase C criterion of 1.3, because MVP's crude execution and fixed thresholds leave edge on the table that full system would capture)

3. **Zero contract matching errors** (absolute threshold — even one matching error on curated manual list means something fundamental is wrong with thesis)

4. **Fewer than 3 single-leg exposure events requiring manual intervention with loss** (some single-leg events expected; too many means execution reliability insufficient)

5. **Evidence that full system would capture meaningful additional edge** (manual tracking confirms opportunities missed due to MVP limitations — too slow, too crude, risk limits too conservative — represent material improvement opportunity, not just marginal gains. If MVP captures everything and there's nothing left for sophisticated system to improve, building full system is waste.)

**MVP Failure = Any of These:**

- **Profit factor below 1.0 after 50+ cycles** — Edge isn't real, or transaction costs consume it
- **Fewer than 20 actionable opportunities identified over 8 weeks** — Dislocations don't occur frequently enough to support systematic strategy
- **Multiple contract matching errors despite manual curation** — Contracts that appear identical have substantive resolution differences not reliably identifiable. Undermines entire thesis.
- **Single-leg exposure events frequent (>1 per week) and costly (average loss >1% of position size)** — Execution on these platforms too unreliable for cross-platform arbitrage

**Transition from MVP to Phase 1:**
- Not a "graduation ceremony" but a build decision
- If MVP validates edge, start building Phase 1 features immediately while continuing to run MVP in production
- MVP doesn't stop — continues generating returns and collecting data while unified order book, NLP matching, model-driven exits, and correlation management are built
- MVP becomes "legacy system" gradually replaced component-by-component as Phase 1 features come online
- No downtime between MVP and Phase 1

### Future Vision

**Phase 1 (Month 6): Full Institutional-Grade System**
- All five architectural pillars operational: unified order book, NLP contract matching, near-simultaneous execution, model-driven exits, portfolio-level risk management
- System running at full capital deployment ($100K-$250K)
- Operational autonomy achieved (30-45 minute daily involvement)
- 50+ validated cross-platform contract pairs
- 15-25 simultaneous open positions

**Phase 2 (Month 12+): Strategic Evolution**
- News-velocity alpha layer development based on 6+ months correlated data
- Potential third platform addition if differentiated liquidity exists
- Expanded contract universe beyond political/economic binaries
- Strategic clarity on whether this is $200K/year lifestyle business, $1M+/year scalable operation, or edge requiring further evolution

**Ring 2 (18-24 Months): Infrastructure Productization**
- Package system as deployable infrastructure for other systematic traders
- Clean documentation, configurable parameters, pluggable platform connectors
- Justifies architectural investments (unified order book, platform-agnostic connectors) that seemed over-engineered for single-user MVP

**Ring 3 (24+ Months): Institutional Scaling**
- Fund structure for managing external capital
- Multi-user access, investor reporting, institutional compliance frameworks
- Contingent on durable edge demonstration and regulatory clarity

**5-Year Speculative Vision (Wildly Successful Scenarios):**

**Prediction Market Infrastructure Provider:**
If cross-platform infrastructure (unified data, contract matching, execution routing) proves robust, potential business in providing this as infrastructure to broader prediction market ecosystem — not just for arbitrage, but for market makers, researchers, institutional traders, potentially platforms themselves. "Bloomberg Terminal for prediction markets" — unified data and execution layer across fragmented venue landscape. Venture-scale business if prediction markets grow to $100B+ annual volume. Wildly speculative, but influences architectural decisions: modular, well-documented infrastructure from early stages has low marginal cost but potentially enormous option value.

**Cross-Asset Event-Driven Trading:**
Prediction market prices reflect probabilities that also affect traditional financial instruments. "Will Fed cut rates in March?" trading at 70% has direct implications for bond prices, interest rate futures, equity sectors. System simultaneously monitoring prediction market prices, identifying dislocations between prediction market implied probabilities and traditional market pricing, and executing across both would operate at sophistication level few firms currently achieve. Requires 3+ years, significantly more capital, regulatory infrastructure, traditional market access — but logical endpoint of "build best system for understanding event probabilities and their market implications."

**Strategic Value of Speculative Vision:**
These shouldn't influence near-term decisions, but useful for two reasons: (1) Help explain why project is worth doing even if pure arbitrage edge eventually compresses (infrastructure and knowledge have value beyond initial strategy). (2) Provide strategic direction for "what comes after Phase 2?" question that inevitably arises if Phase 2 succeeds.
