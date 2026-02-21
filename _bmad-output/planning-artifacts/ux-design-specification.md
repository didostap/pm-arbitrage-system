---
stepsCompleted: [1, 2, 3, 4, 5, 6]
lastStep: 6
status: 'complete'
completedAt: '2026-02-11'
inputDocuments:
  - '_bmad-output/planning-artifacts/product-brief-pm-arbitrage-system-2026-02-09.md'
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
workflowType: 'ux-design'
project_name: 'pm-arbitrage-system'
user_name: 'Arbi'
date: '2026-02-11'
---

# UX Design Specification pm-arbitrage-system

**Author:** Arbi
**Date:** 2026-02-11

---

## Executive Summary

### Project Vision

**pm-arbitrage-system** is an institutional-grade algorithmic trading system that exploits cross-platform arbitrage opportunities in prediction markets (Polymarket ↔ Kalshi). Unlike typical trading interfaces that emphasize excitement and real-time action, this system's UX philosophy centers on **operational autonomy through boring reliability**.

The ultimate UX success metric: the operator can glance at the dashboard over weekend coffee, see everything's healthy, and return to their life without anxiety. This is the "48-hour test" — the system earns trust by being so reliable it disappears into the background.

**Core UX Tension:** Balance transparency with autonomy. The operator (Arbi) is a quantitative trader with institutional risk discipline, shaped by hard-earned lessons from the 2022 drawdown. He needs to *see* what's happening, understand *why* decisions are being made, and intervene when genuinely necessary — but only then. The system walks the tightrope between "show me everything" and "don't bother me unless it matters."

**Success Arc:** Month 1 = supervised monitoring (2-3 hours/day). Month 3 = trusted operation (30-45 min/day). Month 6 = infrastructure (operator spends more time on Phase 2 research than Phase 1 babysitting). The UX must support and visibly reflect this trust progression.

### Target Users

**Primary User: Arbi — Quantitative Independent Trader**

**Background:** Software engineer by training (4+ years backend fintech), transitioned to independent crypto trading 2020-2021. Self-taught quantitative portfolio management through canonical texts and expensive real-world lessons. The 2022 crypto drawdown created permanent "scar tissue" — had a working strategy but no risk framework, gave back significant gains due to correlated exposure and absent drawdown controls. This experience drives non-negotiable risk discipline.

**Technical Profile:** Comfortable with CLI, config files, TypeScript/Python, blockchain infrastructure. Builds his own tools — wants well-structured, extensible codebases, not polished GUIs. Thinks in systems, not trades. Values operational reliability over feature richness: 5 features that work flawlessly > 20 features at 90% reliability.

**Daily Interaction Patterns:**

- **Morning (2-minute target):** Scan system health composite indicator, review overnight activity summary, approve/reject edge-case contract matches (78-84% confidence range), check alerts requiring action
- **Midday (5-min phone check):** Glance at real-time dashboard, verify API connections healthy, scan for open alerts
- **Evening (20-30 min, Month 1 only):** Deep review comparing week's metrics against backtest, analyze slippage tracking, review single-leg exposure events in detail
- **Weekly (1 hour):** Full performance review, statistical comparison against backtest benchmark, identify parameter drift
- **Real-Time Interventions (60-90 seconds each):** Single-leg exposure events, contract match approvals below auto-threshold, risk limit approaches

**Decision-Making Style:** When the system escalates an edge case, decision process takes 60-90 seconds. Needs all relevant information *decision-ready* on a single screen: exact contract descriptions side-by-side, resolution criteria with differences highlighted, NLP matcher's reasoning, historical precedent, current spread and estimated edge, risk scenario (max loss if contracts resolve differently). No hunting through logs, no mental math, no ambiguity.

**Risk Philosophy:** Risk controls are non-negotiable. Will never override risk limits "just this once." The 2022 drawdown created permanent scar tissue — this system's risk architecture and UX transparency reflect that experience.

**Supporting Roles:**

- **Legal Counsel:** Periodic (quarterly or on-demand). Needs complete audit trails, compliance reports, regulatory scan results. Receives exported reports — does NOT interact with system directly.
- **Tax/Accounting Advisor:** Annual or quarterly. Needs complete trade log exports in standard formats, P&L summaries by platform and time period, cost basis tracking.
- **Platform Providers (Polymarket, Kalshi):** Dependency relationship via API. System must maintain compliant trading behavior, reasonable request volumes, proper documentation if inquiries arise.

### Key Design Challenges

**Challenge 1: Information Density vs. Scanability**

The morning dashboard isn't "simplified for beginners" — it's **high-density information designed for expert pattern recognition**. The operator needs to see a lot in 2 minutes without drowning in noise: green/yellow/red health composite, trailing 7-day P&L, execution quality ratio, open position count with aggregate unrealized edge, active alert count. Think terminal UI optimized for pattern recognition, not consumer app optimized for first-time users.

**Tension:** Too sparse = insufficient information for confident decision. Too dense = analysis paralysis. The sweet spot is **hierarchical information architecture with progressive disclosure** — surface shows health at a glance, one click reveals depth.

**Challenge 2: Trust Calibration Over Time**

The UX must evolve with the operator-system relationship:

- **Month 1 (Building Trust):** Operator watching constantly. UI must be transparent about *why* every decision was made. Show reasoning, show calculations, show edge cases handled. Every automated action has visible rationale.
- **Month 3 (Steady State):** Operator trusts the basics. UI needs to surface *anomalies* and *edge cases*, not routine operations. Contract match approved at 97% confidence? Silent background operation. Match at 82% confidence? Escalate for review.
- **Month 6 (Infrastructure):** System is infrastructure. UI needs strategic trend visibility (opportunity frequency declining? time-to-convergence compressing?), not operational blow-by-blow.

**Design Implication:** The same interface serves all three phases, but the *default view* should shift. Month 1 lands on detailed monitoring dashboard. Month 6 lands on strategic summary, with monitoring view still one click away. The system earns its way from "supervised tool" to "trusted infrastructure" — and the UX makes that progression visible.

**Challenge 3: Error States Are Mission-Critical**

When things go wrong (single-leg exposure, platform API failure, risk limit approaching breach), the UX cannot just show a generic error message. These are high-stakes moments where poor UX design could cost 5% of bankroll in 30 seconds.

**Requirements for error/alert states:**

- **Alert immediately:** Telegram notification + dashboard prominence
- **Provide complete context:** What happened, what filled, what didn't, current state, platform status
- **Present decision-ready information:** Estimated P&L scenarios (exit now vs. retry vs. hold), retry parameters, exit costs, time-sensitive constraints
- **Preserve for analysis:** Full context logged for post-mortem review, correlation with other events visible

**Example (from PRD Journey 2):** Single-leg exposure alert shows: "Kalshi leg filled at 0.62, Polymarket leg failed to fill, current Polymarket price 0.64. Estimated loss if exit now: 0.8%. Retry with 0.64 limit? Hold and monitor? Close Kalshi position?" Operator has everything needed to decide in 30 seconds on a phone screen.

**Challenge 4: Mobile-First Critical Paths, Desktop-First Analysis**

Critical interventions (single-leg exposure, risk breaches) may occur when operator is away from desk. These decision points MUST work on phone — readable on 6" screen, tappable targets, no horizontal scrolling for critical information, fast load over cellular.

Non-critical workflows (weekly deep-dive performance review, parameter tuning, compliance export generation) are desktop-optimized — can use full screen real estate, multi-column layouts, complex visualizations.

