from datetime import datetime

from fastmcp import FastMCP

mcp = FastMCP()


@mcp.prompt()
def budget_review(period: str | None = None) -> str:
    """Monthly budget review: analyze overspending and suggest rebalancing."""
    p = period or datetime.now().strftime("%Y-%m")
    return (
        f"Perform a budget review for {p}:\n\n"
        f"1. Call finance_get_summary(period='{p}') for an income, expense, and net summary.\n"
        f"2. Call finance_get_envelopes(period='{p}') for details on each envelope "
        f"(carryover, assigned, activity, available).\n"
        f"3. Identify envelopes that are overspent (negative available).\n"
        f"4. Provide a summary: which envelopes are on track, which need attention.\n"
        f"5. Check finance_get_ready_to_assign(period='{p}') — if there is remaining RTA, "
        f"suggest allocating it to envelopes that are underfunded."
    )


@mcp.prompt()
def monthly_planning(period: str | None = None) -> str:
    """Monthly budget planning guide: check RTA, review targets, assign until RTA = 0."""
    p = period or datetime.now().strftime("%Y-%m")
    return (
        f"Help plan the budget for {p}:\n\n"
        f"1. Call finance_get_ready_to_assign(period='{p}') — see how much money is unallocated.\n"
        f"2. Call finance_get_envelopes(period='{p}') — review each envelope's target and current available.\n"
        f"3. Prioritize envelopes with 'monthly_spending' or 'monthly_savings' targets that are not yet met.\n"
        f"4. For 'savings_balance' and 'needed_by_date' envelopes, check if they are on track toward their deadline.\n"
        f"5. Distribute RTA to the envelopes that need it most until RTA = 0.\n"
        f"Use finance_assign_to_envelope for each allocation. Ask the user if they have specific priorities."
    )
