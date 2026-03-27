from rejeki.database import execute, fetchall


def add_account(name: str, type: str, initial_balance: float = 0) -> dict:
    id = execute(
        "INSERT INTO accounts (name, type, balance) VALUES (?, ?, ?)",
        (name, type, initial_balance),
    )
    return {"id": id, "name": name, "type": type, "balance": initial_balance}


def get_accounts() -> list[dict]:
    rows = fetchall("SELECT id, name, type, balance FROM accounts ORDER BY name")
    total = sum(r["balance"] for r in rows)
    return {"accounts": rows, "total_balance": total}