**Design Implication:** Information architecture must identify "mobile-critical" vs. "desktop-preferred" paths. Mobile-critical paths get ruthless simplification and touch optimization. Desktop workflows can leverage screen space.

### Design Opportunities

**Opportunity 1: Progressive Disclosure That Builds Confidence**

Most dashboards are either "dumbed down" (hiding complexity) or "overwhelming" (showing everything). This system can do something smarter: **surface-level simplicity with one-click drill-down depth**.

**Example:** Morning scan dashboard shows "Execution Quality Ratio: 0.73" with green indicator (above 0.7 target). Click the metric → full-screen drill-down showing trailing 30-day chart, per-platform breakdown (Kalshi 0.76, Polymarket 0.69), slippage attribution (fees 15%, adverse price movement 12%), comparison to backtest projection (0.75 ± 0.05).

The operator doesn't *need* that depth every morning — but knowing it's one click away when curious builds confidence. "The system knows more than it's showing me, and I can access that depth whenever I want" is trust-building.

**Opportunity 2: Event-Driven Real-Time Updates Without Notification Spam**

The architecture (NestJS EventEmitter2 fan-out, WebSocket gateway) already supports real-time event streaming to the dashboard. The UX opportunity is **intelligent tiering** of how events surface:

- **Critical (immediate alert):** Single-leg exposure, risk limit breach, platform degradation, catastrophic errors → Telegram notification + dashboard modal + sound/vibration
- **Important (prominent but non-blocking):** Contract match requiring approval, opportunity identified above edge threshold, position exited → Dashboard notification badge + event stream entry
- **Routine (batch and summarize):** Order fills at expected prices, opportunity filtered (below threshold), health checks passing → Batched into summary counts, individual events in scrollable log
- **Background (silent state sync):** Position P&L ticks, order book updates, platform heartbeats → Update state silently, no notification, visible in real-time metrics

This respects operator attention. The dashboard is "alive" with real-time data, but doesn't cry wolf. When Telegram pings, it genuinely matters.

**Opportunity 3: "Why Did You Do That?" Transparency Layer**

For every automated decision (contract match approved, opportunity filtered, position exited), the system can surface its reasoning. This transparency is the foundation of trust — the operator isn't blindly trusting a black box, they're auditing a well-reasoned trading partner.

**Examples from PRD workflows:**

- **Contract Match (97% confidence, auto-approved):** Click to see: "Resolution criteria align on 14/15 keywords (divergence: 'at or before' vs 'by'). Settlement dates identical. Historical concordance 100% for Fed policy contracts on these platforms. Position sized at 100% (confidence >95%)."
- **Opportunity Filtered:** "Spread: 1.4%, estimated edge 0.8% after fees. Order book depth insufficient — would require $2.2K position across 4 price levels, modeled slippage 0.6%, total impact 1.4% vs. edge 0.8%. Filtered: net expected value negative."
- **Position Exited (Model-Driven):** "Edge recalculated: initial 1.2%, current 0.08% (fees unchanged, liquidity deteriorated, time-to-resolution <18 hours). Exit threshold: 0.3%. Position closed, realized P&L +0.9%, captured 75% of initial edge."

Every "why" has a rationale field stored in the audit log. The UX surfaces this on-demand — not cluttering the main interface, but always available for the operator to understand "what was the system thinking?"

**Opportunity 4: UX-Driven Trust Progression Visibility**

As the operator-system relationship matures from Month 1 (supervised) → Month 3 (steady state) → Month 6 (infrastructure), the UX can make this progression *visible* through subtle cues:

- **Default view configuration (operator-controlled):** The system notices trust signals (autonomy ratio >100:1 for 4 weeks, 48-hour test passed twice) and offers a gentle suggestion: *"Your autonomy ratio has been >100:1 for 4 weeks — would you like to switch your default view to Strategic Summary? (You can always switch back.)"* The operator chooses when they're ready to shift, respecting the "process over outcomes" philosophy and operator control.
- **Intervention ratio tracking:** Dashboard shows "Automated:Manual decision ratio: 127:1 (trailing 30 days)" as a trust signal. Rising ratio over time = system handling more scenarios autonomously.
- **Milestone achievements:** "48-hour test passed (2x)" badge visible in header — external validation that trust milestones have been reached.
- **Confidence calibration:** Contract match auto-approval threshold starts at 95% (Month 1), can be lowered to 90% or 85% (Month 3+) as operator gains confidence in matching accuracy. UI makes this tunable parameter visible and adjustable.

The system doesn't just *become* trusted infrastructure — the UX makes that transformation visible and celebrated.

## Core User Experience

### Defining Experience

**pm-arbitrage-system** is designed around a counterintuitive UX principle: **the best user experience is the one that disappears**. Unlike typical trading platforms that emphasize real-time action and dashboard complexity, this system's core experience is defined by two contrasting interaction modes that represent opposite ends of the operator's relationship with the system.

**Primary Design Constraint: The 60-Second High-Stakes Mobile Decision**

The core UX challenge is not the daily morning scan at a desktop with coffee — that's forgiving. The absolute core experience is the crisis moment: You're at lunch, away from your desk. Telegram pings. "SINGLE-LEG EXPOSURE." You have a 6" phone screen, maybe cellular data, and 60 seconds to make a decision that could cost or save 5% of your bankroll.

Everything you need must be on that screen:
- What filled, what didn't
- Current prices on both platforms
- Estimated P&L scenarios (exit now vs. retry vs. hold)
- Retry parameters, exit costs
- Time-sensitive constraints

**Design Philosophy:** If it works on a phone during a crisis, it works everywhere. The morning scan, weekly analysis, parameter tuning — they all inherit the same information architecture principles (progressive disclosure, decision-ready context, zero hunting). The reverse doesn't work. Designing for leisurely desktop scanning won't produce a good mobile crisis interface.

**Secondary Experience: The 2-Minute Morning Ritual**

The most *frequent* interaction is the daily morning scan. Desktop, coffee in hand, checking: Is everything healthy? Any overnight activity? Any alerts? Any contract matches needing review?

This experience is about **pattern recognition at a glance**:
- Green/yellow/red health composite (system operational status in 1 second)
- Trailing 7-day P&L trend
- Execution quality ratio
- Open position count with aggregate unrealized edge
- Active alert count

Target: 2 minutes for routine scan. 10 seconds if everything's green and healthy. 5-10 minutes if digging into an alert or reviewing a contract match.

**Trust Progression Arc:**

The relationship between operator and system evolves through demonstrated reliability:

- **Month 1 (Building Trust):** Operator watches constantly (2-3 hours/day). Every automated decision needs visible reasoning. Morning scan takes longer because everything is being verified against mental models.
- **Month 3 (Steady State):** Operator trusts the basics (30-45 min/day). Morning scan is genuinely 2 minutes. Interventions are edge cases only. System handles routine with silent confirmation.
- **Month 6 (Infrastructure):** Operator spends more time on Phase 2 research than Phase 1 monitoring. Default view shifts to strategic summary. System has earned "set it and forget it" status — but transparency is still one click away when curiosity strikes.

The UX must support this entire arc without feeling like three different systems.

### Platform Strategy

**Primary Platform: Desktop Web**
- Morning scan dashboard (2-minute target)
- Weekly deep-dive performance reviews (1 hour)
- Parameter tuning and configuration
- Compliance export generation
- Multi-column layouts, complex visualizations, full keyboard/mouse optimization

