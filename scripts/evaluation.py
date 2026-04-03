#!/usr/bin/env python3
"""
MCP Server Evaluation Script
Usage:
    # HTTP transport (server must be running first):
    python scripts/evaluation.py -t http -u http://localhost:8000/mcp \
        -H "Authorization: Bearer eval-token-secret-123" evaluation.xml

    # stdio transport (script launches server automatically):
    python scripts/evaluation.py -t stdio -c python -a server.py \
        -e TEST_TOKEN=eval-token-secret-123 evaluation.xml
"""

import argparse
import asyncio
import json
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """Kamu adalah asisten keuangan yang membantu menjawab pertanyaan menggunakan tools MCP yang tersedia.
Gunakan tools untuk mencari dan menganalisis data keuangan, lalu jawab pertanyaan dengan TEPAT sesuai format yang diminta.
Jawab HANYA dengan nilai yang diminta, tanpa penjelasan tambahan."""


def parse_eval_file(path: str) -> list[dict]:
    tree = ET.parse(path)
    root = tree.getroot()
    pairs = []
    for qa in root.findall("qa_pair"):
        q = qa.findtext("question", "").strip()
        a = qa.findtext("answer", "").strip()
        if q and a:
            pairs.append({"question": q, "answer": a})
    return pairs


async def get_mcp_tools(session: ClientSession) -> list[dict]:
    result = await session.list_tools()
    tools = []
    for tool in result.tools:
        tools.append({
            "name": tool.name,
            "description": tool.description or "",
            "input_schema": tool.inputSchema,
        })
    return tools


async def call_mcp_tool(session: ClientSession, name: str, args: dict) -> str:
    result = await session.call_tool(name, args)
    parts = []
    for content in result.content:
        if hasattr(content, "text"):
            parts.append(content.text)
    return "\n".join(parts)


async def run_agent(client: anthropic.Anthropic, session: ClientSession, question: str) -> tuple[str, int, list]:
    tools = await get_mcp_tools(session)
    anthropic_tools = [
        {
            "name": t["name"],
            "description": t["description"],
            "input_schema": t["input_schema"],
        }
        for t in tools
    ]

    messages = [{"role": "user", "content": question}]
    tool_calls_log = []
    total_tool_calls = 0

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=anthropic_tools,
            messages=messages,
        )

        # Collect assistant message
        assistant_content = []
        final_text = ""

        for block in response.content:
            if block.type == "text":
                final_text = block.text
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })

        messages.append({"role": "assistant", "content": assistant_content})

        if response.stop_reason == "end_turn":
            break

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    total_tool_calls += 1
                    tool_calls_log.append(f"{block.name}({json.dumps(block.input, ensure_ascii=False)[:80]})")
                    result_text = await call_mcp_tool(session, block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_text,
                    })
            messages.append({"role": "user", "content": tool_results})
        else:
            break

    return final_text.strip(), total_tool_calls, tool_calls_log


