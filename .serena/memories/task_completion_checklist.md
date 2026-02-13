# Task Completion Checklist

When completing a task, **ALWAYS** follow this checklist:

## 1. Post-Edit Linting (MANDATORY)
```bash
cd pm-arbitrage-engine
pnpm lint
```

**Workflow:**
1. Complete all code changes
2. Run `pnpm lint` (auto-fix enabled by default)
3. Manually resolve any remaining errors
4. Verify with `pnpm lint` again
5. **Do not proceed if linting fails**

## 2. Run Tests
```bash
pnpm test
```
- All tests must pass before marking task complete
- Add new tests for new functionality

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

## Deployment Checklist (when applicable)
- [ ] All tests pass (`pnpm test`)
- [ ] Linting passes (`pnpm lint`)
- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] Docker build succeeds
- [ ] Health check endpoint responds
