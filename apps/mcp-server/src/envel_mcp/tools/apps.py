from datetime import date
from pathlib import Path

from fastmcp import FastMCP
from envel_mcp.deps import get_user_db
from envel_mcp.tools.analytics import get_ready_to_assign
from envel_mcp.tools.envelopes import get_envelopes

_UI_FILE = Path(__file__).parent.parent / "ui" / "budget-allocator.html"

mcp = FastMCP("apps")


@mcp.resource(
    "ui://envel/budget-allocator",
    name="BudgetAllocatorUI",
    mime_type="text/html;profile=mcp-app",
)
def _budget_allocator_ui() -> str:
    return _UI_FILE.read_text(encoding="utf-8")


@mcp.tool(
    name="budget_allocator",
    meta={"ui": {"resourceUri": "ui://envel/budget-allocator"}},
)
async def _budget_allocator_mcp(period: str | None = None) -> dict:
    """
    Open Budget Allocator — interactive UI to view and assign budget to all envelopes.
    Shows Ready to Assign and all envelopes. Users can assign directly from the UI.
    period format YYYY-MM (defaults to current month).
    """
    p = period or date.today().strftime("%Y-%m")
    with get_user_db() as db:
        envelopes = get_envelopes(db, p)
        rta = get_ready_to_assign(db, p)
    return {
        "period": p,
        "ready_to_assign": rta["ready_to_assign"],
        "is_zero": rta["is_zero"],
        "is_overspent": rta["is_overspent"],
        "total_balance": rta["total_balance"],
        "groups": envelopes["groups"],
    }
