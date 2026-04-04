# Sprint Change Proposal: Epic 10.95 Retro Materialization

**Date:** 2026-04-13
**Triggered by:** Epic 10.95 retrospective — 4 new agreements (#31-34), 10 action items, 13-item debt ledger, slot-zero enforcement
**Scope Classification:** Moderate
**Status:** Approved

---

## 1. Issue Summary

Epic 10.95 retrospective produced actionable process and artifact changes that must be codified before Epic 10.96 development begins. Key findings:

- Two structural guard items (configService type-safety, route prefix validation) slipped two consecutive epics (10.9 → 10.95)
- Previous retro follow-through dropped to 3/6 (below 100% standard)
- Deferred debt ledger grew net +7 (6 → 13 items)
- Four new agreements ratified to prevent recurrence

These must be materialized into CLAUDE.md, sprint-status.yaml, and epics.md before the dev agent starts Epic 10.96.

---

## 2. Impact Analysis

### Artifacts Modified

| Artifact | Change Type |
|----------|-------------|
| CLAUDE.md | Add Agreements #31-34 to Process Conventions; extend #27 in Story Design Conventions |
| sprint-status.yaml | Add slot-zero story 10-96-0; add debt ledger section; fix stale summary statistics |
| epics.md | Add Epic 10.96 section with 5 stories (0-4); update Epic 11 prerequisites |

### No Impact On

- PRD (fixes align with existing FRs)
- Architecture (no structural changes)
- UI/UX (no user-facing changes)
- Code (artifact-only changes)

---

## 3. Recommended Approach

**Direct Adjustment** — discrete, additive edits to 3 existing files.

All changes are well-defined by the retro output. No ambiguity, no code changes, no rollback needed.

---

## 4. Changes Applied

### 4a. CLAUDE.md — Agreements #31-34

Added to Process Conventions section after Agreement #30:
- **#31** Mid-epic discovery split rule (3+ unplanned outside core concern → new epic number)
- **#32** Diagnostic sweep gate for discovery cascades (sweep after first quality-category fix)
- **#33** Debt budget per epic — net zero or negative (force conversation at planning time)
- **#34** Agreement enforcement at sprint planning slot zero (mechanical, not discretionary)

### 4b. CLAUDE.md — Design Sketch Gate #27 Extended

Extended to cover porting stories: sketch must specify implementation site and service boundary. Decomposition designed into story AC, not discovered during review.

### 4c. Sprint-Status — Slot-Zero Story

Added `10-96-0-structural-guards-configservice-route-prefix` as first story in Epic 10.96 (before 10-96-1). Resolves debt items #1, #2, #3. Agreement #34 enforcement.

### 4d. Sprint-Status — Debt Ledger

Added 13-item debt ledger section before summary statistics. Murat owns tracking. Budget: net zero or negative per Agreement #33. Items 1-3 resolved in slot zero.

### 4e. Sprint-Status — Statistics

Fixed stale counts: 158 total stories, 11 backlog (5 in 10.96, 3 in 11, 3 in 12), 0 ready-for-dev, 154 done through Epic 10.95.

### 4f. Epics.md — Epic 10.96 Section

Added full epic section with 5 stories:
- 10-96-0: Structural guards (slot zero)
- 10-96-1: Entry-fee-aware exit PnL & percentage stop-loss
- 10-96-2: Max edge cap & entry liquidity filters
- 10-96-3: Post-TIME_DECAY re-entry cooldown
- 10-96-4: Configuration defaults calibration

### 4g. Epics.md — Epic 11 Prerequisites

Updated to include Epic 10.96 as hard sequencing gate.

---

## 5. Implementation Handoff

**Scope:** Moderate — artifact updates complete. No code changes.

| Recipient | Next Step |
|-----------|-----------|
| Winston (Architect) | Produce design sketches for 10-96-1, 10-96-2, 10-96-3 |
| Bob (SM) | Create story files when design sketches are ready |
| Quinn (QA) | Verify slot-zero is first in sprint plan |
| Murat (Test Architect) | Confirm debt ledger baseline |

**Arbi's directive:** If Agreements #31-34 aren't earning their keep by the 10.96 retro, they get cut.