**Critical Path Platform: Mobile Web (Responsive)**
- Single-leg exposure alerts and decisions
- Contract match approvals (78-84% confidence range)
- Risk breach responses
- Ruthlessly optimized for 6" screen, cellular data, touch targets, fast load
- No native iOS/Android app — responsive web is sufficient

**Push Notification Layer: Telegram**
- Immediate alerts for critical events (single-leg exposure, risk breach, platform degradation)
- Deep-link directly to specific alert detail on mobile dashboard (NOT dashboard home)
- Operator can respond from anywhere with phone and internet
- Architecture already designed for this (EventEmitter2 fan-out → Telegram integration)

**No Native Mobile App:** The PRD doesn't justify iOS/Android native development. Responsive web with Telegram notifications covers the critical path. Native app consideration deferred to Phase 2+ if user base expands (Ring 2/Ring 3).

**Cross-Platform Consistency:** Same visual language, same information architecture, same progressive disclosure patterns across desktop and mobile. What changes is layout density and interaction model (mouse/keyboard vs. touch), not the underlying UX principles.

### Effortless Interactions

The following interactions should feel completely natural and require zero conscious thought:

**1. System Health at a Glance**

Open dashboard. Within 1 second, know if everything's okay. Green composite indicator. No red alerts. Trailing 7-day P&L positive. Close laptop. Successful morning check complete — 10 seconds, not 2 minutes.

**Effortless because:** Single visual hierarchy. Color-coded health status. No drilling down required unless something's wrong.

**2. Decision-Ready Crisis Context (Primary Design Constraint)**

Telegram alert fires ("SINGLE-LEG EXPOSURE"). Tap notification. Mobile dashboard loads directly to alert detail (deep-linked, not home page). Everything needed to decide is on that screen: what happened, current state, P&L scenarios, retry/exit/hold options with parameters. Decide in 60 seconds. No tab-switching, no log hunting, no mental math.

**Effortless because:** The UX did the synthesis work. Pre-calculated scenarios. Highlighted key differences. Surfaced decision options with consequences visible.

**3. Contract Match Approval for Common Case**

Contract match notification: 82% confidence, requires manual review. Open detail view. Resolution criteria side-by-side, differences highlighted. Historical concordance for this contract category shown. Mental decision: "Yep, those are the same thing, just different wording." Single tap "Approve." Optional rationale note (pre-filled suggestion: "Semantic match — criteria align"). Done. 30 seconds total.

**Effortless because:** Common case (approve) is single-tap with optional note. Uncommon case (reject or "needs investigation") has more friction intentionally — edge cases should require deliberation.

**4. Automatic Trust Progression Visibility**

You don't manually track milestones. System shows "48-hour test passed (2x)" badge when achieved. Autonomy ratio displayed as "127:1 (trailing 30 days)" without manual calculation. When trust signals are strong, system offers: "Your autonomy ratio has been >100:1 for 4 weeks — would you like to switch your default view to Strategic Summary?" You choose when you're ready.

**Effortless because:** The work of tracking progress is automated. The operator benefits from visible milestones without doing the bookkeeping.

**5. Progressive Disclosure Depth Access**

Morning scan shows "Execution Quality Ratio: 0.73" (green). Curiosity strikes: "Why is Polymarket lagging Kalshi?" Click the metric. Full drill-down: trailing 30-day chart, per-platform breakdown, slippage attribution, backtest comparison. Satisfy curiosity. Return to summary.

**Effortless because:** Depth is always one click away when wanted, never in the way when not needed.

### Critical Success Moments

The UX succeeds or fails based on these four milestone moments:

**Moment 0: First Successful Arbitrage Cycle (Week 1, Day 1)**

*From PRD Journey 1:* "Arbi exhales. First trade done."

The system detected an opportunity, executed both legs (Kalshi filled, then Polymarket filled), and P&L tracking matches operator's mental calculation. The execution log is clean and confirmatory: timestamps for both legs, prices, fees, net edge captured (1.1% vs. 1.2% expected).

**Why This Matters:** This isn't about trusting autonomy yet — it's about trusting that *basic mechanics work*. If the first trade execution log feels ambiguous or requires detective work to understand what happened, the operator starts the trust journey with doubt instead of confidence.

**UX Requirements:**
- Clear, chronological execution log visible immediately after trade completes
- Both leg fills shown with timestamps, prices, fees
- Net edge calculated and compared to entry expectation
- No ambiguity about "did this work correctly?"

**Moment 1: First Single-Leg Exposure Handled Correctly (Week 3-6)**

*From PRD Journey 1 Week 3:* The first time something goes wrong — one leg fills, the other doesn't. System detects instantly, alerts with full context (what filled, what didn't, current prices, estimated loss scenarios). Operator makes decision (retry), system executes, second leg fills at slightly worse price. Net edge captured: 0.6% vs. 1.0% initial expectation. Acceptable.

**Why This Matters:** This is the trust milestone. The system handled adversity correctly. The operator's internal dialogue shifts from "I hope this works" to "Okay, it actually works."

**UX Requirements:**
- Immediate detection and alerting (Telegram + dashboard)
- Complete decision-ready context on mobile screen
- Clear P&L scenario presentation (exit now vs. retry vs. hold)
- Post-resolution confirmation that shows what was decided and what happened

**Moment 2: First 48-Hour Weekend Away (Month 2 Target)**

Friday evening, operator leaves for the weekend. Telegram notifications enabled but not obsessively checking. Monday morning, opens dashboard. System operated correctly over the weekend. No disasters. No missed opportunities due to overly conservative automation. Maybe 2-3 routine arbitrage cycles executed, 1 contract match auto-approved at 96% confidence. Everything logged, everything clean.

**Why This Matters:** This is the operational autonomy milestone. The operator can genuinely step away for 48 hours without anxiety. Trust deepens from "it handles crises" to "it operates independently."

**UX Requirements:**
- Weekend activity summary visible on Monday morning scan
- Any automated decisions (contract matches approved, opportunities executed) have visible reasoning in activity log
- "48-hour test passed" milestone badge appears after this succeeds twice

**Moment 3: Operator-Controlled Default View Shift (Month 3-6)**

System notices trust signals: autonomy ratio >100:1 for 4 weeks, 48-hour test passed twice, daily involvement consistently 30-45 minutes. Offers suggestion: "Your autonomy ratio has been >100:1 for 4 weeks — would you like to switch your default view to Strategic Summary? (You can always switch back.)"

Operator realizes the system knows they're ready before they consciously decided. Clicks "Yes." Dashboard now lands on strategic summary (opportunity frequency trends, edge degradation indicators, Phase 2 research data) instead of operational monitoring. Monitoring view still one click away.

**Why This Matters:** The relationship has fundamentally shifted. This isn't a tool being monitored anymore — it's infrastructure being managed. The UX makes that transformation visible and operator-controlled.

**UX Requirements:**
- System detects trust signal patterns (autonomy ratio, milestone achievements, time investment trends)
- Offers gentle, non-presumptuous suggestion with clear opt-out
- Operator chooses when to shift, respecting "process over outcomes" philosophy
- Default view change is reversible at any time

### Experience Principles

These principles guide every UX decision for **pm-arbitrage-system**:

**1. Design for Crisis First, Scale to Comfort**

The 60-second high-stakes mobile decision is the primary design constraint. If it works on a 6" phone screen during a crisis, it works everywhere. Morning scans and deep-dive analysis inherit the same information architecture. The reverse doesn't work — designing for leisurely desktop scanning won't produce a good mobile crisis interface.

