"""
Chat API routes — SSE streaming LangGraph agent responses.
"""

import json
import logging
from typing import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from envel_platform.agent import build_agent, get_mcp_token, update_memory
from envel_platform.auth import require_user

logger = logging.getLogger("envel_platform.chat")

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


async def _stream_agent(username: str, message: str) -> AsyncIterator[str]:
    """Stream SSE events from the LangGraph agent."""

    def sse(data: dict) -> str:
        return f"data: {json.dumps(data)}\n\n"

    try:
        token = await get_mcp_token(username)
    except Exception as e:
        logger.error("token_fetch_failed", extra={"username": username, "error": str(e)})
        yield sse({"type": "error", "content": "Failed to authenticate with MCP server."})
        yield sse({"type": "done"})
        return

    try:
        async with build_agent(username, token) as agent:
            config = {"configurable": {"thread_id": f"chat-{username}"}}
            input_state = {"messages": [{"role": "user", "content": message}]}

            final_messages = None

            async for event in agent.astream_events(input_state, config, version="v2"):
                event_type = event["event"]
                event_name = event.get("name", "")

                if event_type == "on_chat_model_stream":
                    chunk = event["data"].get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        content = chunk.content
                        if isinstance(content, str) and content:
                            yield sse({"type": "token", "content": content})
                        elif isinstance(content, list):
                            for part in content:
                                if isinstance(part, dict) and part.get("type") == "text":
                                    yield sse({"type": "token", "content": part["text"]})

                elif event_type == "on_tool_start":
                    tool_name = event_name or event.get("data", {}).get("name", "tool")
                    yield sse({"type": "tool_start", "name": tool_name})

                elif event_type == "on_tool_end":
                    tool_name = event_name or event.get("data", {}).get("name", "tool")
                    output = event.get("data", {}).get("output", "")
                    result_str = output if isinstance(output, str) else json.dumps(output)
                    yield sse({"type": "tool_end", "name": tool_name, "result": result_str[:2000]})

                elif event_type == "on_chain_end" and event_name == "LangGraph":
                    final_messages = event.get("data", {}).get("output", {}).get("messages", [])

            # Update user memory after conversation
            if final_messages:
                try:
                    await update_memory(username, final_messages)
                except Exception:
                    logger.exception("post_chat_memory_update_failed", extra={"username": username})

    except Exception as e:
        logger.exception("agent_stream_failed", extra={"username": username, "error": str(e)})
        yield sse({"type": "error", "content": f"Agent error: {str(e)}"})

    yield sse({"type": "done"})


@router.post("")
async def chat(body: ChatRequest, username: str = Depends(require_user)):
    if not body.message.strip():
        return {"error": "empty message"}

    return StreamingResponse(
        _stream_agent(username, body.message.strip()),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.delete("")
async def clear_history(username: str = Depends(require_user)):
    """Clear conversation history for the current user."""
    import aiosqlite
    from envel_platform.agent import CHECKPOINTS_DB

    thread_id = f"chat-{username}"
    try:
        async with aiosqlite.connect(CHECKPOINTS_DB) as db:
            await db.execute(
                "DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,)
            )
            await db.execute(
                "DELETE FROM checkpoint_writes WHERE thread_id = ?", (thread_id,)
            )
            await db.execute(
                "DELETE FROM checkpoint_blobs WHERE thread_id = ?", (thread_id,)
            )
            await db.commit()
        logger.info("chat_history_cleared", extra={"username": username})
    except Exception as e:
        logger.warning("chat_history_clear_failed", extra={"username": username, "error": str(e)})

    return {"ok": True}
