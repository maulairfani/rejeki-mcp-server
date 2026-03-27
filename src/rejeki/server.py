from fastmcp import FastMCP
from rejeki.database import init_db
from rejeki.tools import accounts, transactions, budgets, saving_goals, others, analytics

init_db()
mcp = FastMCP("rejeki")


# --- Accounts ---

@mcp.tool()
def finance_add_account(name: str, type: str, initial_balance: float = 0) -> dict:
    """Tambah rekening baru. type: bank | ewallet | cash"""
    return accounts.add_account(name, type, initial_balance)


@mcp.tool()
def finance_get_accounts() -> dict:
    """List semua rekening beserta saldo dan total keseluruhan."""
    return accounts.get_accounts()


# --- Transactions ---

@mcp.tool()
def finance_add_transaction(
    amount: float,
    type: str,
    account_id: int,
    category_id: int | None = None,
    to_account_id: int | None = None,
    description: str | None = None,
    transaction_date: str | None = None,
) -> dict:
    """Catat transaksi. type: income | expense | transfer. Untuk transfer isi to_account_id."""
    return transactions.add_transaction(
        amount, type, account_id, category_id, to_account_id, description, transaction_date
    )


@mcp.tool()
def finance_get_transactions(
    account_id: int | None = None,
    category_id: int | None = None,
    type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 50,
) -> list:
    """Query transaksi dengan filter opsional."""
    return transactions.get_transactions(account_id, category_id, type, date_from, date_to, limit)


# --- Budgets ---

@mcp.tool()
def finance_set_budget(category_id: int, amount: float, period: str | None = None) -> dict:
    """Set atau update budget per kategori. period format: YYYY-MM (default bulan ini)."""
    return budgets.set_budget(category_id, amount, period)


@mcp.tool()
def finance_get_budget_status(period: str | None = None) -> list:
    """Status semua budget bulan ini: terpakai, sisa, persen."""
    return budgets.get_budget_status(period)


# --- Saving Goals ---

@mcp.tool()
def finance_add_saving_goal(
    name: str, target_amount: float, priority: int, deadline: str | None = None
) -> dict:
    """Buat saving goal baru. priority 1 = tertinggi (emergency fund)."""
    return saving_goals.add_saving_goal(name, target_amount, priority, deadline)


@mcp.tool()
def finance_get_saving_goals() -> list:
    """List semua saving goals beserta progress."""
    return saving_goals.get_saving_goals()


@mcp.tool()
def finance_update_saving_goal(
    id: int, current_amount: float | None = None, delta: float | None = None
) -> dict:
    """Update progress saving goal. Isi current_amount (set langsung) atau delta (tambah/kurang)."""
    return saving_goals.update_saving_goal(id, current_amount, delta)


# --- Fixed Expenses ---

@mcp.tool()
def finance_add_fixed_expense(
    name: str, amount: float, due_date: int, account_id: int | None = None
) -> dict:
    """Catat kewajiban tetap bulanan. due_date = tanggal dalam bulan (1-31)."""
    return others.add_fixed_expense(name, amount, due_date, account_id)


@mcp.tool()
def finance_get_fixed_expenses() -> dict:
    """List semua kewajiban tetap dan total per bulan."""
    return others.get_fixed_expenses()


# --- Upcoming Expenses ---

@mcp.tool()
def finance_add_upcoming_expense(
    name: str, amount: float, due_date: str, notes: str | None = None
) -> dict:
    """Catat pengeluaran yang akan datang. due_date format: YYYY-MM-DD."""
    return others.add_upcoming_expense(name, amount, due_date, notes)


@mcp.tool()
def finance_get_upcoming_expenses(include_paid: bool = False) -> list:
    """List upcoming expenses yang belum dibayar (default), atau semua."""
    return others.get_upcoming_expenses(include_paid)


@mcp.tool()
def finance_mark_upcoming_paid(id: int) -> dict:
    """Tandai upcoming expense sebagai lunas."""
    return others.mark_upcoming_paid(id)


# --- Wishlist ---

@mcp.tool()
def finance_manage_wishlist(
    action: str,
    name: str | None = None,
    price: float | None = None,
    priority: int | None = None,
    notes: str | None = None,
    id: int | None = None,
) -> dict | list:
    """Kelola wishlist. action: list | add | remove."""
    return others.manage_wishlist(action, name, price, priority, notes, id)


# --- Assets ---

@mcp.tool()
def finance_add_asset(
    name: str, type: str, cost_basis: float, quantity: float, date_acquired: str | None = None
) -> dict:
    """Catat aset investasi berdasarkan cost basis."""
    return others.add_asset(name, type, cost_basis, quantity, date_acquired)


@mcp.tool()
def finance_get_assets() -> dict:
    """List semua aset dan total cost basis."""
    return others.get_assets()


# --- Analytics ---

@mcp.tool()
def finance_get_true_available() -> dict:
    """Hitung True Available Money = total saldo dikurangi semua kewajiban & upcoming."""
    return analytics.get_true_available()


@mcp.tool()
def finance_can_afford(amount: float, description: str | None = None) -> dict:
    """Cek apakah bisa afford sejumlah uang berdasarkan True Available."""
    return analytics.can_afford(amount, description)


@mcp.tool()
def finance_get_summary(period: str | None = None) -> dict:
    """Ringkasan keuangan: income, expense, net, breakdown per kategori. period: YYYY-MM."""
    return analytics.get_summary(period)


@mcp.tool()
def finance_get_spending_trend(category_id: int | None = None, months: int = 3) -> list:
    """Tren pengeluaran per kategori N bulan ke belakang."""
    return analytics.get_spending_trend(category_id, months)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
