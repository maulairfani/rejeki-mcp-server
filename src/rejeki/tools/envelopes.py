from datetime import date
from rejeki.database import Database


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _current_period() -> str:
    return date.today().strftime("%Y-%m")


def _prev_period(period: str) -> str:
    year, month = map(int, period.split("-"))
    if month == 1:
        return f"{year - 1}-12"
    return f"{year}-{month - 1:02d}"


def _activity(db: Database, envelope_id: int, period: str) -> float:
    return db.fetchone(
        """SELECT COALESCE(SUM(amount), 0) AS total FROM transactions
           WHERE envelope_id = ? AND type = 'expense' AND strftime('%Y-%m', date) = ?""",
        (envelope_id, period),
    )["total"]


def _compute_carryover(db: Database, envelope_id: int, period: str) -> float:
    prev = _prev_period(period)
    row = db.fetchone(
        "SELECT assigned, carryover FROM budget_periods WHERE envelope_id = ? AND period = ?",
        (envelope_id, prev),
    )
    if not row:
        return 0.0
    prev_available = row["carryover"] + row["assigned"] - _activity(db, envelope_id, prev)
    return max(0.0, prev_available)


# ---------------------------------------------------------------------------
# Groups
# ---------------------------------------------------------------------------

def get_groups(db: Database) -> list:
    return db.fetchall("SELECT id, name, sort_order FROM envelope_groups ORDER BY sort_order")


def add_group(db: Database, name: str, sort_order: int = 0) -> dict:
    id = db.execute(
        "INSERT INTO envelope_groups (name, sort_order) VALUES (?, ?)",
        (name, sort_order),
    )
    return {"id": id, "name": name, "sort_order": sort_order}


# ---------------------------------------------------------------------------
# Envelope CRUD
# ---------------------------------------------------------------------------

def add_envelope(db: Database, name: str, type: str, icon: str | None = None, group_id: int | None = None) -> dict:
    if type not in ("income", "expense"):
        raise ValueError("type harus 'income' atau 'expense'")
    id = db.execute(
        "INSERT INTO envelopes (name, icon, type, group_id) VALUES (?, ?, ?, ?)",
        (name, icon, type, group_id),
    )
    return {"id": id, "name": name, "icon": icon, "type": type, "group_id": group_id}


def edit_envelope(db: Database, id: int, name: str | None = None, icon: str | None = None, group_id: int | None = None) -> dict:
    env = db.fetchone("SELECT * FROM envelopes WHERE id = ?", (id,))
    if not env:
        raise ValueError(f"Envelope id={id} tidak ditemukan")

    new_name = name or env["name"]
    new_icon = icon if icon is not None else env["icon"]
    new_group_id = group_id if group_id is not None else env["group_id"]

    db.execute(
        "UPDATE envelopes SET name = ?, icon = ?, group_id = ? WHERE id = ?",
        (new_name, new_icon, new_group_id, id),
    )
    return {"id": id, "name": new_name, "icon": new_icon, "type": env["type"], "group_id": new_group_id}


def delete_envelope(db: Database, id: int) -> dict:
    env = db.fetchone("SELECT * FROM envelopes WHERE id = ?", (id,))
    if not env:
        raise ValueError(f"Envelope id={id} tidak ditemukan")

    db.execute("DELETE FROM budget_periods WHERE envelope_id = ?", (id,))
    db.execute("DELETE FROM envelopes WHERE id = ?", (id,))
    return {"deleted_id": id, "name": env["name"]}


def set_target(
    db: Database,
    envelope_id: int,
    target_type: str,
    target_amount: float | None = None,
    target_deadline: str | None = None,
) -> dict:
    env = db.fetchone("SELECT * FROM envelopes WHERE id = ?", (envelope_id,))
    if not env:
        raise ValueError(f"Envelope id={envelope_id} tidak ditemukan")
    if env["type"] != "expense":
        raise ValueError("Hanya envelope expense yang bisa punya target")

    db.execute(
        "UPDATE envelopes SET target_type = ?, target_amount = ?, target_deadline = ? WHERE id = ?",
        (target_type, target_amount, target_deadline, envelope_id),
    )
    return {
        "id": envelope_id,
        "name": env["name"],
        "target_type": target_type,
        "target_amount": target_amount,
        "target_deadline": target_deadline,
    }


# ---------------------------------------------------------------------------
# Budget operations
# ---------------------------------------------------------------------------

