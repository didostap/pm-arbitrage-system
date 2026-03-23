# External Secrets Management Design Document

> **Story:** 10-5-7 (Research Spike)
> **Date:** 2026-03-23
> **Status:** Draft — blocks Story 11.2 (External Secrets Management Integration)
> **Author:** Dev Agent (Claude Opus 4.6)

---

## 1. Executive Summary

### Problem

The PM Arbitrage System manages 8 secrets via plain-text environment variables with no encryption at rest, no rotation mechanism, and no audit trail. Docker Compose files contain hardcoded credentials. The architecture document specifies an AES-256 encrypted keystore for Polymarket that was never implemented — the private key is stored as a plain hex string in `.env`.

### Recommendation

**Primary: AWS Secrets Manager** for operators with an AWS account. Cost: ~$3.20/month for 8 secrets. Fully managed, native rotation, CloudTrail audit, zero infrastructure to maintain.

**Co-recommendation: Infisical (self-hosted)** for operators running a single VPS without AWS. MIT-licensed, uses the existing PostgreSQL instance, keeps secrets on-premises, official Node.js SDK with NestJS integration.

### Migration Timeline

| Phase | Scope | Timeline |
|-------|-------|----------|
| Phase 0 (current) | Plain `.env` files, no encryption | Now |
| Phase 1 (Story 11.2) | Secrets manager + env var fallback with degraded-security alert | Epic 11 |
| Phase 2 (post-Epic 11) | Secrets manager required for production, env fallback disabled | Post-stabilization |

---

## 2. Credential Surface Inventory

### 2.1 Complete Credential Table

| # | Credential | Env Var(s) | Consumer | File | Access Pattern | Refresh Semantics |
|---|-----------|-----------|----------|------|---------------|-------------------|
| 1 | Kalshi API Key ID | `KALSHI_API_KEY_ID` | `KalshiConnector` constructor | `connectors/kalshi/kalshi.connector.ts:101` | Startup-only | Configures `Configuration` object; used for JWT signing on every API call |
| 2 | Kalshi RSA Private Key | `KALSHI_PRIVATE_KEY_PATH` → `readFileSync()` | `KalshiConnector` constructor | `connectors/kalshi/kalshi.connector.ts:102-124` | Startup-only | PEM file read synchronously; content held in memory for JWT signing |
| 3 | Polymarket Private Key | `POLYMARKET_PRIVATE_KEY` | `PolymarketConnector` constructor | `connectors/polymarket/polymarket.connector.ts:71-74` | Startup-only | Hex string; instantiates ethers `Wallet` + `ClobClient` |
| 4 | LLM Primary API Key | `LLM_PRIMARY_API_KEY` | `LlmScoringStrategy` constructor | `modules/contract-matching/llm-scoring.strategy.ts:170-172` | Startup-only | Configures Google GenAI or Anthropic SDK client |
| 5 | LLM Escalation API Key | `LLM_ESCALATION_API_KEY` | `LlmScoringStrategy` constructor | `modules/contract-matching/llm-scoring.strategy.ts:182-184` | Startup-only | Backup LLM provider key for escalation scoring |
| 6 | Telegram Bot Token | `TELEGRAM_BOT_TOKEN` | `TelegramAlertService` constructor | `modules/monitoring/telegram-alert.service.ts:267` | Startup-only | Bot auth token for HTTPS API calls to Telegram |
| 7 | Database URL | `DATABASE_URL` | Prisma (connection string) | `prisma/schema.prisma:10` | Startup-only | Contains username + password; initializes connection pool |
| 8 | Operator API Token | `OPERATOR_API_TOKEN` | `AuthTokenGuard.canActivate()` | `common/guards/auth-token.guard.ts:17` | **Runtime (per-request)** | Read via `ConfigService.get()` on every HTTP request |

### 2.2 Credential Classification

| Classification | Credentials | Description |
|---------------|-------------|-------------|
| **Startup-only** | #1-7 | Read once in constructor or module init; held in instance variables |
| **Runtime per-request** | #8 | Read from `ConfigService` on every authenticated HTTP request |
| **Rotation candidate (high priority)** | #1, #2, #3, #7, #8 | Platform credentials and database — highest blast radius if compromised |
| **Rotation candidate (medium priority)** | #4, #5 | LLM API keys — compromise enables unauthorized API usage, not fund loss |
| **Rotation candidate (low priority)** | #6 | Telegram bot token — compromise enables sending messages, no financial risk |

### 2.3 Current Security Gaps

| Credential | Gap | Severity |
|-----------|-----|----------|
| All 8 | Plain text in `.env` files — no encryption at rest | High |
| All 8 | No rotation mechanism anywhere in the codebase | High |
| All 8 | No vault/secrets manager integration | High |
| #2 (Kalshi RSA Key) | PEM file stored unencrypted on disk at `./secrets/key.pem` | High |
| #7 (DATABASE_URL) | Hardcoded `password` literal in `docker-compose.yml` line 31 and `docker-compose.dev.yml` line 12 | High |
| #3 (Polymarket Key) | Architecture spec requires AES-256 encrypted keystore; implementation uses plain env var — **drift from spec** | Medium |
| All 8 | All loaded in constructors — none are currently runtime-refreshable for rotation | Medium |
| #8 (Operator Token) | No expiration, no rotation, no complexity requirements | Medium |
| All 8 | No audit trail for secret access | Medium |
| All 8 | No log masking — secret values could appear in error messages or structured logs | Medium |

