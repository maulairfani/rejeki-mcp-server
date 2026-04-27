-- Finance MCP Database Schema — Envelope Budget Edition
--
-- Table mapping:
--   envelopes       = envelope definitions (name, icon, type, target)
--   envelope_groups = groups of expense envelopes
--   budget_periods  = per-month budget data (assigned + carryover per envelope)
--   transactions    = all recorded money movements
--   scheduled_transactions = future/recurring transactions
--   accounts        = bank accounts, e-wallets, cash

CREATE TABLE IF NOT EXISTS accounts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    type       TEXT NOT NULL CHECK (type IN ('bank', 'ewallet', 'cash')),
    balance    REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS envelope_groups (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS envelopes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    icon            TEXT,
    type            TEXT NOT NULL CHECK (type IN ('income', 'expense')),
    group_id        INTEGER REFERENCES envelope_groups(id),
    target_type     TEXT CHECK (target_type IN ('monthly_spending', 'monthly_savings', 'savings_balance', 'needed_by_date')),
    target_amount   REAL,
    target_deadline TEXT,
    archived        INTEGER NOT NULL DEFAULT 0,
    sort_order      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS transactions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    amount        REAL NOT NULL,
    type          TEXT NOT NULL CHECK (type IN ('income', 'expense', 'transfer')),
    envelope_id   INTEGER REFERENCES envelopes(id),
    account_id    INTEGER NOT NULL REFERENCES accounts(id),
    to_account_id INTEGER REFERENCES accounts(id),
    payee         TEXT,
    memo          TEXT,
    date          TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Per-period budget data per envelope.
-- Activity (spending) is always computed from transactions — never stored here.
-- Carryover is only positive: overspend reduces RTA next month, not this table.
CREATE TABLE IF NOT EXISTS budget_periods (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    envelope_id INTEGER NOT NULL REFERENCES envelopes(id),
    period      TEXT NOT NULL,  -- YYYY-MM
    assigned    REAL NOT NULL DEFAULT 0,
    carryover   REAL NOT NULL DEFAULT 0,
    UNIQUE(envelope_id, period)
);

CREATE TABLE IF NOT EXISTS scheduled_transactions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    amount         REAL NOT NULL,
    type           TEXT NOT NULL CHECK (type IN ('income', 'expense', 'transfer')),
    envelope_id    INTEGER REFERENCES envelopes(id),
    account_id     INTEGER NOT NULL REFERENCES accounts(id),
    to_account_id  INTEGER REFERENCES accounts(id),
    payee          TEXT,
    memo           TEXT,
    scheduled_date TEXT NOT NULL,
    recurrence     TEXT NOT NULL DEFAULT 'once' CHECK (recurrence IN ('once', 'weekly', 'monthly', 'yearly')),
    is_active      INTEGER NOT NULL DEFAULT 1,
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS wishlist (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    icon       TEXT NOT NULL DEFAULT '🎁',
    price      REAL,
    priority   TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('high', 'medium', 'low')),
    url        TEXT,
    notes      TEXT,
    status     TEXT NOT NULL DEFAULT 'wanted' CHECK (status IN ('wanted', 'bought')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- User-defined tags. Used to mark events that span multiple envelopes
-- (e.g., "konser", "liburan-bali") so spending can be analyzed by event.
CREATE TABLE IF NOT EXISTS tags (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE COLLATE NOCASE,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS transaction_tags (
    transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    tag_id         INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (transaction_id, tag_id)
);

CREATE INDEX IF NOT EXISTS idx_transaction_tags_tag ON transaction_tags(tag_id);

CREATE TABLE IF NOT EXISTS user_memory (
    id         INTEGER PRIMARY KEY CHECK (id = 1),
    content    TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
INSERT OR IGNORE INTO user_memory (id, content) VALUES (1, '');

