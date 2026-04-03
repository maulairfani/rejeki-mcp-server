import os

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.dependencies import Depends
from fastmcp.server.auth.providers.workos import AuthKitProvider

from rejeki.database import Database
from rejeki.deps import get_user_db
from rejeki.platform_db import init_platform_db
from rejeki.tools import accounts, analytics, envelopes, scheduled, transactions
from rejeki.tools import quick_add as _quick_add

load_dotenv()
init_platform_db()

_test_token = os.environ.get("TEST_TOKEN")
if _test_token:
    from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
    auth = StaticTokenVerifier(
        tokens={
            _test_token: {
                "client_id": "test-user-eval-001",
                "scopes": ["read", "write"],
            }
        }
    )
else:
    auth = AuthKitProvider(
        authkit_domain=os.environ["AUTHKIT_DOMAIN"],
        base_url=os.environ.get("BASE_URL", "http://localhost:8000"),
    )

mcp = FastMCP("rejeki", auth=auth)


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------

@mcp.tool()
def finance_add_account(name: str, type: str, initial_balance: float = 0, db: Database = Depends(get_user_db)) -> dict:
    """Tambah rekening baru. type: bank | ewallet | cash"""
    return accounts.add_account(db, name, type, initial_balance)


@mcp.tool()
def finance_get_accounts(db: Database = Depends(get_user_db)) -> dict:
    """List semua rekening beserta saldo dan total keseluruhan."""
    return accounts.get_accounts(db)


@mcp.tool()
def finance_edit_account(id: int, name: str | None = None, type: str | None = None, db: Database = Depends(get_user_db)) -> dict:
    """Edit nama atau tipe rekening."""
    return accounts.edit_account(db, id, name, type)


@mcp.tool()
def finance_update_balance(id: int, balance: float, db: Database = Depends(get_user_db)) -> dict:
    """Set saldo rekening langsung (rekonsiliasi manual)."""
    return accounts.update_balance(db, id, balance)


@mcp.tool()
def finance_delete_account(id: int, db: Database = Depends(get_user_db)) -> dict:
    """Hapus rekening."""
    return accounts.delete_account(db, id)


# ---------------------------------------------------------------------------
# Envelope groups
# ---------------------------------------------------------------------------

@mcp.tool()
def finance_get_groups(db: Database = Depends(get_user_db)) -> list:
    """List semua kelompok envelope."""
    return envelopes.get_groups(db)


@mcp.tool()
def finance_add_group(name: str, sort_order: int = 0, db: Database = Depends(get_user_db)) -> dict:
    """Tambah kelompok envelope baru."""
    return envelopes.add_group(db, name, sort_order)


# ---------------------------------------------------------------------------
# Envelopes — CRUD + budget view
# ---------------------------------------------------------------------------

@mcp.tool()
def finance_get_envelopes(period: str | None = None, db: Database = Depends(get_user_db)) -> dict:
    """
    Tampilkan semua envelope.
    Income sources: referensi untuk mencatat pemasukan.
    Expense envelopes per kelompok: carryover, assigned, activity, available, target.
    period format YYYY-MM (default bulan ini).
    """
    return envelopes.get_envelopes(db, period)


@mcp.tool()
def finance_add_envelope(name: str, type: str, icon: str | None = None, group_id: int | None = None, db: Database = Depends(get_user_db)) -> dict:
    """
    Tambah envelope baru. type: income | expense.
    group_id untuk expense (opsional — tanpa group masuk kelompok 'Lainnya').
    """
    return envelopes.add_envelope(db, name, type, icon, group_id)


@mcp.tool()
def finance_edit_envelope(
    id: int,
    name: str | None = None,
    icon: str | None = None,
    group_id: int | None = None,
    db: Database = Depends(get_user_db),
) -> dict:
    """Edit envelope. Isi hanya field yang mau diubah."""
    return envelopes.edit_envelope(db, id, name, icon, group_id)


@mcp.tool()
def finance_delete_envelope(id: int, db: Database = Depends(get_user_db)) -> dict:
    """Hapus envelope beserta semua data budgetnya."""
    return envelopes.delete_envelope(db, id)