---

## 3. Provider Evaluation

### 3.1 Individual Assessments

#### AWS Secrets Manager

- **Pricing:** $0.40/secret/month + $0.05/10,000 API calls. For 8 secrets with 5-min cache TTL: **~$3.20/month + ~$0.01 API costs**. New accounts (post-July 2025) get $200 free tier credits.
- **Node.js SDK:** `@aws-sdk/client-secrets-manager` — official, well-maintained, TypeScript types included, actively developed.
- **Rotation:** Native 4-step Lambda rotation (createSecret → setSecret → testSecret → finishSecret). Maintains `AWSCURRENT` + `AWSPENDING` versions for zero-downtime. For non-RDS secrets: custom Lambda function required.
- **Audit:** CloudTrail integration — every GetSecretValue, PutSecretValue call logged automatically.
- **API quotas:** GetSecretValue: 10,000 TPS. PutSecretValue: 50 TPS. More than sufficient.
- **VPS connectivity:** Requires HTTPS egress to AWS API endpoints. Standard on any VPS.

**Meta-credential problem:** IAM credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) must themselves be stored somewhere on the VPS. Options:
  - If running on EC2: use IAM instance profile (no static credentials needed).
  - If running on non-AWS VPS: IAM credentials stored in env var or systemd credential. This is an accepted one-level-up dependency — the IAM user should have a policy scoped to `secretsmanager:GetSecretValue` + `secretsmanager:DescribeSecret` only. Document this explicitly.

**Solo-operator fit:** Excellent — minimal ops overhead, cost-effective, rotation built-in, no infrastructure to maintain.

#### HashiCorp Vault

- **Pricing:** Free self-hosted (BSL 1.1 license — source-available, NOT open source).
- **Node.js SDK:** `node-vault` — community-maintained, functional but less polished. No official HashiCorp Node.js SDK.
- **Rotation:** Dynamic secrets (most powerful model), time-limited access.
- **Audit:** Comprehensive audit device system.
- **Operational complexity:** Requires HA setup, unsealing ceremony, storage backend, monitoring, backup. **Massive overkill for 8 secrets on a single VPS.**

**Solo-operator fit:** Poor — operational burden vastly exceeds benefit for this deployment profile.

#### SOPS + age

- **Pricing:** Free (Apache 2.0 / BSD).
- **How it works:** Encrypts `.env`/YAML/JSON files at rest using `age` keys. Decrypts at startup via `sops -d`.
- **Node.js integration:** Must shell out via `child_process.execSync('sops -d ...')` at startup — no native Node.js library.
- **Rotation:** Manual only — re-encrypt file with new values, redeploy. No API for programmatic rotation.
- **Audit:** None built-in — git history only.
- **Note:** Could support file-watcher-based refresh for future use if automated rotation is not needed in Phase 1.

**Solo-operator fit:** Good for basic encryption-at-rest only. Insufficient for rotation requirements (FR-PI-07) and audit trail (NFR-S3).

#### Infisical (Self-Hosted)

- **Pricing:** Free self-hosted (MIT license, truly open source).
- **Node.js SDK:** `@infisical/sdk` — official SDK with TypeScript support. Community NestJS wrapper (`nestjs-infisical-sdk`) with `InfisicalModule.registerAsync()` for NestJS DI integration. CLI approach also available: `infisical run -- pnpm start:dev`.
- **Rotation:** Secret rotation support, dynamic secrets. Less mature than AWS but actively developing.
- **Audit:** Built-in audit logs, access controls, web UI for management.
- **Self-hosted requirements:** Runs on the same VPS alongside PostgreSQL (can share the existing Postgres instance). Requires Redis additionally. Docker Compose deployment available.
- **Advantages over AWS for VPS:** Zero external network dependencies for secret retrieval, secrets stay on-premises, no meta-credential problem.
- **Disadvantages:** Additional services to run and maintain (Infisical server + Redis), less battle-tested than AWS, adds operational surface area.

**Solo-operator fit:** Moderate — good features and no vendor lock-in, but adds infrastructure to maintain. Best when operator wants full self-hosted control or has no AWS account.

### 3.2 Comparison Matrix (Weighted Scoring)

| Criteria (Weight) | AWS Secrets Manager | HashiCorp Vault | SOPS+age | Infisical |
|-------------------|:---:|:---:|:---:|:---:|
| Cost at solo-operator scale (20%) | A (~$3/mo) | A (free) | A+ (free) | A (free self-host) |
| Operational complexity (25%) | A (fully managed) | D (complex self-host) | A+ (no infra) | C+ (extra services) |
| Node.js/NestJS SDK maturity (15%) | A (official SDK) | C (community) | D (shell exec) | B+ (official SDK) |
| Rotation support (20%) | A (native, automated) | A+ (dynamic secrets) | F (manual only) | B (supported) |
| Audit logging (10%) | A (CloudTrail) | A (audit devices) | F (none) | B+ (built-in) |
| Portability / no lock-in (10%) | C (AWS-only) | A (multi-cloud) | A (file-based) | A (self-hosted) |
| **Weighted Score** | **A** | **C+** | **C** | **B** |