**2. Zero Hunting, Zero Math, Zero Ambiguity**

Decision-ready information means no tab-switching, no log searching, no mental calculation required. The UX does the synthesis work: P&L scenarios pre-calculated, resolution criteria differences highlighted, historical precedent surfaced. Single screen contains everything needed to decide with confidence in 60 seconds.

**3. Progressive Trust Through Visible Reasoning**

Every automated decision (match approved, opportunity filtered, position exited) surfaces its reasoning on-demand. Trust is earned through auditable, visible logic — not blind faith in a black box. Transparency layer is always one click away: "Why did you approve this match? Why did you filter that opportunity?"

**4. Respect Attention Ruthlessly**

Critical alerts (single-leg exposure, risk breach) demand immediate attention via Telegram + dashboard modal. Important events (contract match approval, position exit) get prominent but non-blocking notification. Routine operations batch and summarize. Background state syncs silently. When Telegram pings, it genuinely matters — the system earns the right to interrupt.

**5. Optimize for the Common Case, Accommodate the Edge Case**

Single-tap approval for contract matches in the manual review band (below 85% confidence, specifically 78-84% where operator judgment is needed). One-glance health check shows green composite (common case: "everything's fine"). Rejection, investigation, or deep-dive analysis is available but requires more intentional navigation. Default paths assume success; edge cases are accessible but not in the way.

**6. Earn Infrastructure Status Through Milestones**

System doesn't assume trust — it earns it through demonstrated reliability. UX makes trust progression visible: Moment 0 (first trade works), Moment 1 (first crisis handled), Moment 2 (first weekend away), Moment 3 (operator chooses strategic view). Autonomy ratio tracking, milestone badges, default view suggestions all reflect the journey from "supervised tool" to "trusted infrastructure."

## Desired Emotional Response

### Primary Emotional Goals

**Calm Confidence: The Pilot Checklist Emotional State**

The primary emotional goal for **pm-arbitrage-system** is **calm confidence** — the methodical alertness of a pilot running through a pre-flight checklist. Not excitement, not anxiety, not boredom. Productive peace of mind.

Most trading platforms optimize for excitement: dopamine hits from green numbers, celebration animations on trades, urgency and FOMO. This system deliberately rejects that emotional model. The operator wants to feel like they're managing reliable infrastructure, not riding an emotional rollercoaster.

**Calm confidence manifests as:**
- Morning scan that takes 10 seconds because everything's green: "Yep, as expected. I can get on with my day."
- Weekly review showing metrics within expected parameters: "System is performing as designed."
- Monday morning after weekend away: "No disasters, no surprises. It ran correctly."

The opposite of excitement isn't boredom — it's **productive peace of mind**. The system earns the right to be boring through demonstrated reliability.

**Crisis Moments: Anxiety → Focused Action in 5 Seconds**

During crisis moments (single-leg exposure alert, risk breach), there *will* be a spike of anxiety. That's inevitable when real money is at stake. The emotional goal isn't to eliminate anxiety — it's to provide a fast path from anxiety to focused action.

**Target conversion window: 5 seconds**
- 0-2 seconds: Telegram alert fires, operator feels anxiety spike ("Oh shit, something's wrong")
- 2-5 seconds: Tap notification, mobile dashboard loads to decision screen with complete context, anxiety converts to focus ("Okay, I know what's happening, I know my options")
- 5-60 seconds: Operator makes informed decision with confidence

The UX's job is to accelerate that conversion from "adrenaline spike" to "I'm in control and I know what to do." Complete decision-ready context is the emotional bridge.

### Emotional Journey Mapping

**Moment 0: First Successful Arbitrage Cycle (Week 1, Day 1)**

*Emotional Arc: Cautious Optimism → Alert Focus → Relief + Confirmation*

- **Before execution:** Operator feels cautious optimism tinged with doubt. "Will this actually work? Did I build this correctly?"
- **During execution:** Alert focus. Watching execution log in real-time. Both legs need to fill.
- **After successful fill:** Relief + confirmation. "Okay, basic mechanics work. Net edge 1.1% matches 1.2% expectation. First exhale." Trust journey begins with this confirmed expectation.

**UX Requirement:** The execution log must provide immediate, unambiguous confirmation. No detective work required to understand "did this work correctly?"

**Moment 1: First Single-Leg Exposure Handled Correctly (Week 3-6)**

*Emotional Arc: Anxiety Spike → Focus Conversion → Deepening Trust*

- **Alert fires:** Spike of anxiety. Adrenaline response. "Oh shit, something went wrong."
- **Opening mobile dashboard:** Anxiety converting to focus. Alert screen shows complete context: what filled, what didn't, current prices, P&L scenarios. "Okay, what are my options?"
- **After correct resolution:** Trust deepening. "The system detected the problem instantly, gave me everything I needed to decide, and executed my decision correctly. It works even when things go wrong."

**Critical Emotional Milestone:** This is where trust shifts from "basic mechanics work" to "it handles adversity." The operator's internal dialogue changes from "I hope this works" to "Okay, it actually works."

**Moment 2: First 48-Hour Weekend Away (Month 2 Target)**

*Emotional Arc: Background Anxiety → Periodic Checking Resistance → Relief → Trust*

- **Friday evening:** Low-level background anxiety. "Can I really trust this to run unsupervised for 48 hours?"
- **During weekend:** Periodic curiosity and checking resistance. "Should I open the dashboard? No, the whole point is NOT checking."
- **Monday morning scan:** Relief transforming into trust. "System operated correctly. 2-3 routine cycles executed, 1 contract match auto-approved at 96%, everything logged and clean. I can actually step away."

**Emotional Milestone:** Operational autonomy achieved. Trust deepens from "it handles crises" to "it operates independently."

**Moment 3: Operator-Controlled Default View Shift (Month 3-6)**

*Emotional Arc: Mild Surprise → Recognition → Satisfaction + Ownership*

- **System offers suggestion:** Mild surprise combined with recognition. "Your autonomy ratio has been >100:1 for 4 weeks — would you like to switch your default view to Strategic Summary?" The system noticed the pattern before the operator consciously decided.
- **Clicking 'Yes':** Satisfaction + ownership. The operator realizes: "This relationship has fundamentally shifted. I'm no longer monitoring whether it works — I'm managing working infrastructure."

**Emotional Milestone:** The transition from "supervised tool" to "trusted infrastructure" becomes visible and operator-controlled.

### Critical Micro-Emotions

**1. Confidence vs. Confusion (MOST CRITICAL)**

This is the foundation emotion pair. Everything else flows from this. If every interaction increases confidence, trust follows naturally, satisfaction follows naturally, and the autonomy progression happens organically.

**Confidence is built through:**
- Unambiguous state presentation (green = healthy, yellow = attention needed, red = intervention required)
- Decision-ready context (no hunting through logs, no mental math, no ambiguity)
- Confirmed expectations (realized metrics match modeled projections, with variance clearly shown)
- Visible reasoning for automated decisions ("Why did you approve this match? Here's the logic.")

**Confusion undermines everything:**
- Any interaction that creates confusion — ambiguous state, unclear what happened, needing to investigate to understand current status — undermines all other emotional dimensions regardless of how well they're handled
- Confusion during a crisis moment (single-leg exposure) is especially damaging: anxiety can't convert to focused action if the operator doesn't understand the situation

**Design Principle:** Every UX decision must pass the "Does this increase or decrease confidence?" filter. If it creates any ambiguity or requires interpretation, it needs redesign.

