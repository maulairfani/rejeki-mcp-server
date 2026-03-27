from rejeki.database import execute, fetchall, fetchone


# --- Fixed Expenses ---

def add_fixed_expense(name: str, amount: float, due_date: int, account_id: int | None = None) -> dict:
    id = execute(
        "INSERT INTO fixed_expenses (name, amount, due_date, account_id) VALUES (?, ?, ?, ?)",
        (name, amount, due_date, account_id),
    )
    return {"id": id, "name": name, "amount": amount, "due_date": due_date}


def get_fixed_expenses() -> dict:
    rows = fetchall(
        """SELECT f.id, f.name, f.amount, f.due_date, a.name AS account
           FROM fixed_expenses f
           LEFT JOIN accounts a ON f.account_id = a.id
           ORDER BY f.due_date"""
    )
    total = sum(r["amount"] for r in rows)
    return {"fixed_expenses": rows, "total_monthly": total}


# --- Upcoming Expenses ---

def add_upcoming_expense(name: str, amount: float, due_date: str, notes: str | None = None) -> dict:
    id = execute(
        "INSERT INTO upcoming_expenses (name, amount, due_date, notes) VALUES (?, ?, ?, ?)",
        (name, amount, due_date, notes),
    )
    return {"id": id, "name": name, "amount": amount, "due_date": due_date}


def get_upcoming_expenses(include_paid: bool = False) -> list[dict]:
    if include_paid:
        return fetchall("SELECT * FROM upcoming_expenses ORDER BY due_date")
    return fetchall("SELECT * FROM upcoming_expenses WHERE is_paid = 0 ORDER BY due_date")


def mark_upcoming_paid(id: int) -> dict:
    expense = fetchone("SELECT * FROM upcoming_expenses WHERE id = ?", (id,))
    if not expense:
        return {"error": f"Upcoming expense id={id} tidak ditemukan"}
    execute("UPDATE upcoming_expenses SET is_paid = 1 WHERE id = ?", (id,))
    return {"id": id, "name": expense["name"], "status": "paid"}


# --- Wishlist ---

def manage_wishlist(action: str, name: str | None = None, price: float | None = None,
                    priority: int | None = None, notes: str | None = None,
                    id: int | None = None) -> dict | list:
    if action == "list":
        return fetchall("SELECT * FROM wishlist ORDER BY priority NULLS LAST, price")
    if action == "add":
        new_id = execute(
            "INSERT INTO wishlist (name, price, priority, notes) VALUES (?, ?, ?, ?)",
            (name, price, priority, notes),
        )
        return {"id": new_id, "name": name, "price": price, "priority": priority}
    if action == "remove":
        item = fetchone("SELECT * FROM wishlist WHERE id = ?", (id,))
        if not item:
            return {"error": f"Wishlist id={id} tidak ditemukan"}
        execute("DELETE FROM wishlist WHERE id = ?", (id,))
        return {"id": id, "name": item["name"], "status": "removed"}
    return {"error": f"Action '{action}' tidak dikenal. Gunakan: list, add, remove"}


# --- Assets ---

def add_asset(name: str, type: str, cost_basis: float, quantity: float,
              date_acquired: str | None = None) -> dict:
    from datetime import date
    acquired = date_acquired or date.today().isoformat()
    id = execute(
        "INSERT INTO assets (name, type, cost_basis, quantity, date_acquired) VALUES (?, ?, ?, ?, ?)",
        (name, type, cost_basis, quantity, acquired),
    )
    return {"id": id, "name": name, "type": type, "cost_basis": cost_basis, "quantity": quantity}


def get_assets() -> dict:
    rows = fetchall("SELECT * FROM assets ORDER BY type, name")
    total_cost_basis = sum(r["cost_basis"] for r in rows)
    return {"assets": rows, "total_cost_basis": total_cost_basis}