def assign_to_envelope(db: Database, envelope_id: int, amount: float, period: str | None = None) -> dict:
    period = period or _current_period()

    env = db.fetchone("SELECT * FROM envelopes WHERE id = ?", (envelope_id,))
    if not env:
        raise ValueError(f"Envelope id={envelope_id} tidak ditemukan")
    if env["type"] != "expense":
        raise ValueError("Hanya envelope expense yang bisa di-assign")

    existing = db.fetchone(
        "SELECT id, carryover FROM budget_periods WHERE envelope_id = ? AND period = ?",
        (envelope_id, period),
    )
    if existing:
        db.execute("UPDATE budget_periods SET assigned = ? WHERE id = ?", (amount, existing["id"]))
        carryover = existing["carryover"]
    else:
        carryover = _compute_carryover(db, envelope_id, period)
        db.execute(
            "INSERT INTO budget_periods (envelope_id, period, assigned, carryover) VALUES (?, ?, ?, ?)",
            (envelope_id, period, amount, carryover),
        )

    act = _activity(db, envelope_id, period)
    return {
        "envelope": env["name"],
        "icon": env["icon"],
        "period": period,
        "carryover": carryover,
        "assigned": amount,
        "activity": act,
        "available": carryover + amount - act,
    }


def move_money(db: Database, from_id: int, to_id: int, amount: float, period: str | None = None) -> dict:
    period = period or _current_period()

    from_env = db.fetchone("SELECT * FROM envelopes WHERE id = ?", (from_id,))
    to_env = db.fetchone("SELECT * FROM envelopes WHERE id = ?", (to_id,))
    if not from_env or not to_env:
        raise ValueError("Envelope tidak ditemukan")

    from_bp = db.fetchone(
        "SELECT id, assigned, carryover FROM budget_periods WHERE envelope_id = ? AND period = ?",
        (from_id, period),
    )
    to_bp = db.fetchone(
        "SELECT id, assigned, carryover FROM budget_periods WHERE envelope_id = ? AND period = ?",
        (to_id, period),
    )

    from_assigned = from_bp["assigned"] if from_bp else 0.0
    to_assigned = to_bp["assigned"] if to_bp else 0.0
    from_carryover = from_bp["carryover"] if from_bp else _compute_carryover(db, from_id, period)
    to_carryover = to_bp["carryover"] if to_bp else _compute_carryover(db, to_id, period)

    new_from = from_assigned - amount
    new_to = to_assigned + amount

    if from_bp:
        db.execute("UPDATE budget_periods SET assigned = ? WHERE id = ?", (new_from, from_bp["id"]))
    else:
        db.execute(
            "INSERT INTO budget_periods (envelope_id, period, assigned, carryover) VALUES (?, ?, ?, ?)",
            (from_id, period, new_from, from_carryover),
        )

    if to_bp:
        db.execute("UPDATE budget_periods SET assigned = ? WHERE id = ?", (new_to, to_bp["id"]))
    else:
        db.execute(
            "INSERT INTO budget_periods (envelope_id, period, assigned, carryover) VALUES (?, ?, ?, ?)",
            (to_id, period, new_to, to_carryover),
        )

    from_act = _activity(db, from_id, period)
    to_act = _activity(db, to_id, period)

    return {
        "moved": amount,
        "period": period,
        "from": {
            "envelope": from_env["name"],
            "icon": from_env["icon"],
            "assigned": new_from,
            "available": from_carryover + new_from - from_act,
        },
        "to": {
            "envelope": to_env["name"],
            "icon": to_env["icon"],
            "assigned": new_to,
            "available": to_carryover + new_to - to_act,
        },
    }


def get_envelopes(db: Database, period: str | None = None) -> dict:
    period = period or _current_period()

    income_sources = db.fetchall(
        "SELECT id, name, icon FROM envelopes WHERE type = 'income' ORDER BY id"
    )

    expense_envelopes = db.fetchall(
        """SELECT e.id, e.name, e.icon, e.target_type, e.target_amount, e.target_deadline,
                  g.name AS group_name, g.id AS group_id
           FROM envelopes e
           LEFT JOIN envelope_groups g ON e.group_id = g.id
           WHERE e.type = 'expense'
           ORDER BY COALESCE(g.sort_order, 999), e.id""",
    )

    groups: dict = {}
    total_assigned = 0.0
    total_available = 0.0

    for env in expense_envelopes:
        bp = db.fetchone(
            "SELECT assigned, carryover FROM budget_periods WHERE envelope_id = ? AND period = ?",
            (env["id"], period),
        )
        carryover = bp["carryover"] if bp else _compute_carryover(db, env["id"], period)
        assigned = bp["assigned"] if bp else 0.0
        act = _activity(db, env["id"], period)
        available = carryover + assigned - act

        group_name = env["group_name"] or "Lainnya"
        if group_name not in groups:
            groups[group_name] = {"group_id": env["group_id"], "envelopes": [], "group_available": 0.0}

        target = None
        if env["target_type"]:
            if env["target_type"] == "monthly":
                funded = assigned >= (env["target_amount"] or 0)
            else:
                funded = available >= (env["target_amount"] or 0)
            target = {
                "type": env["target_type"],
                "amount": env["target_amount"],
                "deadline": env["target_deadline"],
                "status": "funded" if funded else "underfunded",
            }

        groups[group_name]["envelopes"].append({
            "id": env["id"],
            "name": env["name"],
            "icon": env["icon"],
            "carryover": carryover,
            "assigned": assigned,
            "activity": act,
            "available": available,
            "target": target,
        })
        groups[group_name]["group_available"] += available
        total_assigned += assigned
        total_available += available

    return {
        "period": period,
        "income_sources": income_sources,
        "groups": groups,
        "total_assigned": total_assigned,
        "total_available": total_available,
    }