@mcp.tool()
def finance_set_target(
    envelope_id: int,
    target_type: str,
    target_amount: float | None = None,
    target_deadline: str | None = None,
    db: Database = Depends(get_user_db),
) -> dict:
    """
    Set funding target pada envelope expense.
    target_type: 'monthly' — assign X setiap bulan.
                 'goal'    — kumpulkan X sampai deadline.
    target_deadline format YYYY-MM-DD, hanya untuk goal.
    """
    return envelopes.set_target(db, envelope_id, target_type, target_amount, target_deadline)


@mcp.tool()
def finance_assign_to_envelope(envelope_id: int, amount: float, period: str | None = None, db: Database = Depends(get_user_db)) -> dict:
    """
    Assign uang dari Ready to Assign ke envelope.
    Ini operasi inti Rejeki: 'give every rupiah a job'.
    Memanggil ini lagi pada period yang sama akan menimpa assigned sebelumnya.
    period format YYYY-MM (default bulan ini).
    """
    return envelopes.assign_to_envelope(db, envelope_id, amount, period)


@mcp.tool()
def finance_move_money(
    from_envelope_id: int,
    to_envelope_id: int,
    amount: float,
    period: str | None = None,
    db: Database = Depends(get_user_db),
) -> dict:
    """
    Pindahkan uang antar envelope dalam satu period.
    Dipakai saat overspend di satu envelope dan perlu ditutup dari envelope lain.
    period format YYYY-MM (default bulan ini).
    """
    return envelopes.move_money(db, from_envelope_id, to_envelope_id, amount, period)


# ---------------------------------------------------------------------------
# Quick add
# ---------------------------------------------------------------------------

@mcp.tool()
def finance_quick_add(text: str, db: Database = Depends(get_user_db)) -> dict:
    """
    GUNAKAN INI sebagai satu-satunya cara mencatat pengeluaran sehari-hari.
    JANGAN panggil finance_get_accounts atau finance_get_envelopes terlebih dahulu —
    tool ini sudah menangani resolusi rekening dan envelope secara internal.

    Otomatis deteksi: nominal, rekening, envelope, payee.
    Contoh input: 'makan ayam 15k gopay', 'bensin 50rb bca', 'kopi kenangan 35000 dana'
    """
    return _quick_add.quick_add(db, text)


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

@mcp.tool()
def finance_add_transaction(
    amount: float,
    type: str,
    account_id: int,
    envelope_id: int | None = None,
    to_account_id: int | None = None,
    payee: str | None = None,
    memo: str | None = None,
    transaction_date: str | None = None,
    db: Database = Depends(get_user_db),
) -> dict:
    """
    Catat transaksi dengan ID eksplisit. Gunakan ini hanya untuk:
    - income dan transfer (bukan expense sehari-hari)
    - saat perlu kontrol penuh atas account_id / envelope_id / tanggal

    Untuk expense sehari-hari, gunakan finance_quick_add — lebih cepat dan tidak perlu ID.
    type: income | expense | transfer.
    transaction_date format YYYY-MM-DD (default hari ini).
    """
    return transactions.add_transaction(
        db, amount, type, account_id, envelope_id, to_account_id, payee, memo, transaction_date
    )


@mcp.tool()
def finance_get_transactions(
    account_id: int | None = None,
    envelope_id: int | None = None,
    type: str | None = None,
    payee: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 50,
    db: Database = Depends(get_user_db),
) -> list:
    """
    Query transaksi. Semua filter opsional dan bisa dikombinasikan.
    payee: partial match (misal 'Grab' cocok dengan 'GrabFood').
    """
    return transactions.get_transactions(db, account_id, envelope_id, type, payee, date_from, date_to, limit)


@mcp.tool()
def finance_edit_transaction(
    id: int,
    amount: float | None = None,
    type: str | None = None,
    account_id: int | None = None,
    envelope_id: int | None = None,
    to_account_id: int | None = None,
    payee: str | None = None,
    memo: str | None = None,
    transaction_date: str | None = None,
    db: Database = Depends(get_user_db),
) -> dict:
    """Edit transaksi yang sudah ada. Isi hanya field yang mau diubah."""
    return transactions.edit_transaction(
        db, id, amount, type, account_id, envelope_id, to_account_id, payee, memo, transaction_date
    )


