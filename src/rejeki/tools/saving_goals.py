from rejeki.database import execute, fetchall, fetchone


def add_saving_goal(
    name: str, target_amount: float, priority: int, deadline: str | None = None
) -> dict:
    id = execute(
        "INSERT INTO saving_goals (name, target_amount, deadline, priority) VALUES (?, ?, ?, ?)",
        (name, target_amount, deadline, priority),
    )
    return {"id": id, "name": name, "target_amount": target_amount, "priority": priority, "deadline": deadline}


def get_saving_goals() -> list[dict]:
    rows = fetchall(
        "SELECT id, name, target_amount, current_amount, deadline, priority FROM saving_goals ORDER BY priority"
    )
    for r in rows:
        r["progress_percent"] = (
            round(r["current_amount"] / r["target_amount"] * 100, 1) if r["target_amount"] else 0
        )
        r["remaining"] = r["target_amount"] - r["current_amount"]
    return rows


def update_saving_goal(id: int, current_amount: float | None = None, delta: float | None = None) -> dict:
    goal = fetchone("SELECT * FROM saving_goals WHERE id = ?", (id,))
    if not goal:
        return {"error": f"Saving goal id={id} tidak ditemukan"}

    if current_amount is not None:
        new_amount = current_amount
    elif delta is not None:
        new_amount = goal["current_amount"] + delta
    else:
        return {"error": "Harus isi current_amount atau delta"}

    execute("UPDATE saving_goals SET current_amount = ? WHERE id = ?", (new_amount, id))
    return {
        "id": id,
        "name": goal["name"],
        "current_amount": new_amount,
        "target_amount": goal["target_amount"],
        "progress_percent": round(new_amount / goal["target_amount"] * 100, 1) if goal["target_amount"] else 0,
    }