### 3.3 Recommendation — Architecture Decision Record (ADR)

**ADR-001: External Secrets Manager Provider Selection**

- **Status:** Proposed
- **Context:** The system manages 8 secrets via plain-text `.env` files. PRD requirements FR-PI-06, FR-PI-07, NFR-S1 through NFR-S3 mandate external secrets retrieval, zero-downtime rotation, and audit trails.
- **Decision:**
  - **Primary recommendation: AWS Secrets Manager** — best balance of managed simplicity, rotation capability, audit, and cost for a solo operator.
  - **Co-recommendation: Infisical (self-hosted)** — for operators with no AWS account or strong preference for on-premises secret storage.
- **Decision criteria tree:**
  1. Does the operator have an AWS account? → **AWS Secrets Manager**
  2. No AWS account, willing to self-host? → **Infisical**
  3. Want zero infrastructure, accept no rotation? → **SOPS+age** (Phase 0.5 stopgap only)
- **Consequences:**
  - Story 11.2 implementation must support both AWS and Infisical via a `SecretsProvider` interface.
  - The `SecretsModule` abstracts provider selection behind configuration (`SECRETS_PROVIDER=aws|infisical|env`).
  - Vault is explicitly excluded — operational complexity is disproportionate to the deployment profile.
- **Rationale rejects:**
  - HashiCorp Vault: Operational burden (HA, unsealing, storage backend) for 8 secrets on a single VPS is unjustifiable.
  - SOPS+age: No rotation API, no audit trail — fails FR-PI-07 and NFR-S3.

### 3.4 Architecture Drift Resolution

**ADR-002: Polymarket Encrypted Keystore — Supersede with Secrets Manager**

- **Status:** Proposed
- **Context:** `architecture.md` specifies "AES-256 encrypted keystore file, decrypted at startup with `POLYMARKET_KEYSTORE_PASSWORD`." Implementation uses plain `POLYMARKET_PRIVATE_KEY` env var instead.
- **Decision:** **Supersede the encrypted keystore pattern entirely.** The secrets manager stores the raw private key directly. Rationale:
  1. The encrypted keystore adds a layer of indirection (keystore password → decrypt → private key) that the secrets manager already provides (authenticated API call → decrypted secret).
  2. Implementing both adds complexity without additional security — the keystore password would itself need to be in the secrets manager.
  3. The architecture document should be updated to reflect this decision when Story 11.2 is implemented.
- **Consequences:** Architecture doc line 150 requires update. No `POLYMARKET_KEYSTORE_PASSWORD` env var needed.

---

## 4. Integration Architecture

### 4.1 NestJS Module Design

```
SecretsModule (Global)
├── SecretsService          — fetch/cache/refresh lifecycle, provider abstraction
├── SecretsProviderFactory  — creates AWS or Infisical provider based on config
├── AwsSecretsProvider      — @aws-sdk/client-secrets-manager implementation
├── InfisicalSecretsProvider — @infisical/sdk implementation
└── EnvFallbackProvider     — reads from ConfigService (degraded mode)
```

**Current pattern (direct ConfigService — scattered across constructors):**
```typescript
constructor(private configService: ConfigService<Env, true>) {
  this.apiKey = this.configService.get('KALSHI_API_KEY_ID', '');
}
```

**Target pattern (centralized SecretsService):**
```typescript
@Injectable()
class SecretsService {
  // Typed secret retrieval with cache
  async getSecret(key: SecretKey): Promise<string>;

  // Force refresh from provider (used by rotation endpoint)
  async refreshSecret(key: SecretKey): Promise<string>;

  // Invalidate cache entry (triggers re-fetch on next access)
  invalidate(key: SecretKey): void;

  // Check if running in degraded mode (env fallback)
  isDegraded(): boolean;
}
```

**Key design constraints:**
- `SecretsService` is injectable via standard NestJS DI.
- `SecretsModule.forRootAsync()` with async provider for startup secret fetching.
- Provider selection via `SECRETS_PROVIDER` env var (the one env var that must always be in `.env`).
- `SecretsService` emits `platform.health.degraded` event if secrets manager is unreachable and falls back to env vars.

### 4.2 Sequence Diagrams

#### Startup Bootstrap (SecretsModule → Prisma → ConfigAccessor)

