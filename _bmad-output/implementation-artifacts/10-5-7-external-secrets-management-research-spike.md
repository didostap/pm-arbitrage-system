# Story 10.5.7: External Secrets Management Research Spike

Status: done

## Story

As an operator,
I want a design document mapping the system's credential surface to a secrets manager integration,
so that Story 11.2 (External Secrets Management Integration) starts with zero open architectural questions.

## Context & Motivation

Epic 11 includes Story 11.2 (External Secrets Management Integration) and Story 11.3 (Zero-Downtime Key Rotation). Both require decisions about provider selection, credential lifecycle, fallback strategy, and integration pattern. This spike produces a **design document, not implementation** — following the investigation-first pattern validated in Epic 9 (Story 10-0-3) and codified in Team Agreement from Epic 9 retro.

**Blocks:** Story 11.2 (External Secrets Management Integration) — directly. Story 10-5-8 (documentation can reference spike findings).
**Independent:** Can run in parallel with all other stories (no upstream dependencies).

[Source: `_bmad-output/planning-artifacts/epics.md` Epic 10.5, Story 10-5-7]
[Source: `_bmad-output/implementation-artifacts/sprint-status.yaml` line 219]

## Acceptance Criteria

### AC1 — Credential Surface Inventory

**Given** the system's current credential surface
**When** the spike is completed
**Then** a design document exists covering:
- Complete inventory of all credentials/secrets in the system (see Dev Notes §1 for pre-discovered inventory)
- Which credentials are used at startup-only vs. runtime-refreshable
- Current storage mechanism for each (env var, file path, in-memory)

[Source: `_bmad-output/planning-artifacts/epics.md` Epic 10.5, Story 10-5-7 AC1]

### AC2 — Provider Evaluation

**Given** the secrets manager landscape
**When** providers are evaluated
**Then** the design document includes a provider comparison with recommendation:
- AWS Secrets Manager, HashiCorp Vault, and at least one lightweight alternative (e.g., SOPS/age-encrypted files, Infisical)
- Evaluation criteria: cost at solo-operator scale, complexity, SDK maturity for Node.js/NestJS, rotation support, audit logging
- Clear recommendation with rationale

[Source: `_bmad-output/planning-artifacts/epics.md` Epic 10.5, Story 10-5-7 AC2]

### AC3 — Integration Pattern Design

**Given** the recommended provider
**When** the integration pattern is designed
**Then** the design document covers:
- Credential lifecycle model: fetch → cache → use → refresh → invalidate
- NestJS integration pattern (custom ConfigFactory, provider, or module)
- Fallback strategy when secrets manager is unavailable (env var fallback with degraded-security alert)
- How this interacts with Story 10-5-2's `getEffectiveConfig()` pattern (secrets are NOT in EngineConfig DB — clear boundary)
- Key rotation mechanics: how `POST /api/admin/rotate-credentials/:platform` (Story 11.3) triggers re-fetch

[Source: `_bmad-output/planning-artifacts/epics.md` Epic 10.5, Story 10-5-7 AC3]

### AC4 — Scope & Review

**Given** this is a spike
**When** scope is evaluated
**Then:**
- No production code is written — output is a design document
- The document is placed in `docs/` (project knowledge directory)
- The spike follows the investigation-first pattern

[Source: `_bmad-output/planning-artifacts/epics.md` Epic 10.5, Story 10-5-7 AC4]

## Tasks / Subtasks

