"""Tags let users mark events that span multiple envelopes (e.g. "konser",
"liburan-bali") so spending can later be analyzed by event."""

from envel_mcp.database import Database


def _normalize_tags(raw_tags: list[str]) -> list[str]:
    """Strip + dedupe case-insensitively, preserving the first-seen casing."""
    seen: dict[str, str] = {}
    for raw in raw_tags:
        name = (raw or "").strip()
        if not name:
            continue
        key = name.lower()
        if key not in seen:
            seen[key] = name
    return list(seen.values())


def _ensure_tag_ids(db: Database, names: list[str]) -> dict[str, int]:
    """Resolve tag names to ids, creating any that don't yet exist."""
    out: dict[str, int] = {}
    for name in names:
        existing = db.fetchone(
            "SELECT id FROM tags WHERE name = ? COLLATE NOCASE", (name,)
        )
        if existing:
            out[name.lower()] = existing["id"]
        else:
            tag_id = db.execute("INSERT INTO tags (name) VALUES (?)", (name,))
            out[name.lower()] = tag_id
    return out


def _get_transaction_tags(db: Database, transaction_id: int) -> list[str]:
    rows = db.fetchall(
        """
        SELECT tg.name FROM transaction_tags tt
        JOIN tags tg ON tg.id = tt.tag_id
        WHERE tt.transaction_id = ?
        ORDER BY tg.name COLLATE NOCASE
        """,
        (transaction_id,),
    )
    return [r["name"] for r in rows]


def list_tags(db: Database) -> dict:
    """Return all tags with usage counts, most-used first."""
    rows = db.fetchall(
        """
        SELECT tg.id, tg.name, COALESCE(c.usage, 0) AS usage
        FROM tags tg
        LEFT JOIN (
            SELECT tag_id, COUNT(*) AS usage
            FROM transaction_tags
            GROUP BY tag_id
        ) c ON c.tag_id = tg.id
        ORDER BY usage DESC, tg.name COLLATE NOCASE ASC
        """
    )
    return {"tags": rows, "total": len(rows)}


def tag_transactions(db: Database, transaction_ids: list[int], tags: list[str]) -> dict:
    """Attach tags to one or more transactions. Additive — keeps existing tags."""
    names = _normalize_tags(tags)
    if not names:
        raise ValueError("At least one tag name is required")
    if not transaction_ids:
        raise ValueError("At least one transaction_id is required")

    missing = [
        tid for tid in transaction_ids
        if not db.fetchone("SELECT 1 FROM transactions WHERE id = ?", (tid,))
    ]
    if missing:
        raise ValueError(f"Transactions not found: {missing}")

    tag_ids = _ensure_tag_ids(db, names)

    inserted = 0
    for tid in transaction_ids:
        for name, tag_id in tag_ids.items():
            existing = db.fetchone(
                "SELECT 1 FROM transaction_tags WHERE transaction_id = ? AND tag_id = ?",
                (tid, tag_id),
            )
            if not existing:
                db.execute(
                    "INSERT INTO transaction_tags (transaction_id, tag_id) VALUES (?, ?)",
                    (tid, tag_id),
                )
                inserted += 1

    return {
        "tagged": [
            {"id": tid, "tags": _get_transaction_tags(db, tid)}
            for tid in transaction_ids
        ],
        "links_added": inserted,
    }


def untag_transactions(db: Database, transaction_ids: list[int], tags: list[str]) -> dict:
    """Remove specific tags from one or more transactions. Tags themselves stay."""
    names = _normalize_tags(tags)
    if not names:
        raise ValueError("At least one tag name is required")
    if not transaction_ids:
        raise ValueError("At least one transaction_id is required")

    placeholders_t = ",".join("?" for _ in transaction_ids)
    placeholders_n = ",".join("?" for _ in names)
    sql = f"""
        DELETE FROM transaction_tags
        WHERE transaction_id IN ({placeholders_t})
          AND tag_id IN (
              SELECT id FROM tags WHERE name IN ({placeholders_n}) COLLATE NOCASE
          )
    """
    db.execute(sql, tuple(transaction_ids) + tuple(names))

    return {
        "untagged": [
            {"id": tid, "tags": _get_transaction_tags(db, tid)}
            for tid in transaction_ids
        ],
    }


def set_transaction_tags(db: Database, transaction_id: int, tags: list[str]) -> dict:
    """Replace the entire tag set for a single transaction."""
    if not db.fetchone("SELECT 1 FROM transactions WHERE id = ?", (transaction_id,)):
        raise ValueError(f"Transaction id={transaction_id} not found")

    names = _normalize_tags(tags)
    db.execute("DELETE FROM transaction_tags WHERE transaction_id = ?", (transaction_id,))
    if names:
        tag_ids = _ensure_tag_ids(db, names)
        for tag_id in tag_ids.values():
            db.execute(
                "INSERT INTO transaction_tags (transaction_id, tag_id) VALUES (?, ?)",
                (transaction_id, tag_id),
            )

    return {"id": transaction_id, "tags": _get_transaction_tags(db, transaction_id)}


