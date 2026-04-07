"""
LangGraph agent for the Envel chat page — custom StateGraph build.

Graph structure:
  START → reason → act → tools → reason (loop)
                       ↘ END (no tool calls)

- `reason` node  : LLM reasons about the situation without calling tools.
                   Output stored in `thought` (state field), NOT added to messages.
- `act` node     : LLM with tools bound. Injects `thought` as context, then
                   either calls tools or produces the final answer.
- `tools` node   : Executes tool calls, appends ToolMessages to state.

This separation lets the model plan before acting, without cluttering the
chat history with internal reasoning.
"""

import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Annotated, Literal

import httpx
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openrouter import ChatOpenRouter
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

logger = logging.getLogger("envel_platform.agent")

# ─── CONFIG ──────────────────────────────────────────────────────────────────

MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8001/mcp")
AUTH_SERVER_URL = os.environ.get("AUTH_SERVER_URL", "http://localhost:9004")
PLATFORM_SERVICE_SECRET = os.environ.get("PLATFORM_SERVICE_SECRET", "")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "google/gemini-2.5-flash")
MEMORY_UPDATER_MODEL = os.environ.get("MEMORY_UPDATER_MODEL", "google/gemini-2.0-flash-lite")
CHECKPOINTS_DB = os.environ.get("CHECKPOINTS_DB", "./agent_checkpoints.sqlite")
TEST_TOKEN = os.environ.get("TEST_TOKEN", "")

# ─── STATE ───────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    thought: str  # internal reasoning — NOT added to messages, not shown to user

# ─── PROMPTS ─────────────────────────────────────────────────────────────────

_REASON_SYSTEM = """\
You are Envel, an AI personal finance assistant using envelope budgeting.
All amounts are in IDR (Rupiah). Format currency as "Rp X.XXX.XXX".

## Your memory about this user:
{memory}

---

Your task right now: READ the conversation carefully and THINK step by step.
- What is the user actually asking for?
- What information do you already have from prior messages or tool results?
- What tools (if any) do you need to call to answer fully?
- In what order should you call them?
- Are there any edge cases or clarifications needed?

Write your reasoning concisely. Do NOT call any tools. Do NOT answer the user yet.
Just think out loud."""

_ACT_SYSTEM = """\
You are Envel, an AI personal finance assistant using envelope budgeting.
All amounts are in IDR (Rupiah). Format currency as "Rp X.XXX.XXX".

When a user first contacts you with no prior context, call \
finance_get_onboarding_status first to check their setup.

## Your memory about this user:
{memory}

## Your reasoning about what to do next:
{thought}

---

Now ACT based on your reasoning above:
- If you need data: call the appropriate tool(s).
- If you have all the information needed: give the final answer directly.
Be concise and helpful."""

# ─── MEMORY ──────────────────────────────────────────────────────────────────

from pathlib import Path


def _memory_path(username: str) -> Path:
    path = Path(f"./users/{username}_memory.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_memory(username: str) -> str:
    path = _memory_path(username)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return "*(No memories yet — this is the user's first session.)*"


def save_memory(username: str, content: str) -> None:
    _memory_path(username).write_text(content, encoding="utf-8")


async def update_memory(username: str, messages: list[BaseMessage]) -> None:
    """Use a cheap LLM call to extract key facts and rewrite the memory file."""
    current_memory = load_memory(username)

    recent = []
    for m in messages[-10:]:
        role = getattr(m, "type", "unknown")
        content = m.content if isinstance(m.content, str) else json.dumps(m.content)
        if content:
            recent.append(f"{role}: {content[:500]}")

    if not recent:
        return

    prompt = (
        f"Current memory about the user:\n{current_memory}\n\n"
        f"Recent conversation:\n" + "\n".join(recent) + "\n\n"
        "Update the user memory in markdown format. Add new important facts "
        "(accounts, goals, preferences, recurring patterns). Remove outdated info. "
        "Keep it under 300 words. Return ONLY the updated markdown, starting with '# User Memory'."
    )

    try:
        updater = ChatOpenRouter(model=MEMORY_UPDATER_MODEL, temperature=0)
        response = await updater.ainvoke([{"role": "user", "content": prompt}])
        save_memory(username, response.content)
        logger.debug("memory_updated", extra={"username": username})
    except Exception:
        logger.exception("memory_update_failed", extra={"username": username})


# ─── TOKEN ───────────────────────────────────────────────────────────────────

async def get_mcp_token(username: str) -> str:
    if TEST_TOKEN:
        return TEST_TOKEN
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{AUTH_SERVER_URL}/service-token",
            json={"username": username, "service_secret": PLATFORM_SERVICE_SECRET},
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


# ─── GRAPH NODES ─────────────────────────────────────────────────────────────

def make_reason_node(llm: ChatOpenRouter, username: str):
    """Produces internal reasoning. Updates `thought` only — does NOT touch messages."""

    async def reason(state: AgentState) -> dict:
        memory = load_memory(username)
        system = SystemMessage(content=_REASON_SYSTEM.format(memory=memory))
        response = await llm.ainvoke([system] + list(state["messages"]))
        thought = response.content if isinstance(response.content, str) else ""
        logger.debug("reason_done", extra={"username": username, "thought_len": len(thought)})
        return {"thought": thought}

    return reason


def make_act_node(llm_with_tools: ChatOpenRouter, username: str):
    """Calls tools or produces final answer, informed by the thought from reason node."""

    async def act(state: AgentState) -> dict:
        memory = load_memory(username)
        thought = state.get("thought", "")
        system = SystemMessage(
            content=_ACT_SYSTEM.format(memory=memory, thought=thought or "(none)")
        )
        response = await llm_with_tools.ainvoke([system] + list(state["messages"]))
        return {"messages": [response]}

    return act


def route_after_act(state: AgentState) -> Literal["tools", "__end__"]:
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"
    return END


# ─── GRAPH BUILDER ───────────────────────────────────────────────────────────

def build_graph(llm: ChatOpenRouter, tools: list[BaseTool], username: str, checkpointer):
    llm_with_tools = llm.bind_tools(tools)

    builder = StateGraph(AgentState)

    builder.add_node("reason", make_reason_node(llm, username))
    builder.add_node("act", make_act_node(llm_with_tools, username))
    builder.add_node("tools", ToolNode(tools))

    builder.add_edge(START, "reason")
    builder.add_edge("reason", "act")
    builder.add_conditional_edges("act", route_after_act, {"tools": "tools", END: END})
    builder.add_edge("tools", "reason")  # re-reason after each tool call

    return builder.compile(checkpointer=checkpointer)


# ─── AGENT CONTEXT MANAGER ───────────────────────────────────────────────────

@asynccontextmanager
async def build_agent(username: str, token: str):
    """Async context manager that yields a compiled LangGraph graph."""
    async with MultiServerMCPClient(
        connections={
            "finance": {
                "transport": "http",
                "url": MCP_SERVER_URL,
                "headers": {"Authorization": f"Bearer {token}"},
            }
        }
    ) as mcp_client:
        tools = await mcp_client.get_tools()
        logger.info("mcp_tools_loaded", extra={"username": username, "tool_count": len(tools)})

        llm = ChatOpenRouter(model=OPENROUTER_MODEL, temperature=0)

        async with AsyncSqliteSaver.from_conn_string(CHECKPOINTS_DB) as checkpointer:
            graph = build_graph(llm, tools, username, checkpointer)
            yield graph
