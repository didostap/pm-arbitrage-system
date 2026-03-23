---
stepsCompleted:
  - step-01-preflight-and-context
  - step-02-generation-mode
  - step-03-test-strategy
  - step-04c-aggregate
  - step-05-validate-and-complete
lastStep: step-05-validate-and-complete
lastSaved: '2026-03-22'
storyId: '10-5-2'
storyName: 'Settings CRUD Endpoints & Hot-Reload Mechanics'
detectedStack: backend
generationMode: ai-generation
executionMode: sequential
inputDocuments:
  - _bmad-output/implementation-artifacts/10-5-2-settings-crud-endpoints-hot-reload-mechanics.md
  - _bmad/tea/testarch/knowledge/data-factories.md
  - _bmad/tea/testarch/knowledge/component-tdd.md
  - _bmad/tea/testarch/knowledge/test-quality.md
  - _bmad/tea/testarch/knowledge/test-healing-patterns.md
  - _bmad/tea/testarch/knowledge/test-levels-framework.md
  - _bmad/tea/testarch/knowledge/test-priorities-matrix.md
---

# ATDD Checklist: Story 10-5-2 — Settings CRUD Endpoints & Hot-Reload Mechanics

## TDD Red Phase (Current)

All tests generated with `it.skip()` — they will fail until the feature is implemented.

### Test Files Generated

| # | File | Tests | Priority Coverage |
|---|------|-------|-------------------|
| 1 | `src/common/config/settings-metadata.spec.ts` | 9 | P0: 2, P1: 7 |
| 2 | `src/dashboard/settings.service.spec.ts` | 16 | P0: 3, P1: 13 |
| 3 | `src/dashboard/dto/update-settings.dto.spec.ts` | 25 | P0: 7, P1: 18 |
| 4 | `src/dashboard/dto/reset-settings.dto.spec.ts` | 5 | P1: 5 |
| 5 | `src/dashboard/settings.controller.spec.ts` | 9 | P0: 2, P1: 5, P2: 2 |
| 6 | `src/dashboard/settings.gateway.spec.ts` | 3 | P1: 2, P2: 1 |
| 7 | `src/dashboard/settings-reload.spec.ts` | 14 | P0: 3, P1: 11 |
| 8 | `src/dashboard/settings-audit-backfill.spec.ts` | 3 | P1: 3 |
| **Total** | **8 files** | **84** | **P0: 17, P1: 64, P2: 3** |

### TDD Red Phase Validation

- [x] All 84 tests use `it.skip()` (TDD red phase)
- [x] No placeholder assertions (`expect(true).toBe(true)`)
- [x] All tests assert EXPECTED behavior
- [x] Full test suite passes: 2450 passed, 81 skipped, 0 failures
- [x] Lint clean: 0 errors

## Acceptance Criteria Coverage

| AC | Description | Test File(s) | Test Count |
|----|-------------|-------------|------------|
| AC 1 | GET /api/dashboard/settings | settings.service.spec, settings.controller.spec | 5 |
| AC 2 | PATCH /api/dashboard/settings | settings.service.spec, settings.controller.spec, update-settings.dto.spec | 13 |
| AC 3 | POST /api/dashboard/settings/reset | settings.service.spec, settings.controller.spec, reset-settings.dto.spec | 8 |
| AC 4 | Settings Metadata Registry | settings-metadata.spec | 9 |
| AC 5 | Hot-Reload Mechanism | settings.service.spec | 4 |
| AC 6 | Service Refactoring — DB-Backed Config Reads | settings-reload.spec | 14 |
| AC 7 | WebSocket Broadcast | settings.gateway.spec | 3 |
| AC 8 | Audit Logging | settings.service.spec, settings-audit-backfill.spec | 6 |
| AC 9 | Validation DTOs | update-settings.dto.spec, reset-settings.dto.spec | 30 |
| AC 10 | Tests (meta — all above) | All files | 84 |

## Test Level Distribution

| Level | Count | Purpose |
|-------|-------|---------|
| Unit (metadata) | 9 | SETTINGS_METADATA completeness, type validity, constraint parity |
| Unit (service) | 16 | CRUD orchestration, hot-reload dispatch, event emission, audit |
| Unit (DTO validation) | 30 | class-validator decorators, range/type/enum validation |
| Unit (controller) | 9 | Endpoint routing, response wrappers, ValidationPipe behavior |
| Unit (gateway) | 3 | WS broadcast on event, payload shape |
| Unit (per-service reload) | 14 | reloadConfig() per service, cron/interval hot-reload safety |
| Unit (audit backfill) | 3 | Bankroll update audit log creation |

## Fixture Needs (for Green Phase)

- `buildMockEffectiveConfig()` — mock of all 71 EffectiveConfig fields
- `buildMockSettingsMetadata()` — mock SETTINGS_METADATA registry entries
- Mock services: RiskManagerService, TelegramAlertService, ExitMonitorService, ExecutionService, DataIngestionService
- Mock SchedulerRegistry for cron/interval hot-reload tests
- Mock AuditLogRepository for audit logging tests

## Next Steps (TDD Green Phase)

After implementing Story 10-5-2:

1. Remove `it.skip()` from test files **one group at a time** (implement → unskip → verify green)
2. Recommended implementation order:
   - Task 1: `SETTINGS_METADATA` → unskip `settings-metadata.spec.ts`
   - Task 2: `UpdateSettingsDto` + `ResetSettingsDto` → unskip DTO specs
   - Task 3: `SettingsService` → unskip `settings.service.spec.ts`
   - Task 4: Controller endpoints → unskip `settings.controller.spec.ts`
   - Task 5: Events + WS → unskip `settings.gateway.spec.ts`
   - Task 6: Service `reloadConfig()` methods → unskip `settings-reload.spec.ts`
   - Task 8: Bankroll audit backfill → unskip `settings-audit-backfill.spec.ts`
3. Run `pnpm test` after each unskip group
4. Run `pnpm lint` after all changes
5. Commit passing tests

## Implementation Guidance

### Endpoints to Implement

| Method | Path | DTO | Purpose |
|--------|------|-----|---------|
| GET | `/api/dashboard/settings` | — | Return all 71 settings grouped by 15 sections |
| PATCH | `/api/dashboard/settings` | `UpdateSettingsDto` | Partial update with validation + hot-reload |
| POST | `/api/dashboard/settings/reset` | `ResetSettingsDto` | Reset specific or all keys to NULL (env fallback) |

### Files to Create

| File | Purpose |
|------|---------|
| `src/common/config/settings-metadata.ts` | `SETTINGS_METADATA` registry + `SettingsGroup` enum |
| `src/dashboard/dto/update-settings.dto.ts` | PATCH validation DTO (71 optional fields) |
| `src/dashboard/dto/reset-settings.dto.ts` | Reset validation DTO (keys array) |
| `src/dashboard/settings.service.ts` | Settings CRUD orchestration + hot-reload dispatch |

### Key Patterns (from bankroll precedent)

```
Controller → Service.updateSettings(dto)
  → snapshot previous config
  → engineConfigRepository.upsert(fields)
  → hot-reload affected services (per SERVICE_RELOAD_MAP)
  → auditLogRepository.create(...)
  → eventEmitter.emit(CONFIG_SETTINGS_UPDATED, event)
  → return new grouped settings
```
