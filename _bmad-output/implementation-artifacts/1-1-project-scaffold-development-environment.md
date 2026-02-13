# Story 1.1: Project Scaffold & Development Environment

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want a deployable NestJS project with Docker Compose (PostgreSQL + engine),
So that I have a working development and deployment foundation.

## Acceptance Criteria

**Given** the repository is cloned and dependencies installed
**When** I run `docker-compose up`
**Then** PostgreSQL starts and the NestJS engine connects to it
**And** `GET /api/health` returns 200 with `{ data: { status: "ok" }, timestamp: "<ISO8601>" }`

**Given** a pull request is opened
**When** CI pipeline runs
**Then** lint, test, and build all pass
**And** Vitest runs with unplugin-swc for decorator metadata support

**Given** the project is scaffolded
**When** I inspect the directory structure
**Then** it matches the architecture's module organization (`src/modules/`, `src/connectors/`, `src/common/`, `src/core/`)
**And** Prisma is initialized with an empty schema ready for migrations
**And** environment variables are loaded via `@nestjs/config` from `.env.development`
**And** README.md contains setup instructions for running the project locally

## Tasks / Subtasks

- [x] Task 1: Initialize NestJS project with Fastify (AC: All)
  - [x] Run `npx @nestjs/cli@latest new pm-arbitrage-system --strict --package-manager pnpm`
  - [x] Swap Express for Fastify adapter
  - [x] Add core dependencies (Prisma 6, viem, Vitest, unplugin-swc)
- [x] Task 2: Configure Docker Compose (AC: 1)
  - [x] **FIRST:** Check port 5432 availability and select appropriate host port
  - [x] Create `docker-compose.yml` with PostgreSQL 16+ and engine services
  - [x] Create `docker-compose.dev.yml` for local development (postgres only)
  - [x] Create Dockerfile for NestJS engine
  - [x] Configure health checks and networking
- [x] Task 3: Set up Prisma ORM (AC: 1, 3)
  - [x] Initialize Prisma with PostgreSQL provider
  - [x] Create empty schema foundation
  - [x] Configure connection string via environment variables
- [x] Task 4: Implement /api/health endpoint (AC: 1)
  - [x] Create health controller with proper response format
  - [x] Validate database connectivity
- [x] Task 5: Configure Vitest with decorators (AC: 2)
  - [x] Set up `vitest.config.ts` with unplugin-swc
  - [x] Configure SWC for decorator metadata
  - [x] Add example test file
- [x] Task 6: Set up CI/CD pipeline (AC: 2)
  - [x] Create GitHub Actions workflow
  - [x] Configure lint, test, build steps
- [x] Task 7: Organize directory structure (AC: 3)
  - [x] Create `src/modules/` for core modules
  - [x] Create `src/connectors/` for platform integrations
  - [x] Create `src/common/` for shared code
  - [x] Create `src/core/` for engine lifecycle

## Dev Notes

### Project Foundation Context

This is **Story 1.1** - the absolute first implementation story for the entire project. The repository currently has only one commit ("chore: initial"). This story establishes the complete development foundation that all subsequent stories will build upon.

**🔴 CRITICAL: Repository Structure**

This project uses **separate repositories** per the architecture document:

- `pm-arbitrage-engine/` — NestJS backend (THIS STORY)
- `pm-arbitrage-dashboard/` — React SPA (Epic 7, separate repo)

**Important:**

- This story scaffolds the **engine repository only** as a standalone project
- Do NOT create a monorepo or workspace wrapper
- Do NOT create a dashboard directory inside the engine repo
- The `docker-compose.yml` lives in the engine repo for MVP
- Epic 7 will create the dashboard as a separate repository
- Dashboard container will be added to docker-compose.yml in Epic 7 (pulling from published image or sibling path)

**Critical Foundation Elements:**

- NestJS 11.x as the application framework (NOT Express-based starters)
- Fastify adapter for 2-3x performance vs Express
- PostgreSQL 16+ (NOT SQLite as mentioned in early PRD versions)
- Prisma 6.x as the ORM (type-safe, migration-ready)
- Vitest 4.x with SWC transform for decorators (NOT Jest)
- Docker Compose for local development and deployment
- Strict TypeScript configuration
- pnpm as package manager

### Architecture Alignment

**Tech Stack (from Architecture Decision Document):**