# ---------------------------------------------------------------------------
# FastMCP provider
# ---------------------------------------------------------------------------

from mcp.server.fastmcp import FastMCP
from rejeki.deps import get_user_db

mcp = FastMCP("envelopes")


@mcp.tool(name="get_groups")
def _get_groups_mcp() -> list:
    """List semua kelompok envelope."""
    with get_user_db() as db:
        return get_groups(db)


@mcp.tool(name="add_group")
def _add_group_mcp(name: str, sort_order: int = 0) -> dict:
    """Tambah kelompok envelope baru."""
    with get_user_db() as db:
        return add_group(db, name, sort_order)


@mcp.tool(name="get_envelopes")
def _get_envelopes_mcp(period: str | None = None) -> dict:
    """
    Tampilkan semua envelope.
    Income sources: referensi untuk mencatat pemasukan.
    Expense envelopes per kelompok: carryover, assigned, activity, available, target.
    period format YYYY-MM (default bulan ini).
    """
    with get_user_db() as db:
        return get_envelopes(db, period)


@mcp.tool(name="add_envelope")
def _add_envelope_mcp(name: str, type: str, icon: str | None = None, group_id: int | None = None) -> dict:
    """
    Tambah envelope baru. type: income | expense.
    group_id untuk expense (opsional — tanpa group masuk kelompok 'Lainnya').
    """
    with get_user_db() as db:
        return add_envelope(db, name, type, icon, group_id)


@mcp.tool(name="edit_envelope")
def _edit_envelope_mcp(
    id: int,
    name: str | None = None,
    icon: str | None = None,
    group_id: int | None = None,
) -> dict:
    """Edit envelope. Isi hanya field yang mau diubah."""
    with get_user_db() as db:
        return edit_envelope(db, id, name, icon, group_id)


@mcp.tool(name="delete_envelope")
def _delete_envelope_mcp(id: int) -> dict:
    """Hapus envelope beserta semua data budgetnya."""
    with get_user_db() as db:
        return delete_envelope(db, id)


@mcp.tool(name="set_target")
def _set_target_mcp(
    envelope_id: int,
    target_type: str,
    target_amount: float | None = None,
    target_deadline: str | None = None,
) -> dict:
    """
    Set funding target pada envelope expense.
    target_type: 'monthly' — assign X setiap bulan.
                 'goal'    — kumpulkan X sampai deadline.
    target_deadline format YYYY-MM-DD, hanya untuk goal.
    """
    with get_user_db() as db:
        return set_target(db, envelope_id, target_type, target_amount, target_deadline)


@mcp.tool(name="assign_to_envelope")
def _assign_to_envelope_mcp(envelope_id: int, amount: float, period: str | None = None) -> dict:
    """
    Assign uang dari Ready to Assign ke envelope.
    Ini operasi inti Rejeki: 'give every rupiah a job'.
    Memanggil ini lagi pada period yang sama akan menimpa assigned sebelumnya.
    period format YYYY-MM (default bulan ini).
    """
    with get_user_db() as db:
        return assign_to_envelope(db, envelope_id, amount, period)


@mcp.tool(name="move_money")
def _move_money_mcp(
    from_envelope_id: int,
    to_envelope_id: int,
    amount: float,
    period: str | None = None,
) -> dict:
    """
    Pindahkan uang antar envelope dalam satu period.
    Dipakai saat overspend di satu envelope dan perlu ditutup dari envelope lain.
    period format YYYY-MM (default bulan ini).
    """
    with get_user_db() as db:
        return move_money(db, from_envelope_id, to_envelope_id, amount, period)
