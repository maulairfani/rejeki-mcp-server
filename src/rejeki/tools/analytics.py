from datetime import date
from rejeki.database import fetchone, fetchall


def _current_period() -> str:
    return date.today().strftime("%Y-%m")


def get_true_available() -> dict:
    today = date.today()
    period = today.strftime("%Y-%m")

    total_balance = fetchone("SELECT COALESCE(SUM(balance), 0) AS total FROM accounts")["total"]

    # Fixed expenses belum jatuh tempo bulan ini
    fixed = fetchall("SELECT name, amount, due_date FROM fixed_expenses")
    unpaid_fixed = [f for f in fixed if f["due_date"] >= today.day]
    total_fixed = sum(f["amount"] for f in unpaid_fixed)

    # Upcoming expenses bulan ini yang belum dibayar
    upcoming = fetchall(
        "SELECT name, amount FROM upcoming_expenses WHERE is_paid = 0 AND strftime('%Y-%m', due_date) = ?",
        (period,),
    )
    total_upcoming = sum(u["amount"] for u in upcoming)

    # Saving goals — estimasi alokasi sederhana (current_amount sudah di dalam balance saving)
    # Kita tidak lock saving goals dari balance di v1, cukup informasional
    goals = fetchall("SELECT name, target_amount, current_amount FROM saving_goals ORDER BY priority")
    total_saving_allocated = sum(g["current_amount"] for g in goals)

    true_available = total_balance - total_fixed - total_upcoming

    return {
        "total_balance": total_balance,
        "deductions": {
            "unpaid_fixed_expenses": {"total": total_fixed, "items": unpaid_fixed},
            "upcoming_expenses_this_month": {"total": total_upcoming, "items": upcoming},
        },
        "true_available": true_available,
        "saving_goals_info": goals,
        "as_of": today.isoformat(),
    }


def can_afford(amount: float, description: str | None = None) -> dict:
    ta = get_true_available()
    true_available = ta["true_available"]
    can = true_available >= amount
    return {
        "description": description,
        "amount": amount,
        "true_available": true_available,
        "can_afford": can,
        "remaining_after": true_available - amount if can else None,
    }


def get_summary(period: str | None = None) -> dict:
    period = period or _current_period()

    income = fetchone(
        "SELECT COALESCE(SUM(amount), 0) AS total FROM transactions WHERE type = 'income' AND strftime('%Y-%m', date) = ?",
        (period,),
    )["total"]

    expense = fetchone(
        "SELECT COALESCE(SUM(amount), 0) AS total FROM transactions WHERE type = 'expense' AND strftime('%Y-%m', date) = ?",
        (period,),
    )["total"]

    by_category = fetchall(
        """SELECT c.name AS category, c.icon, COALESCE(SUM(t.amount), 0) AS total
           FROM transactions t
           JOIN categories c ON t.category_id = c.id
           WHERE t.type = 'expense' AND strftime('%Y-%m', t.date) = ?
           GROUP BY c.id
           ORDER BY total DESC""",
        (period,),
    )

    return {
        "period": period,
        "income": income,
        "expense": expense,
        "net": income - expense,
        "expense_by_category": by_category,
    }


def get_spending_trend(category_id: int | None = None, months: int = 3) -> list[dict]:
    rows = fetchall(
        """SELECT strftime('%Y-%m', t.date) AS period,
                  c.name AS category, c.icon,
                  COALESCE(SUM(t.amount), 0) AS total
           FROM transactions t
           JOIN categories c ON t.category_id = c.id
           WHERE t.type = 'expense'
             AND (? IS NULL OR t.category_id = ?)
             AND t.date >= date('now', ? || ' months')
           GROUP BY period, t.category_id
           ORDER BY period DESC, total DESC""",
        (category_id, category_id, f"-{months}"),
    )
    return rows