```
Application Start
│
├─1─► SecretsModule.forRootAsync()
│     ├─ Read SECRETS_PROVIDER from env (aws | infisical | env)
│     ├─ Initialize provider (AWS SDK / Infisical SDK)
│     ├─ Fetch ALL 8 secrets from provider
│     │   ├─ On success: cache all secrets, set healthy = true
│     │   └─ On failure: fall back to env vars, emit platform.health.degraded
│     │                  set isDegraded = true
│     └─ SecretsService now available for injection
│
├─2─► PrismaModule (depends on SecretsModule)
│     ├─ Inject SecretsService
│     ├─ Get DATABASE_URL from SecretsService
│     └─ new PrismaClient({ datasourceUrl: secretsService.getSecret('DATABASE_URL') })
│
├─3─► ConfigAccessor (depends on PrismaModule)
│     ├─ Reads Category B settings from engine_config table
│     └─ Caches EffectiveConfig (DB values with env fallback)
│
├─4─► ConnectorModules (depend on SecretsModule)
│     ├─ KalshiConnector: inject SecretsService, get KALSHI_API_KEY_ID + RSA key PEM
│     ├─ PolymarketConnector: inject SecretsService, get POLYMARKET_PRIVATE_KEY
│     └─ ... other consumers
│
└─5─► Application ready
```

**Critical ordering:** `SecretsModule` must resolve `DATABASE_URL` **before** Prisma connects, which must complete **before** `ConfigAccessor` reads the DB. This is enforced via NestJS module `imports` ordering and async `forRootAsync()` factories.

#### Rotation Trigger (HTTP POST → SecretsService → Connector Hot-Swap)

```
Operator: POST /api/admin/rotate-credentials/kalshi
│
├─1─► AdminController validates auth (AuthTokenGuard)
│
├─2─► Check: is hot-path trade in-flight?
│     ├─ Yes: respond 409 Conflict, emit secrets.rotation.deferred
│     └─ No: proceed
│
├─3─► Emit secrets.rotation.pending { platform: 'kalshi', timestamp }
│
├─4─► SecretsService.refreshSecret('KALSHI_API_KEY_ID')
│     SecretsService.refreshSecret('KALSHI_RSA_PRIVATE_KEY')
│     ├─ Fetches latest version from secrets manager
│     ├─ Updates in-memory cache
│     └─ Returns new values
│
├─5─► KalshiConnector.hotSwapCredentials(newApiKeyId, newPrivateKeyPem)
│     ├─ Construct new Configuration object with new credentials
│     ├─ Construct new API client instances (MarketApi, OrdersApi, AccountApi)
│     ├─ Atomic swap: replace this.marketApi, this.ordersApi, this.accountApi
│     └─ Old instances eligible for GC
│
├─6─► Emit secrets.rotation.completed { platform: 'kalshi', timestamp, success: true }
│
└─7─► Respond 200 { data: { rotated: ['KALSHI_API_KEY_ID', 'KALSHI_RSA_PRIVATE_KEY'] } }
```

#### Fallback Activation

```
SecretsService.getSecret('KALSHI_API_KEY_ID')
│
├─ Check cache: cached && (now - cachedAt) < TTL?
│  ├─ Yes: return cached value
│  └─ No: fetch from provider
│
├─ Fetch from secrets manager provider
│  ├─ Success: update cache, return value
│  └─ Failure (network/auth/timeout):
│     ├─ If cache exists (stale): return stale cached value, log warning
│     └─ If no cache:
│        ├─ Fall back to ConfigService.get(envVarName)
│        ├─ Set isDegraded = true
│        ├─ Emit platform.health.degraded {
│        │    source: 'secrets-manager',
│        │    reason: 'unreachable',
│        │    fallback: 'env-var',
│        │    credential: 'KALSHI_API_KEY_ID',
│        │    timestamp
│        │  }
│        └─ Return env var value
│
└─ If isDegraded && provider recovers on next fetch:
   ├─ Set isDegraded = false
   └─ Emit platform.health.recovered { source: 'secrets-manager' }
```

### 4.3 Fallback Strategy

The fallback strategy is layered:

1. **Primary:** Secrets manager (AWS or Infisical)
2. **Stale cache:** If secrets manager is unreachable but cache exists, serve stale cached values with warning
3. **Env var fallback:** If no cache exists, read from `ConfigService` (env var) with `platform.health.degraded` event
4. **No fallback:** If env var also empty, throw `SystemHealthError` (code 4xxx) — system cannot operate without credentials

**Event payload structure for `platform.health.degraded`:**
```typescript
{
  source: 'secrets-manager',
  reason: 'unreachable' | 'auth-failure' | 'timeout',
  fallback: 'stale-cache' | 'env-var' | 'none',
  credential: string,       // which secret failed
  provider: 'aws' | 'infisical',
  timestamp: string,        // ISO 8601
  correlationId: string
}
```

---

## 5. Credential Lifecycle Model

