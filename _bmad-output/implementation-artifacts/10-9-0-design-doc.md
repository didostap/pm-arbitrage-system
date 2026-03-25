# Epic 10.9 Design Spike: Backtesting & System Calibration

**Story:** 10-9-0 | **Date:** 2026-03-26 | **Status:** Accepted — Gate review passed

---

## 1. Data Source API Verification

### 1.1 Kalshi Historical API

**Base URL:** `https://api.elections.kalshi.com/trade-api/v2`

#### Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/historical/cutoff` | GET | None | Returns partition boundary timestamps |
| `/historical/markets/{ticker}/candlesticks` | GET | None | OHLCV candlestick data |
| `/historical/trades` | GET | None | Cursor-paginated trade history |

#### `/historical/cutoff` — Partition Boundary

Returns three timestamps that determine whether to query historical or live endpoints:

| Field | Partitioned By | Meaning |
|-------|---------------|---------|
| `market_settled_ts` | Settlement time | Markets settled before this → use `/historical/markets` |
| `trades_created_ts` | Fill time | Trades before this → use `/historical/trades` |
| `orders_updated_ts` | Cancel/execution time | Orders before this → use `/historical/orders` |

**Response:** ISO 8601 date-time strings. No auth required.

**CRITICAL:** The cutoff is a **moving boundary** — it advances forward over time. Initial lookback ~1 year (from Feb 19, 2026 launch). Target steady-state: ~3 months in live endpoints, rest in historical. Integration **must** call cutoff before routing queries.

#### `/historical/markets/{ticker}/candlesticks`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ticker` | string (path) | Yes | Market ticker |
| `start_ts` | int64 (query) | Yes | Unix timestamp — candles ending on/after |
| `end_ts` | int64 (query) | Yes | Unix timestamp — candles ending on/before |
| `period_interval` | enum int (query) | Yes | `1` (1min), `60` (1hr), `1440` (1day) only |

**Response schema:**
```json
{
  "ticker": "<string>",
  "candlesticks": [{
    "end_period_ts": 123,
    "yes_bid": { "open": "0.5600", "low": "0.5600", "high": "0.5600", "close": "0.5600" },
    "yes_ask": { "open": "0.5600", "low": "0.5600", "high": "0.5600", "close": "0.5600" },
    "price": {
      "open": "0.5600", "low": "0.5600", "high": "0.5600", "close": "0.5600",
      "mean": "0.5600", "previous": "0.5600"
    },
    "volume": "10.00",
    "open_interest": "10.00"
  }]
}
```

**Prices are dollar strings** (e.g., `"0.5600"`) — already in 0.00–1.00 probability range. Normalize via `new Decimal(value)`.

#### `/historical/trades`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ticker` | string | No | Filter by market ticker |
| `min_ts` | int64 | No | Filter trades after this Unix timestamp |
| `max_ts` | int64 | No | Filter trades before this Unix timestamp |
| `limit` | int64 | No | Results per page, 1–1000 (default: 100) |
| `cursor` | string | No | Pagination cursor from previous response |

**Response schema:**
```json
{
  "trades": [{
    "trade_id": "<string>",
    "ticker": "<string>",
    "count_fp": "10.00",
    "yes_price_dollars": "0.5600",
    "no_price_dollars": "0.5600",
    "taker_side": "yes",
    "created_time": "2023-11-07T05:31:56Z"
  }],
  "cursor": "<string>"
}
```

**Note:** This endpoint was added March 6, 2026 — relatively new.

#### Auth (for protected endpoints)

RSA-PSS signature with SHA-256. Three headers:

| Header | Value |
|--------|-------|
| `KALSHI-ACCESS-KEY` | API Key ID (UUID) |
| `KALSHI-ACCESS-TIMESTAMP` | Current time in **milliseconds** |
| `KALSHI-ACCESS-SIGNATURE` | Base64 RSA-PSS signature of `{timestamp_ms}{METHOD}{path_without_query}` |

**Historical data endpoints are PUBLIC** — no auth headers required. Auth only needed for user-scoped endpoints (`/historical/fills`, `/historical/orders`).

#### Rate Limits

| Tier | Read/sec | Write/sec |
|------|----------|-----------|
| Basic | 20 | 10 |
| Advanced | 30 | 30 |
| Premier | 100 | 100 |
| Prime | 400 | 400 |

At 70% utilization with 20% safety buffer: effective max **14 req/sec** at Basic tier.

#### Gotchas & Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| K1 | **Field naming divergence** — historical uses `open`/`volume`, live uses `open_dollars`/`volume_fp` | Certain | High | Separate parsers per endpoint; normalization layer maps both to common schema |
| K2 | **Moving cutoff boundary** — data partition shifts over time | Certain | Medium | Cache cutoff with TTL (1hr); query cutoff before each batch ingestion run |
| K3 | **Data removed from live endpoints** (March 6, 2026) | Done | High | Always route via cutoff; never assume data exists in live endpoints |
| K4 | **Historical endpoint is new** (added March 6, 2026) | Known | Low | Monitor for schema changes; pin response parsing |
| K5 | **Subpenny pricing** — some markets have price levels < $0.01 | Possible | Low | Check `price_level_structure` field; Decimal handles arbitrary precision |

---

### 1.2 Polymarket CLOB API

**Base URL:** `https://clob.polymarket.com`

#### `/prices-history`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `market` | string | **Yes** | **Token ID** (asset ID) — large decimal number. NOT condition_id, NOT slug |
| `startTs` | number | No | Unix timestamp (seconds) — filter after |
| `endTs` | number | No | Unix timestamp (seconds) — filter before |
| `interval` | enum | No | `max`, `all`, `1m`, `1w`, `1d`, `6h`, `1h` |
| `fidelity` | int | No | Data resolution in minutes (default: 1) |

**`startTs`/`endTs` and `interval` are NOT mutually exclusive** — they can be combined. `interval` sets the window, `startTs`/`endTs` constrain further. Test empirically for combined behavior.

**Response:**
```json
{
  "history": [
    { "t": 1700000000, "p": 0.65 }
  ]
}
```

- `t` = Unix timestamp (seconds)
- `p` = Decimal probability (0.00–1.00) — **no conversion needed**

**Auth:** None. Read-only market data endpoint.

**Rate limit:** 1,000 req/10s. Cloudflare **throttles (queues/delays)** rather than returning 429 — requests may hang instead of failing cleanly.

#### Gotchas & Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| P1 | **Token ID confusion** — `market` param takes token_id, not condition_id or slug. Each binary market has TWO token IDs (Yes/No) | Certain | Critical | Map ContractMatch.polymarketClobTokenId to token ID; document clearly |
| P2 | **Throttling, not rejection** — Cloudflare queues requests instead of 429 | Certain | Medium | Set HTTP timeout (30s); detect slow responses as rate limiting signal |
| P3 | **Large payloads** — 1-min fidelity over months = massive response | Likely | Medium | Increase fidelity for long ranges; paginate by time window |
| P4 | **Geographic restrictions** — IP-level blocking for some jurisdictions | Possible | High | Monitor; document deployment region requirements |

---

### 1.3 Goldsky Subgraph

**Endpoint:** `https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn`

**Protocol:** GraphQL POST. **Auth:** None. **Rate limit:** 100 req/s per IP (1,000 req/10s).

#### `OrderFilledEvent` Schema

```graphql
type OrderFilledEvent @entity {
  id: ID!                      # txHash + orderHash
  transactionHash: Bytes!
  timestamp: BigInt!            # Unix timestamp
  orderHash: Bytes!
  maker: String!               # Maker address
  taker: String!               # Taker address
  makerAssetId: String!        # Maker asset token ID
  takerAssetId: String!        # Taker asset token ID
  makerAmountFilled: BigInt!   # Raw units (÷10^6 for USDC)
  takerAmountFilled: BigInt!   # Raw units (÷10^6 for USDC)
  fee: BigInt!                 # Fee paid by maker
}
```

**CRITICAL:** No `side`, `price`, or `blockNumber` fields on the entity. Must **derive** using the following algorithm:

```
USDC_ASSET_ID = "..." // Collateral token ID (constant, from Polymarket docs)

1. Identify direction:
   if makerAssetId == USDC_ASSET_ID:
     side = 'buy'  // Maker pays USDC for outcome tokens
     usdcAmount = makerAmountFilled / 10^6
     tokenAmount = takerAmountFilled / 10^6
   else if takerAssetId == USDC_ASSET_ID:
     side = 'sell'  // Taker pays USDC, maker sells outcome tokens
     usdcAmount = takerAmountFilled / 10^6
     tokenAmount = makerAmountFilled / 10^6
   else:
     skip  // token-to-token trade, not relevant

2. Derive price:  price = usdcAmount / tokenAmount  (0-1 range)

3. Fee: fee field is post-fill maker deduction. Derived price is pre-fee — use as-is.

4. Size:  size = usdcAmount  (trade size in USD)
```

**Token ID mapping:** Cross-reference the non-USDC asset ID with `ContractMatch.polymarketClobTokenId` to identify the contract.