| Layer      | Technology       | Version       | Why                                                             |
| ---------- | ---------------- | ------------- | --------------------------------------------------------------- |
| Language   | TypeScript       | 5.x (strict)  | Event loop model, Ethereum/Polygon SDK ecosystem                |
| Runtime    | Node.js          | LTS           | Single-threaded event loop for sequential execution             |
| Framework  | NestJS + Fastify | 11.x / 11.1.x | Module system maps to 5-module architecture, DI for testability |
| ORM        | Prisma           | 6.x           | Type-safe queries, migrations, PostgreSQL support               |
| Database   | PostgreSQL       | 16+           | Query power for Phase 1, 7-year retention, replaces SQLite      |
| Blockchain | viem             | Latest stable | TypeScript-native Polygon transactions                          |
| Testing    | Vitest           | 4.x           | Native TypeScript, Jest-compatible, faster execution            |

**Official Initialization Command (from Architecture):**

```bash
# 1. Scaffold NestJS project
npx @nestjs/cli@latest new pm-arbitrage-system --strict --package-manager pnpm

# 2. Swap to Fastify adapter
pnpm add @nestjs/platform-fastify @nestjs/config
pnpm remove @nestjs/platform-express

# 3. Add core dependencies
pnpm add prisma@6 @prisma/client@6 viem
pnpm add -D vitest unplugin-swc @swc/core @golevelup/ts-vitest
```

### Directory Structure Requirements

**Target Structure (from Architecture):**

**Note:** This is the `pm-arbitrage-engine/` repository structure. The dashboard is a separate repository (Epic 7).

```
pm-arbitrage-engine/
├── src/
│   ├── modules/          # Feature modules (5 core modules from PRD)
│   │   ├── data-ingestion/
│   │   ├── arbitrage-detection/
│   │   ├── execution/
│   │   ├── risk-management/
│   │   └── monitoring/
│   ├── connectors/       # Platform integrations
│   │   ├── kalshi/
│   │   └── polymarket/
│   ├── common/           # Shared cross-cutting code
│   │   ├── interfaces/
│   │   ├── errors/
│   │   ├── events/
│   │   └── config/
│   ├── core/             # Engine lifecycle, scheduler
│   ├── main.ts
│   └── app.module.ts
├── prisma/
│   └── schema.prisma
├── test/                 # E2E tests
├── docker-compose.yml
├── Dockerfile
├── vitest.config.ts
├── .env.development
└── .env.example
```

**Module Organization Pattern:**

- Feature-based modules matching PRD's 5 core modules
- Platform connectors isolated in `connectors/`
- Shared code in `common/` (NO generic `utils/` directory)
- Tests co-located with source files (`*.spec.ts`)

### API Response Format (from Architecture)

**Health Endpoint Contract:**

```typescript
// Success Response
{
  "data": {
    "status": "ok"
  },
  "timestamp": "2026-02-11T10:30:00.000Z"
}

// Error Response (if database down, per Architecture error format)
{
  "error": {
    "code": 4001,  // SystemHealthError code from architecture
    "message": "Database connection failed",
    "severity": "critical"
  },
  "timestamp": "2026-02-11T10:30:00.000Z"
}
```

### Docker Compose Architecture

**Three-Service Design (from Architecture):**

1. `postgres` - PostgreSQL 16+ database
2. `engine` - NestJS trading engine
3. `dashboard` - React SPA (Epic 7, separate repository)

**For Story 1.1:** Implement postgres + engine only. Dashboard service will be added to docker-compose.yml in Epic 7 when the separate dashboard repository is created.

**Docker Compose Files:**

- `docker-compose.yml` - Full stack (postgres + engine + dashboard when added)
- `docker-compose.dev.yml` - Development override (postgres only, engine runs locally via `pnpm dev`)

**For Story 1.1:** Create both files. The dev compose allows running postgres in Docker while developing engine locally with hot reload.

**Docker Configuration Requirements:**

- PostgreSQL 16+ official image
- Health checks on both services
- Volume mount for PostgreSQL data persistence
- Environment variable injection for credentials
- Network isolation (all services on same Docker network)

### 🚨 CRITICAL: Port Conflict Handling

**BEFORE configuring Docker Compose, check port 5432 availability:**