- [x] **Task 1: Credential Surface Inventory** (AC: #1)
  - [x] 1.1 Document all 8 credentials with current storage mechanism, access pattern, refresh semantics (use pre-discovered inventory in Dev Notes §1)
  - [x] 1.2 Classify each credential: startup-only vs. runtime-refreshable vs. rotation-candidate
  - [x] 1.3 Document current security gaps per credential (plain text on disk, hardcoded in docker-compose, no rotation, etc.)

- [x] **Task 2: Provider Evaluation** (AC: #2)
  - [x] 2.1 Evaluate AWS Secrets Manager — include VPS→AWS connectivity feasibility (egress, IAM credential meta-problem: where do AWS creds live?) (see Dev Notes §2, §9)
  - [x] 2.2 Evaluate HashiCorp Vault (see Dev Notes §2)
  - [x] 2.3 Evaluate lightweight alternatives: SOPS+age, Infisical (see Dev Notes §2) — re-evaluate Infisical as co-recommendation for VPS with no AWS account (see §9 finding #11)
  - [x] 2.4 Create comparison matrix with weighted scoring for solo-operator context
  - [x] 2.5 Write clear recommendation with rationale — include decision criteria tree (e.g., "Choose Infisical if no AWS account")
  - [x] 2.6 Resolve architecture drift decision: encrypted keystore for Polymarket vs. secrets manager superseding it (see §6, §9 finding #5)

- [x] **Task 3: Integration Pattern Design** (AC: #3)
  - [x] 3.1 Design credential lifecycle model (fetch → cache → use → refresh → invalidate) — specify cache TTL (recommend 5 min), invalidation on rotation, memory-zeroing feasibility in Node.js (see §9 finding #3)
  - [x] 3.2 Design NestJS integration pattern — custom `SecretsModule` with async provider
  - [x] 3.3 Document boundary with EngineConfig DB (Category A vs Category B split)
  - [x] 3.4 Design fallback strategy — specify exact event payload structure for `platform.health.degraded` emission (see §9 finding #7)
  - [x] 3.5 Design per-credential rotation atomicity sequences — Kalshi (JWT invalidation + SDK reconfiguration), Polymarket (Wallet + ClobClient double-buffer swap), DATABASE_URL (Prisma pool drain + reconnect feasibility), OPERATOR_API_TOKEN (cache-based, no per-request secrets manager call) (see §9 finding #2, #4)
  - [x] 3.6 Document ConfigAccessor bootstrap ordering problem: SecretsModule must resolve DATABASE_URL before Prisma connects before ConfigAccessor reads DB (see §9 finding #7)
  - [x] 3.7 Document secret leak prevention: pino log redaction config, error message masking, heap snapshot policy (see §9 recommendation #8)
  - [x] 3.8 Address race condition: rotation during in-flight execution — specify that rotation must not occur during active hot-path trade (see §9 finding #6)
  - [x] 3.9 Document Kalshi RSA key handling: in-memory PEM vs. temp file, multi-line string preservation in secrets manager, file permissions (see §9 finding #8)
  - [x] 3.10 Document break-glass / rollback procedure: operator lockout prevention, secret version rollback, emergency env var override (see §9 questions #6, #13)

- [x] **Task 4: Write Design Document** (AC: #1, #2, #3, #4)
  - [x] 4.1 Create `docs/external-secrets-design.md` with all sections (see §7 for structure)
  - [x] 4.2 Include architecture decision record (ADR) format for provider selection
  - [x] 4.3 Include sequence diagrams (text-based) for: startup bootstrap (SecretsModule → Prisma → ConfigAccessor), rotation trigger (HTTP POST → SecretsService → connector hot-swap), fallback activation
  - [x] 4.4 Include phased migration plan: Phase 0 (current env vars) → Phase 1 (secrets manager + env fallback) → Phase 2 (secrets manager required, disable fallback for production)
  - [x] 4.5 Include Docker secrets migration guidance for docker-compose.yml (see §9 finding #9)
  - [x] 4.6 Include testing strategy section: mock secrets manager / localstack for Story 11.2 tests (see §9 question #9)
  - [x] 4.7 Include open questions list for operator decision before Story 11.2 (consolidate §9 questions)

## Dev Notes

### §1 — Pre-Discovered Credential Surface Inventory

Codebase investigation has identified **8 secrets** currently managed via environment variables:

| # | Credential | Env Var(s) | Loaded By | File | Startup-Only? | Notes |
|---|-----------|-----------|-----------|------|---------------|-------|
| 1 | Kalshi API Key ID | `KALSHI_API_KEY_ID` | `ConfigService.get()` | `src/connectors/kalshi/kalshi.connector.ts` (constructor) | Yes (constructor) | Used to configure Kalshi SDK `Configuration` object |
| 2 | Kalshi RSA Private Key | `KALSHI_PRIVATE_KEY_PATH` → `readFileSync()` | `readFileSync` at init | `src/connectors/kalshi/kalshi.connector.ts` (constructor, lines 102-124) | Yes (constructor) | File path in env, PEM content read synchronously. JWT signing for API auth |
| 3 | Polymarket Private Key | `POLYMARKET_PRIVATE_KEY` | `ConfigService.get()` | `src/connectors/polymarket/polymarket.connector.ts` (constructor, lines 71-74) | Yes (constructor) | Hex string (no 0x prefix). Used with ethers `Wallet` for on-chain signing |
| 4 | LLM Primary API Key | `LLM_PRIMARY_API_KEY` | `ConfigService.get()` | `src/modules/contract-matching/llm-scoring.strategy.ts` (constructor) | Yes (constructor) | Gemini or Anthropic key for contract matching NLP |
| 5 | LLM Escalation API Key | `LLM_ESCALATION_API_KEY` | `ConfigService.get()` | `src/modules/contract-matching/llm-scoring.strategy.ts` (constructor) | Yes (constructor) | Backup LLM provider key |
| 6 | Telegram Bot Token | `TELEGRAM_BOT_TOKEN` | `ConfigService.get()` | `src/modules/monitoring/telegram-alert.service.ts` | Yes (constructor) | Bot auth token for alert delivery |
| 7 | Database URL | `DATABASE_URL` | Prisma (connection string) | `prisma/schema.prisma` + Prisma runtime | Yes (connection pool init) | Contains username + password in connection string |
| 8 | Operator API Token | `OPERATOR_API_TOKEN` | `ConfigService.get()` | `src/common/guards/auth-token.guard.ts` (line 17) | Runtime (per-request) | Static Bearer token for dashboard auth. Only credential read per-request |

**Current Security Gaps Discovered:**
- All secrets are plain text in `.env` files — no encryption at rest
- No secrets rotation mechanism exists anywhere in the codebase
- No vault/secrets manager integration
- `KALSHI_PRIVATE_KEY_PATH` points to an unencrypted PEM file on disk (`./secrets/key.pem`)
- `docker-compose.yml` has hardcoded `DATABASE_URL` with literal password `password`
- Architecture doc mentions "AES-256 encrypted keystore for Polymarket private key" but implementation uses plain env var instead — **drift from architecture spec**
- All 8 secrets loaded at startup in constructors → none are currently runtime-refreshable

[Source: Codebase investigation of `pm-arbitrage-engine/` — `env.schema.ts`, connector files, guard, alert service]

### §2 — Pre-Researched Provider Comparison Data

#### AWS Secrets Manager
- **Pricing:** $0.40/secret/month + $0.05/10,000 API calls. For 8 secrets with startup-only fetch + 5-min cache TTL: **~$3.20/month + negligible API costs (~$0.01)**
- **Node.js SDK:** `@aws-sdk/client-secrets-manager` — mature, well-maintained, TypeScript types included
- **Rotation:** Native 4-step Lambda rotation (createSecret → setSecret → testSecret → finishSecret). Maintains `AWSCURRENT` + `AWSPENDING` versions during rotation for zero-downtime
- **Audit:** CloudTrail integration — every API call logged automatically
- **Pros:** Fully managed, no infrastructure to maintain, cheap at solo-operator scale, native rotation, audit built-in
- **Cons:** AWS vendor lock-in, requires AWS account + IAM setup, not portable to non-AWS deployment
- **Solo-operator fit:** Excellent — minimal ops overhead, cost-effective, rotation built-in

[Source: Web research — AWS Secrets Manager pricing page (aws.amazon.com/secrets-manager/pricing), Infisical comparison blog, CostGoat pricing calculator]

#### HashiCorp Vault
- **Pricing:** Free (self-hosted, BSL 1.1 license — source-available, NOT open source). Vault Enterprise/HCP Vault for managed hosting (expensive)
- **Node.js SDK:** `node-vault` (community-maintained) — functional but less polished than AWS SDK. No official HashiCorp Node.js SDK
- **Rotation:** Dynamic secrets (credentials generated on-demand with TTL), time-limited access — most powerful rotation model
- **Audit:** Comprehensive audit device system — every operation logged
- **Pros:** Most powerful and flexible, cloud-agnostic, dynamic secrets, fine-grained policies
- **Cons:** Significant operational complexity (HA, unsealing, storage backend, monitoring, backup). BSL license restricts competitive use. Community Node.js SDK. **Massive overkill for solo operator running single-VPS deployment**
- **Solo-operator fit:** Poor — operational burden vastly exceeds benefit for 8 secrets on a single VPS

[Source: Web research — Infisical AWS vs Vault comparison (2026), ayedo.de comparison]

#### SOPS + age (Lightweight Alternative #1)
- **Pricing:** Free (open source, Apache 2.0 for SOPS, BSD for age)
- **How it works:** Encrypts `.env` / YAML / JSON files at rest using `age` keys. Decrypts at startup. No runtime API — file-based only
- **Node.js integration:** Shell exec (`sops -d file.enc.env`) at startup, parse output. No native Node.js library — must shell out or use `child_process`
- **Rotation:** Manual — re-encrypt file with new values, redeploy. No automated rotation
- **Audit:** None built-in — git history of encrypted file changes only
- **Pros:** Zero infrastructure, zero cost, zero network dependency, files are encrypted at rest, git-friendly (encrypted files can be committed)
- **Cons:** No runtime refresh, no automated rotation, manual key management, no audit trail, no API for Story 11.3 rotation endpoint
- **Solo-operator fit:** Good for basic encryption-at-rest. Insufficient for Phase 1 rotation requirements (FR-PI-07)

[Source: Web research — github.com/getsops/sops (21.2K stars, actively maintained as of March 2026)]

#### Infisical (Lightweight Alternative #2)
- **Pricing:** Free self-hosted (MIT license, truly open source). Cloud: free tier for up to 5 team members
- **Node.js SDK:** `@infisical/sdk` — official SDK with TypeScript support. Also CLI wrapper for NestJS (`infisical run -- npm run start:dev`)
- **Rotation:** Secret rotation support, dynamic secrets. Less mature than AWS but actively developing
- **Audit:** Built-in audit logs, access controls, approval workflows
- **Pros:** Open source (MIT), self-hostable on same VPS, NestJS integration documented, rotation support, audit logs, web UI for management, no vendor lock-in
- **Cons:** Additional service to run and maintain on VPS (PostgreSQL + Redis + Infisical server), less battle-tested than AWS, adds operational surface area
- **Solo-operator fit:** Moderate — good features but adds infrastructure to maintain. Better suited when operator wants full self-hosted control

[Source: Web research — infisical.com, infisical.com/docs/integrations/frameworks/nestjs]

#### Pre-Scored Comparison Matrix

| Criteria (Weight) | AWS Secrets Manager | HashiCorp Vault | SOPS+age | Infisical |
|-------------------|:---:|:---:|:---:|:---:|
| Cost at solo-operator scale (20%) | A (~$3/mo) | A (free) | A+ (free) | A (free self-host) |
| Operational complexity (25%) | A (fully managed) | D (complex self-host) | A+ (no infra) | C+ (extra services) |
| Node.js/NestJS SDK maturity (15%) | A (official SDK) | C (community) | D (shell exec) | B+ (official SDK) |
| Rotation support (20%) | A (native, automated) | A+ (dynamic secrets) | F (manual only) | B (supported) |
| Audit logging (10%) | A (CloudTrail) | A (audit devices) | F (none) | B+ (built-in) |
| Portability / no lock-in (10%) | C (AWS-only) | A (multi-cloud) | A (file-based) | A (self-hosted) |

### §3 — Critical Boundary: EngineConfig DB vs Secrets Manager

Story 10-5-2 established a clear two-tier configuration model that **must not be violated**:

- **Category A (Secrets — env-only, NEVER in database):** All 8 credentials above. These are the scope of the secrets manager.
- **Category B (Operational settings — DB-backed with env fallback):** 71 tunable parameters in `engine_config` table. Managed by `ConfigAccessor.getEffectiveConfig()`. NOT in scope for secrets manager.

The Prisma schema (`prisma/schema.prisma` lines 56, 67) has explicit comments: `// tokens/chatId stay as env secrets` and `// API keys stay as env secrets`.

The design document **must** clearly delineate this boundary and explain that `SecretsModule` (new) replaces direct `ConfigService.get()` calls for Category A credentials ONLY. `ConfigAccessor` continues to serve Category B settings unchanged.

[Source: `pm-arbitrage-engine/src/common/config/config-accessor.service.ts`, `pm-arbitrage-engine/prisma/schema.prisma`]

### §4 — NestJS Integration Pattern Guidance

The current pattern for accessing secrets is:
```typescript
// Current (direct ConfigService — scattered across constructors)
constructor(private configService: ConfigService<Env, true>) {
  this.apiKey = this.configService.get('KALSHI_API_KEY_ID', '');
}
```

The design should propose a centralized `SecretsModule` pattern:
```typescript
// Target (centralized secrets provider — design document should specify this)
// SecretsModule provides SecretsService which fetches from secrets manager
// Falls back to ConfigService (env vars) with degraded-security event emission
@Injectable()
class SecretsService {
  // fetch → cache → use → refresh → invalidate lifecycle
  // Emits 'platform.health.degraded' if secrets manager unavailable
}
```

Key NestJS integration considerations for the design:
- `ConfigModule.forRoot()` with async `load` factories can integrate secrets fetching at startup
- Custom async provider using `useFactory` for secrets retrieval before module initialization
- The `ModuleRef`-based hot-reload pattern from Story 10-5-2 can be extended for credential refresh
- Secrets should be injectable via a dedicated `SecretsService` (not mixed into `ConfigService`)

[Source: `pm-arbitrage-engine/src/app.module.ts` (ConfigModule setup), `pm-arbitrage-engine/src/common/config/env.schema.ts` (Zod validation)]

### §5 — PRD Requirements the Design Must Address

| Requirement | ID | Phase | Key Constraint |
|------------|-----|-------|----------------|
| External secrets retrieval at startup | FR-PI-06 | Phase 1 | Not stored in process memory long-term |
| Zero-downtime key rotation | FR-PI-07 | Phase 1 | <5 seconds degraded operation during switchover |
| Credential storage evolution | NFR-S1 | Phase 1 | Secrets manager with rotation, audit, encryption |
| Key rotation support | NFR-S2 | Phase 1 | Immediate rotation on security incident |
| Audit trail for secrets access | NFR-S3 | Phase 1 | All secrets access logged |
| Zero credential exposure | NFR-S1 | Phase 1 | Zero credentials in logs, repos, or unencrypted storage |

[Source: `_bmad-output/planning-artifacts/prd.md` — FR-PI-06, FR-PI-07, NFR-S1, NFR-S2, NFR-S3]

### §6 — Architecture Drift Alert

The architecture document (`docs/architecture.md`) specifies:
> "Polymarket wallet private key: AES-256 encrypted keystore file, decrypted at startup with master password from `POLYMARKET_KEYSTORE_PASSWORD` environment variable."

**Actual implementation:** `POLYMARKET_PRIVATE_KEY` is stored as a plain hex string in `.env` — no encrypted keystore exists. The design document should note this drift and recommend whether the secrets manager migration should also implement the encrypted keystore pattern or supersede it entirely.

[Source: `_bmad-output/planning-artifacts/architecture.md` — Platform Credential Management section; `pm-arbitrage-engine/src/connectors/polymarket/polymarket.connector.ts` lines 71-74]

### §7 — Design Document Output Structure

The design document should be placed at `docs/external-secrets-design.md` and follow this structure:

1. **Executive Summary** — Problem statement, recommendation, migration timeline
2. **Credential Surface Inventory** — Table from §1 with refresh classification
3. **Provider Evaluation** — Comparison matrix, individual assessments, recommendation with ADR format
4. **Integration Architecture** — NestJS module design, sequence diagrams, fallback strategy
5. **Credential Lifecycle Model** — fetch → cache → use → refresh → invalidate for each credential type
6. **EngineConfig Boundary** — Clear separation from Category B settings (§3)
7. **Key Rotation Design** — How `POST /api/admin/rotate-credentials/:platform` (Story 11.3) triggers credential refresh
8. **Migration Plan** — Phased rollout from env vars to secrets manager
9. **Open Questions** — Anything requiring operator decision before Story 11.2

### §9 — Lad MCP Design Review Findings (Pre-Implementation)

A system design review was run against this story. The following findings must be addressed in the design document:

**Critical Issues (MUST address):**

1. **AWS feasibility for single VPS** — The VPS must reach AWS APIs (HTTPS egress). IAM credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) themselves must be stored somewhere — this is the "meta-credential" problem. The design document must explicitly address where AWS bootstrap credentials live (instance profile if EC2, or env var with documented acceptance of the one-level-up dependency).

2. **Per-credential rotation atomicity** — Each credential type has different rotation mechanics:
   - **Kalshi RSA Key:** JWT signing uses key at request time. Must reconstruct `Configuration` object with new key PEM. Double-buffer pattern: prepare new config, swap atomically.
   - **Polymarket Private Key:** `Wallet` + `ClobClient` instantiated in constructor. Must construct new instances, swap reference, destroy old. Cannot rotate mid-order-signing.
   - **DATABASE_URL:** Requires Prisma connection pool drain + reconnect. Investigate whether Prisma supports runtime connection string change or requires process restart.
   - **OPERATOR_API_TOKEN:** Read per-request from guard. Must cache in SecretsService with TTL — never call secrets manager per HTTP request (100-300ms latency unacceptable).

3. **Cache TTL and invalidation** — Specify 5-minute default TTL for cached secrets. Version-based invalidation (check `VersionId` on access). Discuss Node.js heap snapshot exposure and whether memory-zeroing is feasible (Buffer.alloc vs string immutability).

4. **OPERATOR_API_TOKEN latency** — `AuthTokenGuard` reads token per-request. SecretsService must serve from in-memory cache, not from network call. Fallback to env var if cache is cold.

5. **Architecture drift decision** — The design MUST explicitly recommend: (a) implement AES-256 encrypted keystore for Polymarket AND use secrets manager for the decryption password, OR (b) supersede keystore entirely — secrets manager stores the raw private key. Include rationale in ADR.

**Moderate Issues (SHOULD address):**

6. **Race condition during execution** — If secret rotation triggers while a two-leg trade is in flight, first leg may use old credentials, second leg may use new. Design should specify: rotation must acquire a lock or wait for hot-path idle window. Emit `secrets.rotation.pending` event before swap, `secrets.rotation.completed` after.

7. **ConfigAccessor bootstrap ordering** — `DATABASE_URL` is a Category A secret needed to connect to PostgreSQL, which is needed by `ConfigAccessor` to load Category B settings. Initialization order must be: `SecretsModule.init()` (fetch DATABASE_URL) → `PrismaModule.init()` → `ConfigAccessor.init()`. Document this explicitly.

8. **Kalshi RSA key file handling** — Current code uses `readFileSync(privateKeyPath)`. Design should specify whether secrets manager stores PEM content directly (multi-line string — verify newline preservation) or writes to temp file. If temp file: specify permissions (0600), cleanup on rotation, tmpdir location.

9. **Docker compose hardcoded secrets** — `docker-compose.yml` has literal `password` in DATABASE_URL. Migration plan should include Docker secrets or `.env` file mounting pattern for production compose.

**Minor Issues (COULD address):**

10. **Infisical may be undervalued** — For VPS with no AWS account, Infisical self-hosted uses the same PostgreSQL instance, has zero external network dependencies, and keeps secrets on-premises. Include as co-recommendation with decision criteria.

11. **SOPS+age rotation** — Scored F on rotation but could support file-watcher refresh. Note this as a future option if automated rotation is not needed in Phase 1.

12. **Secret versioning and rollback** — Document break-glass procedure: if rotated credentials fail, how to roll back to previous version. Emergency env var override path.

13. **Log masking** — All secret values must be redacted in pino structured logs. Recommend pino `redact` configuration for known secret field paths. Error messages from connectors must not include credential values.

14. **Telegram bot token rotation UX** — Rotating Telegram token requires BotFather interaction + potential chat ID change. Document as manual-only rotation with operator steps.

15. **Testing strategy for 11.2** — Recommend localstack or mock secrets manager for integration tests. Document how to test rotation without affecting production credentials.

[Source: Lad MCP `system_design_review` output, primary reviewer (moonshotai/kimi-k2.5)]

### §8 — What This Story Does NOT Do

- **No production code changes** — output is documentation only
- **No provider account creation** — research and recommendation only
- **No Prisma schema changes** — secrets stay out of the database
- **No changes to existing `.env` files** — current flow remains unchanged
- **No dashboard UI changes** — Story 11.2 will handle integration

### Project Structure Notes

- Design document output: `docs/external-secrets-design.md` (project knowledge directory per `config.yaml`)
- No source code files created or modified
- Aligns with investigation-first pattern (Team Agreement, Epic 9 retro)

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` lines 2827-3373 — Epic 10.5 and 11 complete text]
- [Source: `_bmad-output/planning-artifacts/architecture.md` — Authentication & Security, Configuration Management sections]
- [Source: `_bmad-output/planning-artifacts/prd.md` — FR-PI-06, FR-PI-07, NFR-S1 through NFR-S4]
- [Source: `pm-arbitrage-engine/src/common/config/env.schema.ts` — all env var definitions with Zod validation]
- [Source: `pm-arbitrage-engine/src/common/config/config-accessor.service.ts` — EffectiveConfig caching pattern]
- [Source: `pm-arbitrage-engine/prisma/schema.prisma` lines 19-142 — engine_config model with Category A/B comments]
- [Source: `pm-arbitrage-engine/src/connectors/kalshi/kalshi.connector.ts` — Kalshi credential loading]
- [Source: `pm-arbitrage-engine/src/connectors/polymarket/polymarket.connector.ts` — Polymarket credential loading]
- [Source: `pm-arbitrage-engine/src/common/guards/auth-token.guard.ts` — Operator token validation]
- [Source: Web research — AWS Secrets Manager pricing (2026), Infisical docs, SOPS GitHub, Vault vs AWS comparison articles]

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Debug Log References
N/A (documentation-only spike — no code, no tests)

### Completion Notes List
- **Task 1 (Credential Surface Inventory):** Verified all 8 credentials against source code. Documented storage mechanism, access pattern, refresh semantics. Classified as startup-only (7) vs runtime per-request (1). Documented 10 security gaps including architecture drift (AES-256 keystore spec vs plain env var).
- **Task 2 (Provider Evaluation):** Evaluated 4 providers with web research (AWS pricing, Infisical NestJS integration, Prisma runtime connection string, Node.js memory-zeroing). Created weighted comparison matrix. Primary recommendation: AWS Secrets Manager. Co-recommendation: Infisical (self-hosted). ADR-001 (provider selection) and ADR-002 (Polymarket keystore supersession) documented.
- **Task 3 (Integration Pattern Design):** Designed SecretsModule architecture, credential lifecycle model (5-min TTL cache), per-credential rotation atomicity (6 credential types with specific swap patterns), bootstrap ordering (SecretsModule → Prisma → ConfigAccessor), fallback strategy with event payloads, race condition prevention (rotation lock during hot-path), secret leak prevention (pino redaction, error masking, heap snapshot policy), Kalshi RSA key handling (direct PEM in secrets manager, no temp file), break-glass/rollback procedure with emergency env var override.
- **Task 4 (Write Design Document):** Created `docs/external-secrets-design.md` — 13 sections, 2 ADRs, 3 sequence diagrams, 3-phase migration plan, Docker secrets guidance, testing strategy (LocalStack/Infisical), 8 open questions.
- **Key decisions:** (1) Supersede AES-256 keystore with secrets manager (ADR-002), (2) Prisma rotation requires new PrismaClient instance (no runtime URL change), (3) Memory-zeroing infeasible for JS strings — accepted as known limitation, (4) OPERATOR_API_TOKEN served from cache only (never network call per request).

### Change Log
- 2026-03-23: Story implemented — design document created at `docs/external-secrets-design.md`

### File List
- `docs/external-secrets-design.md` (NEW) — External secrets management design document
