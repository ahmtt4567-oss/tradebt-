CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS candles (
  time TIMESTAMPTZ NOT NULL,
  symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL,
  open DOUBLE PRECISION NOT NULL,
  high DOUBLE PRECISION NOT NULL,
  low DOUBLE PRECISION NOT NULL,
  close DOUBLE PRECISION NOT NULL,
  volume DOUBLE PRECISION NOT NULL,
  PRIMARY KEY (time, symbol, timeframe)
);
SELECT create_hypertable('candles', by_range('time'), if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS trade_decisions (
  id BIGSERIAL PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  symbol TEXT NOT NULL,
  direction TEXT NOT NULL,
  confidence NUMERIC(5,2) NOT NULL,
  entry_price NUMERIC,
  stop_loss NUMERIC,
  tp1 NUMERIC,
  tp2 NUMERIC,
  tp3 NUMERIC,
  explanation TEXT
);

CREATE TABLE IF NOT EXISTS paper_account_snapshots (
  account_key TEXT PRIMARY KEY,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  payload JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS application_state_snapshots (
  state_key TEXT PRIMARY KEY,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  payload JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS market_ticks (
  time TIMESTAMPTZ NOT NULL,
  symbol TEXT NOT NULL,
  price DOUBLE PRECISION NOT NULL,
  bid DOUBLE PRECISION NOT NULL,
  ask DOUBLE PRECISION NOT NULL,
  bid_qty DOUBLE PRECISION NOT NULL,
  ask_qty DOUBLE PRECISION NOT NULL,
  spread_bps DOUBLE PRECISION NOT NULL,
  quote_volume_24h DOUBLE PRECISION NOT NULL,
  source TEXT NOT NULL,
  PRIMARY KEY (time, symbol)
);
SELECT create_hypertable('market_ticks', by_range('time'), if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS orderbook_snapshots (
  time TIMESTAMPTZ NOT NULL,
  symbol TEXT NOT NULL,
  best_bid DOUBLE PRECISION NOT NULL,
  best_ask DOUBLE PRECISION NOT NULL,
  bid_qty DOUBLE PRECISION NOT NULL,
  ask_qty DOUBLE PRECISION NOT NULL,
  spread_bps DOUBLE PRECISION NOT NULL,
  PRIMARY KEY (time, symbol)
);
SELECT create_hypertable('orderbook_snapshots', by_range('time'), if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS market_twin_events (
  id BIGSERIAL PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  kind TEXT NOT NULL,
  symbol TEXT,
  message TEXT NOT NULL,
  details JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS paper_twin_fills (
  id TEXT PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  symbol TEXT NOT NULL,
  side TEXT NOT NULL,
  strategy TEXT NOT NULL,
  requested_notional DOUBLE PRECISION NOT NULL,
  filled_notional DOUBLE PRECISION NOT NULL,
  fill_pct DOUBLE PRECISION NOT NULL,
  execution_price DOUBLE PRECISION NOT NULL,
  quantity DOUBLE PRECISION NOT NULL,
  fee_usdt DOUBLE PRECISION NOT NULL,
  impact_bps DOUBLE PRECISION NOT NULL,
  latency_ms INTEGER NOT NULL,
  paper_only BOOLEAN NOT NULL DEFAULT TRUE
);

-- V27 keeps only non-secret Testnet decisions, plans and evidence. Exchange
-- credentials are never written to these evidence tables.
CREATE TABLE IF NOT EXISTS protrebot_cloud_state (
  state_key TEXT PRIMARY KEY,
  version TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  payload JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS protrebot_cloud_evidence (
  event_key TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  symbol TEXT,
  event_time TIMESTAMPTZ NOT NULL,
  payload JSONB NOT NULL,
  stored_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_protrebot_cloud_evidence_time
  ON protrebot_cloud_evidence (event_time DESC);

-- V28 exchange credentials are stored only as authenticated ciphertext.  API
-- and Secret key columns deliberately do not exist.
CREATE TABLE IF NOT EXISTS protrebot_exchange_vault (
  mode TEXT PRIMARY KEY CHECK (mode IN ('TESTNET', 'LIVE')),
  encrypted_payload BYTEA NOT NULL,
  fingerprint TEXT NOT NULL,
  active BOOLEAN NOT NULL DEFAULT FALSE,
  last_test_ok BOOLEAN NOT NULL DEFAULT FALSE,
  last_test_at TIMESTAMPTZ,
  last_error TEXT,
  account_summary JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