```bash
# Check if port 5432 is in use
lsof -i :5432
# OR
ss -tlnp | grep 5432
```

**If port 5432 is occupied** (common when local PostgreSQL is installed):

1. **Select next available port:** 5433, 5434, 5435, etc.
2. **Update ALL references consistently:**
   - `docker-compose.yml` → `ports: ["5433:5432"]` (host:container)
   - `docker-compose.dev.yml` → `ports: ["5433:5432"]`
   - `.env.development` → `DATABASE_URL="postgresql://postgres:password@postgres:5433/..."`
   - `.env.example` → `DATABASE_URL="postgresql://postgres:password@postgres:5433/..."`
3. **Container-internal port stays 5432** — only the host mapping changes

**Example with port 5433 (if 5432 occupied):**

```yaml
# docker-compose.dev.yml
services:
  postgres:
    image: postgres:16
    ports:
      - '5433:5432' # Host port 5433, container port 5432
    environment:
      POSTGRES_DB: pmarbitrage
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ['CMD-SHELL', 'pg_isready -U postgres']
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

**Corresponding .env.development:**

```env
# If using host port 5433
DATABASE_URL="postgresql://postgres:password@postgres:5433/pmarbitrage?schema=public"
```

**Default assumption (if port 5432 is free):**

```yaml
ports:
  - '5432:5432' # Standard mapping when no conflict
```

Then run: `docker-compose -f docker-compose.dev.yml up` for local dev.

### Environment Variable Strategy

**Configuration Approach (from Architecture):**

- `.env.development` - Non-sensitive config (ports, polling intervals, feature flags)
- `.env.production` - Production config (same structure, different values)
- Docker secrets (production) - Sensitive credentials mounted as files

**MVP (Story 1.1) Environment Variables:**

```env
# Application
NODE_ENV=development
PORT=8080  # Per architecture: 8080 (not 3000)

# Database
DATABASE_URL="postgresql://postgres:password@postgres:5432/pmarbitrage?schema=public"
# Note: host is "postgres" (Docker Compose service name), not "localhost"

# (Kalshi, Polymarket credentials added in later stories)
```

### Testing Configuration - Critical Details

**Vitest + Decorator Metadata Challenge:**

NestJS uses TypeScript decorators heavily (`@Injectable()`, `@Module()`, etc.). These decorators rely on `reflect-metadata` and emit decorator metadata at compile time. **Vitest does NOT support decorator metadata out of the box.**

**Solution: unplugin-swc**

The `unplugin-swc` package provides SWC transformation for Vitest, which properly handles decorator metadata:

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config';
import swc from 'unplugin-swc';

export default defineConfig({
  test: {
    globals: true,
    root: './',
  },
  plugins: [
    swc.vite({
      module: { type: 'es6' },
    }),
  ],
});
```

**Required Dependencies:**

- `vitest` - Test runner
- `unplugin-swc` - SWC plugin for Vitest
- `@swc/core` - SWC compiler
- `@golevelup/ts-vitest` - NestJS testing utilities for Vitest

**Test File Example:**

```typescript
// app.controller.spec.ts
import { Test, TestingModule } from '@nestjs/testing';
import { AppController } from './app.controller';
import { AppService } from './app.service';

describe('AppController', () => {
  let appController: AppController;

  beforeEach(async () => {
    const app: TestingModule = await Test.createTestingModule({
      controllers: [AppController],
      providers: [AppService],
    }).compile();

    appController = app.get<AppController>(AppController);
  });

  it('should return health status', () => {
    expect(appController.getHealth()).toHaveProperty('status');
  });
});
```

### CI/CD Pipeline (GitHub Actions)

**Workflow Requirements:**

1. Trigger on PR and push to main
2. Run on Ubuntu latest
3. Set up Node.js LTS with pnpm
4. Install dependencies
5. Run lint (`pnpm lint`)
6. Run tests (`pnpm test`)
7. Run build (`pnpm build`)

**Example `.github/workflows/ci.yml`:**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v2
        with:
          version: 8
      - uses: actions/setup-node@v4
        with:
          node-version: 'lts/*'
          cache: 'pnpm'
      - run: pnpm install
      - run: pnpm lint
      - run: pnpm test
      - run: pnpm build
```

### Prisma Initialization

**Minimal Schema Foundation:**

```prisma
// prisma/schema.prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