### 5.1 General Lifecycle: fetch → cache → use → refresh → invalidate

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  FETCH   │───►│  CACHE   │───►│   USE    │───►│ REFRESH  │───►│INVALIDATE│
│          │    │          │    │          │    │          │    │          │
│ From     │    │ In-memory│    │ Consumers│    │ TTL-based│    │ On error │
│ provider │    │ Map with │    │ read     │    │ or manual│    │ or manual│
│ or env   │    │ TTL      │    │ from     │    │ rotation │    │ rotation │
│ fallback │    │ metadata │    │ cache    │    │ trigger  │    │ clear    │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
```

**Cache parameters:**
- **Default TTL:** 5 minutes (configurable via `SECRETS_CACHE_TTL_MS` env var)
- **Cache structure:** `Map<SecretKey, { value: string, fetchedAt: number, version?: string }>`
- **Cleanup:** `Map.delete()` on invalidation, `Map.clear()` on module destroy. /** Cleanup: .delete() on invalidation/rotation, .clear() on onModuleDestroy */
- **Version-based invalidation:** For AWS, check `VersionId` on access — if version changed, re-fetch immediately regardless of TTL.

### 5.2 Per-Credential Rotation Atomicity

#### Kalshi (Credentials #1, #2): JWT Invalidation + SDK Reconfiguration

```
1. Operator uploads new RSA key pair to Kalshi platform + secrets manager
2. POST /api/admin/rotate-credentials/kalshi
3. SecretsService fetches new KALSHI_API_KEY_ID + RSA PEM from provider
4. Construct new Configuration({ apiKey: newKeyId, privateKeyPem: newPem })
5. Construct new MarketApi(config), OrdersApi(config), AccountApi(config)
6. Atomic swap: replace instance references (single assignment)
7. Old Configuration + API instances become unreachable → GC
```

**Atomicity guarantee:** JavaScript single-threaded execution ensures reference swaps are atomic. No request can observe a partially-swapped state.

#### Polymarket (Credential #3): Wallet + ClobClient Double-Buffer Swap

```
1. Operator generates new wallet, transfers positions, updates secrets manager
2. POST /api/admin/rotate-credentials/polymarket
3. SecretsService fetches new POLYMARKET_PRIVATE_KEY
4. Construct new ethers.Wallet(newPrivateKey)
5. Construct new ClobClient with new wallet
6. Atomic swap: replace this.wallet and this.clobClient references
7. Old Wallet + ClobClient become unreachable → GC
```

**WARNING:** Polymarket wallet rotation requires on-chain position transfer. This is a manual operator procedure — the rotation endpoint only handles the credential swap, not the position migration.

#### DATABASE_URL (Credential #7): Prisma Pool Drain + Reconnect

```
1. Operator updates DB password in PostgreSQL + secrets manager
2. POST /api/admin/rotate-credentials/database
3. SecretsService fetches new DATABASE_URL
4. Prisma does NOT support runtime connection string changes on existing client
5. Strategy: Create new PrismaClient({ datasourceUrl: newUrl })
6. Drain old client: await oldPrisma.$disconnect()
7. Swap PrismaService.client reference to new instance
8. All subsequent queries use new connection pool
```

**Prisma limitation:** `PrismaClient` does not support changing `datasourceUrl` after construction. The `datasourceUrl` constructor option (or `datasources.db.url`) is read once. Runtime rotation requires creating a new `PrismaClient` instance and swapping the reference in `PrismaService`.

**Risk:** Brief period (~100ms) during pool drain where DB queries may fail. Mitigate by constructing new client first, verifying connectivity, then swapping + disconnecting old. No trade should be in-flight during DB credential rotation.

#### OPERATOR_API_TOKEN (Credential #8): Cache-Based, No Per-Request Secrets Manager Call

```
1. Operator updates token in secrets manager
2. AuthTokenGuard reads from SecretsService cache (NOT from ConfigService)
3. SecretsService cache TTL (5 min) ensures eventual consistency
4. For immediate rotation: POST /api/admin/rotate-credentials/operator → force cache refresh
```

**Critical constraint:** `AuthTokenGuard.canActivate()` runs per HTTP request. Latency budget: <1ms. SecretsService MUST serve from in-memory cache — **never** make a network call to secrets manager per request. If cache is cold at startup, pre-warm during `SecretsModule` initialization.

#### Telegram Bot Token (Credential #6): Manual-Only Rotation

```
1. Operator creates new bot via BotFather
2. Operator updates TELEGRAM_BOT_TOKEN in secrets manager
3. POST /api/admin/rotate-credentials/telegram
4. SecretsService fetches new token
5. TelegramAlertService.hotSwapToken(newToken) — update instance variable
6. Chat ID may change if new bot → operator must also update TELEGRAM_CHAT_ID
```

**Note:** Telegram bot token rotation is inherently manual (requires BotFather interaction). The rotation endpoint handles the credential swap only.

#### LLM API Keys (Credentials #4, #5): SDK Client Reconfiguration

```
1. Operator regenerates API key on provider dashboard (Google AI Studio / Anthropic Console)
2. Operator updates key in secrets manager
3. POST /api/admin/rotate-credentials/llm
4. SecretsService fetches new LLM_PRIMARY_API_KEY and/or LLM_ESCALATION_API_KEY
5. LlmScoringStrategy reconstructs SDK client(s) with new key(s)
6. Next scoring call uses new credentials
```

### 5.3 Race Condition: Rotation During In-Flight Execution

**Problem:** If credential rotation triggers while a two-leg trade is in-flight, the first leg may use old credentials and the second leg may use new (or vice versa). This could cause:
- Auth failure on second leg → single-leg exposure
- Inconsistent state between platforms

**Solution:** Rotation must coordinate with the trading hot path:

```
POST /api/admin/rotate-credentials/:platform
│
├─ 1. Acquire rotation lock (or check TradingEngine.isExecuting())
│     ├─ If trade in-flight: respond 409 Conflict
│     │   { error: { code: 4050, message: 'Rotation deferred: trade in-flight' } }
│     │   Emit secrets.rotation.deferred { platform, reason: 'trade-in-flight' }
│     └─ If idle: proceed
│
├─ 2. Set TradingEngine.rotationInProgress = true
│     (prevents new trades from starting during rotation)
│
├─ 3. Perform rotation (steps above per credential type)
│
├─ 4. Set TradingEngine.rotationInProgress = false
│
└─ 5. Resume trading
```

**Event catalog additions:**
- `secrets.rotation.pending` — rotation about to start
- `secrets.rotation.completed` — rotation finished successfully
- `secrets.rotation.failed` — rotation failed (credentials may be in inconsistent state)
- `secrets.rotation.deferred` — rotation blocked by in-flight trade

### 5.4 Node.js Memory-Zeroing Feasibility

**JavaScript strings are immutable** — once a secret is stored as a JS string, it cannot be zeroed. V8's garbage collector will eventually reclaim the memory, but the timing is non-deterministic. Secrets may persist in heap memory indefinitely.

**Best-effort mitigations:**
1. **Minimize retention:** Don't store secrets in multiple locations. `SecretsService` cache is the single source.
2. **Buffer for sensitive operations:** Where possible, use `Buffer` instead of `string` for secret values (Buffers can be zeroed via `buf.fill(0)`). However, most SDKs (AWS, Kalshi, ethers) accept `string` — so this is limited in practice.
3. **Avoid heap snapshots in production:** Heap snapshots (`v8.writeHeapSnapshot()`) will contain secrets. Document as operational policy: never take heap snapshots on production without sanitization.
4. **Short cache TTL:** 5-minute TTL limits the window of exposure in memory.

**Conclusion:** Full memory-zeroing is infeasible in Node.js for string-based secrets. Accept this as a known limitation and mitigate through operational controls (no heap snapshots, short TTLs, process isolation).

---

## 6. EngineConfig Boundary

### Category A vs Category B — Clear Separation

Story 10-5-2 established a two-tier configuration model. The secrets manager design **must not violate this boundary.**

| Category | Description | Storage | Manager |
|----------|-------------|---------|---------|
| **A (Secrets)** | All 8 credentials listed in §2 | Env vars → Secrets manager (Phase 1) | `SecretsService` (new) |
| **B (Operational settings)** | 71 tunable parameters in `engine_config` table | PostgreSQL DB with env fallback | `ConfigAccessor.getEffectiveConfig()` (existing) |

**Boundary rules:**
- `SecretsService` replaces `ConfigService.get()` calls for Category A credentials **only**.
- `ConfigAccessor` continues to serve Category B settings unchanged.
- Secrets are **NEVER** stored in the `engine_config` database table.
- The Prisma schema comments (lines 56, 67) explicitly state: `// tokens/chatId stay as env secrets` and `// API keys stay as env secrets` — this refers to Category A boundary.
- `SecretsModule` does not depend on `ConfigAccessor`; `ConfigAccessor` does not depend on `SecretsModule`.