#### Other Available Entities

| Entity | Key Fields | Use Case |
|--------|-----------|----------|
| `Orderbook` | `tradesQuantity`, `collateralVolume`, `scaledCollateralVolume` | Aggregate volume per token |
| `MarketData` | `condition`, `outcomeIndex` | Market ↔ token mapping |
| `OrdersMatchedEvent` | `makerAmountFilled`, `takerAmountFilled` | Simpler trade events |

#### Gotchas & Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| G1 | **No price/side fields** — must derive from amounts and asset IDs | Certain | High | Build derivation logic; maintain USDC token ID mapping |
| G2 | **Two exchange contracts** — CTF Exchange + Neg Risk Exchange | Certain | Medium | Verify subgraph indexes both; filter by relevant contracts |
| G3 | **Heavy subgraph** — Polymarket subgraphs accumulate data rapidly | Known | Medium | Use time-bounded queries; cursor-based pagination (id_gt) |
| G4 | **Version pinning** (`0.0.1`) — schema may update | Possible | Medium | Monitor for new versions; pin in config |
| G5 | **Per-IP rate limiting** — no way to increase without Goldsky support | Known | Low | Stay within 70 req/s (70% of 100) |

**Source:** https://github.com/Polymarket/polymarket-subgraph (398+ commits, actively maintained)

---

### 1.4 PMXT Archive

**Base URL:** `https://archive.pmxt.dev/data/`

**Auth:** None. Direct HTTP download from public directory listing.

#### File Format

| Attribute | Value |
|-----------|-------|
| Naming | `polymarket_orderbook_YYYY-MM-DDTHH.parquet` |
| Granularity | Hourly snapshots, UTC |
| File sizes | 150–605 MB/hour (off-peak ~150MB, peak ~600MB) |
| Daily total | ~5–12 GB |
| Content | L2 orderbook data (bids/asks) |
| `update_type` | `price_change` (level updates) and `book_snapshot` (full snapshots) — **unconfirmed, needs Parquet inspection** |
| Also available | Kalshi data in `/data/Kalshi/` directory |

**Node.js SDK:** `pmxtjs` (npm, v2.22.1) — provides `fetchOrderBook()`, `fetchOHLCV()`, `fetchTrades()`. Prices 0.0–1.0, timestamps in Unix ms. **Note:** pmxtjs is for **live** data; archive.pmxt.dev is for **historical** dumps — complementary but separate tools.

#### Gotchas & Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| M1 | **No schema documentation** — must inspect Parquet files to discover columns | Certain | Medium | Download one file and run `pyarrow.parquet.read_schema()` before building parser |
| M2 | **Massive bandwidth** — full day = 5–12 GB | Certain | High | Incremental download strategy; only fetch needed hours |
| M3 | **No SLA or uptime guarantee** — community-run, sponsor-supported | Known | Medium | Treat as supplementary source; fallback to Predexon orderbook data |
| M4 | **Early reliability issues** — went down shortly after launch due to demand | Known | Medium | Retry with exponential backoff; don't depend on for critical path |
| M5 | **`book_snapshot` periodicity is irregular** — not every hour has full snapshots | Likely | Medium | Interpolation strategy for gaps; document limitations in backtest reports |

---

### 1.5 OddsPipe

**Base URL:** `https://oddspipe.com/v1`

**Auth:** `X-API-Key` header. Free signup (email only, instant).

#### Endpoints

| Endpoint | Params | Response |
|----------|--------|----------|
| `GET /v1/markets/{id}/candlesticks` | `interval`: 1m, 5m, 1h, 1d | OHLCV candlestick data |
| `GET /v1/spreads` | `min_spread`: decimal (e.g., 0.03) | Cross-platform divergences with `yes_diff` |
| `GET /v1/markets/search` | `q`: search text, platform/status filters | Full-text market search |

#### Limits

| Tier | Rate | History | Price | Status |
|------|------|---------|-------|--------|
| Free | 100 req/min | **30 days only** | $0 | Available |
| Pro | Higher limits | Full archive | $99/mo | **Coming Soon — NOT available** |

**SDK:** Python only (`pip install oddspipe`). **No Node.js/TypeScript SDK** — raw HTTP calls from NestJS.

**Matched pairs:** 2,500+ cross-platform pairs via fuzzy title matching with post-validation rules.

#### Gotchas & Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| O1 | **30-day history limit** — severely limits backtesting utility | Certain | Critical | Use as supplementary/validation source only; not primary historical data |
| O2 | **Pro tier not available** — "Coming Soon"; no timeline | Known | High | Cannot rely on full history access; use Predexon or platform APIs instead |
| O3 | **Very new** (~18 days since Reddit launch) — limited track record | Known | Medium | Light integration; don't build critical dependencies |
| O4 | **No TypeScript SDK** — Python only | Certain | Low | Raw REST calls; straightforward endpoints |
| O5 | **Fuzzy matching accuracy** — unverified at scale | Possible | Medium | Cross-validate against Predexon and our ContractMatch data |

---

### 1.6 Predexon

**Base URL:** `https://api.predexon.com`

**Auth:** `x-api-key` header (lowercase). Free key at `dashboard.predexon.com`.

#### Free Endpoints (All Plans — Unlimited, Don't Count Toward Monthly Quota)

| Endpoint | Description |
|----------|-------------|
| `GET /v2/polymarket/candlesticks/{condition_id}` | OHLCV; intervals: 1 (1m), 60 (1h), 1440 (1d) |
| `GET /v2/polymarket/trades` | Trade history, cursor pagination |
| `GET /v2/polymarket/orderbooks` | Orderbook history snapshots |
| `GET /v2/polymarket/markets` | List/search markets |
| `GET /v2/polymarket/market-price/{token_id}` | Current price |
| `GET /v2/kalshi/markets` | Kalshi market listing |
| `GET /v2/kalshi/trades` | Kalshi trade history |
| `GET /v2/kalshi/orderbooks` | Kalshi orderbook history |

**Candlestick time range limits:** 1m = max 7 days, 1h = max 30 days, 1d = max 365 days.

**Historical depth:** 5+ years (since 2020).

#### Paid Endpoints (Dev+ $49/mo)

| Endpoint | Description |
|----------|-------------|
| `GET /v2/matching-markets` | Find matching markets (pass slug or condition_id) |
| `GET /v2/matching-markets/pairs` | Pre-computed matched pairs |

Claims **99%+ matching accuracy** with thousands of manually labeled data points. `match_type` removed in v2 — all pairs are exact matches (similarity >= 95%).

#### Rate Limits

| Tier | Rate | Monthly | Price |
|------|------|---------|-------|
| Free | 1 req/sec | 1,000 (gated endpoints only) | $0 |
| Dev | 20 req/sec | 1,000,000 | $49/mo |
| Pro | 100 req/sec | 5,000,000 | $249/mo |

**Note:** Free monthly limit only counts toward gated endpoints. Core data endpoints are unlimited.

**OpenAPI 3.0 spec available** — enables `swagger-typescript-api` client generation (same pattern as dashboard API client).

#### Gotchas & Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| D1 | **Seconds vs milliseconds** — candlesticks use seconds, orderbooks use milliseconds | Certain | High | Per-endpoint timestamp normalization; explicit unit conversion in parser |
| D2 | **Free tier too slow for production** — 1 req/sec, 1K/month gated | Certain | Medium | Dev tier ($49/mo) required for matching validation; free endpoints sufficient for data |
| D3 | **Kalshi data gap** — March 12–14, 2026 (upstream API format change) | Known | Low | Document gap; fill from Kalshi direct API if needed |
| D4 | **No Node.js data SDK** — TypeScript SDK is trading-only | Certain | Low | Raw REST calls or generate client from OpenAPI spec |
| D5 | **LLM-based matching** — small % may be incorrect | Known | Low | Cross-validate against our ContractMatch + OddsPipe |

---

### 1.7 poly_data

**Repository:** `github.com/warproxxx/poly_data` | **Stars:** 646 | **Forks:** 152

| Attribute | Value |
|-----------|-------|
| Language | Python (48.2%) + Jupyter (50.8%) |
| Package manager | UV (`uv sync`, `uv run`) |
| Last commit | Feb 20, 2026 |
| License | Informal ("Go wild with it") |

**Bootstrap snapshot:** Saves 2+ days of initial Goldsky subgraph collection. Download link in README.

**Output files:**
- `markets.csv` — Market metadata (id, question, tokens, condition_id, volume)
- `goldsky/orderFilled.csv` — Raw on-chain fill events
- `processed/trades.csv` — Structured trades (timestamp, price, usd_amount, side)

**Backtesting examples:** Includes `Example 2 Backtest.ipynb` with backtrader integration.

**Use case:** Bootstrap Polymarket trade data for initial backtest dataset. **Not a runtime dependency** — Python-only batch pipeline.

---

### 1.8 Cost-Benefit Assessment

