---
stepsCompleted:
  - step-01-preflight-and-context
  - step-02-generation-mode
  - step-03-test-strategy
  - step-04c-aggregate
  - step-05-validate-and-complete
lastStep: step-05-validate-and-complete
lastSaved: '2026-03-22'
storyId: '10-5-1'
storyName: 'EngineConfig Schema Expansion & Seed Migration'
inputDocuments:
  - _bmad-output/implementation-artifacts/10-5-1-engine-config-schema-expansion-seed-migration.md
  - _bmad/tea/testarch/knowledge/data-factories.md
  - _bmad/tea/testarch/knowledge/test-quality.md
  - _bmad/tea/testarch/knowledge/test-healing-patterns.md
  - _bmad/tea/testarch/knowledge/test-levels-framework.md
  - _bmad/tea/testarch/knowledge/test-priorities-matrix.md
---

# ATDD Checklist: Story 10-5.1 — EngineConfig Schema Expansion & Seed Migration

## TDD Red Phase (Current)

All 39 failing tests generated with `it.skip()`.

| Test File | Tests | P0 | P1 | P2 |
|---|---|---|---|---|
| `src/persistence/repositories/engine-config.repository.spec.ts` | 17 new | 8 | 6 | 3 |
| `src/common/config/config-defaults.spec.ts` | 12 | 4 | 5 | 3 |
| `prisma/seed-config.spec.ts` | 10 | 6 | 2 | 2 |
| **Total** | **39** | **18** | **13** | **8** |

E2E Tests: 0 (story has no new endpoints or UI — deferred to 10-5-2/10-5-3)

## Acceptance Criteria Coverage

| AC | Description | Test File | Coverage |
|---|---|---|---|
| AC3 | `getEffectiveConfig()` method | `engine-config.repository.spec.ts` | All-DB, all-NULL fallback, mixed, Decimal→string, bankroll inclusion, single read |
| AC5 | Repository expansion | `engine-config.repository.spec.ts` | `upsert()` partial updates, field isolation, backward compat `upsertBankroll()` |
| AC6 | Env var fallback mapping | `config-defaults.spec.ts` | 71-field completeness, bankrollUsd mapping, structure, Zod key alignment, no dupes |
| AC8 | Seed script | `seed-config.spec.ts` | NULL-only seeding, idempotency, fresh install, boolean transform, paperBankroll exclusion |
| AC9 | Decimal round-trip | `engine-config.repository.spec.ts`, `seed-config.spec.ts` | string → Prisma.Decimal → string |
| AC1 | Prisma schema expansion | Compile-time (Prisma generate) | Verified by mock data structure in tests |
| AC4 | EffectiveConfig type | Compile-time (TypeScript) | Import in repository spec |
| AC7 | Migration | Manual verification | `pnpm prisma migrate dev` |
| AC10 | No consumer changes | `engine-config.repository.spec.ts` | Existing tests preserved unchanged |

## Generated Files

### Test Files (TDD RED)
- `pm-arbitrage-engine/src/persistence/repositories/engine-config.repository.spec.ts` — Expanded with 17 new `it.skip()` tests (5 existing tests preserved)
- `pm-arbitrage-engine/src/common/config/config-defaults.spec.ts` — NEW: 12 `it.skip()` tests
- `pm-arbitrage-engine/prisma/seed-config.spec.ts` — NEW: 10 `it.skip()` tests

### No Fixtures Needed
Backend unit tests use `vi.fn()` mocks — no shared fixtures required.

## Next Steps (TDD Green Phase)

After implementing the feature:

1. Remove `it.skip()` from all 39 new tests
2. Run tests: `cd pm-arbitrage-engine && pnpm test`
3. Verify tests PASS (green phase)
4. If any tests fail:
   - Fix implementation (feature bug) OR
   - Fix test (test bug — unlikely since tests match story ACs)
5. Run `pnpm lint` — zero errors
6. Commit passing tests

## Implementation Guidance

### Files to Create
| File | Purpose |
|---|---|
| `src/common/config/effective-config.types.ts` | `EffectiveConfig` interface + `EngineConfigUpdateInput` type |
| `src/common/config/config-defaults.ts` | `CONFIG_DEFAULTS` mapping (DB field → env key → default) |
| `prisma/seed-config.ts` | Seed script for populating DB from env vars |

### Files to Modify
| File | Change |
|---|---|
| `prisma/schema.prisma` | Add ~71 nullable columns to EngineConfig model |
| `src/persistence/repositories/engine-config.repository.ts` | Add `getEffectiveConfig()`, `upsert()` |
| `package.json` | Add `prisma:seed-config` script |

### Execution Report
- Execution Mode: SUBAGENT (API + E2E parallel)
- Unit Test Generation: Worker A (subagent)
- E2E Assessment: Worker B (subagent) — determined no E2E tests needed
- Performance: ~50% faster than sequential
