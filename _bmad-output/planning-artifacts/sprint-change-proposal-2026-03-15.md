# Sprint Change Proposal — Epic 9 Retro Integration

**Date:** 2026-03-15
**Trigger:** Epic 9 Retrospective (complete document)
**Scope Classification:** Moderate
**Mode:** Incremental (all 11 proposals reviewed individually)

## Section 1: Issue Summary

Epic 9 retrospective identified critical prerequisites, process commitments, and technical debt that must be formalized into planning artifacts before Epic 10 story creation can begin. The retro documented:

- **8 action items** (process improvements, tech debt, documentation, Epic 10 prep)
- **28 tech debt items** (8 new from Epic 9 + 20 carry-forward from prior epics)
- **6 new team agreements** (#18-#23)
- **4 critical-path pre-Epic 10 blockers** (WebSocket subscriptions, debt triage, exit monitor architecture review, sprint-status update)
- **4 new watched items** (#10-#13)

**Core problem:** Epic 10 ("Model-Driven Exits & Advanced Execution") as currently defined in the epics document has critical prerequisites not yet met, needs process changes baked into story design, needs architectural decisions formalized, and needs capacity budgeting per new team agreements.

**Evidence:** Epic 9 delivered 26/26 stories (4.3x scope expansion from 6 planned), 380 new tests, 60+ code review findings. 20 course corrections were handled reactively. The retro's central insight: preventive planning is better than reactive correction.

## Section 2: Impact Analysis

### Epic Impact

**Epic 10 (Model-Driven Exits & Advanced Execution):**
- Cannot be completed as originally planned
- Add 3 pre-epic stories (10-0-1, 10-0-2, 10-0-3)
- Modify ACs for all 4 existing stories (10.1-10.4)
- Document 30-40% correction capacity budget (Agreement #22)

**Epic 11 (Platform Extensibility):**
- Minor ripple to Story 11.1 — `IPlatformConnector` interface expanded by Epic 10, plugin documentation must cover new WebSocket methods

**Epic 12 (Compliance & Reporting):**
- No impact

### Story Impact

| Story | Change Type | Summary |
|-------|------------|---------|
| 10-0-1 (NEW) | Add | WebSocket subscription establishment + divergence monitoring |
| 10-0-2 (NEW) | Add | Carry-forward debt triage + 3 critical fixes (SingleLegContext, realizedPnl, resolutionDate) |
| 10-0-3 (NEW) | Add | Exit monitor architecture review spike |
| 10.1 | Modify ACs | WebSocket data path for exits, dashboard edge display, polling fallback |
| 10.2 | Modify ACs | Explicit dependencies (resolutionDate, realizedPnl), criteria proximity display, shadow mode comparison table, paper/live boundary, internal verification |
| 10.3 | Modify ACs | SingleLegContext dependency, paper/live divergent behavior, auto-unwind dashboard display, internal verification |
| 10.4 | Modify ACs | Divergence monitoring for depth data, conservative depth selection, execution detail display, WebSocket dependency |
| 11.1 | Add note | IPlatformConnector expansion awareness |

### Artifact Conflicts

| Artifact | Impact | Changes |
|----------|--------|---------|
| epics.md | High | 3 new stories, 4 modified stories, 1 note addition, capacity budget, architecture decision |
| sprint-status.yaml | Medium | 3 new story entries, updated statistics, capacity budget comment |
| architecture.md | Medium | Dual data path communication pattern, IPlatformConnector interface expansion (+2 methods), data flow diagram update |
| CLAUDE.md | Medium | 6 new conventions (3 testing, 3 story design) from Epic 9 retro |
| PRD | None | No conflicts — FRs unchanged, MVP complete |
| UX spec | Low | 6 new dashboard surfaces implied by vertical slice ACs — covered in story-level ACs rather than spec update |

### Technical Impact

- `IPlatformConnector` interface gains `subscribeToContracts()` and `unsubscribeFromContracts()` — all connector implementations must update
- Dual data path architecture: polling (entry) + WebSocket (exit) with divergence monitoring
- 3 schema/data model changes in 10-0-2: `SingleLegContext` interface, `realized_pnl` column, `resolution_date` write path
- No infrastructure or deployment changes

## Section 3: Recommended Approach

**Selected: Option 1 — Direct Adjustment**

Add pre-epic stories within Epic 10, modify existing story ACs, update supporting artifacts. This follows the established pattern (Epic 3 sprint-0, Epic 9-0-1/9-0-2) and addresses the retro's central finding: preventive planning over reactive correction.

**Alternatives considered and rejected:**
- **Rollback:** Nothing to revert — Epic 9's work is correct and tested
- **MVP/Scope Review:** MVP complete, Phase 1 FRs unchanged and deliverable

**Rationale:**
1. Pattern consistency with 9 prior epics
2. Prevention over reaction (retro's core recommendation)
3. Bounded scope — 3 well-defined pre-epic stories
4. Low risk — additive changes, no rollbacks, no resequencing
5. Retro integrity — executing on commitments the team made

**Effort:** Medium — 3 pre-epic stories + artifact updates
**Risk:** Low — established patterns, bounded scope
**Timeline:** Pre-epic stories add ~1 sprint equivalent before feature work begins

## Section 4: Detailed Change Proposals

### Proposal 1: epics.md — Add Pre-Epic 10 Stories
- Add capacity budget note and architecture decision at epic level
- Add Story 10-0-1: WebSocket Subscription Establishment & Divergence Monitoring
- Add Story 10-0-2: Carry-Forward Debt Triage & Critical Fixes (SingleLegContext, realizedPnl, resolutionDate)
- Add Story 10-0-3: Exit Monitor Architecture Review (Spike)
- Full ACs defined with dependencies, vertical slice surfaces, and tech debt notes

### Proposal 2: epics.md — Modify Story 10.1
- Add WebSocket data path for exit decisions (primary) with polling fallback
- Add dashboard surface: recalculated edge, delta, data source indicator, staleness
- Add `platform.data.fallback` event for WS unavailability
- Add explicit dependencies on 10-0-1 and 10-0-3

### Proposal 3: epics.md — Modify Story 10.2
- Make resolutionDate and realizedPnl dependencies explicit (criterion #3, P&L tracking)
- Add dashboard surface: criteria proximity display, exit mode indicator
- Add shadow mode comparison table on performance page
- Add paper/live boundary testing mandate (Agreement #20)
- Add internal subsystem verification mandate (Agreement #19)
- Add explicit dependencies on 10-0-1, 10-0-2, 10-0-3

### Proposal 4: epics.md — Modify Story 10.3
- Add SingleLegContext dependency (resolved in 10-0-2)
- Add detailed paper/live divergent behavior (simulated vs real fills)
- Add dashboard surface: auto-unwind status, action, result, loss
- Add internal verification: test that unwind orders reach connector
- Add dependency on 10-0-2

### Proposal 5: epics.md — Modify Story 10.4
- Add divergence monitoring for depth data between poll/WS paths
- Add conservative depth selection when paths disagree
- Add dashboard surface: sequencing decision, latency, matched vs ideal count
- Add internal verification for connector interaction
- Add dependency on 10-0-1

### Proposal 6: sprint-status.yaml — Update Epic 10
- Add 3 pre-epic story entries with inline context comments
- Add capacity budget comment (Agreement #22)
- Update totals: 93→96 stories, 4→7 backlog
- Update CURRENT status line

### Proposal 7: architecture.md — Dual Data Path
- Add third communication pattern bullet: dual data path with divergence monitoring
- Documents polling (entry) vs WebSocket (exit) authority split

### Proposal 8: architecture.md — IPlatformConnector
- Add `subscribeToContracts(contractIds: ContractId[]): Promise<void>`
- Add `unsubscribeFromContracts(contractIds: ContractId[]): Promise<void>`

### Proposal 9: architecture.md — Data Flow Diagram
- Split diagram into ENTRY PATH (polling) and EXIT PATH (WebSocket)
- Update execution notes for Epic 10.4 matched-count model
- Add divergence monitoring annotation

### Proposal 10: CLAUDE.md — Epic 9 Conventions
- 3 testing conventions: internal subsystem verification, paper/live boundary, investigation-first
- 3 story design conventions: vertical slice minimum, compiler-driven migration, dual data path divergence

### Proposal 11: epics.md — Epic 11.1 Note
- Interface awareness note: IPlatformConnector expanded by Epic 10, documentation must cover WebSocket methods

## Section 5: Implementation Handoff

**Change scope: Moderate** — Backlog reorganization + artifact updates needed before story creation.

**Handoff plan:**

| Recipient | Responsibility | Deliverable |
|-----------|---------------|-------------|
| Bob (SM) | Apply all 11 edit proposals to planning artifacts | Updated epics.md, sprint-status.yaml, architecture.md, CLAUDE.md |
| Bob (SM) | Create story files for 10-0-1, 10-0-2, 10-0-3 via Create Story workflow | Story files in implementation-artifacts/ |
| Alice (PO) | Review and approve modified Epic 10 scope + capacity budget | Sign-off on 7-story base + 30-40% correction buffer |
| Charlie + Winston | Implement 10-0-1 (WebSocket subscriptions) | Working subscriptions + divergence monitoring |
| Charlie | Implement 10-0-2 (debt triage + critical fixes) | Triage doc + SingleLegContext + realizedPnl + resolutionDate |
| Winston | Implement 10-0-3 (architecture review spike) | ThresholdEvaluatorService design document |
| Dana | Paper/live boundary test suite inventory (parallel) | isPaper branch coverage report |

**Success criteria:**
- All 11 edit proposals applied to artifacts
- Pre-epic stories (10-0-1, 10-0-2, 10-0-3) created and ready-for-dev
- Epic 10 feature stories (10.1-10.4) reflect retro commitments in ACs
- CLAUDE.md conventions available to dev agent before implementation begins

**Execution order:**
1. Apply artifact edits (this session, after approval)
2. Create story files for 10-0-1, 10-0-2, 10-0-3 (SM Create Story workflow)
3. Begin implementation: 10-0-1 → 10-0-2 → 10-0-3 (sequential, each informs next)
4. Feature stories after all pre-epic stories complete

---

**Proposal Status:** Awaiting approval
**Artifacts to modify:** 4 (epics.md, sprint-status.yaml, architecture.md, CLAUDE.md)
**Edit proposals:** 11 (all reviewed in Incremental mode)
