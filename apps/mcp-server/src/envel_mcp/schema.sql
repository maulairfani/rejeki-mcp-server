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
    target_deadline TEXT
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
    price      REAL,
    priority   TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('high', 'medium', 'low')),
    url        TEXT,
    notes      TEXT,
    status     TEXT NOT NULL DEFAULT 'wanted' CHECK (status IN ('wanted', 'bought')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Default envelope groups
INSERT OR IGNORE INTO envelope_groups (id, name, sort_order) VALUES
    (1, 'Fixed Expenses',    1),
    (2, 'Daily Essentials',  2),
    (3, 'Personal Spending', 3),
    (4, 'Savings & Goals',   4),
    (5, 'Unexpected',        5);

-- Default envelopes
INSERT OR IGNORE INTO envelopes (id, name, icon, type, group_id) VALUES
    -- Income sources (no group)
    (1,  'Salary',           '💼', 'income',  NULL),
    (2,  'Freelance',        '💻', 'income',  NULL),
    (3,  'Investments',      '📈', 'income',  NULL),
    (4,  'Other Income',     '💰', 'income',  NULL),
    -- Fixed Expenses
    (5,  'Rent',             '🏡', 'expense', 1),
    (6,  'Bills',            '📄', 'expense', 1),
    (7,  'Subscriptions',    '🔄', 'expense', 1),
    (8,  'Family Support',   '🏠', 'expense', 1),
    -- Daily Essentials
    (9,  'Food',             '🍽️', 'expense', 2),
    (10, 'Transport',        '🚗', 'expense', 2),
    -- Personal Spending
    (11, 'Shopping',         '🛍️', 'expense', 3),
    (12, 'Entertainment',    '🎮', 'expense', 3),
    (13, 'Health',           '🏥', 'expense', 3),
    (14, 'Education',        '📚', 'expense', 3),
    -- Savings & Goals
    (15, 'Emergency Fund',   '🛡️', 'expense', 4),
    (16, 'Savings',          '💎', 'expense', 4),
    -- Unexpected
    (17, 'Miscellaneous',    '💸', 'expense', 5);
