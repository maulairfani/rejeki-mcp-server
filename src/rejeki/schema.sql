-- Rejeki Database Schema

CREATE TABLE IF NOT EXISTS accounts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    type       TEXT NOT NULL CHECK (type IN ('bank', 'ewallet', 'cash')),
    balance    REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS categories (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    icon TEXT,
    type TEXT NOT NULL CHECK (type IN ('income', 'expense'))
);

CREATE TABLE IF NOT EXISTS transactions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    amount        REAL NOT NULL,
    type          TEXT NOT NULL CHECK (type IN ('income', 'expense', 'transfer')),
    category_id   INTEGER REFERENCES categories(id),
    account_id    INTEGER NOT NULL REFERENCES accounts(id),
    to_account_id INTEGER REFERENCES accounts(id),
    description   TEXT,
    date          TEXT NOT NULL DEFAULT (date('now'))
);

CREATE TABLE IF NOT EXISTS budgets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    amount      REAL NOT NULL,
    period      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS saving_goals (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL,
    target_amount  REAL NOT NULL,
    current_amount REAL NOT NULL DEFAULT 0,
    deadline       TEXT,
    priority       INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS fixed_expenses (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    amount     REAL NOT NULL,
    due_date   INTEGER NOT NULL,
    recurrence TEXT NOT NULL DEFAULT 'monthly',
    account_id INTEGER REFERENCES accounts(id)
);

CREATE TABLE IF NOT EXISTS upcoming_expenses (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name     TEXT NOT NULL,
    amount   REAL NOT NULL,
    due_date TEXT NOT NULL,
    notes    TEXT,
    is_paid  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS wishlist (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    price      REAL NOT NULL,
    priority   INTEGER,
    notes      TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS assets (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    type          TEXT NOT NULL,
    cost_basis    REAL NOT NULL,
    quantity      REAL NOT NULL,
    date_acquired TEXT NOT NULL DEFAULT (date('now'))
);

-- Seed default categories
INSERT OR IGNORE INTO categories (id, name, icon, type) VALUES
    -- Income
    (1,  'Gaji',          '💼', 'income'),
    (2,  'Freelance',     '💻', 'income'),
    (3,  'Investasi',     '📈', 'income'),
    (4,  'Lainnya',       '💰', 'income'),
    -- Expense
    (5,  'Makan',         '🍽️', 'expense'),
    (6,  'Transport',     '🚗', 'expense'),
    (7,  'Belanja',       '🛍️', 'expense'),
    (8,  'Hiburan',       '🎮', 'expense'),
    (9,  'Kesehatan',     '🏥', 'expense'),
    (10, 'Pendidikan',    '📚', 'expense'),
    (11, 'Tagihan',       '📄', 'expense'),
    (12, 'Langganan',     '🔄', 'expense'),
    (13, 'Kirim Ortu',    '🏠', 'expense'),
    (14, 'Kos/Sewa',      '🏡', 'expense'),
    (15, 'Lainnya',       '💸', 'expense');
