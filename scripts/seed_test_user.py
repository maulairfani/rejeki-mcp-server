"""
Seed a test user into platform.db and populate their SQLite DB with
3 months of realistic finance data (Jan–Mar 2025).

Usage:
    python scripts/seed_test_user.py

The test user will have:
    username  : testuser
    workos_id : test-user-eval-001
    db_path   : ./users/test.db

To connect to the server as this user, set:
    TEST_TOKEN=eval-token-secret-123
"""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
load_dotenv()

from rejeki.platform_db import init_platform_db, _get_conn  # noqa: E402
from rejeki.database import Database, init_db              # noqa: E402

# ── Config ────────────────────────────────────────────────────────────────────
USERNAME  = "testuser"
WORKOS_ID = "test-user-eval-001"
DB_PATH   = "./users/test.db"
# ─────────────────────────────────────────────────────────────────────────────

Path("./users").mkdir(exist_ok=True)

# ── 1. Register in platform DB ────────────────────────────────────────────────
init_platform_db()
platform = _get_conn()
existing = platform.execute("SELECT id FROM users WHERE workos_id = ?", (WORKOS_ID,)).fetchone()
if existing:
    platform.close()
    print(f"User '{USERNAME}' sudah ada, skip registrasi platform.")
else:
    platform.execute(
        "INSERT INTO users (username, workos_id, db_path) VALUES (?, ?, ?)",
        (USERNAME, WORKOS_ID, DB_PATH),
    )
    platform.commit()
    platform.close()
    print(f"User '{USERNAME}' berhasil didaftarkan.")

# ── 2. Seed user DB ───────────────────────────────────────────────────────────
conn = sqlite3.connect(DB_PATH)
db = Database(conn)
init_db(db)

# Clear existing seed data (idempotent re-run)
for tbl in ["scheduled_transactions", "budget_periods", "transactions", "accounts"]:
    conn.execute(f"DELETE FROM {tbl}")
conn.commit()

# ── Accounts ──────────────────────────────────────────────────────────────────
# Balance will be set to final computed value after all transactions
conn.executemany(
    "INSERT INTO accounts (id, name, type, balance) VALUES (?, ?, ?, ?)",
    [
        (1, "BCA Tabungan", "bank",    0),
        (2, "GoPay",        "ewallet", 0),
        (3, "Tunai",        "cash",    300_000),
    ],
)
conn.commit()

# ── Envelope targets ──────────────────────────────────────────────────────────
targets = [
    (5,  "monthly", 1_500_000, None),          # Kos/Sewa
    (6,  "monthly",   350_000, None),          # Tagihan
    (7,  "monthly",    54_000, None),          # Langganan
    (8,  "monthly", 1_000_000, None),          # Kirim Ortu
    (9,  "monthly", 1_200_000, None),          # Makan
    (10, "monthly",   500_000, None),          # Transport
    (11, "monthly",   400_000, None),          # Belanja
    (12, "monthly",   200_000, None),          # Hiburan
    (13, "monthly",   150_000, None),          # Kesehatan
    (14, "monthly",   200_000, None),          # Pendidikan
    (15, "goal",   30_000_000, "2027-12-31"),  # Dana Darurat
    (16, "monthly",   500_000, None),          # Tabungan
]
for eid, ttype, amount, deadline in targets:
    conn.execute(
        "UPDATE envelopes SET target_type=?, target_amount=?, target_deadline=? WHERE id=?",
        (ttype, amount, deadline, eid),
    )
conn.commit()

