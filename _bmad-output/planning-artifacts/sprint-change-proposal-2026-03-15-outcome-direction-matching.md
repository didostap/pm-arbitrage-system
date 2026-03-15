# Sprint Change Proposal: Outcome Direction Validation in Contract Matching

**Date:** 2026-03-15
**Triggered by:** Operator dashboard review — 3 UFC Fight Night matches showing phantom APR >1500%
**Severity:** Critical (safety) — if executed, produces unhedged directional bets instead of arbitrage
**Scope:** Moderate — new story in Epic 10 pre-feature series, touches connectors + contract-matching + schema

---

## Section 1: Issue Summary

### Problem Statement

The contract matching pipeline (Epic 8) incorrectly matches Polymarket "Fighter A wins" contracts with Kalshi "Fighter B wins" contracts for head-to-head events (UFC fights, 1v1 matchups). The arbitrage detection engine then treats both as the same YES outcome, computing phantom edges of ~27-30% and APR projections of 1500%+.

If executed, these would be **unhedged directional bets** — the system loses both legs if the "wrong" participant wins. This violates the PRD's zero-tolerance policy on contract matching errors.

### Discovery Context

Identified during Epic 10 sprint while reviewing the matches table sorted by APR. Three UFC Fight Night matches (all March 21, 2026 resolution) displayed APR values 50-100x higher than other legitimate matches.

### Evidence

| Match ID | Polymarket YES = | Kalshi Contract | Kalshi YES = | Phantom Net Edge | Phantom APR |
|----------|-----------------|-----------------|-------------|-----------------|-------------|
| `339a6d3e` | Michael Page wins | `KXUFCFIGHT-26MAR21PAGPAT-PAT` | Sam Patterson wins | 27.15% | 1535% |
| `85b96578` | Louie Sutherland wins | `KXUFCFIGHT-26MAR21SUTPER-PER` | Brando Pericic wins | 29.75% | 1683% |
| `ec7aa3cb` | Luke Riley wins | `KXUFCFIGHT-26MAR21RILASW-ASW` | Michael Aswell wins | 28.99% | 1638% |

All confirmed via database queries + live platform price screenshots. The ~30% "edge" is simply the probability gap between favorite and underdog — not an arbitrage opportunity.

### Root Cause — 4-Layer Failure Chain

1. **Polymarket catalog** (`polymarket-catalog-provider.ts:173`): Always takes `clobTokenIds[0]` — blind to which outcome the token represents. Ignores the `outcomes` array from the API.
2. **Kalshi catalog** (`kalshi-catalog-provider.ts`): Returns separate contracts per participant (`-PAT`, `-PAG`) as independent entries with no side-linking metadata.
3. **TF-IDF pre-filter** (`candidate-discovery.service.ts`): Ranks both Kalshi sides equally — same event text means high cosine similarity for both the correct and incorrect contract.
4. **LLM scoring** (`llm-scoring.strategy.ts:65-84`): Prompt warns about outcome specificity but it's soft guidance, not a hard constraint. No downstream validation that auto-approved matches resolve YES for the same real-world outcome.

---

## Section 2: Impact Analysis

### Epic Impact

| Epic | Impact | Details |
|------|--------|---------|
| **Epic 10** (in-progress) | Direct | Fix story added to `10-0-x` pre-feature series |
| Epic 8 (done) | Origin | Bug introduced here, no reopening needed |
| Epic 11 (backlog) | Note | Story 11.1 connector plugin docs should cover multi-outcome token handling |
| Epics 1-9, 12 | None | No changes |

### Story Impact

- **New story:** `10-0-2b-outcome-direction-matching-validation` added to Epic 10
- **Sequencing:** Must complete before Story 10-1 (Continuous Edge Recalculation) which would amplify phantom edges
- **No existing stories modified** — fix is additive

### Artifact Conflicts

| Artifact | Impact | Action |
|----------|--------|--------|
| **PRD** | Restores compliance with FR-CM-02 and zero-tolerance matching policy | No text changes needed |
| **Architecture — Data model** | `ContractSummary` interface lacks outcome metadata, `contract_matches` table lacks outcome labels | Add `outcomeLabel`, `outcomeTokens` to interface; add migration for `polymarket_outcome_label`, `kalshi_outcome_label` |
| **Architecture — Validation** | No outcome direction validation exists between LLM scoring and auto-approve | Add post-scoring validation gate |
| **UX** | Match detail page doesn't surface outcome direction | Add outcome label display for operator verification |
| **Testing** | No test coverage for complementary-outcome detection | New test scenarios required |
| **Data** | 3 mis-matched UFC matches approved, 456 other matches need revalidation audit | Reject + full audit |

### Technical Impact

- **Files affected:** ~8-10 files across `connectors/polymarket/`, `connectors/kalshi/`, `modules/contract-matching/`, `common/interfaces/`, `prisma/schema.prisma`, `dashboard/`
- **Schema migration:** 1 new migration (2 nullable text columns)
- **No breaking changes** — all new fields are nullable/optional for backward compatibility