def delete_tag(db: Database, name: str) -> dict:
    """Fully delete a tag. Removes it from every transaction it was on."""
    row = db.fetchone("SELECT id, name FROM tags WHERE name = ? COLLATE NOCASE", (name,))
    if not row:
        raise ValueError(f"Tag '{name}' not found")
    db.execute("DELETE FROM tags WHERE id = ?", (row["id"],))
    return {"deleted": row["name"]}


def tag_spend_summary(
    db: Database,
    tag: str | None = None,
    period: str | None = None,
) -> dict:
    """Spending totals grouped by tag.

    - period: optional YYYY-MM filter (date range based on transactions.date)
    - tag: optional single-tag filter; returns just that tag's transactions
    Only expense transactions are counted.
    """
    where = ["t.type = 'expense'"]
    params: list = []
    if period:
        where.append("strftime('%Y-%m', t.date) = ?")
        params.append(period)
    if tag:
        where.append("tg.name = ? COLLATE NOCASE")
        params.append(tag)

    where_clause = " AND ".join(where)

    rows = db.fetchall(
        f"""
        SELECT
            tg.name AS tag,
            COUNT(DISTINCT t.id) AS count,
            SUM(t.amount) AS total
        FROM transactions t
        JOIN transaction_tags tt ON tt.transaction_id = t.id
        JOIN tags tg ON tg.id = tt.tag_id
        WHERE {where_clause}
        GROUP BY tg.id
        ORDER BY total DESC
        """,
        tuple(params),
    )

    out: dict = {
        "period": period,
        "tag_filter": tag,
        "tags": rows,
        "grand_total": sum(r["total"] or 0 for r in rows),
    }

    if tag:
        # Include the actual transactions for context.
        txns = db.fetchall(
            f"""
            SELECT t.id, t.date, t.amount, t.payee, t.memo,
                   a.name AS account, e.name AS envelope
            FROM transactions t
            JOIN transaction_tags tt ON tt.transaction_id = t.id
            JOIN tags tg ON tg.id = tt.tag_id
            LEFT JOIN accounts a ON a.id = t.account_id
            LEFT JOIN envelopes e ON e.id = t.envelope_id
            WHERE {where_clause}
            ORDER BY t.date DESC, t.id DESC
            """,
            tuple(params),
        )
        out["transactions"] = txns

    return out


# ---------------------------------------------------------------------------
# FastMCP provider
# ---------------------------------------------------------------------------

from fastmcp import FastMCP
from fastmcp.server.context import Context
from fastmcp.server.dependencies import CurrentContext
from envel_mcp.deps import get_user_db

mcp = FastMCP("tags")


@mcp.tool(name="list_tags")
async def _list_tags_mcp(ctx: Context = CurrentContext()) -> dict:
    """List all tags with how many transactions each is attached to."""
    await ctx.info("list_tags")
    with get_user_db() as db:
        return list_tags(db)


@mcp.tool(name="tag_transactions")
async def _tag_transactions_mcp(
    transaction_ids: list[int],
    tags: list[str],
    ctx: Context = CurrentContext(),
) -> dict:
    """Attach one or more tags to one or more transactions. Additive — does not
    replace existing tags. Tag names are case-insensitive and auto-created if new."""
    await ctx.info(f"tag_transactions: ids={transaction_ids}, tags={tags}")
    with get_user_db() as db:
        return tag_transactions(db, transaction_ids, tags)


@mcp.tool(name="untag_transactions")
async def _untag_transactions_mcp(
    transaction_ids: list[int],
    tags: list[str],
    ctx: Context = CurrentContext(),
) -> dict:
    """Remove specific tags from one or more transactions. The tags themselves
    remain — use delete_tag to remove a tag entirely."""
    await ctx.info(f"untag_transactions: ids={transaction_ids}, tags={tags}")
    with get_user_db() as db:
        return untag_transactions(db, transaction_ids, tags)


@mcp.tool(name="set_transaction_tags")
async def _set_transaction_tags_mcp(
    transaction_id: int,
    tags: list[str],
    ctx: Context = CurrentContext(),
) -> dict:
    """Replace the entire tag set on a single transaction. Pass [] to clear all tags."""
    await ctx.info(f"set_transaction_tags: id={transaction_id}, tags={tags}")
    with get_user_db() as db:
        return set_transaction_tags(db, transaction_id, tags)


@mcp.tool(name="delete_tag")
async def _delete_tag_mcp(name: str, ctx: Context = CurrentContext()) -> dict:
    """Permanently delete a tag and detach it from every transaction."""
    await ctx.info(f"delete_tag: name={name}")
    with get_user_db() as db:
        return delete_tag(db, name)


@mcp.tool(name="tag_spend_summary")
async def _tag_spend_summary_mcp(
    tag: str | None = None,
    period: str | None = None,
    ctx: Context = CurrentContext(),
) -> dict:
    """Total expense spending grouped by tag.

    - tag: optional single-tag filter (returns just that tag's totals + the
      individual transactions on it)
    - period: optional YYYY-MM filter (e.g. "2026-04")

    Useful for answering "total habis buat tag konser bulan ini?" or
    "ringkasan semua tag tahun ini"."""
    await ctx.info(f"tag_spend_summary: tag={tag}, period={period}")
    with get_user_db() as db:
        return tag_spend_summary(db, tag=tag, period=period)
