# Technology Stack

**Runtime & Framework:**
- Node.js runtime
- NestJS framework (TypeScript-based)

**Language:**
- TypeScript (strict mode enabled)
- Key strictness flags:
  - `noUncheckedIndexedAccess` - Array access returns `T | undefined`
  - `noUnusedLocals` and `noUnusedParameters`
  - `noImplicitReturns`
  - `strictNullChecks`

**Database:**
- PostgreSQL
- Prisma ORM (schema-first approach)
- Development port: 5433
- Production port: 5432 (internal Docker network)

**Testing:**
- Vitest test framework
- Co-located test files (`.spec.ts` next to source files)
- Target coverage: >80% on critical paths

**Package Manager:**
- pnpm (NOT npm or yarn)

**Containerization:**
- Docker
- Docker Compose
- Environment-specific configurations

**Code Quality Tools:**
- ESLint (with auto-fix)
- Prettier
- class-validator for DTOs