### Interaction with `getEffectiveConfig()` Pattern

```
Category B flow (unchanged):
  env.schema.ts → ConfigService → ConfigAccessor.getEffectiveConfig() → DB value ?? env value

Category A flow (new):
  SecretsService → secrets manager → cached value ?? env var fallback (degraded mode)
```

These are **independent, parallel flows** with no intersection.

---

## 7. Key Rotation Design

### 7.1 REST Endpoint (Story 11.3)

```
POST /api/admin/rotate-credentials/:platform
```

**Parameters:**
- `:platform` — `kalshi` | `polymarket` | `database` | `llm` | `telegram` | `operator`

**Request:** No body required — the rotation endpoint instructs `SecretsService` to fetch the latest version from the secrets manager (operator must have already updated the value in the provider).

**Response (success):**
```json
{
  "data": {
    "platform": "kalshi",
    "rotated": ["KALSHI_API_KEY_ID", "KALSHI_RSA_PRIVATE_KEY"],
    "previousVersion": "v1",
    "newVersion": "v2",
    "rotatedAt": "2026-03-23T12:00:00.000Z"
  },
  "timestamp": "2026-03-23T12:00:00.000Z"
}
```

**Response (deferred — trade in-flight):**
```json
{
  "error": {
    "code": 4050,
    "message": "Rotation deferred: trade in-flight. Retry when trading is idle.",
    "severity": "warning"
  },
  "timestamp": "2026-03-23T12:00:00.000Z"
}
```

### 7.2 Rotation Flow Per Platform

See §5.2 for detailed per-credential rotation atomicity sequences.

### 7.3 Verification Step

