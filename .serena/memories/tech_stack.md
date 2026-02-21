# Technology Stack

## Runtime & Framework
- **Node.js** runtime
- **NestJS 11** framework with **Fastify** adapter (`@nestjs/platform-fastify`)
- **TypeScript 5.7+** (strict mode)

## Key strictness flags
- `noUncheckedIndexedAccess` — array access returns `T | undefined`
- `noUnusedLocals`, `noUnusedParameters`
- `noImplicitReturns`
- `strictNullChecks`

## Database
- **PostgreSQL 16+**
- **Prisma 6** ORM (schema-first approach)
- Development port: 5433 | Production port: 5432

## Key Dependencies
| Package | Version | Purpose |
|---------|---------|---------|
| `@nestjs/*` | ^11.x | Core framework |
| `@nestjs/event-emitter` | ^3.0 | EventEmitter2 async events |
| `@nestjs/schedule` | ^6.1 | Cron/interval scheduling |
| `@nestjs/config` | ^4.0 | Typed configuration |
| `@prisma/client` | 6 | Database ORM |
| `decimal.js` | ^10.6 | Financial math (NEVER use native JS operators) |
| `kalshi-typescript` | ^3.6 | Kalshi REST SDK |
| `@polymarket/clob-client` | ^5.2 | Polymarket CLOB SDK |
| `viem` | ^2.45 | Polymarket on-chain interactions |
| `ws` | ^8.19 | WebSocket clients |
| `nestjs-pino` + `pino-http` | ^4.1 / ^11.0 | Structured JSON logging |
| `ntp-time-sync` | ^0.5 | NTP synchronization |
| `js-yaml` | ^4.1 | YAML config parsing |
| `class-validator` + `class-transformer` | ^0.14 / ^0.5 | DTO validation |
| `uuid` | ^13.0 | UUID generation |

## Testing
- **Vitest 4** test framework + `unplugin-swc` for decorator metadata
- **fast-check** ^4.5 for property-based testing
- **@golevelup/ts-vitest** for NestJS mock utilities
- **@nestjs/testing** for module-level testing
- Co-located test files (`.spec.ts` next to source)
- E2E tests in `test/` directory
- Target coverage: >80% on critical paths

## Package Manager
- **pnpm** (NOT npm or yarn)

## Containerization
- Docker + Docker Compose
- `docker-compose.dev.yml` — PostgreSQL only
- `docker-compose.yml` — Full stack

## Code Quality
- **ESLint 9** with `eslint-config-prettier`
- **Prettier 3**
- **class-validator** for DTO validation
