# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PM Arbitrage System is a NestJS-based trading engine for prediction market arbitrage detection and execution. It detects price discrepancies between prediction markets (Kalshi and Polymarket) and executes coordinated trades to capture arbitrage opportunities.

**Working Directory:** All development work happens in `/pm-arbitrage-engine/` subdirectory. The root directory contains only project documentation and BMAD configuration.

**Tech Stack:**
- **Runtime:** Node.js with NestJS framework
- **Language:** TypeScript (strict mode)
- **Database:** PostgreSQL with Prisma ORM
- **Testing:** Vitest
- **Package Manager:** pnpm
- **Containerization:** Docker & Docker Compose

## Development Commands
```bash
# Navigate to engine directory first
cd pm-arbitrage-engine

# Installation
pnpm install

# Development
pnpm start:dev          # Hot-reload development server
pnpm start:debug        # Debug mode with --watch
pnpm build              # Production build
pnpm start:prod         # Run production build

# Testing
pnpm test               # Run all tests with Vitest
pnpm test:watch         # Watch mode
pnpm test:cov           # Coverage report

# Code Quality
pnpm lint               # ESLint with auto-fix
pnpm format             # Prettier formatting

# Database (Prisma)
pnpm prisma migrate dev       # Create and apply migration
pnpm prisma generate          # Generate Prisma client after schema changes
pnpm prisma studio            # GUI for database inspection
pnpm prisma migrate reset     # Reset database (destructive)

# Docker
docker-compose -f docker-compose.dev.yml up -d    # Start PostgreSQL only
docker-compose up                                  # Full stack (engine + db)
docker-compose down                                # Stop containers
```

## Architecture & Project Structure
```
pm-arbitrage-engine/
├── src/
│   ├── modules/          # Feature modules (arbitrage, markets, execution)
│   ├── common/           # Shared utilities, decorators, guards
│   ├── config/           # Configuration modules
│   └── main.ts           # Application entry point
├── prisma/
│   └── schema.prisma     # Database schema
├── test/                 # E2E and integration tests
└── vitest.config.ts      # Test configuration
```

**Key Patterns:**
- **Module-based architecture:** Each feature is a self-contained NestJS module
- **Dependency Injection:** Use NestJS DI container, avoid manual instantiation
- **DTOs for validation:** Use class-validator decorators on DTOs
- **Repository pattern:** Database access through Prisma repositories

## Technology Stack Decisions

### Strict TypeScript

`tsconfig.json` enables aggressive strictness:
- `noUncheckedIndexedAccess` - Array access returns `T | undefined`
- `noUnusedLocals` and `noUnusedParameters` - Enforced code cleanliness
- `noImplicitReturns` - All code paths must return values
- `strictNullChecks` - Explicit handling of null/undefined

**Implications:**
- Always check array access: `const item = array[0]; if (item) { ... }`
- Remove unused imports and variables immediately
- Ensure all function branches return appropriate values

### Prisma ORM

- **Schema-first approach:** Modify `schema.prisma`, then run migrations
- **Type safety:** Prisma Client provides full TypeScript types
- **Migration workflow:**
  1. Edit `prisma/schema.prisma`
  2. Run `pnpm prisma migrate dev --name descriptive_name`
  3. Commit both schema and migration files
- **Always regenerate client:** Run `pnpm prisma generate` after schema changes

### NestJS Conventions

- **Decorators:** Use `@Injectable()`, `@Controller()`, `@Module()` appropriately
- **Exception handling:** Throw `HttpException` or built-in exceptions (e.g., `NotFoundException`)
- **Configuration:** Use `@nestjs/config` with validated environment variables
- **Logging:** Use NestJS Logger, not console.log

## Code Quality Standards

### Post-Edit Linting

**Always run linting after completing all file modifications** in a task:
```bash
cd pm-arbitrage-engine
pnpm lint
```