// Placeholder model for initial migration (required for Prisma to generate migration)
// This will be removed in Story 1.4 when real tables are added
model SystemMetadata {
  id        String   @id @default(cuid())
  key       String   @unique
  value     String
  createdAt DateTime @default(now()) @map("created_at")
  updatedAt DateTime @updatedAt @map("updated_at")

  @@map("system_metadata")
}

// Tables will be added in subsequent stories:
// - Story 1.4: order_book_snapshots, platform_health_logs (SystemMetadata removed)
// - Story 3.4: contract_matches
// - Story 4.1: risk_states
// - Story 5.1: open_positions, orders
// - Story 6.5: audit_logs
```

**First Migration Command:**

```bash
# Generate Prisma client
pnpm prisma generate

# Create initial migration (with placeholder SystemMetadata model)
pnpm prisma migrate dev --name init

# Note: SystemMetadata table will be dropped in Story 1.4's migration
```

### Fastify Integration

**Main.ts Configuration:**

```typescript
import { NestFactory } from '@nestjs/core';
import {
  FastifyAdapter,
  NestFastifyApplication,
} from '@nestjs/platform-fastify';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create<NestFastifyApplication>(
    AppModule,
    new FastifyAdapter(),
  );

  app.setGlobalPrefix('api');

  // Bind to 0.0.0.0 in development (required for Docker container networking)
  // Production uses 127.0.0.1:8080 per architecture (localhost-only with SSH tunnel)
  const host = process.env.NODE_ENV === 'production' ? '127.0.0.1' : '0.0.0.0';
  const port = process.env.PORT || 8080;

  await app.listen(port, host);
  console.log(`Application is running on: http://${host}:${port}`);
}
bootstrap();
```

**Why Fastify over Express:**

- 2-3x faster request handling (critical for sub-second detection cycles)
- Lower memory footprint
- Native async/await support
- Better TypeScript integration
- Architecture explicitly chose Fastify for performance (NFR-P1, NFR-P2)

### Configuration Module (@nestjs/config)

**App Module Setup:**

```typescript
import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: `.env.${process.env.NODE_ENV || 'development'}`,
    }),
  ],
})
export class AppModule {}
```

**Environment File Pattern:**

- `.env.development` - Local development (committed to repo with safe defaults)
- `.env.production` - Production config (NOT committed, deployed separately)
- `.env.example` - Template showing all required variables (committed)

### Project Context Reference

**Related Artifacts:**

- [Source: _bmad-output/planning-artifacts/architecture.md#Starter Template Evaluation] - Official initialization command
- [Source: _bmad-output/planning-artifacts/architecture.md#Technology Stack Decisions] - Complete tech stack rationale
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns] - Directory structure and naming conventions
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.1] - Complete acceptance criteria and story context

**Subsequent Stories Dependency:**

- Story 1.2 depends on this story's engine lifecycle hooks
- Story 1.3 depends on this story's connector directory structure
- Story 1.4 depends on this story's Prisma foundation
- Story 1.5 depends on this story's NestJS module setup

### Critical Success Factors

**Must Have Before Story Complete:**

1. ✅ `docker-compose up` starts cleanly with no errors
2. ✅ `/api/health` returns proper JSON format
3. ✅ Database connection verified (Prisma can connect)
4. ✅ Vitest runs with decorator support (example test passes)
5. ✅ CI pipeline passes all steps
6. ✅ Directory structure matches architecture specification
7. ✅ `.env.development` and `.env.example` exist
8. ✅ README has setup instructions

**Common Pitfalls to Avoid:**

- ❌ Using Express instead of Fastify
- ❌ Forgetting unplugin-swc for Vitest (decorators won't work)
- ❌ Using SQLite instead of PostgreSQL
- ❌ Creating `utils/` directory (use `common/` instead)
- ❌ Hardcoding environment variables
- ❌ Skipping Docker health checks
- ❌ **Not checking port 5432 availability before Docker Compose setup** (causes immediate failure if local PostgreSQL is running)
- ❌ **Creating a monorepo or adding dashboard directory inside engine repo** (separate repos per architecture)

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

No critical issues encountered. Port 5432 conflict resolved by using port 5433 for PostgreSQL.

### Completion Notes List

- ✅ NestJS 11.x initialized in `pm-arbitrage-engine/` subdirectory with strict TypeScript
- ✅ Fastify adapter configured for 2-3x performance improvement over Express
- ✅ Core dependencies added: Prisma 6.19.2, viem 2.45.3, Vitest 4.0.18, unplugin-swc 1.5.9
- ✅ Docker Compose configured with PostgreSQL 16 on host port 5433 (avoiding conflict with local PostgreSQL)
- ✅ Tested `docker-compose -f docker-compose.dev.yml up` - PostgreSQL starts cleanly, health endpoint responds 200
- ✅ Tested full `docker-compose up` - Engine container builds and connects to PostgreSQL successfully
- ✅ Prisma initialized with SystemMetadata placeholder model and initial migration created
- ✅ `/api/health` endpoint implemented with proper JSON format and database connectivity validation
- ✅ Vitest configured with SWC for decorator metadata support - tests passing (including DB failure case)
- ✅ GitHub Actions CI pipeline configured for lint, test, build
- ✅ Directory structure created matching architecture: modules/, connectors/, common/, core/
- ✅ README.md updated with comprehensive setup instructions
- ✅ All lint, test, and build checks passing

**Architecture Deviations Documented:**
- **PrismaService location:** Implemented in `src/common/prisma.service.ts` instead of `src/persistence/prisma.service.ts` per architecture. Rationale: Deferring full persistence module structure to Story 1.4 when actual database tables are added. PrismaService is foundational infrastructure needed immediately, so placed in `common/` for now. Will be moved to `persistence/` module in Epic 1 Story 1.4 when implementing order book snapshots and health logs tables.

- **Docker migration strategy:** Dockerfile CMD runs `prisma migrate deploy` on every container startup (line 47). This is acceptable for MVP single-instance deployment but has known limitations: (1) Multiple replicas starting simultaneously could race on migrations, (2) Failed migrations block container startup with no graceful degradation, (3) Long-running migrations extend deployment downtime. Future epics should implement separate migration job for production blue/green deployments.

### File List

**New Files:**
- `pm-arbitrage-engine/.env`
- `pm-arbitrage-engine/.env.development`
- `pm-arbitrage-engine/.env.example`
- `pm-arbitrage-engine/.gitignore`
- `pm-arbitrage-engine/.prettierrc`
- `pm-arbitrage-engine/Dockerfile`
- `pm-arbitrage-engine/README.md`
- `pm-arbitrage-engine/docker-compose.dev.yml`
- `pm-arbitrage-engine/docker-compose.yml`
- `pm-arbitrage-engine/eslint.config.mjs`
- `pm-arbitrage-engine/nest-cli.json`
- `pm-arbitrage-engine/package.json`
- `pm-arbitrage-engine/pnpm-lock.yaml`
- `pm-arbitrage-engine/prisma.config.ts`
- `pm-arbitrage-engine/prisma/schema.prisma`
- `pm-arbitrage-engine/prisma/migrations/20260211094744_init/migration.sql`
- `pm-arbitrage-engine/prisma/migrations/migration_lock.toml`
- `pm-arbitrage-engine/src/app.controller.spec.ts`
- `pm-arbitrage-engine/src/app.controller.ts`
- `pm-arbitrage-engine/src/app.module.ts`
- `pm-arbitrage-engine/src/app.service.ts`
- `pm-arbitrage-engine/src/common/prisma.service.ts`
- `pm-arbitrage-engine/src/main.ts`
- `pm-arbitrage-engine/test/app.e2e-spec.ts`
- `pm-arbitrage-engine/test/jest-e2e.json`
- `pm-arbitrage-engine/tsconfig.build.json`
- `pm-arbitrage-engine/tsconfig.json`
- `pm-arbitrage-engine/vitest.config.ts`
- `pm-arbitrage-engine/.github/workflows/ci.yml`

**Directory Structure Created:**
- `pm-arbitrage-engine/src/modules/{data-ingestion,arbitrage-detection,execution,risk-management,monitoring}/` (each with `.gitkeep`)
- `pm-arbitrage-engine/src/connectors/{kalshi,polymarket}/` (each with `.gitkeep`)
- `pm-arbitrage-engine/src/common/{interfaces,errors,events,config}/` (each with `.gitkeep`)
- `pm-arbitrage-engine/src/core/` (with `.gitkeep`)