| Service | Tier | Cost | Value for Calibration | Recommendation |
|---------|------|------|----------------------|----------------|
| Predexon Dev | $49/mo | Matching pairs (99%+), 20 req/sec, 1M req/mo | **High** — validates our ContractMatch, free data endpoints for prices/trades/orderbooks | **Subscribe** — strongest data source for calibration |
| OddsPipe Pro | $99/mo | Full history, higher limits | **Low** — not yet available; free tier has 30-day limit | **Skip** — revisit when Pro launches |

**Rationale:** Predexon free endpoints already provide unlimited candlesticks, trades, and orderbooks for both platforms with 5+ years of history. The $49/mo Dev tier adds cross-platform matching validation — critical for AC2 of story 10-9-2. OddsPipe's 30-day free limit makes it supplementary at best, and Pro isn't available.

---

### 1.9 Integration Risk Matrix

| Source | Reliability | Data Quality | Rate Limit Risk | Fallback |
|--------|------------|-------------|----------------|----------|
| Kalshi API | **High** — official, stable | **High** — dollar strings, documented schema | Low (20 req/sec sufficient for batch) | Predexon Kalshi endpoints |
| Polymarket API | **High** — official, no auth | **High** — decimal probability, clean | Low (1K req/10s generous) | Predexon Polymarket endpoints |
| Goldsky | **High** — infrastructure-grade | **Medium** — requires price/side derivation | Low (100 req/s) | poly_data bootstrap for trade data |
| PMXT Archive | **Medium** — community-run, early reliability issues | **Unknown** — schema undocumented | N/A (file download) | Predexon orderbook endpoints |
| OddsPipe | **Low** — 18 days old, limited track record | **Medium** — fuzzy matching | Low (100 req/min) | Predexon for matching, platform APIs for data |
| Predexon | **High** — 100+ customers, established | **High** — OpenAPI spec, documented | Medium (1 req/sec free) | Platform APIs direct |
| poly_data | **Medium** — community, Python-only | **High** — structured output | N/A (local batch) | Goldsky direct queries |

**Primary data path:** Kalshi API + Polymarket API + Predexon (free endpoints) for prices/trades. PMXT Archive or Predexon for depth. Predexon Dev ($49/mo) for matching validation.

**Secondary/validation:** OddsPipe spreads for cross-validation. poly_data for Polymarket trade bootstrap. Goldsky for on-chain verification.

---

## 2. Data Persistence Strategy

### 2.1 Prisma Model Definitions

#### New Enums

```prisma
enum HistoricalDataSource {
  KALSHI_API        @map("kalshi_api")
  POLYMARKET_API    @map("polymarket_api")
  GOLDSKY           @map("goldsky")
  PMXT_ARCHIVE      @map("pmxt_archive")
  ODDSPIPE          @map("oddspipe")
  PREDEXON          @map("predexon")
  POLY_DATA         @map("poly_data")
}

enum BacktestStatus {
  IDLE              @map("idle")
  CONFIGURING       @map("configuring")
  LOADING_DATA      @map("loading_data")
  SIMULATING        @map("simulating")
  GENERATING_REPORT @map("generating_report")
  COMPLETE          @map("complete")
  FAILED            @map("failed")
  CANCELLED         @map("cancelled")
}

enum BacktestExitReason {
  EDGE_EVAPORATION       @map("edge_evaporation")
  TIME_DECAY             @map("time_decay")
  PROFIT_CAPTURE         @map("profit_capture")
  RESOLUTION_FORCE_CLOSE @map("resolution_force_close")
  INSUFFICIENT_DEPTH     @map("insufficient_depth")
  RISK_BUDGET            @map("risk_budget")
  LIQUIDITY_DETERIORATION @map("liquidity_deterioration")
}
```

#### `HistoricalPrice` — OHLCV Candlestick Data

```prisma
model HistoricalPrice {
  id                Int                  @id @default(autoincrement())
  platform          PlatformId
  contractId        String               @map("contract_id")
  source            HistoricalDataSource
  intervalMinutes   Int                  @map("interval_minutes")  // 1, 5, 60, 1440
  timestamp         DateTime             // Period end timestamp
  open              Decimal              @db.Decimal(20, 10)
  high              Decimal              @db.Decimal(20, 10)
  low               Decimal              @db.Decimal(20, 10)
  close             Decimal              @db.Decimal(20, 10)
  volume            Decimal?             @db.Decimal(20, 6)
  openInterest      Decimal?             @map("open_interest") @db.Decimal(20, 6)
  ingestionTs       DateTime             @default(now()) @map("ingestion_ts")
  qualityFlags      Json?                @map("quality_flags")
  createdAt         DateTime             @default(now()) @map("created_at")

  @@unique([platform, contractId, source, intervalMinutes, timestamp], name: "uq_historical_price")
  @@index([platform, contractId, timestamp], name: "idx_price_contract_time")
  @@index([source, timestamp], name: "idx_price_source_time")
  @@index([timestamp], name: "idx_price_time")
  @@map("historical_prices")
}
```

#### `HistoricalTrade` — Individual Fill Records

```prisma
model HistoricalTrade {
  id                Int                  @id @default(autoincrement())
  platform          PlatformId
  contractId        String               @map("contract_id")
  source            HistoricalDataSource
  externalTradeId   String?              @map("external_trade_id")
  price             Decimal              @db.Decimal(20, 10)
  size              Decimal              @db.Decimal(20, 6)
  side              String               // 'buy' | 'sell'
  timestamp         DateTime
  ingestionTs       DateTime             @default(now()) @map("ingestion_ts")
  qualityFlags      Json?                @map("quality_flags")
  createdAt         DateTime             @default(now()) @map("created_at")

  @@unique([platform, contractId, source, externalTradeId], name: "uq_historical_trade")
  @@index([platform, contractId, timestamp], name: "idx_trade_contract_time")
  @@index([source, timestamp], name: "idx_trade_source_time")
  @@index([timestamp], name: "idx_trade_time")
  @@map("historical_trades")
}
```

#### `HistoricalDepth` — L2 Orderbook Snapshots

```prisma
model HistoricalDepth {
  id                Int                  @id @default(autoincrement())
  platform          PlatformId
  contractId        String               @map("contract_id")
  source            HistoricalDataSource
  bids              Json                 // Array of {price: string, size: string}
  asks              Json                 // Array of {price: string, size: string}
  timestamp         DateTime
  updateType        String?              @map("update_type")  // 'snapshot' | 'price_change'
  ingestionTs       DateTime             @default(now()) @map("ingestion_ts")
  qualityFlags      Json?                @map("quality_flags")
  createdAt         DateTime             @default(now()) @map("created_at")

  @@index([platform, contractId, timestamp], name: "idx_depth_contract_time")
  @@index([source, timestamp], name: "idx_depth_source_time")
  @@index([timestamp], name: "idx_depth_time")
  @@map("historical_depths")
}
```

#### `BacktestRun` — Backtest Execution Record

```prisma
model BacktestRun {
  id                  String          @id @default(uuid())
  status              BacktestStatus  @default(IDLE)
  config              Json            // BacktestConfig DTO serialized
  dateRangeStart      DateTime        @map("date_range_start")
  dateRangeEnd        DateTime        @map("date_range_end")
  totalPositions      Int?            @map("total_positions")
  profitablePositions Int?            @map("profitable_positions")
  totalPnl            Decimal?        @map("total_pnl") @db.Decimal(20, 6)
  maxDrawdown         Decimal?        @map("max_drawdown") @db.Decimal(20, 6)
  sharpeRatio         Decimal?        @map("sharpe_ratio") @db.Decimal(10, 4)
  profitFactor        Decimal?        @map("profit_factor") @db.Decimal(10, 4)
  winRate             Decimal?        @map("win_rate") @db.Decimal(10, 4)
  avgHoldingHours     Decimal?        @map("avg_holding_hours") @db.Decimal(10, 2)
  capitalUtilization  Decimal?        @map("capital_utilization") @db.Decimal(10, 4)
  report              Json?           // Full calibration report
  walkForwardResults  Json?           @map("walk_forward_results")
  sensitivityResults  Json?           @map("sensitivity_results")
  error               String?
  startedAt           DateTime?       @map("started_at")
  completedAt         DateTime?       @map("completed_at")
  createdAt           DateTime        @default(now()) @map("created_at")
  updatedAt           DateTime        @updatedAt @map("updated_at")

  positions           BacktestPosition[]

  @@index([status], name: "idx_backtest_status")
  @@index([createdAt], name: "idx_backtest_created")
  @@map("backtest_runs")
}
```

#### `BacktestPosition` — Simulated Position Record