**2. Autonomy vs. Dependence (SECOND MOST CRITICAL)**

The product thesis is about the operator's relationship with the system shifting over time. The system must feel like it's **expanding the operator's capability**, not replacing their judgment.

**Autonomy progression:**
- Month 1: Operator validates every decision ("Show me your reasoning, I'll verify it's correct")
- Month 3: Operator audits edge cases only ("Handle routine autonomously, escalate anomalies")
- Month 6: Operator manages strategic direction ("You handle operations, I'll focus on Phase 2 research")

**Anti-pattern — Dependence:**
- Operator feels like they've lost understanding of what the system is doing
- Black box decision-making without visible reasoning
- Inability to override or intervene when operator judgment differs from system logic
- System making choices that should belong to the operator (e.g., auto-changing default view without asking)

**Design Principle:** The operator is always in ultimate control. The system provides increasingly sophisticated automation, but transparency and override capability are always one click away.

**3. Satisfaction Over Delight**

This system is optimized for **satisfaction** (predictable reliability, confirmed expectations, "yep, as expected"), not **delight** (surprise, novelty, "wow moments").

**Satisfaction comes from:**
- 2-minute morning scan that takes 10 seconds because everything's green
- Metrics landing within expected ranges
- Automated decisions that match what operator would have chosen
- System doing what it said it would do

**Delight is not the goal:**
- Unexpected new features appearing = potential confusion, not positive surprise
- UI redesigns without operator initiation = violation of trust
- Gamification or celebration of routine operations = misaligned emotional model

**Critical Constraint: Never Surprise the Operator with Changes**

Predictability IS the product. The only acceptable surprise is operator-initiated (they choose to enable something). No silent changes:
- No A/B testing different UI behaviors
- No "we redesigned the dashboard" updates without explicit opt-in
- No features appearing without operator choosing to enable them
- No automatic parameter adjustments without notification

The dashboard the operator used yesterday should be the dashboard they use today, unless they chose to change it. Even the "switch to Strategic Summary default view" suggestion requires operator approval before changing anything.

### Design Implications for Emotional Goals

**To Create Calm Confidence:**

1. **Consistent, predictable visual language**
   - Green/yellow/red health composite never changes meaning
   - Layout stability: sections don't move, metrics don't relocate
   - Terminology consistency: "execution quality ratio" is always called that, never "fill efficiency" or "capture rate"

