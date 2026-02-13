# Suggested Development Commands

**IMPORTANT:** All commands must be run from the `pm-arbitrage-engine/` directory.

## Installation
```bash
cd pm-arbitrage-engine
pnpm install
```

## Development
```bash
pnpm start:dev          # Hot-reload development server
pnpm start:debug        # Debug mode with --watch (debugger on port 9229)
pnpm build              # Production build
pnpm start:prod         # Run production build
```

## Testing
```bash
pnpm test               # Run all tests with Vitest
pnpm test:watch         # Watch mode
pnpm test:cov           # Coverage report
```

## Code Quality
```bash
pnpm lint               # ESLint with auto-fix
pnpm format             # Prettier formatting
```

## Database (Prisma)
```bash
pnpm prisma migrate dev --name <migration_name>  # Create and apply migration
pnpm prisma generate                              # Generate Prisma client after schema changes
pnpm prisma studio                                # GUI for database inspection
pnpm prisma migrate reset                         # Reset database (DESTRUCTIVE)
```

## Docker
```bash
# Development - PostgreSQL only
docker-compose -f docker-compose.dev.yml up -d

# Full stack (engine + database)
docker-compose up

# Stop containers
docker-compose down
```

## System Utilities (Darwin/macOS)
Standard Unix commands work:
- `git` - Version control
- `ls` - List files
- `cd` - Change directory
- `grep` - Search text
- `find` - Find files
- `cat` - Display file contents
- `docker ps` - List running containers