After rotation, the endpoint should verify the new credentials work:
- **Kalshi:** Call a lightweight API endpoint (e.g., `GET /portfolio/balance`) with new credentials
- **Polymarket:** Sign a test message with new wallet
- **Database:** Execute `SELECT 1` with new connection
- **LLM:** Make a minimal API call with new key
- **Telegram:** Call `getMe` with new bot token
- **Operator:** No verification possible (token is for incoming auth)

If verification fails: roll back to previous cached credentials, emit `secrets.rotation.failed`, respond 500.

---

## 8. Migration Plan

### Phase 0 (Current State)

- All secrets in `.env` files (plain text)
- Docker Compose has hardcoded passwords
- No encryption at rest, no rotation, no audit

### Phase 1 (Story 11.2) — Secrets Manager + Env Fallback

**Changes:**
1. Add `SecretsModule` with `SecretsService`, provider abstraction, cache
2. Add `SECRETS_PROVIDER` env var (`aws` | `infisical` | `env`)
3. Refactor all 8 credential consumers to inject `SecretsService` instead of `ConfigService`
4. Implement env var fallback with `platform.health.degraded` event emission
5. Add rotation endpoint `POST /api/admin/rotate-credentials/:platform`
6. Add pino log redaction for secret field paths
7. Update docker-compose to use `.env` file reference instead of hardcoded credentials

**Migration steps for operator:**
1. Choose provider (AWS or Infisical)
2. Create secrets in provider (same names as env vars)
3. Set `SECRETS_PROVIDER=aws` (or `infisical`) in `.env`
4. For AWS: set `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`
5. For Infisical: set `INFISICAL_CLIENT_ID`, `INFISICAL_CLIENT_SECRET`, `INFISICAL_PROJECT_ID`
6. Restart application — secrets fetched from provider, env vars remain as fallback
7. Verify via dashboard health endpoint

**Docker Compose migration:**
```yaml
# BEFORE (hardcoded):
environment:
  DATABASE_URL: postgresql://postgres:password@postgres:5432/pmarbitrage?schema=public

# AFTER (env file reference):
env_file:
  - .env.production
# .env.production contains DATABASE_URL (or SECRETS_PROVIDER=aws fetches it)
```

For production Docker deployments, consider Docker secrets:
```yaml
services:
  engine:
    secrets:
      - db_url
secrets:
  db_url:
    file: ./secrets/db_url.txt
```

### Phase 2 (Post-Stabilization) — Secrets Manager Required

**Changes:**
1. Remove env var fallback for production (`NODE_ENV=production`)
2. Application refuses to start without secrets manager connectivity (except in development)
3. `SECRETS_PROVIDER=env` still allowed for local development
4. Audit all secret accesses via provider's audit trail

### Phase 2 Activation Criteria
- Story 11.2 has been in production for at least 2 weeks without secrets manager outages
- Operator has verified rotation works for all credential types
- Monitoring confirms no `platform.health.degraded` events from secrets manager

---

## 9. Secret Leak Prevention

### 9.1 Pino Log Redaction

Configure pino `redact` option to mask known secret field paths:

```typescript
const logger = pino({
  redact: {
    paths: [
      'apiKey', 'privateKey', 'privateKeyPem', 'token',
      'password', 'secret', 'credential',
      'data.apiKey', 'data.privateKey', 'data.token',
      'metadata.apiKey', 'metadata.privateKey',
      '*.password', '*.secret', '*.token',
    ],
    censor: '[REDACTED]',
  },
});
```

### 9.2 Error Message Masking

Connector error messages must not include credential values. When catching SDK errors from Kalshi/Polymarket/LLM providers, sanitize the error message before logging or emitting events:

```typescript
// BAD: error.message might contain "Invalid API key: sk-abc123..."
this.logger.error({ message: error.message });

// GOOD: strip potential credential leaks
this.logger.error({ message: sanitizeErrorMessage(error.message) });
```

### 9.3 Heap Snapshot Policy

- **Development:** Heap snapshots allowed (no production credentials)
- **Production:** Heap snapshots MUST NOT be taken without operator acknowledgment that secrets will be exposed. Add a warning to documentation.
- No automated heap snapshot on OOM in production.

---

## 10. Kalshi RSA Key Handling

### Current State
`KALSHI_PRIVATE_KEY_PATH` env var points to `./secrets/key.pem`. The PEM content is read via `readFileSync()` at startup and held in memory as a string.

### Secrets Manager Approach
Store the PEM content directly in the secrets manager (not the file path).

**Multi-line string preservation:** Both AWS Secrets Manager and Infisical support multi-line string values. PEM format uses `\n` line breaks — these must be preserved exactly. When storing:
- AWS: store as plain text secret (not JSON). `GetSecretValue` returns the string with newlines intact.
- Infisical: store as secret value. SDK returns the string as-is.

**No temp file needed:** After migration, the connector reads PEM content from `SecretsService` directly — no file I/O required. The `readFileSync` call is replaced with `await secretsService.getSecret('KALSHI_RSA_PRIVATE_KEY')`.

**Phase 1 compatibility:** During Phase 1 (env fallback), if falling back to env var, the system still reads from `KALSHI_PRIVATE_KEY_PATH` file. Both code paths must be maintained until Phase 2.