2. **Information clarity over visual excitement**
   - Data-dense terminal UI aesthetic (optimized for pattern recognition by expert users)
   - No animations on routine updates (P&L ticks don't flash or celebrate)
   - Functional typography and spacing, not decorative design elements

3. **"Everything's fine" state immediately obvious**
   - One-glance green composite confirmation
   - Summary metrics visible without scrolling
   - No interpretation required to answer "Is intervention needed?"

**To Enable Anxiety → Focused Action Conversion (Crisis Moments):**

1. **Complete decision-ready context on alert screen**
   - What happened (which leg filled, which didn't)
   - Current state (prices on both platforms, time elapsed)
   - Options available (retry, exit, hold)
   - Consequences visible (estimated P&L for each option)

2. **Clear visual hierarchy: Problem → Options → Decision**
   - Problem statement at top (impossible to miss)
   - Decision options with tap targets (no scrolling to find action buttons)
   - Consequences shown inline with each option

3. **Deep-linking eliminates navigation anxiety**
   - Telegram alert → tap → decision screen (not home page requiring navigation)
   - 2-second load target on cellular data
   - All context pre-loaded (no "Loading..." states during decision window)

**To Build Trust Through Transparency:**

1. **Reasoning on-demand for every automated decision**
   - Contract match approved at 97%? Click to see: "Resolution criteria align on 14/15 keywords, settlement dates identical, historical concordance 100%"
   - Opportunity filtered? Click to see: "Order book depth insufficient, slippage would exceed edge"

2. **Expected vs. actual metrics everywhere**
   - Execution quality ratio: 0.73 (vs. 0.75 ± 0.05 backtest)
   - Slippage: 0.4% realized (vs. 0.35% modeled)
   - Variance shown, not hidden

3. **Audit trails with full context**
   - Every decision logged with timestamp, inputs, reasoning, outcome
   - Operator can reconstruct "Why did the system do that?" for any action
   - Post-mortem analysis supported by complete event chains

**To Optimize for Satisfaction (Not Delight):**

1. **"As expected" confirmations, not surprising changes**
   - Morning scan shows green → satisfaction that system operated correctly overnight
   - Metrics within projected ranges → satisfaction that model is accurate
   - Routine operations don't generate notifications → satisfaction that system handles autonomously

2. **Milestone celebrations explicit, routine operations silent**
   - "48-hour test passed (2x)" badge → explicit recognition of trust milestone
   - 10th consecutive day of green morning scan → silent confirmation (no fanfare)
   - Contract match auto-approved at 96% → logged but not celebrated

3. **Predictability over novelty**
   - Same dashboard layout every day
   - Metrics in same locations
   - Navigation patterns stable
   - Only operator-initiated changes to interface or defaults

### Emotional Design Principles

**1. Confidence Over Everything**

Every UX decision must increase operator confidence, never create confusion. If a design choice requires interpretation, investigation, or creates ambiguity, it fails this principle regardless of other benefits.

**2. Operator Autonomy Is Sacred**

The system expands operator capability through increasingly sophisticated automation, but never replaces operator judgment. Transparency and override capability are always available. The operator is in ultimate control.

**3. Predictability IS the Product**

The dashboard used yesterday is the dashboard used today unless the operator chose to change it. No surprises, no silent updates, no A/B testing. Reliability through consistency.

**4. Anxiety Deserves Respect, Not Elimination**

Crisis moments create anxiety when real money is at stake. The UX doesn't pretend anxiety won't happen — it provides the fastest path from anxiety to informed decision. Complete context in 5 seconds.

**5. Satisfaction Through Confirmed Expectations**

Success isn't delight or surprise — it's the system doing exactly what it said it would do, exactly when it said it would do it, with results matching projections. Boring reliability is the highest praise.

**6. Trust Is Earned Through Visible Milestones**

The journey from "supervised tool" (Month 1) to "trusted infrastructure" (Month 6) is made visible through explicit milestones, autonomy ratio tracking, and operator-controlled default view shifts. The UX celebrates this progression.

## UX Pattern Analysis & Inspiration

### Inspiring Products Analysis

**Grafana: Dashboard-of-Dashboards for Operational Monitoring**

**What it does right:**
- **Information-dense panels that remain scannable:** Panels pack significant data (time-series charts, stat summaries, tables) without creating visual overwhelm. Clean visual hierarchy separates metric title, current value, and trend visualization.
- **Threshold visualization:** Charts show green/yellow/red zones inline — you see where a metric sits relative to its acceptable range instantly, without needing to remember "is 0.73 good or bad?" The threshold line provides context.
- **Drill-down from panel to full exploration:** Progressive disclosure pattern. Panel shows summary, click for full exploration view with extended time range, detailed breakdowns, and query customization.
- **Alerting integration shares data model:** Dashboard panels and alert notifications reference the same underlying queries. When an alert fires, the dashboard shows the same data. No divergence between "what Telegram says" and "what dashboard shows."

**Transferable patterns for pm-arbitrage-system:**
- Dashboard composed of information-dense panels (system health, P&L trend, execution quality, open positions, alerts)
- Threshold lines on metrics: execution quality ratio chart shows 0.7 target line, slippage chart shows modeled expectation band
- Click panel → full-screen drill-down with extended history and detailed breakdowns
- EventEmitter2 events feed both Telegram alerts and dashboard real-time updates (shared data model)

**Linear: Predictable, Stable Interface for Operational Work**

**What it does right:**
- **Nothing moves unless you move it:** Interface stability across sessions. Navigation structure, button locations, keyboard shortcuts remain constant. No A/B testing, no surprise reorganizations.
- **High information density without overwhelm:** Clean visual hierarchy through consistent spacing, typography weight, and color usage. Information-dense but scannable because patterns are predictable.
- **Keyboard shortcuts optimize common case:** Frequent actions (create issue, assign, change status) accessible via muscle-memory shortcuts. Reduces friction for repetitive workflows.
- **Status as first-class visual concept:** Issue status (backlog/in progress/done) immediately visible through consistent iconography and color. Scan a list and know state of everything without reading details.

**Transferable patterns for pm-arbitrage-system:**
- Interface layout stability: metrics stay in same locations, navigation doesn't reorganize
- Visual hierarchy through consistent spacing and typography (terminal UI aesthetic)
- Keyboard shortcuts for common actions (approve contract match, acknowledge alert, refresh data)
- System health status as first-class visual: green/yellow/red composite indicator visible before anything else

**Stripe Dashboard: Transparency Through Audit Trails**

**What it does right:**
- **Transaction detail as clean chronological timeline:** Each transaction shows event sequence: created → authorized → captured → settled. Timestamps for each step. Expandable detail shows full payload and metadata.
- **Event/webhooks view demonstrates audit trail transparency:** Every event logged with timestamp, event type, success/failure status, payload visible, retry attempts shown. Complete transparency into what happened and when.
- **Overview page provides key metrics without investigation:** Landing page shows critical summary metrics (volume, success rate, recent failures) without requiring drill-down to assess health.
- **"Everything's fine" state handled well:** When metrics are within expected ranges, overview confirms operational normalcy quickly. Green success rates, no failure spikes, recent activity looks routine.

**Transferable patterns for pm-arbitrage-system:**
- Execution log as chronological timeline: opportunity identified → risk validated → leg 1 submitted → leg 1 filled → leg 2 submitted → leg 2 filled, with timestamps and expandable detail
- Audit log view: every automated decision (contract match approved, opportunity filtered) logged with timestamp, inputs, reasoning, outcome
- Morning scan landing page: key summary metrics answer "is anything wrong?" without investigation
- "Everything's green" state immediately obvious through overview page design

### Transferable UX Patterns

**Pattern 1: Panel-Based Information Architecture (from Grafana)**

**Application:** Dashboard composed of scannable panels, each representing a domain (system health, performance, positions, alerts, activity log).

**Benefits:**
- Information density without overwhelm (each panel self-contained)
- Scannable at a glance during 2-minute morning ritual
- Progressive disclosure: panel summary → click → full-screen detail
- Flexible layout: operator can reorganize panels (not locked into rigid layout)

**Implementation:** React dashboard with panel components, each subscribing to relevant WebSocket events for real-time updates.

**Pattern 2: Threshold Visualization (from Grafana)**

**Application:** Time-series charts show not just metric values, but acceptable range context inline.

**Benefits:**
- Operator doesn't need to remember "is 0.73 good?" — chart shows 0.7 threshold line
- Visual at-a-glance answer: above threshold (green), approaching threshold (yellow), below threshold (red)
- Trends visible (moving toward or away from threshold over time)

**Implementation:** Execution quality ratio chart shows 0.7 target line, trailing 30-day actual values, variance band from backtest (0.75 ± 0.05). Slippage chart shows modeled expectation band.

**Pattern 3: Status as First-Class Visual (from Linear)**

**Application:** System health composite indicator visible before scrolling, before reading any text.

**Benefits:**
- Answers "is intervention needed?" in <1 second
- Color-coded (green = fine, yellow = attention, red = action) with consistent iconography
- Muscle memory: operator lands on dashboard, eyes go to top-left health composite immediately

**Implementation:** Persistent header component showing composite health status (API connectivity + execution engine + data feeds + platform health), updates via WebSocket.

**Platform Mode Badges:** Each platform tile in the header health bar displays a mode badge:
- **LIVE** — green badge, normal operation
- **PAPER** — amber badge with dotted border, paper trading active

Badge placement: inline after platform name (e.g., `Kalshi [LIVE]` · `Polymarket [PAPER]`). Badges are static — they reflect startup configuration and do not change at runtime.

**Paper Position Distinction:** Positions created via paper trading display with:
- Amber left-border accent (vs. default neutral border for live positions)
- `[PAPER]` tag after the pair name
- Paper positions are excluded from P&L summary totals by default (toggle to include)
- Filter toggle: All / Live Only / Paper Only

**Pattern 4: Chronological Event Timeline (from Stripe)**

**Application:** Execution log and audit log presented as timeline with expandable detail.

**Benefits:**
- Chronological narrative of "what happened" (critical for Moment 0 trust building)
- Expandable detail: summary shows key info, expand shows full payload/reasoning
- Post-mortem analysis: operator can reconstruct event chain for any trade

**Implementation:** Activity log panel shows recent events as timeline entries. Click event → full detail modal with timestamps, inputs, reasoning, outputs, related events linked.

**Pattern 5: Shared Data Model Between Alerts and Dashboard (from Grafana)**

**Application:** Telegram alerts and dashboard real-time updates consume same EventEmitter2 events.

**Benefits:**
- No divergence: alert says "execution quality 0.68", dashboard shows 0.68
- Operator trusts that alert content matches current dashboard state
- Single source of truth reduces confusion

**Implementation:** EventEmitter2 fan-out architecture already designed for this. Telegram integration and WebSocket gateway both subscribe to domain events (`execution.order.filled`, `risk.limit.approached`).

### Anti-Patterns to Avoid

**Anti-Pattern 1: Information Overload Without Hierarchy (Binance/Crypto Exchange Pattern)**

**Description:** Everything equally prominent. Flashing numbers, color changes on every tick, multiple competing attention demands. Charts, order books, recent trades, account balance, open orders, all shouting for attention simultaneously.

**Why it's wrong for pm-arbitrage-system:**
- Violates "calm confidence" emotional goal
- Creates anxiety through constant visual motion and color changes
- Makes "everything's fine" state indistinguishable from "intervention needed" state
- Optimizes for excitement and urgency, which we explicitly reject

**Design Principle:** Visual hierarchy must clearly separate "needs attention now" from "routine status." Critical alerts demand attention (Telegram + modal). Routine updates (P&L ticks, order book refreshes) update silently in background.

**Anti-Pattern 2: Oversimplified Dashboards That Hide Critical Information**

**Description:** Overly aggressive simplification where surface level shows only "✓ System Healthy" with no context. Requires 3-4 clicks through nested menus to understand actual state. Critical information hidden behind "Advanced" or "Details" sections.

**Why it's wrong for pm-arbitrage-system:**
- Violates "information density" design requirement
- Morning scan becomes investigation instead of confirmation
- Operator can't actually answer "is anything wrong?" without drilling down
- Treats operator like beginner instead of expert

**Design Principle:** Surface level must be genuinely informative. If "everything's green" truly means healthy, show the key metrics that prove it (uptime, execution quality, P&L trend, open position count). "One click for depth, zero clicks for confidence."

**Anti-Pattern 3: UI Changes Without Warning**

**Description:** Product updates that move buttons, rename features, reorganize navigation, or change keyboard shortcuts without operator control. A/B testing different layouts across sessions. "We redesigned the dashboard!" surprise updates.

**Why it's wrong for pm-arbitrage-system:**
- Violates "Predictability IS the Product" principle
- Breaks muscle memory during crisis moments (single-leg exposure alert on phone)
- Creates confusion ("where did the close position button go?")
- Undermines trust ("if the UI can change arbitrarily, what else is unpredictable?")

**Design Principle:** Interface stability is a feature, not a limitation. Layout, navigation, button locations, terminology stay constant across sessions. Only operator-initiated changes (reorganize panels, switch default view) modify interface. No silent updates, no A/B testing, no surprise redesigns.

**Anti-Pattern 4: Celebrating Routine Operations**

**Description:** Gamification of normal activity. Confetti animations when trade executes. "Streak" counters for consecutive profitable days. Achievement badges for operational milestones ("100 trades executed!"). Sound effects on every order fill.

**Why it's wrong for pm-arbitrage-system:**
- Violates "satisfaction over delight" principle
- Creates noise that desensitizes operator to genuine alerts
- Optimizes for engagement instead of operational efficiency
- Misaligned emotional model (excitement instead of calm confidence)

**Design Principle:** Routine operations are silent confirmations. 10th profitable trade in a row generates no fanfare — that's expected behavior. Milestone achievements (48-hour test passed, autonomy ratio threshold) get explicit recognition, but routine success is logged, not celebrated.

### Design Inspiration Strategy

**What to Adopt Directly:**

1. **Grafana's threshold visualization on charts**
   - Execution quality ratio, slippage, opportunity frequency charts all show acceptable range inline
   - Operator sees metric value and context (relative to target/model) simultaneously
   - Implementation: Chart component with configurable threshold lines and variance bands

2. **Linear's interface stability principle**
   - Layout doesn't change between sessions unless operator chooses
   - Metrics stay in same panel locations, navigation structure constant
   - Keyboard shortcuts documented and stable (no remapping without major version)

3. **Stripe's event timeline for audit trails**
   - Execution log and audit log presented as chronological timelines with expandable detail
   - Every event timestamped, full context preserved, related events linked
   - Implementation: Timeline component with expandable detail modals

**What to Adapt for This System:**

1. **Grafana's panel-based dashboard → Single-user customization**
   - Adopt panel-based architecture for information density and progressive disclosure
   - Adapt: Panels aren't shared/templated across users (no "team dashboards"). Operator customizes layout once, system preserves it.
   - Simplify: No complex query editor — panels show predefined metrics, drill-down shows extended history

2. **Linear's status concept → Multi-dimensional health composite**
   - Adopt: Status as first-class visual, immediately visible, consistent iconography
   - Adapt: Linear has single status dimension (backlog/in progress/done). This system needs composite health (API connectivity AND execution engine AND data feeds AND platform health).
   - Implementation: Health composite shows overall status (green/yellow/red) with drill-down showing per-component status

3. **Stripe's "everything's fine" overview → Confidence-building morning scan**
   - Adopt: Overview page answers "is intervention needed?" without investigation
   - Adapt: Stripe optimizes for transaction volume metrics. This system optimizes for trust progression and edge validation.
   - Implementation: Morning scan view shows: health composite, trailing 7-day P&L, execution quality vs. backtest, open positions count, active alerts, autonomy ratio (Month 3+)

**What to Avoid (Anti-Pattern Prevention):**

1. **Binance's attention-demand chaos**
   - No flashing numbers, no color changes on routine ticks, no competing attention demands
   - Visual motion reserved for critical alerts only (single-leg exposure modal)
   - Real-time updates are silent state changes, not animated events

2. **Oversimplified "healthy system" checkmarks**
   - Surface level must show key metrics, not just status icon
   - Drill-down provides depth, but surface provides genuine operational insight
   - "Everything's green" backed by visible confirmation (uptime 99.2%, execution quality 0.73, no red alerts)

3. **Surprise UI changes**
   - Interface stability documented as design principle, not implementation detail
   - Version updates don't reorganize layout, move buttons, or rename features without major version bump and operator opt-in
   - Predictability treated as core product value, not constraint

**This strategy ensures pm-arbitrage-system adopts battle-tested patterns from Grafana (information density + progressive disclosure), Linear (predictability + status visibility), and Stripe (audit transparency + "healthy state" confirmation) while avoiding the anti-patterns of crypto exchange chaos, oversimplification, and unpredictable interfaces.**

## Design System Foundation

### Design System Choice

**shadcn/ui** (Tailwind CSS + Radix Primitives)

shadcn/ui is not a traditional component library — it's a collection of copy-paste React components built on Tailwind CSS utilities and Radix UI primitives. Components are added to the project's source code directly, giving full ownership and control rather than depending on an external package that could introduce breaking changes or unwanted updates.

**Core Technology Stack:**
- **Tailwind CSS** — Utility-first CSS framework for precise control over spacing, typography, and responsive behavior
- **Radix UI Primitives** — Unstyled, accessible component foundations (alerts, modals, dropdowns, tooltips) that provide proper ARIA attributes and keyboard navigation
- **React 19.x** — Modern React with concurrent features for real-time dashboard updates
- **Vite** — Fast build tool optimized for single-page applications

### Rationale for Selection

**1. Component Ownership Enables Predictability**

The copy-paste model means components live in the project's source code, not in node_modules. This aligns with the **"Predictability IS the Product"** principle — there are no surprise component updates from an external maintainer, no framework version conflicts, no runtime behavior changes between deploys.

When the operator uses the dashboard on Monday morning, the interface is identical to Sunday evening *because the component code is under direct control*. Updates are explicit, opt-in decisions, not side effects of dependency updates.

**2. Tailwind Enables Terminal UI Aesthetic**

Utility-first CSS makes data-dense, functional layouts straightforward. The terminal UI aesthetic — monospace typography for metrics, tight spacing for information density, precise control over visual hierarchy — is easier to achieve with Tailwind's granular utilities than by overriding an opinionated component library's defaults.

**Examples:**
- Custom panel layouts with exact spacing (`space-y-2`, `gap-4`, `p-6`)
- Monospace metric displays (`font-mono`, `text-lg`, `tabular-nums`)
- Threshold visualization color zones (`bg-green-50`, `border-yellow-500`, `text-red-700`)
- Responsive breakpoints for mobile crisis paths (`sm:`, `md:`, `lg:` prefixes)

This supports the **"information clarity over visual excitement"** design implication from the emotional goals. No animations on routine updates, functional typography over decorative design, layout optimized for pattern recognition.

**3. Minimal Runtime Overhead for Mobile Performance**

No heavy framework runtime, no CSS-in-JS overhead, no component abstraction layers. Tailwind generates static CSS at build time. Radix provides minimal JavaScript for accessibility and interaction logic.

This matters for the **mobile-first critical paths** (single-leg exposure alert on cellular data). Fast initial load, fast time-to-interactive, predictable performance characteristics. The operator tapping a Telegram notification during a crisis moment gets the decision screen in <2 seconds even on cellular data.

**4. Radix Provides Accessibility Foundations**

Alerts, modals, tooltips, dropdowns need proper ARIA attributes, keyboard navigation, focus management. Radix handles this correctly while remaining unstyled — the visual presentation is entirely controlled via Tailwind classes.

Critical for:
- **Mobile crisis alerts:** Modal overlay for single-leg exposure with proper focus trap
- **Contract match review:** Tooltip showing full resolution criteria on hover/tap
- **Keyboard shortcuts:** Accessible dropdown menus for common actions

**5. Flexibility for Grafana-Style Patterns**

The panel-based dashboard architecture (inspired by Grafana) requires custom layouts that don't fit pre-built component library templates. shadcn/ui's utility-first approach makes this straightforward:

- Custom panel components with configurable layouts
- Threshold visualization charts with inline zones
- Drill-down modals with full-screen detail views
- Timeline components for execution logs (Stripe-inspired pattern)

Fighting an opinionated component library's layout constraints would slow development and produce compromises. Tailwind + custom components built for this exact use case is faster and cleaner.

### Implementation Approach

**Component Strategy:**

**1. Use shadcn/ui Components Where They Fit:**
- **Alert/AlertDialog** — Critical alerts (single-leg exposure modal, risk breach notifications)
- **Tooltip** — Contextual information on metrics (hover execution quality ratio → see definition)
- **DropdownMenu** — Action menus (contract match review options, position actions)
- **Badge** — Status indicators (health composite, milestone achievements)
- **Tabs** — View switching (monitoring view ↔ strategic summary view)

**2. Build Custom Components for Domain-Specific Needs:**
- **DashboardPanel** — Container component for Grafana-style panels with consistent spacing, borders, hover states
- **MetricDisplay** — Standardized metric presentation (value, label, trend indicator, threshold context)
- **ThresholdChart** — Time-series chart with green/yellow/red zones for threshold visualization
- **EventTimeline** — Stripe-inspired chronological event log with expandable detail
- **HealthComposite** — Multi-dimensional health indicator (API + engine + data feeds + platform status)
- **ContractMatchReview** — Side-by-side contract criteria comparison with highlighted differences

**3. Shared Design Tokens via Tailwind Config:**

Define system-wide tokens in `tailwind.config.js` for consistency:

```javascript
{
  colors: {
    // Health status palette
    status: {
      healthy: colors.green[500],
      warning: colors.yellow[500],
      critical: colors.red[500],
    },
    // Background hierarchy
    panel: colors.gray[50],
    surface: colors.white,
    // Terminal aesthetic
    mono: {
      primary: colors.gray[900],
      secondary: colors.gray[600],
      tertiary: colors.gray[400],
    }
  },
  fontFamily: {
    sans: ['Inter', 'system-ui', 'sans-serif'],
    mono: ['JetBrains Mono', 'Consolas', 'monospace'],
  },
  spacing: {
    // Panel spacing
    'panel-padding': '1.5rem',
    'panel-gap': '1rem',
  }
}
```

This ensures:
- Green always means healthy (never changes meaning)
- Monospace font is consistent across all metric displays
- Panel spacing matches Grafana-inspired information density
- Color palette supports terminal UI aesthetic (grays, minimal color for status only)

**4. Component Development Priority:**

Match implementation sequence from architecture document:

1. **Week 1-2:** Core layout and health composite (dashboard shell, header with status indicator)
2. **Week 3-4:** Panel system and basic metrics (P&L trend, execution quality, open positions)
3. **Week 5-6:** Alert components and mobile optimization (single-leg exposure modal, deep-linking)
4. **Week 7-8:** Timeline components and drill-down views (execution log, audit trail)
5. **Phase 1 ongoing:** Progressive enhancement (threshold charts, contract match review, milestone badges)

### Customization Strategy

**Terminal UI Aesthetic Through Tailwind:**

**1. Typography Hierarchy:**
- Metric values: `font-mono text-2xl tabular-nums` (monospace, large, aligned decimals)
- Metric labels: `font-sans text-sm text-gray-600` (sans-serif, small, muted)
- Panel titles: `font-sans text-lg font-semibold` (sans-serif, larger, bold)
- Body text: `font-sans text-base` (default readable text)

**2. Color Usage Discipline:**
- **Semantic only:** Green/yellow/red reserved for health status, never decorative
- **Grayscale primary:** Most UI uses gray scale for calm, non-distracting aesthetic
- **Accent minimal:** Color used sparingly to draw attention (critical alerts only)
- **No gradients, no shadows:** Flat design aligned with terminal aesthetic

**3. Spacing for Information Density:**
- Panel padding: `p-6` (1.5rem) — tight but not cramped
- Metric spacing: `space-y-2` (0.5rem) — scannable rows
- Panel gaps: `gap-4` (1rem) — clear separation without wasted space
- Mobile touch targets: Minimum `h-12 w-12` (3rem) — accessible tap zones

**4. Responsive Strategy:**
- **Desktop default:** Multi-column panel layout, information-dense
- **Tablet (md:):** Two-column layout, slightly larger touch targets
- **Mobile (sm:):** Single-column, ruthlessly prioritized (health composite + critical alerts + recent activity only)

**Component Customization Examples:**

**HealthComposite Component:**
```tsx
// Custom component using shadcn Badge + Tailwind utilities
<div className="flex items-center gap-2 font-mono">
  <Badge variant={status === 'healthy' ? 'success' : 'warning'}>
    {status}
  </Badge>
  <span className="text-sm text-gray-600">
    APIs: {apiStatus} | Engine: {engineStatus}
  </span>
</div>
```

**MetricDisplay Component:**
```tsx
// Data-dense metric presentation
// Note: Use semantic tokens (text-status-healthy/warning) in implementation,
// not hardcoded color values shown in this example
<div className="space-y-1">
  <div className="flex items-baseline justify-between">
    <span className="text-sm text-gray-600">Execution Quality</span>
    <span className={cn(
      "font-mono text-2xl tabular-nums",
      value >= 0.7 ? "text-status-healthy" : "text-status-warning"
    )}>
      {value.toFixed(2)}
    </span>
  </div>
  <ThresholdIndicator value={value} target={0.7} />
</div>
```

**Mobile Alert Modal (shadcn AlertDialog + custom content):**
```tsx
<AlertDialog open={alertActive}>
  <AlertDialogContent className="max-w-lg">
    <AlertDialogTitle className="text-status-critical">
      Single-Leg Exposure
    </AlertDialogTitle>
    <AlertDialogDescription className="space-y-4">
      <div className="font-mono text-sm">
        <p>Kalshi leg filled: 0.62</p>
        <p>Polymarket leg failed</p>
        <p className="text-status-critical">Est. loss if exit: 0.8%</p>
      </div>
      <div className="flex gap-2">
        <Button onClick={handleRetry}>Retry</Button>
        <Button variant="outline" onClick={handleExit}>Exit</Button>
      </div>
    </AlertDialogDescription>
  </AlertDialogContent>
</AlertDialog>
```

**Design Token Consistency:**

All custom components reference shared tokens from Tailwind config:
- `text-status-healthy` instead of hardcoded `text-green-500`
- `font-mono` defined once, used everywhere for metrics
- `panel-padding` and `panel-gap` spacing tokens ensure consistent density

This prevents drift where different components use different shades of green for "healthy" or different monospace fonts for metrics.

**Progressive Enhancement Path:**

- **Month 1:** Core components functional, terminal aesthetic established, information density correct
- **Month 3:** Refinements based on operator feedback — adjust spacing, improve threshold visualization clarity, optimize mobile tap targets
- **Month 6:** Polish milestone badges, trust progression UI elements, strategic summary view customization

The system prioritizes **functional over beautiful from day one**, then refines based on real usage patterns.