---

## Section 3: Recommended Approach

### Selected Path: Direct Adjustment (Option 1)

Add a single course correction story to Epic 10's pre-feature series.

### Rationale

- Bug is well-understood with clear 4-layer root cause
- Fix is contained — one story, no epic restructuring
- Zero trades executed on phantom opportunities (`total_cycles_traded = 0` for all 3)
- Fix strengthens the pipeline for ALL future head-to-head markets (elections, sports, 1v1 competitions)
- Low risk to existing correct matches — validation is additive
- Fits naturally into `10-0-x` series alongside existing debt/fix stories

### Effort & Risk

- **Effort:** Medium — 8-10 files, one migration, new validation logic + full audit
- **Risk:** Low — additive changes, existing correct matches unaffected
- **Timeline:** No delay to Epic 10 feature stories — this slots into the pre-feature series

---

## Section 4: Detailed Change Proposals

### CP-1: ContractSummary Interface — Add Outcome Metadata

**File:** `common/interfaces/contract-catalog-provider.interface.ts`

Add `outcomeLabel?: string`, `outcomeTokens?: OutcomeToken[]` to `ContractSummary`. New `OutcomeToken` interface with `tokenId` + `outcomeLabel`. This is the foundational data model gap — all downstream fixes depend on this metadata.

### CP-2: Polymarket Catalog Provider — Store All Tokens With Outcome Labels

**File:** `connectors/polymarket/polymarket-catalog-provider.ts:159-176`

Parse the `outcomes` JSON array (currently ignored) alongside `clobTokenIds`. Pair each token ID with its outcome label. Populate `outcomeTokens[]` and `outcomeLabel` on the returned `ContractSummary`. Requires API verification that the `outcomes` field is present on the market response.

### CP-3: Kalshi Catalog Provider — Extract Outcome Label

**File:** `connectors/kalshi/kalshi-catalog-provider.ts`

Extract outcome direction from Kalshi market metadata (`yes_sub_title` or similar field — needs API verification). Populate `outcomeLabel` on `ContractSummary`. The ticker suffix (`-PAT`, `-PAG`) is a fallback signal if no explicit API field exists.

### CP-4: Post-Scoring Outcome Direction Validation

**File:** `modules/contract-matching/candidate-discovery.service.ts` (~line 302-340)

Insert validation gate between LLM scoring and auto-approve. If both `outcomeLabel` values are available and indicate opposite participants in a head-to-head event:
- **Self-correct** by finding the matching Polymarket token from `outcomeTokens[]` if available
- **Downgrade to manual review** if self-correction not possible (cap score at 50, add `divergence_notes`)

This is the critical safety gate.

### CP-5: Schema Migration — Persist Outcome Direction

**File:** `prisma/schema.prisma` + new migration

Add nullable columns `polymarket_outcome_label` (text) and `kalshi_outcome_label` (text) to `contract_matches`. Enables audit queries, operator verification on dashboard, and historical tracking.

### CP-6: Data Cleanup + Full Revalidation Audit

**Phase A — Immediate:** Reject the 3 confirmed mis-matched UFC pairs. Null out phantom APR/edge values.

**Phase B — Full audit of all 459 approved matches:**

1. **Automated — Outcome label extraction:** LLM pass over all match descriptions to extract and compare outcome direction. Flag any `aligned: false | uncertain`.
2. **Automated — Complementary price check:** For matches with active order books, compute `polyBestAsk + kalshiBestAsk`. If ≈ 1.00 (±0.05), contracts are likely complementary — flag.
3. **Manual review queue:** All flagged matches set to pending with explanation. Operator must re-approve or reject.
4. **Halt trading on flagged matches immediately** — exclude from detection cycle while review is pending.
5. **Acceptance gate:** Story not done until all 459 audited, zero flagged matches remain in approved status without re-review, results documented.

---

## Section 5: Implementation Handoff

### Scope Classification: Moderate

Requires both development work (new story) and backlog adjustment (SM/PO sequencing).

### Handoff Plan

| Role | Responsibility |
|------|---------------|
| **Scrum Master** | Add story `10-0-2b` to sprint-status.yaml, sequence before `10-0-2` |
| **Developer (dev agent)** | Implement story via TDD workflow: CP-1 through CP-6 |
| **Operator** | Review flagged matches from Phase B audit, re-approve or reject |

### Success Criteria

1. All 3 confirmed mis-matched UFC pairs are rejected
2. Full revalidation audit completed with results documented
3. Post-scoring outcome direction validation gate is active
4. New head-to-head market discoveries are correctly matched (or flagged for review)
5. No phantom edges >10% appear in the matches table without legitimate price dislocation
6. All new code has co-located test coverage following TDD

### Sprint Status Update

```yaml
# Add to Epic 10 section:
10-0-2b-outcome-direction-matching-validation: ready-for-dev
# Sequence: 10-0-1 (done) → 10-0-2b (NEW, next up) → 10-0-2a → 10-0-2 → 10-0-3
```
