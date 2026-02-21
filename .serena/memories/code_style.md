# Code Style & Conventions

## Naming Conventions
| Context | Convention | Example |
|---------|-----------|---------|
| Files | kebab-case | `risk-manager.service.ts` |
| Classes/Interfaces | PascalCase | `IRiskManager`, `KalshiConnector` |
| Functions/variables | camelCase | `validatePosition`, `currentExposure` |
| Constants | UPPER_SNAKE_CASE | `MAX_POSITION_SIZE` |
| DB tables | snake_case (Prisma @map) | `contract_matches`, `audit_logs` |
| DB columns | snake_case (Prisma @map) | `confidence_score`, `created_at` |
| API URLs | kebab-case | `/api/contract-matches` |
| API JSON fields | camelCase | `confidenceScore` |
| Events | dot-notation | `execution.order.filled` |

## File Organization
- Imports grouped: external, internal, relative
- One class per file (except small DTOs/interfaces)
- Co-locate tests: `risk-manager.service.ts` → `risk-manager.service.spec.ts` (same directory)
- E2E tests in `test/` directory

## TypeScript Patterns
- **Always check array access:** `const item = array[0]; if (item) { ... }` (noUncheckedIndexedAccess)
- **Remove unused imports immediately** (noUnusedLocals)
- **Ensure all function branches return values** (noImplicitReturns)
- **Prefer async/await** over .then() chains
- **Error handling:** Always extend SystemError hierarchy, NEVER throw raw `Error`

## NestJS Patterns
- **Module-based architecture:** Each feature is a self-contained NestJS module
- **Dependency Injection:** Via interfaces in `common/interfaces/` — modules never import other module services directly
- **DTOs:** Use class-validator decorators for validation
- **Repository pattern:** Database access through Prisma repositories in `persistence/repositories/`
- **Logging:** NestJS Logger (via nestjs-pino), NOT console.log. Structured JSON with correlationId.
- **Configuration:** `@nestjs/config` with validated environment variables
- **Events:** EventEmitter2 for async fan-out (monitoring, alerts). NEVER block execution.
- **Guards:** `AuthTokenGuard` for Bearer token auth on operator API endpoints

## Communication Patterns
- **Hot path (synchronous DI):** Detection → Risk validation → Execution (blocking is correct)
- **Fan-out (async EventEmitter2):** All modules emit events → Monitoring subscribes (never block execution)

## Financial Math Rules
- ALL monetary calculations MUST use `decimal.js` Decimal: `.mul()`, `.plus()`, `.minus()`, `.div()`
- NEVER use native JS `*`, `+`, `-`, `/` on monetary values
- Prisma Decimal → decimal.js: `new Decimal(value.toString())`