@mcp.tool()
def finance_delete_transaction(id: int, db: Database = Depends(get_user_db)) -> dict:
    """Hapus transaksi dan balikkan efeknya ke saldo rekening."""
    return transactions.delete_transaction(db, id)


# ---------------------------------------------------------------------------
# Scheduled transactions
# ---------------------------------------------------------------------------

@mcp.tool()
def finance_add_scheduled_transaction(
    amount: float,
    type: str,
    account_id: int,
    scheduled_date: str,
    envelope_id: int | None = None,
    to_account_id: int | None = None,
    payee: str | None = None,
    memo: str | None = None,
    recurrence: str = "once",
    db: Database = Depends(get_user_db),
) -> dict:
    """
    Jadwalkan transaksi di masa depan.
    recurrence: once | weekly | monthly | yearly.
    scheduled_date format YYYY-MM-DD.
    """
    return scheduled.add_scheduled_transaction(
        db, amount, type, account_id, scheduled_date, envelope_id, to_account_id, payee, memo, recurrence
    )


@mcp.tool()
def finance_get_scheduled_transactions(include_inactive: bool = False, db: Database = Depends(get_user_db)) -> list:
    """List transaksi terjadwal, termasuk field days_until (berapa hari lagi)."""
    return scheduled.get_scheduled_transactions(db, include_inactive)


@mcp.tool()
def finance_approve_scheduled_transaction(id: int, db: Database = Depends(get_user_db)) -> dict:
    """
    Eksekusi scheduled transaction sebagai transaksi nyata.
    Jika recurring, otomatis jadwalkan ke occurrence berikutnya.
    """
    return scheduled.approve_scheduled_transaction(db, id)


@mcp.tool()
def finance_skip_scheduled_transaction(id: int, db: Database = Depends(get_user_db)) -> dict:
    """
    Lewati occurrence ini tanpa mencatat transaksi.
    Jika recurring, maju ke occurrence berikutnya.
    """
    return scheduled.skip_scheduled_transaction(db, id)


@mcp.tool()
def finance_delete_scheduled_transaction(id: int, db: Database = Depends(get_user_db)) -> dict:
    """Hapus scheduled transaction sepenuhnya."""
    return scheduled.delete_scheduled_transaction(db, id)


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

@mcp.tool()
def finance_get_onboarding_status(db: Database = Depends(get_user_db)) -> dict:
    """
    Cek status onboarding: rekening, targets, envelope assignment, RTA.
    Panggil ini di awal setiap sesi baru.
    """
    return analytics.get_onboarding_status(db)


@mcp.tool()
def finance_get_ready_to_assign(period: str | None = None, db: Database = Depends(get_user_db)) -> dict:
    """
    Hitung Ready to Assign = total saldo rekening − total available semua envelope.
    Target: nol. Setiap rupiah harus punya tugas.
    """
    return analytics.get_ready_to_assign(db, period)


@mcp.tool()
def finance_get_age_of_money(db: Database = Depends(get_user_db)) -> dict:
    """
    Hitung Age of Money: rata-rata berapa hari uang duduk sebelum dipakai.
    Dihitung FIFO. Target: 30+ hari.
    """
    return analytics.get_age_of_money(db)


@mcp.tool()
def finance_get_summary(period: str | None = None, db: Database = Depends(get_user_db)) -> dict:
    """Ringkasan bulanan: income, expense, net, breakdown per envelope. period: YYYY-MM."""
    return analytics.get_summary(db, period)


@mcp.tool()
def finance_get_spending_trend(envelope_id: int | None = None, months: int = 3, db: Database = Depends(get_user_db)) -> list:
    """Tren pengeluaran per envelope, N bulan ke belakang."""
    return analytics.get_spending_trend(db, envelope_id, months)


# ---------------------------------------------------------------------------

def main():
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