```prisma
model BacktestPosition {
  id                    Int              @id @default(autoincrement())
  backtestRunId         String           @map("backtest_run_id")
  pairId                String           @map("pair_id")
  entryTimestamp        DateTime         @map("entry_timestamp")
  exitTimestamp         DateTime?        @map("exit_timestamp")
  kalshiSide            String           @map("kalshi_side")
  polymarketSide        String           @map("polymarket_side")
  kalshiEntryPrice      Decimal          @map("kalshi_entry_price") @db.Decimal(20, 10)
  polymarketEntryPrice  Decimal          @map("polymarket_entry_price") @db.Decimal(20, 10)
  kalshiExitPrice       Decimal?         @map("kalshi_exit_price") @db.Decimal(20, 10)
  polymarketExitPrice   Decimal?         @map("polymarket_exit_price") @db.Decimal(20, 10)
  size                  Decimal          @db.Decimal(20, 6)
  entryEdge             Decimal          @map("entry_edge") @db.Decimal(20, 10)
  exitReason            BacktestExitReason? @map("exit_reason")
  realizedPnl           Decimal?         @map("realized_pnl") @db.Decimal(20, 6)
  fees                  Decimal          @db.Decimal(20, 6)
  createdAt             DateTime         @default(now()) @map("created_at")

  backtestRun           BacktestRun      @relation(fields: [backtestRunId], references: [id], onDelete: Cascade)

  @@index([backtestRunId], name: "idx_bt_pos_run")
  @@index([pairId], name: "idx_bt_pos_pair")
  @@map("backtest_positions")
}
```

### 2.2 Monthly Partition Strategy

Aligned with existing `OrderBookSnapshot` architecture (referenced in architecture doc lines 665–682):

```sql
-- Partition historical_prices by month on timestamp
CREATE TABLE historical_prices (
  -- columns as above
) PARTITION BY RANGE (timestamp);

CREATE TABLE historical_prices_2025_01 PARTITION OF historical_prices
  FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
-- ... repeat per month
```

**Partition tables:** `historical_prices`, `historical_trades`, `historical_depths`.

