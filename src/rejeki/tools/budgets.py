from datetime import date
from rejeki.database import execute, fetchall, fetchone


def _current_period() -> str:
    return date.today().strftime("%Y-%m")


def set_budget(category_id: int, amount: float, period: str | None = None) -> dict:
    period = period or _current_period()
    existing = fetchone(
        "SELECT id FROM budgets WHERE category_id = ? AND period = ?", (category_id, period)
    )
    if existing:
        execute("UPDATE budgets SET amount = ? WHERE id = ?", (amount, existing["id"]))
    else:
        execute(
            "INSERT INTO budgets (category_id, amount, period) VALUES (?, ?, ?)",
            (category_id, amount, period),
        )
    category = fetchone("SELECT name, icon FROM categories WHERE id = ?", (category_id,))
    return {"category": category["name"], "icon": category["icon"], "amount": amount, "period": period}


def get_budget_status(period: str | None = None) -> list[dict]:
    period = period or _current_period()
    rows = fetchall(
        """SELECT b.id, c.name AS category, c.icon, b.amount AS budget,
                  COALESCE(SUM(t.amount), 0) AS spent
           FROM budgets b
           JOIN categories c ON b.category_id = c.id
           LEFT JOIN transactions t
             ON t.category_id = b.category_id
            AND t.type = 'expense'
            AND strftime('%Y-%m', t.date) = ?
           WHERE b.period = ?
           GROUP BY b.id
           ORDER BY c.name""",
        (period, period),
    )
    for r in rows:
        r["remaining"] = r["budget"] - r["spent"]
        r["percent_used"] = round(r["spent"] / r["budget"] * 100, 1) if r["budget"] else 0
    return rows
