# Task Completion Checklist

When completing a task, **ALWAYS** follow this checklist:

## 1. Post-Edit Linting (MANDATORY)
```bash
cd pm-arbitrage-engine && pnpm lint
```
- Auto-fix enabled by default
- Manually resolve any remaining errors
- **Do not proceed if linting fails**

## 2. Run Tests
```bash
pnpm test
```
- All tests must pass before marking task complete
- Add new tests for new functionality (co-located `.spec.ts`)

## 3. Prisma Workflow (if schema changed)
```bash
pnpm prisma migrate dev --name <descriptive_name>
pnpm prisma generate
```
- Always commit both schema and migration files
- Never edit migrations manually

## 4. Verify Build (for significant changes)
```bash
pnpm build
```

## 5. Git Commit (DUAL REPO!)
- Engine changes: commit in `pm-arbitrage-engine/`
- Doc/config changes: commit in root repo
- These are separate git repositories!

## Error Handling Checks
- [ ] Extended SystemError hierarchy (never raw Error)
- [ ] Appropriate severity level set
- [ ] Domain events emitted for observable state changes
- [ ] Financial math uses decimal.js (never native operators)

## Architecture Checks
- [ ] Module dependency rules respected (see CLAUDE.md)
- [ ] Inter-module communication via interfaces in `common/interfaces/`
- [ ] No forbidden imports (connectors ← modules, common ← modules, etc.)
