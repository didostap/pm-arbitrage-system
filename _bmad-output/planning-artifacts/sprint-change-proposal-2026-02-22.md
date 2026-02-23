# Sprint Change Proposal — Epic 5 Retro Artifact Alignment

**Date:** 2026-02-22
**Triggered by:** Epic 5 Retrospective (2026-02-21)
**Scope Classification:** Minor — Direct Adjustment
**Facilitator:** Bob (Scrum Master)
**Participant:** Arbi (Project Lead / Tech Lead)

## Section 1: Issue Summary

The Epic 5 retrospective committed to Story 5.5.0 (Interface Stabilization & Test Infrastructure), a gas estimation story in Epic 6, and 3 process changes. None were reflected in planning artifacts (`epics.md`, `sprint-status.yaml`). Story 5.5.1 has a hard dependency on 5.5.0's deliverables — the decorator pattern requires a stable, frozen interface and centralized mock factories. Starting Epic 5.5 without this correction would break the dependency chain.

**Category:** Misalignment between retro commitments and planning artifacts.

**Evidence:**

- `sprint-status.yaml` listed Epic 5.5 with only Stories 5.5.1-5.5.3 (no 5.5.0)
- `epics.md` had no Story 5.5.0 section
- Retro document defined full Story 5.5.0 spec with 7 deliverables and explicit dependency chain
- Gas estimation TODO carried since Epic 2 with retro commitment to make it an Epic 6 story
- Sprint-status summary statistics were stale (retro count, story totals)

## Section 2: Impact Analysis

### Epic Impact

| Epic       | Impact     | Details                                                              |
| ---------- | ---------- | -------------------------------------------------------------------- |
| Epic 5.5   | **Direct** | Story 5.5.0 added as first story. Dependency: 5.5.0 → 5.5.1          |
| Epic 6     | **Direct** | Story 6.0 (gas estimation) added before Story 6.1                    |
| Epic 9     | Watched    | Interface freeze constrains how new `IRiskManager` methods are added |
| Epic 10    | Watched    | `resolutionDate` write path deferred here                            |
| All others | None       | No impact                                                            |

### Artifact Impact

| Artifact             | Change                                                                               | Status                                   |
| -------------------- | ------------------------------------------------------------------------------------ | ---------------------------------------- |
| `epics.md`           | Story 5.5.0 added, Story 6.0 added, summary entries updated                          | Applied                                  |
| `sprint-status.yaml` | Story 5.5.0 entry, Story 6.0 entry, summary statistics corrected, retro status fixed | Applied                                  |
| Architecture doc     | Reconciliation module location update                                                | Handled within Story 5.5.0 scope         |
| `gotchas.md`         | P&L source-of-truth rule                                                             | Handled within Story 5.5.0 scope         |
| `technical-debt.md`  | Mark resolved items, add Epic 5 items                                                | Handled within Story 5.5.0 scope         |
| Story template       | "Check gotchas.md" reminder                                                          | Skipped — revisit when gotchas.md exists |

### PRD Impact

- None. MVP scope unchanged. These are infrastructure and quality stories supporting the existing MVP path.

## Section 3: Recommended Approach

**Selected: Direct Adjustment** — modify/add stories within existing plan.

**Rationale:**