---

## 11. Break-Glass / Rollback Procedure

### Operator Lockout Prevention

If secrets manager becomes permanently unreachable AND env var fallback is disabled (Phase 2):
1. Operator sets `SECRETS_PROVIDER=env` in `.env` file
2. Operator ensures all 8 secrets are present in `.env`
3. Restart application — bypasses secrets manager entirely
4. This is an emergency-only procedure — log a `SystemHealthError` at startup

### Secret Version Rollback

If rotated credentials fail after rotation:
1. **AWS:** Use `UpdateSecretVersionStage` API to restore `AWSCURRENT` label to previous version
2. **Infisical:** Use Infisical's point-in-time recovery to restore previous secret version
3. **Application-level:** Call `POST /api/admin/rotate-credentials/:platform` again — it fetches the (now rolled-back) current version from provider

### Emergency Env Var Override

For any credential, the system should accept an env var override that takes precedence over the secrets manager value. This provides a last-resort mechanism:

```
SECRETS_OVERRIDE_KALSHI_API_KEY_ID=emergency-key-id
```

If `SECRETS_OVERRIDE_<KEY>` is set, `SecretsService.getSecret(key)` returns it directly, bypassing cache and provider. Emits `secrets.override.active` event.

---

## 12. Testing Strategy (Story 11.2)

### Unit Tests
- Mock `SecretsProvider` interface — test `SecretsService` cache TTL, invalidation, fallback logic
- Test each per-credential rotation sequence with mocked connectors
- Test `AuthTokenGuard` with `SecretsService` instead of `ConfigService`

### Integration Tests
- **LocalStack** (for AWS): Run `localstack` Docker container with `secretsmanager` service enabled. Tests create/read/rotate real secrets in LocalStack.
- **Infisical test mode:** Use Infisical's Docker Compose for local self-hosted instance in CI.
- **Environment variable fallback:** Test degraded mode by making secrets manager unavailable.

### E2E Tests
- Full startup with secrets manager → verify all connectors initialize correctly
- Rotation endpoint → verify credentials are swapped and old ones no longer used
- Fallback activation → verify `platform.health.degraded` event and continued operation

### Test Configuration
```
# test.env — for CI/CD
SECRETS_PROVIDER=env  # Tests use env vars by default
# Integration tests override to SECRETS_PROVIDER=aws with LocalStack endpoint
AWS_ENDPOINT_URL=http://localhost:4566  # LocalStack
```

---

## 13. Open Questions for Operator Decision (Before Story 11.2)

| # | Question | Impact | Default if Undecided |
|---|----------|--------|---------------------|
| 1 | AWS or Infisical? | Provider selection, SDK dependencies | AWS (if operator has AWS account) |
| 2 | Should Phase 1 support both providers simultaneously, or just the chosen one? | Implementation complexity | Single provider + env fallback |
| 3 | Cache TTL for secrets: 5 minutes acceptable? | Latency vs freshness trade-off | 5 minutes |
| 4 | Should DB credential rotation require application restart or attempt live swap? | Prisma limitation complexity | Live swap (new PrismaClient instance) |
| 5 | Is SOPS+age acceptable as a Phase 0.5 stopgap (encryption at rest, no rotation)? | Incremental security improvement | Skip — go directly to Phase 1 |
| 6 | Acceptable downtime window during DB credential rotation? | Operational planning | ~100ms (connection pool drain/reconnect) |
| 7 | Should `SECRETS_OVERRIDE_*` emergency env vars be supported? | Break-glass complexity | Yes (safety net) |
| 8 | How should Kalshi RSA key be generated and distributed? Operator-managed or automated? | Operational procedure | Operator-managed (manual upload to both Kalshi and secrets manager) |

---

## References

- PRD: FR-PI-06, FR-PI-07, NFR-S1, NFR-S2, NFR-S3
- Architecture: `_bmad-output/planning-artifacts/architecture.md` lines 148-151, 222-225
- Env schema: `pm-arbitrage-engine/src/common/config/env.schema.ts`
- ConfigAccessor: `pm-arbitrage-engine/src/common/config/config-accessor.service.ts`
- Prisma schema: `pm-arbitrage-engine/prisma/schema.prisma`
- Kalshi connector: `pm-arbitrage-engine/src/connectors/kalshi/kalshi.connector.ts`
- Polymarket connector: `pm-arbitrage-engine/src/connectors/polymarket/polymarket.connector.ts`
- Auth guard: `pm-arbitrage-engine/src/common/guards/auth-token.guard.ts`
- Telegram service: `pm-arbitrage-engine/src/modules/monitoring/telegram-alert.service.ts`
- AWS Secrets Manager pricing: $0.40/secret/month + $0.05/10K API calls (March 2026)
- Infisical docs: infisical.com/docs/integrations/frameworks/nestjs
- Prisma datasourceUrl: Supported in PrismaClient constructor, not changeable at runtime
- Node.js CVE-2025-55131: Buffer.alloc race condition (patched in 22.22.0+)