async def evaluate_http(url: str, headers: dict, pairs: list[dict], client: anthropic.Anthropic) -> list[dict]:
    results = []
    async with streamablehttp_client(url, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            for i, pair in enumerate(pairs, 1):
                print(f"  [{i}/{len(pairs)}] {pair['question'][:70]}...")
                start = time.time()
                try:
                    answer, n_tools, tool_log = await run_agent(client, session, pair["question"])
                    elapsed = time.time() - start
                    correct = answer.strip().lower() == pair["answer"].strip().lower()
                    results.append({
                        "question": pair["question"],
                        "expected": pair["answer"],
                        "actual": answer,
                        "correct": correct,
                        "tool_calls": n_tools,
                        "tool_log": tool_log,
                        "elapsed": elapsed,
                    })
                    status = "PASS" if correct else "FAIL"
                    print(f"         [{status}] expected={pair['answer']!r}  got={answer!r}  ({n_tools} tool calls, {elapsed:.1f}s)")
                except Exception as e:
                    elapsed = time.time() - start
                    results.append({
                        "question": pair["question"],
                        "expected": pair["answer"],
                        "actual": f"ERROR: {e}",
                        "correct": False,
                        "tool_calls": 0,
                        "tool_log": [],
                        "elapsed": elapsed,
                    })
                    print(f"         [ERROR] {e}")
    return results


async def evaluate_stdio(command: str, args: list[str], env: dict, pairs: list[dict], client: anthropic.Anthropic) -> list[dict]:
    results = []
    server_params = StdioServerParameters(command=command, args=args, env=env)
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            for i, pair in enumerate(pairs, 1):
                print(f"  [{i}/{len(pairs)}] {pair['question'][:70]}...")
                start = time.time()
                try:
                    answer, n_tools, tool_log = await run_agent(client, session, pair["question"])
                    elapsed = time.time() - start
                    correct = answer.strip().lower() == pair["answer"].strip().lower()
                    results.append({
                        "question": pair["question"],
                        "expected": pair["answer"],
                        "actual": answer,
                        "correct": correct,
                        "tool_calls": n_tools,
                        "tool_log": tool_log,
                        "elapsed": elapsed,
                    })
                    status = "PASS" if correct else "FAIL"
                    print(f"         [{status}] expected={pair['answer']!r}  got={answer!r}  ({n_tools} tool calls, {elapsed:.1f}s)")
                except Exception as e:
                    elapsed = time.time() - start
                    results.append({
                        "question": pair["question"],
                        "expected": pair["answer"],
                        "actual": f"ERROR: {e}",
                        "correct": False,
                        "tool_calls": 0,
                        "tool_log": [],
                        "elapsed": elapsed,
                    })
                    print(f"         [ERROR] {e}")
    return results


def print_report(results: list[dict], output: str | None = None):
    correct = sum(1 for r in results if r["correct"])
    total = len(results)
    accuracy = correct / total * 100 if total else 0
    avg_tools = sum(r["tool_calls"] for r in results) / total if total else 0
    avg_elapsed = sum(r["elapsed"] for r in results) / total if total else 0

    lines = [
        "",
        "=" * 70,
        "EVALUATION REPORT",
        "=" * 70,
        f"Accuracy   : {correct}/{total} ({accuracy:.0f}%)",
        f"Avg tools  : {avg_tools:.1f} calls/question",
        f"Avg time   : {avg_elapsed:.1f}s/question",
        "=" * 70,
        "",
    ]

    for i, r in enumerate(results, 1):
        status = "[PASS]" if r["correct"] else "[FAIL]"
        lines += [
            f"Q{i}: {r['question']}",
            f"     Expected : {r['expected']}",
            f"     Got      : {r['actual']}",
            f"     Status   : {status}  ({r['tool_calls']} tool calls, {r['elapsed']:.1f}s)",
        ]
        if r["tool_log"]:
            lines.append(f"     Tools    : {' → '.join(r['tool_log'][:5])}" + (" ..." if len(r["tool_log"]) > 5 else ""))
        lines.append("")

    report = "\n".join(lines)
    print(report)

    if output:
        Path(output).write_text(report, encoding="utf-8")
        print(f"Report saved to: {output}")


async def main():
    parser = argparse.ArgumentParser(description="MCP Server Evaluation")
    parser.add_argument("eval_file", help="Path to evaluation XML file")
    parser.add_argument("-t", "--transport", choices=["stdio", "http", "sse"], default="http")
    parser.add_argument("-m", "--model", default=MODEL)
    parser.add_argument("-o", "--output", help="Save report to file")
    # stdio options
    parser.add_argument("-c", "--command", help="Command to run MCP server (stdio)")
    parser.add_argument("-a", "--args", nargs="+", help="Args for command (stdio)")
    parser.add_argument("-e", "--env", nargs="+", help="ENV vars as KEY=VALUE (stdio)")
    # http/sse options
    parser.add_argument("-u", "--url", help="MCP server URL (http/sse)")
    parser.add_argument("-H", "--header", nargs="+", help="HTTP headers as 'Key: Value'")

    args = parser.parse_args()

    pairs = parse_eval_file(args.eval_file)
    print(f"Loaded {len(pairs)} questions from {args.eval_file}")

    client = anthropic.Anthropic()

    print(f"\nRunning evaluation ({args.transport} transport)...\n")

    if args.transport in ("http", "sse"):
        if not args.url:
            parser.error("-u/--url required for http/sse transport")
        headers = {}
        for h in (args.header or []):
            k, _, v = h.partition(": ")
            if k:
                headers[k] = v
        results = await evaluate_http(args.url, headers, pairs, client)
    else:
        if not args.command:
            parser.error("-c/--command required for stdio transport")
        env = {}
        for e in (args.env or []):
            k, _, v = e.partition("=")
            if k:
                env[k] = v
        results = await evaluate_stdio(
            args.command,
            args.args or [],
            env,
            pairs,
            client,
        )

    print_report(results, args.output)


if __name__ == "__main__":
    asyncio.run(main())