# ── Transactions ──────────────────────────────────────────────────────────────
# Columns: amount, type, account_id, envelope_id, to_account_id, payee, memo, date
TX = [
    # ── January 2025 ──────────────────────────────────────────────────────────
    # Income
    (8_000_000, "income",   1, 1, None, "Perusahaan ABC",     "Gaji Januari",    "2025-01-01"),
    # Top-up GoPay
    (  600_000, "transfer", 1, None, 2, None,                 "Top-up GoPay",    "2025-01-01"),
    # Fixed
    (1_500_000, "expense",  1, 5, None, "Pak Kos",            None,              "2025-01-02"),
    (1_000_000, "expense",  1, 8, None, "Transfer Keluarga",  None,              "2025-01-03"),
    # Makan
    (   15_000, "expense",  2, 9, None, "Warteg Pak Dhe",     None,              "2025-01-05"),
    (   45_000, "expense",  2, 9, None, "GrabFood",           None,              "2025-01-06"),
    (   15_000, "expense",  2, 9, None, "Warteg Pak Dhe",     None,              "2025-01-08"),
    (   75_000, "expense",  2, 9, None, "McDonald's",         None,              "2025-01-14"),
    (   55_000, "expense",  2, 9, None, "GoFood",             None,              "2025-01-18"),
    (   18_000, "expense",  3, 9, None, "Warteg Pak Dhe",     None,              "2025-01-22"),
    (   40_000, "expense",  3, 9, None, "Warung Sate Pak Mul",None,              "2025-01-28"),
    # Tagihan
    (  150_000, "expense",  2, 6, None, "PLN",                "Listrik Januari", "2025-01-10"),
    (  180_000, "expense",  1, 6, None, "Telkom",             "Internet Januari","2025-01-10"),
    # Langganan
    (   54_000, "expense",  1, 7, None, "Netflix",            None,              "2025-01-15"),
    # Transport
    (   25_000, "expense",  2, 10, None, "Grab",              None,              "2025-01-07"),
    (   50_000, "expense",  2, 10, None, "KRL",               None,              "2025-01-16"),
    (   35_000, "expense",  2, 10, None, "Grab",              None,              "2025-01-24"),
    # Belanja
    (  250_000, "expense",  1, 11, None, "Shopee",            None,              "2025-01-12"),
    (  120_000, "expense",  2, 11, None, "Indomaret",         None,              "2025-01-25"),
    # Kesehatan
    (   85_000, "expense",  3, 13, None, "Apotek",            None,              "2025-01-20"),
    # Savings
    (  500_000, "expense",  1, 15, None, "Dana Darurat",      None,              "2025-01-30"),
    (  500_000, "expense",  1, 16, None, "Tabungan",          None,              "2025-01-31"),

    # ── February 2025 ─────────────────────────────────────────────────────────
    (8_000_000, "income",   1, 1, None, "Perusahaan ABC",     "Gaji Februari",   "2025-02-01"),
    (  700_000, "transfer", 1, None, 2, None,                 "Top-up GoPay",    "2025-02-01"),
    (1_500_000, "expense",  1, 5, None, "Pak Kos",            None,              "2025-02-02"),
    (1_000_000, "expense",  1, 8, None, "Transfer Keluarga",  None,              "2025-02-03"),
    # Makan
    (   15_000, "expense",  2, 9, None, "Warteg Pak Dhe",     None,              "2025-02-05"),
    (   60_000, "expense",  2, 9, None, "GrabFood",           None,              "2025-02-08"),
    (   18_000, "expense",  3, 9, None, "Warteg Pak Dhe",     None,              "2025-02-12"),
    (   70_000, "expense",  2, 9, None, "GoFood",             None,              "2025-02-19"),
    (   20_000, "expense",  3, 9, None, "Warteg Pak Dhe",     None,              "2025-02-25"),
    # Tagihan
    (  140_000, "expense",  2, 6, None, "PLN",                "Listrik Februari","2025-02-10"),
    (  180_000, "expense",  1, 6, None, "Telkom",             "Internet Februari","2025-02-10"),
    # Langganan
    (   54_000, "expense",  1, 7, None, "Netflix",            None,              "2025-02-15"),
    # Transport
    (   30_000, "expense",  2, 10, None, "Grab",              None,              "2025-02-06"),
    (   50_000, "expense",  2, 10, None, "KRL",               None,              "2025-02-17"),
    (   40_000, "expense",  2, 10, None, "Grab",              None,              "2025-02-23"),
    # Belanja
    (  180_000, "expense",  1, 11, None, "Lazada",            None,              "2025-02-13"),
    (   95_000, "expense",  2, 11, None, "Alfamart",          None,              "2025-02-21"),
    # Hiburan
    (  120_000, "expense",  2, 12, None, "CGV",               "Bioskop",         "2025-02-14"),
    # Savings
    (  500_000, "expense",  1, 15, None, "Dana Darurat",      None,              "2025-02-26"),
    (  500_000, "expense",  1, 16, None, "Tabungan",          None,              "2025-02-28"),

    # ── March 2025 ────────────────────────────────────────────────────────────
    (8_000_000, "income",   1, 1, None, "Perusahaan ABC",     "Gaji Maret",      "2025-03-01"),
    (  700_000, "transfer", 1, None, 2, None,                 "Top-up GoPay",    "2025-03-01"),
    (1_500_000, "expense",  1, 5, None, "Pak Kos",            None,              "2025-03-03"),
    (1_000_000, "expense",  1, 8, None, "Transfer Keluarga",  None,              "2025-03-04"),
    # Makan
    (   15_000, "expense",  2, 9, None, "Warteg Pak Dhe",     None,              "2025-03-05"),
    (   65_000, "expense",  2, 9, None, "GoFood",             None,              "2025-03-08"),
    (   85_000, "expense",  2, 9, None, "McDonald's",         None,              "2025-03-14"),
    (   18_000, "expense",  3, 9, None, "Warteg Pak Dhe",     None,              "2025-03-20"),
    (   45_000, "expense",  3, 9, None, "Warung Sate Pak Mul",None,              "2025-03-25"),
    # Tagihan
    (  160_000, "expense",  2, 6, None, "PLN",                "Listrik Maret",   "2025-03-10"),
    (  180_000, "expense",  1, 6, None, "Telkom",             "Internet Maret",  "2025-03-10"),
    # Langganan
    (   54_000, "expense",  1, 7, None, "Netflix",            None,              "2025-03-15"),
    # Freelance income
    (2_500_000, "income",   1, 2, None, "PT Desain Kreatif",  "Project UI/UX",   "2025-03-15"),
    # Transport
    (   25_000, "expense",  2, 10, None, "Grab",              None,              "2025-03-06"),
    (   50_000, "expense",  2, 10, None, "KRL",               None,              "2025-03-18"),
    (   45_000, "expense",  2, 10, None, "Grab",              None,              "2025-03-24"),
    # Belanja
    (  320_000, "expense",  1, 11, None, "Shopee",            None,              "2025-03-17"),
    # Hiburan
    (  100_000, "expense",  1, 12, None, "Steam",             None,              "2025-03-27"),
    # Kesehatan
    (  150_000, "expense",  1, 13, None, "Klinik Sehat",      None,              "2025-03-22"),
    # Pendidikan
    (  150_000, "expense",  1, 14, None, "Udemy",             "Kursus Python",   "2025-03-12"),
    # Savings (higher this month due to freelance)
    (  700_000, "expense",  1, 15, None, "Dana Darurat",      None,              "2025-03-28"),
    (  700_000, "expense",  1, 16, None, "Tabungan",          None,              "2025-03-31"),
]