- The retro already designed the solution with explicit deliverables and dependency chains
- No rollback needed (Epic 5.5 hasn't started)
- No MVP scope change required
- Zero architectural risk — changes align with existing architecture doc
- Story-or-drop discipline (5 epics of evidence) demands these committed items become stories

**Alternatives considered:**

- Rollback: Not applicable — no completed work to revert
- MVP Review: Not needed — MVP scope unaffected

**Effort:** Low | **Risk:** Low | **Timeline impact:** None (prep work was already planned)

## Section 4: Detailed Change Proposals

### Applied Changes

**4.1 — Story 5.5.0 added to `epics.md`** (Approved)

- Full story spec with 7 acceptance criteria covering: `cancelOrder()` implementation, centralized mock factories, test file migration, gotchas.md creation, technical-debt.md update, architecture doc update, persistence coverage audit
- Sequencing constraint and interface freeze documented in story
- DoD gates from Epic 4.5 retro included
- Epic 5.5 summary entry updated

**4.2 — Story 6.0 (Gas Estimation) added to `epics.md`** (Approved)

- Full story spec with acceptance criteria covering: TODO removal, gas estimation logic, 20% safety buffer, paper trading calibration
- Technical debt provenance documented (Epic 2 carry-forward)
- Epic 6 summary entry updated

**4.3 — `sprint-status.yaml` updated** (Approved)

- `5-5-0-interface-stabilization-test-infrastructure: backlog` added
- `6-0-gas-estimation-implementation: backlog` added
- Total Stories: 55 → 57
- Total Items: 72 → 74
- Retrospectives done: 5 → 6, stale note removed

### Skipped Changes

**4.4 — Story template gotchas.md reminder** (Skipped)

- Rationale: gotchas.md doesn't exist yet. Revisit after Story 5.5.0 delivers it.

## Section 5: Implementation Handoff

**Scope:** Minor — direct implementation by dev team.

| Recipient              | Responsibility                                                                                  |
| ---------------------- | ----------------------------------------------------------------------------------------------- |
| **Scrum Master (Bob)** | Artifacts updated (this session). Create Story 5.5.0 file via CS workflow when Epic 5.5 begins. |
| **Dev agent**          | Implement Story 5.5.0 → 5.5.1 → 5.5.2 → 5.5.3 in sequence                                       |
| **Arbi (operator)**    | Approve story files as they're created. Monitor interface freeze compliance.                    |

**Success Criteria:**

- Story 5.5.0 merges with all 7 deliverables complete before 5.5.1 begins
- Interface freeze enforced after 5.5.0
- Gas estimation story picked up early in Epic 6

**Next Steps:**

1. Run Create Story [CS] workflow for Story 5.5.0 when ready to begin Epic 5.5
2. Story 5.5.2 spec review can happen during 5.5.0 development (parallel prep)
3. Story 5.5.3 spec review can happen during 5.5.1 development (parallel prep)

---

**Proposal Status:** Approved and applied
**Sprint Change Proposal Date:** 2026-02-22

---

---

# Sprint Change Proposal #2 — Kalshi Connector OrdersApi Type Safety Fix

**Date:** 2026-02-22
**Triggered by:** Story 5-5-0 (Interface Stabilization & Test Infrastructure) pre-implementation investigation
**Change Scope:** Minor
**Facilitator:** Bob (Scrum Master)
**Participant:** Arbi (Project Lead / Tech Lead)

## Section 1: Issue Summary

The Kalshi connector (`src/connectors/kalshi/kalshi.connector.ts`) has two interrelated type-safety issues caused by the `kalshi-typescript` SDK v3.6.0's incompatibility with the project's `moduleResolution: "nodenext"` TypeScript configuration:

1. **`OrdersApi` import fails (TS2305):** The SDK's barrel re-export chain (`index.d.ts → api.d.ts → api/orders-api.d.ts`) does not resolve under `nodenext`. Only `Configuration` and `MarketApi` are visible through the barrel — all other 14+ API classes are invisible to TypeScript. A type-unsafe workaround (`as unknown as KalshiOrdersApi` + eslint-disable + manually duplicated interface) was applied.

2. **`createOrder()` called on wrong API class:** The `submitOrder()` method calls `this.marketApi.createOrder(...)`, but `createOrder` is defined on `OrdersApi`, not `MarketApi`. This works at runtime by accident (SDK auto-generation artifact) but is architecturally incorrect and completely untyped.

**Evidence:**

- `npx tsc --noEmit` produces: `error TS2305: Module '"kalshi-typescript"' has no exported member 'OrdersApi'`
- SDK v3.6.0 has no `exports` field in `package.json` and uses extensionless relative specifiers in `.d.ts` barrels
- Runtime verification confirms `OrdersApi` is correctly exported (`require('kalshi-typescript').OrdersApi` → function)
- Direct subpath import `kalshi-typescript/dist/api/orders-api.js` resolves correctly under `nodenext` (verified via tsc)

## Section 2: Impact Analysis

### Epic Impact

| Epic                        | Impact         | Details                                                                                     |
| --------------------------- | -------------- | ------------------------------------------------------------------------------------------- |
| Epic 5.5 (Paper Trading)    | Minor          | Fix required before story 5-5-0 begins; 5-5-1 wraps real connectors and needs type-safe API |
| Epic 10 (Exits & Execution) | Future benefit | Stories 10-3, 10-4 will implement `cancelOrder`, batch orders via `OrdersApi`               |
| All other epics             | None           | No direct connector SDK usage                                                               |

### Story Impact

- **5-5-0 (Interface Stabilization):** Prerequisite fix — connector must have correct types before interface stabilization
- No other current or future stories require modification

### Artifact Conflicts

- **PRD:** No conflict
- **Architecture:** No conflict — `IPlatformConnector` interface boundary is correct; SDK usage is an implementation detail
- **UI/UX:** No conflict

### Technical Impact

- **Files affected:** `kalshi.connector.ts` (source), `kalshi.connector.spec.ts` (test — mock structure already correct, may need minor import adjustment)
- **Runtime behavior:** Unchanged — same SDK classes, same methods, same execution paths
- **Build:** Eliminates 1 TS2305 error from `tsc --noEmit`

## Section 3: Recommended Approach

**Selected: Direct Adjustment** — Modify the Kalshi connector to use a direct subpath import for `OrdersApi`, move `createOrder` to the correct API class, and remove all type-safety workarounds.

**Rationale:**

- Subpath import verified working under `nodenext` via `tsc --noEmit`
- Zero runtime risk — same underlying SDK class and methods
- Eliminates manual `KalshiOrdersApi` interface that can drift from the SDK
- Removes `eslint-disable` comment and `as unknown as` cast
- Low effort (~20 lines changed in single file)
- Necessary foundation before Epic 5.5 interface stabilization

**Alternatives considered:**

- Rollback: Not applicable — nothing to revert
- MVP Review: Not applicable — MVP unaffected
- Patching SDK `package.json` with `exports` field: Too fragile, overwritten on `pnpm install`

**Effort:** Low | **Risk:** Low | **Timeline impact:** None

## Section 4: Detailed Change Proposals

### Change 1: Fix OrdersApi Import (Approved)

```
File: src/connectors/kalshi/kalshi.connector.ts
Section: Imports

OLD:
import { Configuration, MarketApi, OrdersApi } from 'kalshi-typescript';

NEW:
import { Configuration, MarketApi } from 'kalshi-typescript';
import { OrdersApi } from 'kalshi-typescript/dist/api/orders-api.js';
```

### Change 2: Remove Workaround Interfaces, Fix Type and Cast (Approved)

```
File: src/connectors/kalshi/kalshi.connector.ts

REMOVE:
- KalshiOrderResponse interface (lines 27-37)
- KalshiOrdersApi interface (lines 40-42)

CHANGE field type:
  private readonly ordersApi: KalshiOrdersApi;
→ private readonly ordersApi: OrdersApi;

CHANGE constructor:
  // eslint-disable-next-line @typescript-eslint/no-unsafe-call
  this.ordersApi = new OrdersApi(config) as unknown as KalshiOrdersApi;
→ this.ordersApi = new OrdersApi(config);
```

### Change 3: Move createOrder to Correct API Class (Approved)

```
File: src/connectors/kalshi/kalshi.connector.ts
Section: submitOrder method

OLD:
  this.marketApi.createOrder({...})

NEW:
  this.ordersApi.createOrder({...})
```

## Section 5: Implementation Handoff

**Scope:** Minor — direct implementation by dev team.

| Recipient           | Responsibility                                                       |
| ------------------- | -------------------------------------------------------------------- |
| **Dev agent**       | Apply 3 edit proposals to `kalshi.connector.ts`, verify tests + lint |
| **Arbi (operator)** | Review and approve code changes                                      |

**Success Criteria:**

- `npx tsc --noEmit` no longer reports TS2305 for OrdersApi
- `pnpm test` passes (kalshi.connector.spec.ts green)
- `pnpm lint` clean
- No `eslint-disable` comments related to OrdersApi remain
- No manual `KalshiOrdersApi` or `KalshiOrderResponse` interfaces remain

**Timing:** Apply before starting story 5-5-0-interface-stabilization-test-infrastructure

---

**Proposal Status:** Approved — pending implementation
**Sprint Change Proposal Date:** 2026-02-22