**Non-partitioned:** `backtest_runs`, `backtest_positions` (low volume, query patterns don't benefit from partitioning).

**Partition management:** Create partitions 3 months ahead via startup check or migration. Monthly cron to create new partitions.

### 2.3 Index Strategy

| Table | Index | Columns | Purpose |
|-------|-------|---------|---------|
| `historical_prices` | `uq_historical_price` | `(platform, contractId, source, intervalMinutes, timestamp)` UNIQUE | Idempotent upsert |
| `historical_prices` | `idx_price_contract_time` | `(platform, contractId, timestamp)` | Backtest range queries by contract |
| `historical_prices` | `idx_price_source_time` | `(source, timestamp)` | Data quality monitoring by source |
| `historical_prices` | `idx_price_time` | `(timestamp)` | Partition pruning, retention cleanup |
| `historical_trades` | `uq_historical_trade` | `(platform, contractId, source, externalTradeId)` UNIQUE | Idempotent upsert (when externalTradeId available) |
| `historical_trades` | `idx_trade_contract_time` | `(platform, contractId, timestamp)` | Trade lookup by contract |
| `historical_depths` | `idx_depth_contract_time` | `(platform, contractId, timestamp)` | Depth lookup for VWAP modeling |

### 2.4 Batch Insert Strategy

**Primary:** Prisma `createMany` with `skipDuplicates: true` for idempotent batch inserts.

```typescript
await prisma.historicalPrice.createMany({
  data: normalizedPrices,
  skipDuplicates: true,  // Leverages unique constraint
});
```

**High-volume fallback:** For PMXT Archive data (thousands of depth snapshots per hour), use raw SQL `INSERT ... ON CONFLICT DO NOTHING` via `$executeRaw` for better performance:

```typescript
await prisma.$executeRaw`
  INSERT INTO historical_depths (platform, contract_id, source, bids, asks, timestamp, ingestion_ts)
  SELECT * FROM UNNEST(${platforms}::text[], ${contractIds}::text[], ...)
  ON CONFLICT DO NOTHING
  -- MODE-FILTERED
`;
```

**Batch sizing:** 500 records per transaction for `createMany`; 1,000 for raw SQL.

### 2.5 Hybrid Storage Assessment

| Approach | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| **PostgreSQL only** | Single query interface, joins with other tables, existing Prisma tooling | 150–600MB Parquet files → DB bloat; slow ingestion | **Use for processed/sampled depth data** |
| **Parquet files only** | No ingestion overhead, native PMXT format, fast columnar reads | Separate query path, no SQL joins, needs parquet-wasm or Node binding | **Use for raw PMXT Archive storage** |
| **Hybrid** | Best of both — raw Parquet for archive, PostgreSQL for queried subset | Two code paths, complexity | **Recommended** |

**Decision:** Hybrid approach.
- **Raw PMXT Parquet files:** Store in `data/pmxt-archive/` directory, indexed by a `DataCatalog` table (file path, time range, size, status)
- **PostgreSQL `historical_depths`:** Store **sampled** depth snapshots (e.g., every 4th hour, or only for contracts we actively trade). Ingested from Parquet on-demand.
- **Predexon orderbooks:** Direct to PostgreSQL `historical_depths` (already structured, lower volume)

### 2.6 Retention Policy

| Table | Retention | Cleanup |
|-------|-----------|---------|
| `historical_prices` | 2 years | Drop partitions older than 2 years |
| `historical_trades` | 1 year | Drop partitions older than 1 year |
| `historical_depths` | 6 months (PostgreSQL); indefinite (Parquet files) | Drop partitions; manual Parquet cleanup |
| `backtest_runs` | Indefinite (audit trail) | Archive after 1 year (move report JSON to file) |
| `backtest_positions` | Cascade with parent `backtest_runs` | Automatic via FK cascade |

### 2.7 Ingestion Scope

**Historical data is ingested only for known matched pairs.** No bulk platform-wide ingestion.

The target contract list is the **union** of:
1. **Our `ContractMatch` records** — authoritative internal matching (Polymarket ↔ Kalshi pairs)
2. **Third-party matched pairs** — Predexon `/v2/matching-markets/pairs` (Dev tier, $49/mo) and OddsPipe `/v1/spreads`

The ingestion orchestrator builds this target list before each ingestion run:
1. Query `ContractMatch` for all active pairs → extract `kalshiContractId`, `polymarketClobTokenId`
2. Query Predexon/OddsPipe for their matched pairs → merge with step 1 (dedup by contract ID)
3. For each unique contract in the target list → fetch historical data from the appropriate source

**Contract ID mapping for API queries:**

| ContractMatch Field | API Target |
|---|---|
| `kalshiContractId` | Kalshi `/historical/markets/{ticker}/candlesticks` and `/historical/trades` |
| `polymarketClobTokenId` | Polymarket `/prices-history` (`market` param) |
| `polymarketContractId` | Predexon endpoints, Goldsky subgraph |

**Scope rationale:**
- Keeps storage bounded — ingesting only matched pairs avoids millions of irrelevant contract records
- Keeps ingestion focused — rate limit budget is spent on data that directly supports calibration
- Third-party pair merging surfaces pairs our `ContractMatch` may have missed (different matching algorithms)

**Not scoped exclusively to backtesting.** The historical data tables (`historical_prices`, `historical_trades`, `historical_depths`) may serve future live pipeline use cases (e.g., trend analysis, regime detection, rolling volatility). Do not add restrictions that prevent non-backtesting reads.

---

## 3. Common Schema Design

### 3.1 Normalized Price Schema (OHLCV)

```typescript
interface NormalizedPrice {
  platform: PlatformId;
  contractId: string;          // Platform-specific contract identifier
  source: HistoricalDataSource;
  intervalMinutes: number;     // 1, 5, 60, 1440
  timestamp: Date;             // Period end timestamp (UTC)
  open: Decimal;               // Decimal probability 0.00–1.00
  high: Decimal;
  low: Decimal;
  close: Decimal;
  volume: Decimal | null;      // Platform-denominated volume
  openInterest: Decimal | null;
  qualityFlags: DataQualityFlags | null;
}
```

### 3.2 Normalized Trade Schema

```typescript
interface NormalizedTrade {
  platform: PlatformId;
  contractId: string;
  source: HistoricalDataSource;
  externalTradeId: string | null;  // Platform trade ID (if available)
  price: Decimal;                   // Decimal probability 0.00–1.00
  size: Decimal;                    // Dollar amount
  side: 'buy' | 'sell';
  timestamp: Date;                  // Fill timestamp (UTC)
  qualityFlags: DataQualityFlags | null;
}
```

### 3.3 Normalized Depth Schema

Aligns with existing `NormalizedOrderBook` type (`src/common/types/normalized-order-book.type.ts`):

```typescript
interface NormalizedHistoricalDepth {
  platform: PlatformId;
  contractId: string;
  source: HistoricalDataSource;
  bids: Array<{ price: Decimal; size: Decimal }>;  // Descending price order
  asks: Array<{ price: Decimal; size: Decimal }>;  // Ascending price order
  timestamp: Date;
  updateType: 'snapshot' | 'price_change' | null;
  qualityFlags: DataQualityFlags | null;
}
```

**Compatibility:** The `bids`/`asks` structure matches `NormalizedOrderBook` from `normalized-order-book.type.ts`, enabling direct use with `calculateVwapWithFillInfo()` and `calculateVwapClosePrice()` from `financial-math.ts`.

### 3.4 Provenance Metadata

```typescript
interface DataQualityFlags {
  gaps: boolean;           // Coverage gaps detected in time series
  interpolated: boolean;   // Values were interpolated from surrounding data
  stale: boolean;          // Data older than expected freshness threshold
  lowVolume: boolean;      // Trading volume below minimum threshold
  sourceConflict: boolean; // Multiple sources disagree on values
  notes: string | null;    // Human-readable quality note
}

interface IngestionMetadata {
  source: HistoricalDataSource;
  ingestionTimestamp: Date;
  coverageStart: Date;
  coverageEnd: Date;
  recordCount: number;
  qualityFlags: DataQualityFlags;
}
```

### 3.5 Normalization Rules Per Source

| Source | Price Format | Normalization | Timestamp | Side |
|--------|-------------|---------------|-----------|------|
| **Kalshi API** (historical) | Dollar strings (`"0.5600"`) | `new Decimal(value)` — already 0–1 range | `end_period_ts` (Unix seconds) | N/A (OHLCV) |
| **Kalshi API** (live) | Dollar strings with `_dollars` suffix | `new Decimal(value)` | Same | N/A |
| **Kalshi trades** | `yes_price_dollars`, `no_price_dollars` | `new Decimal(value)` | `created_time` ISO 8601 | `taker_side` ('yes'/'no' → 'buy'/'sell') |
| **Polymarket API** | Decimal probability (`0.65`) | `new Decimal(p)` — passthrough | `t` (Unix seconds) | N/A |
| **Goldsky** | Raw amounts (`makerAmountFilled`, `takerAmountFilled`) | Derive: `amount / 10^6` for USDC; price = ratio | `timestamp` (BigInt) | Derive from asset IDs |
| **PMXT Archive** | Parquet columns (TBD — needs schema inspection) | TBD after Parquet inspection | TBD | N/A (orderbook) |
| **OddsPipe** | OHLCV (format TBD) | Direct mapping (likely 0–1 probability) | TBD | N/A |
| **Predexon** | Dual format: `price` (int) + `price_dollars` (string) | `new Decimal(price_dollars)` | **Seconds** for candles, **milliseconds** for orderbooks | N/A |

**Key invariant:** After normalization, ALL prices are `Decimal` in 0.00–1.00 probability range. ALL sizes are `Decimal` in USD. ALL timestamps are `Date` (UTC).

---

## 4. Backtest Engine State Machine

### 4.1 State Diagram

```
                    ┌─────────┐
          ┌────────>│  idle   │<──────────────────┐
          │         └────┬────┘                    │
          │              │ submitConfig()           │
          │              v                         │
          │         ┌─────────────┐                │
          │         │ configuring │                │
          │         └──────┬──────┘                │
          │                │ configValid()          │
          │                v                       │
          │         ┌──────────────┐               │
          │    ┌───>│ loading-data │               │
          │    │    └──────┬───────┘               │
          │    │           │ dataLoaded()           │ reset()
          │    │           v                       │
          │    │    ┌─────────────┐                │
   cancel()   │    │ simulating  │────────────────>│
          │    │    └──────┬──────┘   failed()     │
          │    │           │ simulationComplete()   │
          │    │           v                       │
          │    │    ┌────────────────────┐         │
          │    │    │ generating-report  │─────────>│
          │    │    └────────┬───────────┘ failed() │
          │    │             │ reportGenerated()    │
          │    │             v                     │
          │    │    ┌────────────┐                  │
          └────┴───│  complete  │──────────────────┘
                   └────────────┘

  Any state except idle/complete ──cancel()──> cancelled ──reset()──> idle
  Any state except idle ──fail()──> failed ──reset()──> idle
```

### 4.2 State Transition Table

| Current State | Event | Next State | Guard |
|--------------|-------|------------|-------|
| `idle` | `submitConfig` | `configuring` | — |
| `configuring` | `configValid` | `loading-data` | All required params present, date range valid |
| `configuring` | `configInvalid` | `failed` | Validation errors |
| `loading-data` | `dataLoaded` | `simulating` | Minimum data coverage threshold met |
| `loading-data` | `insufficientData` | `failed` | Coverage below minimum for meaningful backtest |
| `simulating` | `simulationComplete` | `generating-report` | All time steps processed |
| `simulating` | `timeout` | `failed` | Exceeds configured timeout (default: 5 min) |
| `generating-report` | `reportGenerated` | `complete` | Report passes validation |
| `generating-report` | `reportError` | `failed` | Report generation fails |
| Any (except idle, complete) | `cancel` | `cancelled` | User-initiated |
| `cancelled` | `reset` | `idle` | — |
| `complete` | `reset` | `idle` | — |
| `failed` | `reset` | `idle` | — |

**Startup recovery:** On application startup, scan for `BacktestRun` records in `CONFIGURING`, `LOADING_DATA`, `SIMULATING`, or `GENERATING_REPORT` status. Any run whose `startedAt` is older than `timeoutSeconds * 2` is transitioned to `FAILED` with error `"Process restart — run orphaned"`. This prevents stale runs from blocking the concurrent run limit.

**Concurrency:** The `maxConcurrentRuns` parameter (default: 2) limits simultaneous active runs. New `submitConfig` requests are rejected with a `4204 BACKTEST_STATE_ERROR` when the limit is reached.

### 4.3 Parameterized Input Schema (BacktestConfig DTO)

```typescript
class BacktestConfigDto {
  // Time range
  dateRangeStart: Date;                // Backtest start (UTC)
  dateRangeEnd: Date;                  // Backtest end (UTC)

  // Detection parameters — all *Pct fields use DECIMAL form (0.008 = 0.8%, NOT 0.8 or 80)
  edgeThresholdPct: number;            // Minimum net edge as decimal (default: 0.008 = 0.8%)
  minConfidenceScore: number;          // ContractMatch confidence floor (default: 0.8)

  // Position sizing
  positionSizePct: number;             // Fraction of bankroll per pair as decimal (default: 0.03 = 3%)
  maxConcurrentPairs: number;          // Max open positions (default: 10)
  bankrollUsd: string;                 // Simulated starting capital — string for Decimal conversion at service boundary

  // Trading window (UTC-only, does NOT adjust for DST)
  tradingWindowStartHour: number;      // UTC hour (default: 14)
  tradingWindowEndHour: number;        // UTC hour (default: 23)

  // Fee model
  kalshiFeeSchedule: FeeSchedule;      // From platform.type.ts
  polymarketFeeSchedule: FeeSchedule;
  gasEstimateUsd: string;              // Per-trade gas — string for Decimal conversion (default: "0.50")

  // Exit criteria — all *Pct fields use DECIMAL form
  exitEdgeEvaporationPct: number;      // Exit when edge drops below this decimal (default: 0.002 = 0.2%)
  exitTimeLimitHours: number;          // Max holding period (default: 72)
  exitProfitCapturePct: number;        // Take profit at this fraction of entry edge (default: 0.80 = 80%)

  // Walk-forward (optional)
  walkForwardEnabled: boolean;         // Enable walk-forward validation
  walkForwardTrainPct: number;         // Training set fraction (default: 0.70 = 70%)

  // Simulation
  timeoutSeconds: number;              // Max simulation time (default: 300)
  maxConcurrentRuns: number;           // Max simultaneous backtest runs (default: 2) — prevents resource exhaustion
}

// Service boundary conversion: new Decimal(dto.bankrollUsd), new Decimal(dto.gasEstimateUsd)
// Metric edge cases: Sharpe ratio → null when stddev(returns) == 0; profit factor → null when grossLoss == 0
```

### 4.4 Detection Model Integration

Reuses `FinancialMath` from `src/common/utils/financial-math.ts` (lines 1–260):

| Step | Function | Source |
|------|----------|--------|
| Gross edge | `FinancialMath.calculateGrossEdge(buyPrice, sellPrice)` | financial-math.ts |
| Fee rate | `FinancialMath.calculateTakerFeeRate(price, feeSchedule)` | financial-math.ts |
| Net edge | `FinancialMath.calculateNetEdge(grossEdge, buyPrice, sellPrice, buyFeeSchedule, sellFeeSchedule, gasEstimate, positionSize)` | financial-math.ts |
| Threshold check | `FinancialMath.isAboveThreshold(netEdge, threshold)` | financial-math.ts |

**Data flow:** For each time step `t`, the engine:
1. Looks up `HistoricalPrice` close prices for both platforms at `t`
2. Calculates gross edge between the pair
3. Applies fee model via `calculateNetEdge`
4. If `isAboveThreshold` → simulated entry (if capital available)
5. For open positions → evaluate exit criteria

**No reimplementation.** All edge/fee math delegates to the existing tested functions.

### 4.5 VWAP Fill Modeling

Reuses `calculateVwapWithFillInfo()` from `financial-math.ts`:

```typescript
const fillResult = calculateVwapWithFillInfo(
  historicalDepthSnapshot,  // NormalizedHistoricalDepth → NormalizedOrderBook
  closeSide,                // 'buy' or 'sell'
  positionSize              // Decimal
);
```

**Conservative assumptions:**
- **Taker-only fills** — no maker queue position modeling
- **No market impact** — price doesn't move due to our order
- **Partial fills** — proportional to available depth at each price level
- **Depth interpolation** — between hourly PMXT snapshots, use nearest-neighbor (not linear interpolation) for conservative estimate
- If `fillResult === null` (insufficient depth) → skip opportunity, log as `insufficient_depth`

### 4.6 Exit Logic

For each open simulated position at time step `t`:

| Exit Criterion | Check | Source |
|---------------|-------|--------|
| Edge evaporation | Current net edge < `exitEdgeEvaporationPct` | Recalculate via `calculateNetEdge` with current prices |
| Time decay | `t - entryTimestamp > exitTimeLimitHours` | Config parameter |
| Profit capture | Unrealized P&L >= `exitProfitCapturePct * entryEdge * size` | `calculateLegPnl` per leg |
| Resolution force-close | Contract has resolved (resolution date <= t) | `ContractMatch.resolutionDate` |
| Insufficient depth | No depth data available for exit VWAP | `calculateVwapWithFillInfo` returns null |

**Exit evaluation priority** (when multiple criteria trigger at the same time step):
1. **Resolution force-close** — highest priority, deterministic outcome
2. **Insufficient depth** — cannot exit via market, use last known mid-price as fallback
3. **Profit capture** — take the win
4. **Edge evaporation** — defensive exit
5. **Time decay** — lowest priority, backstop

**Resolution-date force-close** is a distinct exit path:
- Uses resolution price (1.00 or 0.00) instead of market price. Non-binary resolutions (void/refund) are excluded from backtesting — the Known Limitations section documents this.
- No VWAP modeling needed — settlement is at fixed price
- P&L calculation: `calculateLegPnl` with resolution price as close price

**Coverage gap handling:** If a position spans a data gap (no price data for multiple time steps), time-based exit criteria continue to accrue but the position is held until prices resume. Exit evaluation uses the first available price after the gap. The `DataQualityFlags.gaps` flag is set on the position.

### 4.7 Simulated Portfolio State

```typescript
interface BacktestPortfolioState {
  availableCapital: Decimal;          // bankroll - deployed capital
  deployedCapital: Decimal;           // Sum of open position sizes
  openPositions: Map<string, SimulatedPosition>;  // pairId → position. Cleanup: .delete() on exit, .clear() on reset/complete
  closedPositions: SimulatedPosition[];            // Bounded by simulation scope — cleared on reset
  peakEquity: Decimal;                // Highest equity mark (for drawdown)
  currentEquity: Decimal;             // available + unrealized P&L
  realizedPnl: Decimal;               // Cumulative closed P&L
  maxDrawdown: Decimal;               // (peak - trough) / peak
}
```

**Drawdown calculation:** Track peak equity. At each time step, `drawdown = (peakEquity - currentEquity) / peakEquity`. `maxDrawdown = max(all drawdowns)`.

**Capital utilization:** `avgDeployedCapital / bankroll` over the simulation period.

### 4.8 Known Limitations

Include verbatim in every calibration report:

> **Known Limitations of This Backtest:**
>
> 1. **No single-leg risk modeling** — Assumes both legs fill atomically. In live trading, one leg may fill while the other fails, creating directional exposure.
> 2. **No market impact** — Assumes our orders don't move the price. In practice, large orders relative to depth will experience slippage beyond VWAP.
> 3. **No queue position modeling** — Assumes taker-only fills at current prices. Maker limit orders would improve pricing but introduce fill uncertainty.
> 4. **Depth interpolation** — PMXT Archive provides hourly snapshots. Depth between hours is estimated via nearest-neighbor, not continuous data.
> 5. **No correlation modeling** — Positions are evaluated independently. In practice, correlated events may cause simultaneous adverse moves.
> 6. **No funding/holding costs** — Ignores capital opportunity cost and any platform-specific holding fees.
> 7. **Execution latency not modeled** — Assumes instant execution. Live system has network latency, API processing time, and blockchain confirmation delays.
> 8. **Historical data biases** — Survivorship bias (only markets that resolved are analyzed), lookback bias (pair matches applied retroactively).
> 9. **Cross-platform clock skew** — Kalshi uses server timestamps; Polymarket uses blockchain timestamps (can lag real-world time by minutes). Edges detected via timestamp alignment may not have existed simultaneously in real-time.
> 10. **Non-binary resolution excluded** — Contracts that resolve as void, refunded, or at fractional values are excluded from backtesting. Only binary resolution (0 or 1) is modeled.

---

## 5. Test Fixture Strategy

### 5.1 Directory Structure

```
src/modules/backtesting/__fixtures__/
├── scenarios/
│   ├── profitable-2leg-arb.fixture.json
│   ├── unprofitable-fees-exceed.fixture.json
│   ├── breakeven.fixture.json
│   ├── resolution-force-close.fixture.json
│   ├── insufficient-depth.fixture.json
│   └── coverage-gap.fixture.json
├── price-series/
│   ├── kalshi-sample-candles.fixture.json
│   └── polymarket-sample-candles.fixture.json
├── depth-snapshots/
│   ├── sufficient-depth.fixture.json
│   └── thin-orderbook.fixture.json
└── trades/
    └── sample-trades.fixture.json
```

### 5.2 Hand-Crafted Scenarios

| Scenario | Description | Expected Outcome |
|----------|-------------|------------------|
| **Profitable 2-leg arb** | Kalshi YES @ 0.45, Polymarket NO @ 0.48. Edge = 3%, fees = 1.5%, net = 1.5%. Exits via profit capture at 80% of edge. | P&L > 0. Entry edge = 1.5%. Exit edge < 0.3%. |
| **Unprofitable (fees exceed edge)** | Kalshi YES @ 0.50, Polymarket NO @ 0.51. Gross edge 1%, fees 1.2%. | Position NOT opened (net edge below 0.8% threshold). |
| **Breakeven** | Entry at net edge 1.0%. Prices converge to exactly offset fees. | P&L ≈ 0 (within Decimal precision). |
| **Resolution force-close** | Position open when contract resolves. Kalshi YES wins (price → 1.00). | Exit via resolution. P&L depends on entry prices. Force-close exit reason. |
| **Insufficient depth** | Edge detected but orderbook has < $10 at best price. Position size $100. | Position NOT opened. Logged as `insufficient_depth`. |
| **Coverage gap** | Price data missing for 6 hours mid-simulation. | Positions held through gap. Quality flag `gaps: true` on affected data points. |

### 5.3 Fixture Format

```json
{
  "name": "profitable-2leg-arb",
  "description": "Standard profitable arbitrage with profit capture exit",
  "config": {
    "bankrollUsd": 10000,
    "edgeThresholdPct": 0.8,
    "positionSizePct": 3.0,
    "exitProfitCapturePct": 80
  },
  "pair": {
    "pairId": "fixture-pair-001",
    "kalshiContractId": "FIXTURE-K-001",
    "polymarketClobTokenId": "FIXTURE-P-001"
  },
  "priceSeries": [
    { "t": "2025-06-01T14:00:00Z", "kalshi": "0.4500", "polymarket": "0.5200" },
    { "t": "2025-06-01T14:01:00Z", "kalshi": "0.4520", "polymarket": "0.5180" },
    { "t": "2025-06-01T14:02:00Z", "kalshi": "0.4600", "polymarket": "0.5100" }
  ],
  "depthSnapshots": [
    {
      "t": "2025-06-01T14:00:00Z",
      "kalshi": { "bids": [["0.45", "500"]], "asks": [["0.46", "300"]] },
      "polymarket": { "bids": [["0.51", "400"]], "asks": [["0.52", "350"]] }
    }
  ],
  "expectedOutcome": {
    "positionsOpened": 1,
    "entryEdge": "0.015",
    "exitReason": "profit_capture",
    "pnlPositive": true,
    "pnlApprox": "3.50"
  }
}
```

### 5.4 Real Data Generation Strategy

1. **Select date range:** Pick a 2-week window with known market activity
2. **Select pairs:** Choose 3–5 ContractMatch pairs with resolution dates in the range
3. **Extract data:** Pull prices, trades, and depth from Predexon free endpoints + Kalshi API
4. **Calculate expected outcomes:** Manually compute edge at each time step, determine which positions would open/close
5. **Anonymize:** Replace contract IDs with fixture IDs, shift timestamps by a random offset
6. **Store:** Save as fixture JSON alongside the hand-crafted scenarios

**Script location:** `src/modules/backtesting/__fixtures__/generate-from-real-data.ts` (developer tool, not production code).

---

## 6. Story Sizing Review

### 6.1 Task Count Estimates

| Story | Est. Tasks | Est. Subtasks | Integration Boundaries | Status |
|-------|-----------|--------------|----------------------|--------|
| 10-9-1a Platform API Ingestion | 8 | 16 | 2 (Kalshi API, Polymarket API) | **Within limits** |
| 10-9-1b Depth/Third-Party Ingestion | 7 | 14 | 2 (PMXT Archive, Predexon) | **Within limits** |
| 10-9-2 Pair Matching Validation | 6 | 10 | 2 (OddsPipe, Predexon matching) | **Within limits** |
| 10-9-3 Backtest Engine Core | **12** | **24** | **3+** (financial-math, persistence, state machine) | **EXCEEDS — split required** |
| 10-9-4 Calibration Report | 8 | 16 | 2 (engine output, persistence) | **Within limits** |
| 10-9-5 Dashboard Page | 7 | 14 | 2 (backend API, React frontend) | **Within limits** |
| 10-9-6 Freshness/Incremental | 6 | 12 | 2 (cron, platform APIs) | **Within limits** |

### 6.2 Integration Boundary Analysis

**Story 10-9-3 boundaries:**
1. `common/utils/financial-math.ts` — edge, VWAP, fee, P&L calculations
2. `persistence/` — BacktestRun, BacktestPosition CRUD
3. Historical data queries — HistoricalPrice, HistoricalTrade, HistoricalDepth reads
4. State machine — internal transitions with event emission
5. Exit criteria evaluation — reuses exit management patterns

**3+ integration boundaries AND 12+ tasks → Agreement #25 triggered.**

### 6.3 Split Assessment: 10-9-3

**Recommended split:**

**10-9-3a: Backtest Engine Core — State Machine & Data Loading** (~7 tasks)
- State machine implementation (idle → configuring → loading-data)
- BacktestConfig DTO validation
- Historical data query service (range queries, coverage checking)
- Data loading pipeline (price + depth alignment)
- BacktestRun persistence (create, update status)
- Config validation guards
- Event emission for state transitions

**10-9-3b: Backtest Engine Core — Simulation & Portfolio** (~7 tasks)
- Simulation loop (loading-data → simulating → generating-report)
- Detection model integration (edge calculation per time step)
- VWAP fill modeling (entry/exit sizing)
- Portfolio state tracking (capital, positions, P&L)
- Exit criteria evaluation (all 5 exit types)
- BacktestPosition persistence
- Drawdown/utilization metrics calculation

### 6.4 Other Stories — No Splits Needed

All other stories are within Agreement #25 thresholds (<=10 tasks, <=2 integration boundaries). Monitor 10-9-4 if sensitivity analysis adds complexity beyond the 8-task estimate.

---

## 7. Minimum Viable Calibration Cut Line

### 7.1 Must-Have (Minimum Viable Calibration)

| Capability | Story | Rationale |
|-----------|-------|-----------|
| Kalshi + Polymarket price ingestion | 10-9-1a | Primary data for edge detection |
| At least one depth source (Predexon OR PMXT) | 10-9-1b (partial) | VWAP fill modeling requires depth |
| Backtest engine with edge + fee model | 10-9-3a + 10-9-3b | Core simulation capability |
| Basic calibration report (total P&L, win rate, positions, drawdown) | 10-9-4 (partial) | Answers "is the system profitable with these parameters?" |
| Resolution force-close exit path | 10-9-3b | Must handle contract resolution |
| Known limitations section | 10-9-4 (partial) | Prevents overconfidence in results |

**Minimum viable output:** A report that shows, for a given set of parameters and date range, the simulated P&L, win rate, and max drawdown — enough to determine whether the detection model can identify profitable opportunities.

### 7.2 Nice-to-Have (Deferrable)

| Capability | Story | Deferral Impact |
|-----------|-------|-----------------|
| Walk-forward validation (70/30 split) | 10-9-4 (advanced) | Cannot verify out-of-sample robustness — risk of overfitting |
| Parameter sweep / sensitivity analysis | 10-9-4 (advanced) | Manual parameter exploration instead of automated sweep |
| Overfit detection (>30% degradation) | 10-9-4 (advanced) | No automated overfit warning |
| OddsPipe/Predexon matching validation | 10-9-2 | **Elevated importance:** Since ingestion scope uses the union of ContractMatch + third-party pairs (Section 2.7), third-party pair accuracy directly affects which contracts get ingested. Should-have if third-party pairs are used for ingestion targeting; deferrable if ingestion uses ContractMatch only. |
| Dashboard UI for backtests | 10-9-5 | CLI/log output only; no visual charts |
| Incremental data updates | 10-9-6 | Manual re-ingestion for new data; no freshness tracking |
| Bootstrap confidence intervals | 10-9-4 (advanced) | Point estimates only, no statistical confidence |

### 7.3 Dependencies Between Retained and Deferred

```
Must-have:                          Nice-to-have:
┌─────────────────┐                 ┌──────────────────────┐
│ 10-9-1a (prices)│────────────────>│ 10-9-2 (matching     │
└────────┬────────┘                 │   validation)        │
         │                          └──────────────────────┘
         v
┌─────────────────┐                 ┌──────────────────────┐
│ 10-9-1b (depth) │                 │ 10-9-6 (incremental  │
│   partial       │────────────────>│   updates)           │
└────────┬────────┘                 └──────────────────────┘
         │
         v
┌─────────────────┐                 ┌──────────────────────┐
│ 10-9-3a+3b      │────────────────>│ 10-9-5 (dashboard)   │
│ (engine)        │                 └──────────────────────┘
└────────┬────────┘
         │
         v
┌─────────────────┐                 ┌──────────────────────┐
│ 10-9-4 (report) │────────────────>│ Walk-forward,        │
│   basic         │                 │ sensitivity, overfit  │
└─────────────────┘                 └──────────────────────┘
```

**Key:** Deferred items have no upstream dependencies on each other. Each can be independently added later. Walk-forward/sensitivity are extensions to the basic report, not prerequisites.

---

## 8. Spec File Naming Map

### 8.1 Module Directory Tree

```
src/modules/backtesting/
├── backtesting.module.ts
├── ingestion/
│   ├── ingestion.module.ts                          # Sub-module for data ingestion
│   ├── kalshi-historical.service.ts                 # Kalshi API historical data fetcher
│   ├── kalshi-historical.service.spec.ts
│   ├── polymarket-historical.service.ts             # Polymarket API + Goldsky fetcher
│   ├── polymarket-historical.service.spec.ts
│   ├── predexon-data.service.ts                     # Predexon free endpoints fetcher
│   ├── predexon-data.service.spec.ts
│   ├── pmxt-archive.service.ts                      # PMXT Parquet file processor
│   ├── pmxt-archive.service.spec.ts
│   ├── ingestion-orchestrator.service.ts            # Builds target contract list from ContractMatch + third-party pairs, coordinates per-contract ingestion
│   ├── ingestion-orchestrator.service.spec.ts
│   └── data-quality.service.ts                      # Quality flag computation
│   └── data-quality.service.spec.ts
├── engine/
│   ├── backtest-engine.service.ts                   # State machine + simulation orchestration
│   ├── backtest-engine.service.spec.ts
│   ├── backtest-portfolio.service.ts                # Portfolio state tracking, drawdown
│   ├── backtest-portfolio.service.spec.ts
│   ├── fill-model.service.ts                        # VWAP fill modeling for backtests
│   ├── fill-model.service.spec.ts
│   └── exit-evaluator.service.ts                    # Exit criteria evaluation
│   └── exit-evaluator.service.spec.ts
├── reporting/
│   ├── reporting.module.ts                          # Sub-module for report generation
│   ├── calibration-report.service.ts                # Report generation
│   ├── calibration-report.service.spec.ts
│   ├── sensitivity-analysis.service.ts              # Parameter sweep
│   ├── sensitivity-analysis.service.spec.ts
│   └── walk-forward.service.ts                      # Walk-forward validation
│   └── walk-forward.service.spec.ts
├── dto/
│   ├── backtest-config.dto.ts
│   ├── backtest-result.dto.ts
│   ├── calibration-report.dto.ts
│   ├── historical-data-query.dto.ts
│   └── ingestion-progress.dto.ts
├── controllers/
│   ├── backtest.controller.ts                       # POST /api/backtesting/runs, GET /runs/:id
│   ├── backtest.controller.spec.ts
│   ├── historical-data.controller.ts                # POST /api/backtesting/ingest, GET /coverage
│   └── historical-data.controller.spec.ts
└── __fixtures__/
    ├── scenarios/
    │   ├── profitable-2leg-arb.fixture.json
    │   ├── unprofitable-fees-exceed.fixture.json
    │   ├── breakeven.fixture.json
    │   ├── resolution-force-close.fixture.json
    │   ├── insufficient-depth.fixture.json
    │   └── coverage-gap.fixture.json
    ├── price-series/
    │   ├── kalshi-sample-candles.fixture.json
    │   └── polymarket-sample-candles.fixture.json
    ├── depth-snapshots/
    │   ├── sufficient-depth.fixture.json
    │   └── thin-orderbook.fixture.json
    └── trades/
        └── sample-trades.fixture.json
```

**Module provider analysis:**
- `BacktestingModule` (root): ~4 providers (backtest-engine, backtest-portfolio, fill-model, exit-evaluator) + 2 controllers. Imports `IngestionModule` and `ReportingModule` as sub-modules. Total own providers: **6** — within limit.
- `IngestionModule` (sub-module): ~6 providers (kalshi-historical, polymarket-historical, predexon-data, pmxt-archive, ingestion-orchestrator, data-quality). Within limit.
- `ReportingModule` (sub-module): ~3 providers (calibration-report, sensitivity-analysis, walk-forward). Within limit.
- All three modules within ~8 provider limit. Infrastructure deps (PrismaService, EventEmitter2, HttpModule) are imported, not provided.

### 8.2 New Prisma Models

| Model | Table Name | Key |
|-------|-----------|-----|
| `HistoricalPrice` | `historical_prices` | Partitioned by timestamp |
| `HistoricalTrade` | `historical_trades` | Partitioned by timestamp |
| `HistoricalDepth` | `historical_depths` | Partitioned by timestamp |
| `BacktestRun` | `backtest_runs` | UUID PK |
| `BacktestPosition` | `backtest_positions` | Auto-increment PK, FK to BacktestRun |

New enums: `HistoricalDataSource`, `BacktestStatus`, `BacktestExitReason`.

### 8.3 New Interfaces

| Interface | File | Token |
|-----------|------|-------|
| `IHistoricalDataProvider` | `common/interfaces/historical-data-provider.interface.ts` | `HISTORICAL_DATA_PROVIDER_TOKEN` |
| `IBacktestEngine` | `common/interfaces/backtest-engine.interface.ts` | `BACKTEST_ENGINE_TOKEN` |
| `ICalibrationReporter` | `common/interfaces/calibration-reporter.interface.ts` | `CALIBRATION_REPORTER_TOKEN` |

### 8.4 New Event Classes

| Event Class | Dot-notation Name | File |
|------------|-------------------|------|
| `BacktestRunStartedEvent` | `backtesting.run.started` | `common/events/backtesting.events.ts` |
| `BacktestRunCompletedEvent` | `backtesting.run.completed` | same |
| `BacktestRunFailedEvent` | `backtesting.run.failed` | same |
| `BacktestRunCancelledEvent` | `backtesting.run.cancelled` | same |
| `BacktestDataIngestedEvent` | `backtesting.data.ingested` | same |
| `BacktestDataQualityWarningEvent` | `backtesting.data.quality-warning` | same |
| `BacktestPositionOpenedEvent` | `backtesting.position.opened` | same |
| `BacktestPositionClosedEvent` | `backtesting.position.closed` | same |
| `BacktestReportGeneratedEvent` | `backtesting.report.generated` | same |

Add to `event-catalog.ts` constants.

### 8.5 New Error Codes

**Range: 4200–4299** (SystemHealthError subclass)

> **COLLISION NOTE:** The story originally proposed 4100–4199, but 4100–4103 are already allocated to LLM scoring errors (`LLM_API_FAILURE`, `LLM_RESPONSE_PARSE_FAILURE`, `LLM_TIMEOUT`, `LLM_RATE_LIMITED`). Allocating 4200–4299 to avoid collision.

| Code | Name | Description |
|------|------|-------------|
| 4200 | `BACKTEST_INGESTION_FAILURE` | Historical data ingestion failed |
| 4201 | `BACKTEST_PARQUET_PARSE_ERROR` | PMXT Parquet file parsing failed |
| 4202 | `BACKTEST_TIMEOUT` | Backtest simulation exceeded timeout |
| 4203 | `BACKTEST_INSUFFICIENT_DATA` | Not enough historical data for meaningful backtest |
| 4204 | `BACKTEST_STATE_ERROR` | Invalid state transition attempted |
| 4205 | `BACKTEST_REPORT_ERROR` | Calibration report generation failed |
| 4206 | `BACKTEST_EXTERNAL_API_ERROR` | Third-party API (OddsPipe/Predexon/PMXT) failed |
| 4207 | `BACKTEST_DATA_QUALITY_ERROR` | Data quality below acceptable threshold |

### 8.6 API Endpoint Paths

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/backtesting/runs` | Create and start a new backtest run |
| `GET` | `/api/backtesting/runs` | List backtest runs (paginated) |
| `GET` | `/api/backtesting/runs/:id` | Get backtest run details + report |
| `DELETE` | `/api/backtesting/runs/:id` | Cancel a running backtest |
| `POST` | `/api/backtesting/ingest` | Trigger historical data ingestion |
| `GET` | `/api/backtesting/coverage` | Get data coverage report (per contract, per source) |
| `GET` | `/api/backtesting/coverage/:contractId` | Coverage for specific contract |

---

## 9. Reviewer Context Template

### Reusable `context` Parameter for Lad MCP `code_review`

```
## Module: Backtesting & Calibration (Epic 10.9)

### Architecture
- Module: src/modules/backtesting/ with sub-modules: ingestion/, engine/, reporting/
- Ingestion sub-module: fetches historical data from Kalshi API, Polymarket API, Predexon, PMXT Archive
- Engine sub-module: state machine-driven backtest simulation with parameterized inputs
- Reporting sub-module: calibration reports, sensitivity analysis, walk-forward validation
- Persistence: 5 new Prisma models (HistoricalPrice, HistoricalTrade, HistoricalDepth, BacktestRun, BacktestPosition)

### Hard Constraints
- ALL financial math uses decimal.js (Decimal) — NEVER native JS operators on monetary values
- Import via interfaces only (common/interfaces/) — NEVER direct service imports across modules
- ALL errors extend SystemError hierarchy — codes 4200-4299 for backtesting
- Every observable state change emits domain event via EventEmitter2
- Prisma Decimal → decimal.js: new Decimal(value.toString())
- Services max ~300 lines, files max ~400 lines
- Constructor deps: leaf ≤5, facade ≤8
- Module providers ≤8 per module

### External API Patterns
- Kalshi historical: dollar strings ("0.5600") → new Decimal(value). Historical vs live field naming divergence.
- Polymarket: decimal probability passthrough. market param = token ID (not condition_id).
- Predexon: seconds vs milliseconds timestamps per endpoint. x-api-key auth.
- PMXT Archive: Parquet files, 150-605MB/hour. Schema requires runtime inspection.

### Testing Requirements
- Co-located specs (service.ts → service.spec.ts)
- Vitest + unplugin-swc for decorator metadata
- Assertion depth: verify payloads with expect.objectContaining, not bare toHaveBeenCalled
- Event wiring: expectEventHandled() integration tests for @OnEvent handlers
- Paper/live boundary: N/A for backtesting (operates on historical data only)
- Collection cleanup: every Map/Set must document cleanup strategy + test cleanup path
- Test fixtures in __fixtures__/ with deterministic expected outcomes

### Acceptance Criteria Context
[PASTE RELEVANT ACs FROM STORY FILE HERE]
```

---

## Appendix A: Data Flow Diagram

```
Pair Sources                   Target List                     Ingestion Scope
─────────────────────          ─────────────────────          ─────────────────────
contract_matches ─────────────>┌─────────────────────┐
                               │ IngestionOrchestrator│──────> Target contract list
Predexon /matching-markets ───>│ (union + dedup)      │        (kalshiContractId,
OddsPipe /spreads ────────────>│                      │         polymarketClobTokenId)
                               └──────────┬──────────┘
                                          │ per-contract
                                          v
External Sources                    Ingestion Layer                     Storage
─────────────────────          ─────────────────────          ─────────────────────
                               ┌─────────────────────┐
Kalshi /candlesticks ─────────>│ KalshiHistorical    │──────> historical_prices
Kalshi /historical/trades ────>│ Service              │──────> historical_trades
                               └─────────────────────┘
                               ┌─────────────────────┐
Polymarket /prices-history ───>│ PolymarketHistorical│──────> historical_prices
Goldsky subgraph ─────────────>│ Service              │──────> historical_trades
                               └─────────────────────┘
                               ┌─────────────────────┐
Predexon /candlesticks ───────>│ PredexonData        │──────> historical_prices
Predexon /orderbooks ─────────>│ Service              │──────> historical_depths
                               └─────────────────────┘
                               ┌─────────────────────┐
PMXT Archive .parquet ────────>│ PmxtArchive         │──────> historical_depths
                               │ Service              │       (sampled to PG)
                               └─────────────────────┘       + raw Parquet files

Storage                         Engine                         Output
─────────────────────          ─────────────────────          ─────────────────────
                               ┌─────────────────────┐
historical_prices ────────────>│ BacktestEngine      │
historical_depths ────────────>│ (state machine)     │──────> backtest_runs
contract_matches  ────────────>│                     │──────> backtest_positions
                               │ Uses:               │
                               │ • FinancialMath.*   │       ┌─────────────────────┐
                               │ • calculateVwap*    │──────>│ CalibrationReport   │
                               │ • calculateLegPnl   │       │ Service              │
                               └─────────────────────┘       └─────────────────────┘
                                                                      │
                                                                      v
                                                              Calibration Report
                                                              (JSON + dashboard)
```
