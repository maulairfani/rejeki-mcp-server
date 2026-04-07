"""
Seed demo data for a user's personal database.

Usage:
    python scripts/seed_demo.py <username> [--users-db PATH]
"""
import argparse
import sqlite3
from pathlib import Path

USERS_DB = Path(__file__).parent.parent / "users.db"
SCHEMA = Path(__file__).parent.parent / "apps/mcp-server/src/envel_mcp/schema.sql"


def get_user_db_path(username: str, users_db: Path) -> str:
    conn = sqlite3.connect(str(users_db))
    row = conn.execute("SELECT db_path FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if not row:
        raise SystemExit(f"User '{username}' not found in {users_db}")
    return row[0]


def seed(db_path: str):
    conn = sqlite3.connect(db_path)

    # Apply schema
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))

    # ── Accounts ────────────────────────────────────────────────────
    conn.executescript("""
    DELETE FROM transactions;
    DELETE FROM budget_periods;
    DELETE FROM accounts;
    """)

    conn.executemany(
        "INSERT INTO accounts (id, name, type, balance) VALUES (?, ?, ?, ?)",
        [
            (1, "BCA",          "bank",    12_500_000),
            (2, "GoPay",        "ewallet",  1_200_000),
            (3, "Cash",         "cash",       450_000),
        ],
    )

    # ── Budget periods (April 2026) ──────────────────────────────────
    # envelope_id: 5=Rent, 6=Bills, 7=Subscriptions, 8=Family Support
    #              9=Food, 10=Transport, 11=Shopping, 12=Entertainment
    #              13=Health, 14=Education, 15=Emergency, 16=Savings, 17=Misc
    conn.executemany(
        "INSERT OR REPLACE INTO budget_periods (envelope_id, period, assigned, carryover) VALUES (?, ?, ?, ?)",
        [
            (5,  "2026-04", 2_500_000, 0),
            (6,  "2026-04",   500_000, 0),
            (7,  "2026-04",   250_000, 0),
            (8,  "2026-04",   800_000, 0),
            (9,  "2026-04", 1_200_000, 0),
            (10, "2026-04",   400_000, 0),
            (11, "2026-04",   500_000, 0),
            (12, "2026-04",   300_000, 0),
            (13, "2026-04",   200_000, 0),
            (14, "2026-04",   150_000, 0),
            (15, "2026-04",   500_000, 0),
            (16, "2026-04",   700_000, 0),
            (17, "2026-04",   200_000, 0),
            # March carryover
            (9,  "2026-03", 1_200_000,  50_000),
            (11, "2026-03",   500_000, 120_000),
        ],
    )

    # ── Transactions ─────────────────────────────────────────────────
    # April 2026 income
    txns = [
        # (amount, type, envelope_id, account_id, payee, memo, date)
        (8_500_000, "income", 1,  1, "PT Maju Jaya",    "Salary April",         "2026-04-01 09:00:00"),
        (1_500_000, "income", 2,  1, "Client Freelance", "UI project payment",  "2026-04-03 14:30:00"),

        # Fixed expenses
        (2_500_000, "expense", 5,  1, "Pak Budi (kost)", "Rent April",          "2026-04-01 10:00:00"),
        (  150_000, "expense", 6,  2, "PLN",             "Electricity",          "2026-04-02 08:00:00"),
        (   80_000, "expense", 6,  2, "PDAM",            "Water bill",           "2026-04-02 08:05:00"),
        (  159_000, "expense", 7,  2, "Netflix",         "Monthly subscription", "2026-04-02 12:00:00"),
        (   79_000, "expense", 7,  2, "Spotify",         "Monthly subscription", "2026-04-02 12:05:00"),
        (  800_000, "expense", 8,  1, "Ibu",             "Family support",       "2026-04-02 15:00:00"),

        # Daily — food
        (  35_000, "expense", 9,  3, "Warung Bu Sari",  "Lunch",                "2026-04-01 12:00:00"),
        (  45_000, "expense", 9,  3, "Warung Bu Sari",  "Dinner",               "2026-04-01 19:00:00"),
        (  28_000, "expense", 9,  3, "Indomaret",       "Breakfast snack",      "2026-04-02 07:30:00"),
        (  62_000, "expense", 9,  2, "GrabFood",        "Nasi goreng + drinks", "2026-04-02 12:30:00"),
        (  45_000, "expense", 9,  3, "Warung Padang",   "Lunch",                "2026-04-03 12:15:00"),
        (  38_000, "expense", 9,  3, "Mie Ayam Pak Joko","Dinner",              "2026-04-03 18:45:00"),
        (  55_000, "expense", 9,  2, "GoFood",          "Ayam geprek delivery", "2026-04-04 12:00:00"),
        (  72_000, "expense", 9,  1, "Superindo",       "Groceries",            "2026-04-05 10:00:00"),

        # Transport
        (  25_000, "expense", 10, 2, "Gojek",           "To office",            "2026-04-01 08:00:00"),
        (  25_000, "expense", 10, 2, "Gojek",           "From office",          "2026-04-01 18:00:00"),
        (  22_000, "expense", 10, 2, "Gojek",           "To office",            "2026-04-02 08:00:00"),
        (  18_000, "expense", 10, 2, "Grab",            "From office",          "2026-04-02 18:00:00"),
        (  30_000, "expense", 10, 3, "Bensin",          "Fuel top-up",          "2026-04-03 07:30:00"),
        (  25_000, "expense", 10, 2, "Gojek",           "To client meeting",    "2026-04-04 09:00:00"),

        # Shopping
        ( 299_000, "expense", 11, 1, "Shopee",          "T-shirt",              "2026-04-02 20:00:00"),
        (  85_000, "expense", 11, 2, "Alfamart",        "Toiletries",           "2026-04-04 16:00:00"),

        # Entertainment
        (  50_000, "expense", 12, 3, "CGV",             "Movie ticket",         "2026-04-05 19:00:00"),
        (  75_000, "expense", 12, 3, "Timezone",        "Weekend fun",          "2026-04-06 15:00:00"),

        # Health
        (  85_000, "expense", 13, 1, "Apotek K-24",     "Vitamins",             "2026-04-03 17:00:00"),

        # Previous months (March)
        (8_500_000, "income", 1, 1, "PT Maju Jaya",    "Salary March",         "2026-03-01 09:00:00"),
        (  35_000, "expense", 9, 3, "Warung",           "Lunch",                "2026-03-15 12:00:00"),
        ( 450_000, "expense", 9, 1, "Superindo",        "Monthly groceries",    "2026-03-20 10:00:00"),
        ( 200_000, "expense", 10,2, "Gojek",            "March transport",      "2026-03-31 18:00:00"),
        (  25_000, "expense", 9, 3, "Warung",           "Dinner",               "2026-03-31 19:00:00"),

        # February
        (8_500_000, "income", 1, 1, "PT Maju Jaya",    "Salary February",      "2026-02-01 09:00:00"),
        ( 380_000, "expense", 9, 1, "Superindo",        "Groceries",            "2026-02-15 10:00:00"),
        ( 180_000, "expense", 10,2, "Transport Feb",    "Monthly Gojek",        "2026-02-28 18:00:00"),
        ( 450_000, "expense", 11,1, "Shopee",           "Shoes",                "2026-02-20 14:00:00"),
    ]

    conn.executemany(
        """INSERT INTO transactions (amount, type, envelope_id, account_id, payee, memo, date)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        txns,
    )

    # ── Wishlist ─────────────────────────────────────────────────────
    conn.executemany(
        "INSERT INTO wishlist (name, price, priority, notes) VALUES (?, ?, ?, ?)",
        [
            ("Mechanical Keyboard",  1_200_000, "high",   "For WFH setup"),
            ("Monitor 27 inch",      3_500_000, "medium", "IPS panel, 1440p"),
            ("Running Shoes",          800_000, "low",    "Nike Air Zoom"),
        ],
    )

    conn.commit()
    conn.close()
    print(f"[OK] Seed data inserted into {db_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("username")
    parser.add_argument("--users-db", default=str(USERS_DB))
    args = parser.parse_args()

    db_path = get_user_db_path(args.username, Path(args.users_db))
    seed(db_path)
    print(f"  User     : {args.username}")
    print(f"  DB       : {db_path}")


if __name__ == "__main__":
    main()