**Workflow:**
1. Complete all code changes
2. Run `pnpm lint` (auto-fix enabled by default)
3. Manually resolve any remaining errors
4. Verify with `pnpm lint` again
5. Only then mark task as complete

**Do not proceed if linting fails.**

### Testing Requirements

- **Unit tests:** Write tests for business logic, services, and utilities
- **Test location:** Co-locate tests with source files (e.g., `service.spec.ts` next to `service.ts`)
- **Coverage:** Aim for >80% coverage on critical paths (arbitrage detection, execution)
- **Run tests before committing:** `pnpm test` should pass

### Code Style

- **Naming conventions:**
  - Classes: PascalCase (e.g., `ArbitrageService`)
  - Files: kebab-case (e.g., `arbitrage.service.ts`)
  - Variables/functions: camelCase (e.g., `detectArbitrage`)
  - Constants: UPPER_SNAKE_CASE (e.g., `MAX_RETRY_ATTEMPTS`)
- **File organization:**
  - Imports grouped: external, internal, relative
  - Exports at bottom of file
  - One class per file (except small DTOs/interfaces)

## Environment Configuration

Uses environment-specific files:
- `.env.development` - Local development (port 5433 for PostgreSQL)
- `.env.production` - Production deployment (port 5432 internal Docker network)
- `.env.example` - Template showing required variables

**Critical Variables:**
- `DATABASE_URL` - PostgreSQL connection string
- `PORT` - Application port (default: 8080)
- `NODE_ENV` - Controls which `.env.*` file is loaded
- API keys for Kalshi/Polymarket (check `.env.example`)

**Network Configuration:**
- Development: Binds to `0.0.0.0` (Docker networking)
- Production: Binds to `127.0.0.1` (localhost-only with SSH tunnel)

## Database Workflow

### Making Schema Changes

1. **Edit schema:** Modify `prisma/schema.prisma`
2. **Create migration:** `pnpm prisma migrate dev --name add_user_table`
3. **Generate client:** `pnpm prisma generate` (auto-runs with migrate)
4. **Update code:** Use new Prisma types in services
5. **Test:** Verify migrations work in clean database

### Common Pitfalls

- **Don't edit migrations manually** - Always use Prisma CLI
- **Commit migrations** - Both schema and `migrations/` directory
- **Reset carefully** - `migrate reset` destroys all data

## Common Tasks

### Adding a New Feature Module

1. Generate module: `nest g module features/feature-name`
2. Generate service: `nest g service features/feature-name`
3. Generate controller: `nest g controller features/feature-name`
4. Update module imports in `app.module.ts`
5. Add tests: Create `.spec.ts` files
6. Document API endpoints in controller

### Debugging

- Use `pnpm start:debug` for debugging
- Attach debugger to port 9229
- Set breakpoints in VS Code
- Use NestJS Logger for structured logging

### Deployment Checklist

- [ ] All tests pass (`pnpm test`)
- [ ] Linting passes (`pnpm lint`)
- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] Docker build succeeds
- [ ] Health check endpoint responds

## Troubleshooting

**"Prisma Client not found"**
→ Run `pnpm prisma generate`

**Port 5433 already in use**
→ Check for existing PostgreSQL: `docker ps` and stop conflicting containers

**Module not found errors**
→ Run `pnpm install` and restart dev server

**TypeScript errors after schema change**
→ Regenerate Prisma Client: `pnpm prisma generate`

## Additional Notes

- **Async/await:** Prefer async/await over callbacks/promises.then()
- **Error handling:** Wrap async code in try-catch, throw appropriate NestJS exceptions
- **Validation:** Use `class-validator` on all DTOs
- **Documentation:** Add JSDoc comments for complex business logic
- **Performance:** Consider pagination for large datasets, use database indexes

## Resources

- [NestJS Documentation](https://docs.nestjs.com/)
- [Prisma Documentation](https://www.prisma.io/docs/)
- [Project README](../README.md) - Deployment and setup guide