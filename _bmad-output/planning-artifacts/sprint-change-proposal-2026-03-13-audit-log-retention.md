# Sprint Change Proposal: Audit Log Retention & Pruning

**Date:** 2026-03-13
**Triggered by:** Operational observation — unbounded audit_logs table growth
**Current Sprint:** Epic 9 (Advanced Risk & Portfolio Management)
**Scope Classification:** Minor — direct implementation by dev team

---

## 1. Issue Summary

The `audit_logs` table grows without bound. `EventConsumerService` logs all domain events (except `monitoring.audit.*`) to `AuditLogService`, producing one insert per event with SHA-256 hash chaining (`previous_hash` → `current_hash`). No pruning, archiving, or retention policy exists.

**Evidence:**
- Epic 7.5.2 documented "133K+ rows and growing" and added a btree index to cope
- `verifyChain()` scans the entire table — cost scales linearly with row count
- Dashboard audit trail queries (position detail filtered by `pairId` in JSONB) are affected by table bloat even with the btree index, due to vacuum, backup, and index maintenance costs
- Current phase is pre-revenue paper/early-live trading — indefinite retention adds operational cost with no compliance benefit yet

**Context:** The system was built with 7-year retention as a long-term compliance requirement (NFR-S3, NFR-R5). However, 7-year retention is a Phase 1+ concern (Epic 12). Current phase only needs recent history for debugging and operations.

---

## 2. Impact Analysis

### Epic Impact

| Epic | Impact | Detail |
|------|--------|--------|
| **Epic 9** (current) | Add story | New course correction story 9-6. No disruption to existing stories (9-2 through 9-4). |
| **Epic 12** | Precondition | Story 12.2 (on-demand audit trail export, 7-year window) gets precondition: "Requires 7-year retention enabled." |
| All others | None | No other epics touch audit log storage mechanics. |

### Artifact Conflicts

| Artifact | Section | Conflict | Resolution |
|----------|---------|----------|------------|
| **PRD** | NFR-S3 | "7-year retention" stated unconditionally | Add phase qualifier: "7-year retention applies from Phase 1+ (Epic 12). Current phase uses configurable short retention (default 7 days)." |
| **PRD** | NFR-R5 | "7-year retention" stated unconditionally | Same phase qualifier. |
| **PRD** | FR-DE-04 | "any period within 7-year window" | Add precondition: "Requires 7-year retention to be enabled (Phase 1+)." |
| **Architecture** | Audit Log Architecture | Describes append-only with no mention of retention phases | Add retention-phase annotation: current-phase pruning behavior, chain head semantics after pruning, transition to indefinite retention in Phase 1+. |

### Technical Impact

- **Hash chain:** Pruning removes rows referenced by `previous_hash` of retained rows. No code change needed — `verifyChain()` already walks from the first row found. After pruning, the oldest retained row is the de-facto chain head. Verification covers the retained window only; this is documented, not a defect.
- **Dashboard:** Position detail audit trail queries recent data for open/recently-closed positions. 7-day retention more than covers any position the operator would view.
- **Hot path:** Zero impact — pruning runs on a daily cron schedule, not in the execution path.

---

## 3. Recommended Approach

**Selected: Direct Adjustment** — add a single course correction story to Epic 9.

### Rationale

- Smallest possible change that solves the problem — one new service, one config var, one cron job
- No rollback of existing work, no scope reduction, no epic restructuring
- Follows established course correction pattern (9-1a, 9-1b, 9-5)
- Future-proof: `AUDIT_LOG_RETENTION_DAYS=0` disables pruning, enabling seamless transition to 7-year retention when Epic 12 arrives

### Alternatives Considered

| Alternative | Why Not |
|-------------|---------|
| **Rollback** (remove audit logging) | Disproportionate — loses compliance capability entirely. The feature works; it just needs a retention policy. |
| **MVP scope reduction** | Not applicable — MVP was completed at Epic 7. |
| **Archive-then-delete** | Adds complexity (archive storage, restore logic) with no current benefit. When 7-year retention is needed, the system retains from that point forward. |
| **Event type whitelist** | Reduces write volume but adds configuration surface and risks silently dropping useful debugging events. Can be layered on later if volume remains a concern after pruning is in place. |

### Effort & Risk

- **Effort:** Low — single service, one env var, daily cron, straightforward tests
- **Risk:** Low — pruning old rows has no effect on active trading, dashboard, or the hot path
- **Timeline impact:** None — can be implemented in parallel with 9-2

---

## 4. Detailed Change Proposals

### 4.1 New Story: 9-6-audit-log-retention-pruning

**Story:** Add configurable audit log retention with daily pruning to bound storage growth.

Full story to be created via the Create Story workflow.

**Key acceptance criteria (preview):**
- `AUDIT_LOG_RETENTION_DAYS` config (default 7, 0 = keep forever)
- `AuditLogRetentionService` with `@Cron` daily pruning — deletes rows older than retention window
- `verifyChain()` documented to verify retained window only (oldest retained row = chain head)
- `monitoring.audit.pruned` event emitted with pruned row count
- Tests: pruning logic, config validation (0 disables), chain verification post-pruning

### 4.2 PRD Annotation Updates

**NFR-S3:**

```
OLD:
NFR-S3: Complete audit trail for all trades, 7-year retention, tamper-evident

NEW:
NFR-S3: Complete audit trail for all trades, tamper-evident. 7-year retention applies from Phase 1+ (Epic 12); current phase uses configurable short retention (default 7 days) to bound storage.
```

**NFR-R5:**

```
OLD:
NFR-R5: All snapshots/executions logged with microsecond timestamps, 7-year retention

NEW:
NFR-R5: All snapshots/executions logged with microsecond timestamps. 7-year retention applies from Phase 1+ (Epic 12); current phase uses configurable short retention.
```

**FR-DE-04:**

```
OLD:
FR-DE-04 [Phase 1]: On-demand audit trail export for any period within 7-year window

NEW:
FR-DE-04 [Phase 1]: On-demand audit trail export for any period within 7-year window. Precondition: 7-year retention must be enabled (Epic 12).
```

### 4.3 Architecture Annotation Update

**Audit Log Architecture paragraph — append after existing text:**

```
NEW (append):
Retention policy is phase-dependent. Current phase: configurable retention window
(AUDIT_LOG_RETENTION_DAYS, default 7 days). A daily cron job prunes rows older than
the retention window. After pruning, the oldest retained row serves as the chain head
for hash verification — verifyChain() walks from the first row found, so no code
change is needed. Setting retention to 0 disables pruning, enabling indefinite
retention for Phase 1+ compliance (Epic 12, NFR-S3).
```

### 4.4 Epics Update

Add story 9-6 entry under Epic 9 in `epics.md`.

---

## 5. Implementation Handoff

**Scope:** Minor — direct implementation by dev team.

| Role | Responsibility |
|------|---------------|
| **SM** | Finalize this proposal, update sprint-status.yaml, update epics.md with story entry |
| **Dev agent** | Implement story 9-6 via Create Story → TDD workflow |
| **SM/PO** | Apply PRD and Architecture annotation edits (text-only, no structural changes) |

**Success criteria:**
- `audit_logs` table holds at most ~N days of data when retention is enabled
- Storage no longer grows unbounded
- `verifyChain()` works correctly on retained window
- Setting `AUDIT_LOG_RETENTION_DAYS=0` preserves current behavior (no pruning)
- All existing tests pass, no regressions
