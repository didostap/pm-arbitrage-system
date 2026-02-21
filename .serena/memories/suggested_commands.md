# Development Commands

**IMPORTANT:** All commands must be run from the `pm-arbitrage-engine/` directory.

## Essential Workflow
```bash
cd pm-arbitrage-engine
pnpm install              # Install dependencies
pnpm start:dev            # Hot-reload development server
pnpm lint                 # ESLint with auto-fix (ALWAYS run after edits)
pnpm test                 # Vitest run (ALWAYS run before committing)
pnpm test:watch           # Watch mode
pnpm test:cov             # Coverage report
pnpm format               # Prettier formatting
pnpm build                # Production build
```

## Database (Prisma)
```bash
pnpm prisma migrate dev --name <migration_name>  # Create + apply migration
pnpm prisma generate                              # Regenerate client after schema changes
pnpm prisma studio                                # GUI for database inspection
pnpm prisma migrate reset                         # Reset database (DESTRUCTIVE)
```

## Docker
```bash
docker-compose -f docker-compose.dev.yml up -d    # PostgreSQL only
docker-compose up                                  # Full stack
docker-compose down                                # Stop containers
```

## Debugging
```bash
pnpm start:debug          # Debug mode with --watch (debugger on port 9229)
```

## Git (DUAL REPO!)
The engine is an independent git repo. Commits must be made separately:
```bash
# Engine repo commits
cd pm-arbitrage-engine && git add ... && git commit ...

# Main repo commits (docs, CLAUDE.md, BMAD artifacts)
cd /path/to/pm-arbitrage-system && git add ... && git commit ...
```
