# Code Style & Conventions

## Naming Conventions
- **Classes:** PascalCase (e.g., `ArbitrageService`)
- **Files:** kebab-case (e.g., `arbitrage.service.ts`)
- **Variables/Functions:** camelCase (e.g., `detectArbitrage`)
- **Constants:** UPPER_SNAKE_CASE (e.g., `MAX_RETRY_ATTEMPTS`)

## File Organization
- Imports grouped: external, internal, relative
- Exports at bottom of file
- One class per file (except small DTOs/interfaces)
- Co-locate tests with source files (`.spec.ts` next to implementation)

## TypeScript Patterns
- **Always check array access:** `const item = array[0]; if (item) { ... }`
- **Remove unused imports immediately**
- **Ensure all function branches return values**
- **Prefer async/await** over callbacks/promises.then()
- **Error handling:** Wrap async code in try-catch, throw NestJS exceptions

## NestJS Patterns
- **Decorators:** Use `@Injectable()`, `@Controller()`, `@Module()` appropriately
- **Dependency Injection:** Use NestJS DI container, avoid manual instantiation
- **DTOs:** Use class-validator decorators for validation
- **Repository pattern:** Database access through Prisma repositories
- **Exception handling:** Throw `HttpException` or built-in exceptions (e.g., `NotFoundException`)
- **Logging:** Use NestJS Logger, NOT console.log
- **Configuration:** Use `@nestjs/config` with validated environment variables

## Module Architecture
- **Module-based architecture:** Each feature is a self-contained NestJS module
- **Module location:** `src/modules/` for feature modules
- **Shared code:** `src/common/` for utilities, decorators, guards

## Best Practices
- Add JSDoc comments for complex business logic
- Use database indexes for performance
- Consider pagination for large datasets
- Validate all DTOs with class-validator
- Write unit tests for business logic (>80% coverage target)