conn.executemany(
    """INSERT INTO transactions
       (amount, type, account_id, envelope_id, to_account_id, payee, memo, date)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
    TX,
)
conn.commit()

# ── Compute & update account balances ─────────────────────────────────────────
# BCA (id=1) and GoPay (id=2) start at 0; Tunai (id=3) starts at 300,000.
balances = {1: 0, 2: 0, 3: 300_000}

for amount, txtype, acct, _, to_acct, *_ in TX:
    if txtype == "income":
        balances[acct] += amount
    elif txtype == "expense":
        balances[acct] -= amount
    elif txtype == "transfer":
        balances[acct]    -= amount
        balances[to_acct] += amount

for acct_id, bal in balances.items():
    conn.execute("UPDATE accounts SET balance = ? WHERE id = ?", (bal, acct_id))
conn.commit()

# ── Budget periods (assigned per envelope per month) ──────────────────────────
BP = [
    # Jan 2025
    (5,  "2025-01", 1_500_000, 0),  # Kos/Sewa
    (6,  "2025-01",   330_000, 0),  # Tagihan
    (7,  "2025-01",    54_000, 0),  # Langganan
    (8,  "2025-01", 1_000_000, 0),  # Kirim Ortu
    (9,  "2025-01", 1_200_000, 0),  # Makan
    (10, "2025-01",   500_000, 0),  # Transport
    (11, "2025-01",   400_000, 0),  # Belanja
    (12, "2025-01",   200_000, 0),  # Hiburan
    (13, "2025-01",   100_000, 0),  # Kesehatan
    (15, "2025-01",   500_000, 0),  # Dana Darurat
    (16, "2025-01",   500_000, 0),  # Tabungan
    # Feb 2025
    (5,  "2025-02", 1_500_000, 0),
    (6,  "2025-02",   320_000, 0),
    (7,  "2025-02",    54_000, 0),
    (8,  "2025-02", 1_000_000, 0),
    (9,  "2025-02", 1_200_000, 0),
    (10, "2025-02",   500_000, 0),
    (11, "2025-02",   400_000, 0),
    (12, "2025-02",   200_000, 0),
    (15, "2025-02",   500_000, 0),
    (16, "2025-02",   500_000, 0),
    # Mar 2025
    (5,  "2025-03", 1_500_000, 0),
    (6,  "2025-03",   340_000, 0),
    (7,  "2025-03",    54_000, 0),
    (8,  "2025-03", 1_000_000, 0),
    (9,  "2025-03", 1_200_000, 0),
    (10, "2025-03",   500_000, 0),
    (11, "2025-03",   400_000, 0),
    (12, "2025-03",   300_000, 0),  # extra for hiburan
    (13, "2025-03",   200_000, 0),  # kesehatan
    (14, "2025-03",   200_000, 0),  # pendidikan
    (15, "2025-03",   700_000, 0),  # more due to freelance
    (16, "2025-03",   700_000, 0),
]
conn.executemany(
    "INSERT OR REPLACE INTO budget_periods (envelope_id, period, assigned, carryover) VALUES (?, ?, ?, ?)",
    BP,
)
conn.commit()

# ── Scheduled transactions ────────────────────────────────────────────────────
SCHED = [
    (1_500_000, "expense", 5, 1, None, "Pak Kos",           None,    "2025-04-03", "monthly"),
    (1_000_000, "expense", 8, 1, None, "Transfer Keluarga", None,    "2025-04-04", "monthly"),
    (   54_000, "expense", 7, 1, None, "Netflix",           None,    "2025-04-15", "monthly"),
    (  180_000, "expense", 6, 1, None, "Telkom",            "Internet","2025-04-10","monthly"),
]
conn.executemany(
    """INSERT INTO scheduled_transactions
       (amount, type, envelope_id, account_id, to_account_id, payee, memo, scheduled_date, recurrence)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
    SCHED,
)
conn.commit()
conn.close()

# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\nTest user berhasil di-seed!")
print(f"  username  : {USERNAME}")
print(f"  workos_id : {WORKOS_ID}")
print(f"  db_path   : {DB_PATH}")
print(f"\nAccount balances:")
for aid, name in [(1, "BCA"), (2, "GoPay"), (3, "Tunai")]:
    print(f"  {name}: Rp {balances[aid]:,.0f}")
print(f"\nTransactions: {len(TX)} records (Jan–Mar 2025)")
print(f"Budget periods: {len(BP)} records")
print(f"Scheduled: {len(SCHED)} recurring transactions")
print(f"\nFor server TEST_TOKEN, set: TEST_TOKEN=eval-token-secret-123")
