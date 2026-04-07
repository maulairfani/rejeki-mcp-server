from fastmcp import FastMCP

mcp = FastMCP()


@mcp.prompt()
def onboarding_guide() -> str:
    """Setup wizard: accounts → envelopes → budget allocation."""
    return (
        "Help the user set up their personal finance system from scratch:\n\n"
        "1. Read finance://onboarding-status to see current progress.\n"
        "2. If no accounts exist: add them with finance_add_account (type: bank | ewallet | cash).\n"
        "3. Create envelope groups with finance_add_group (e.g., Needs, Wants, Savings).\n"
        "4. Create envelopes for each category with finance_add_envelope (type: income | expense).\n"
        "5. Set targets with finance_set_target for envelopes that have monthly or goal targets.\n"
        "6. Assign budget to each envelope with finance_assign_to_envelope until RTA = 0.\n\n"
        "Ask the user which step they want to start from, or continue with the next incomplete step."
    )
