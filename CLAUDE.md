# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Rejeki** is an AI-powered envelope budgeting MCP (Model Context Protocol) server designed to integrate with claude.ai. It implements envelope budgeting methodology where every rupiah (IDR) is assigned to a specific category.

This is a monorepo with three apps:

- `apps/mcp-server/` — FastMCP server exposing financial tools and prompts to Claude (port 8001)
- `apps/auth-server/` — OAuth 2.1 authentication server (port 9004)
- `apps/platform/` — Future financial dashboard (placeholder)

Both services communicate only via HTTP (token introspection), not via shared Python imports.

## Commands

### Install

```bash
pip install -e apps/mcp-server
pip install -e apps/auth-server
```

### Run

```bash
# MCP server
cd apps/mcp-server && python -m rejeki_mcp.server
# or via entry point (after install):
rejeki

# Auth server
cd apps/auth-server && python -m rejeki_auth.server
# or via entry point (after install):
rejeki-auth
```

### Minimal `.env` for local testing

```env
TEST_TOKEN=any-token-value
TEST_DB=./users/test.db
```

With these set, `TestTokenVerifier` activates — no auth server needed.

### Production (VPS)

```bash
systemctl start rejeki-auth rejeki-mcp
journalctl -u rejeki-mcp -f
```

## Architecture

### Request Flow

```text
claude.ai → Nginx → /rejeki/mcp/  → MCP Server  (port 8001)
                  → /rejeki/auth/ → Auth Server (port 9004)
```

### Per-User Database Isolation

Each user has their own SQLite database. The path is stored in `users.json` and injected via a `ContextVar` (`_db_path` in `apps/mcp-server/src/rejeki_mcp/deps.py`) when a token is verified. All tools access the database through `get_user_db()` context manager in `deps.py`, which also auto-initializes schema from `schema.sql` on first access.

### Token Verification

`apps/mcp-server/src/rejeki_mcp/server.py` defines two verifiers:

- **`RejekiTokenVerifier`** — production; calls `INTROSPECT_URL` on the auth server to resolve token → DB path
- **`TestTokenVerifier`** — development; accepts `TEST_TOKEN` env var and uses `TEST_DB` path

### Tool Organization

Tools are implemented as FastMCP sub-servers in `apps/mcp-server/src/rejeki_mcp/tools/` and mounted under a "finance" namespace in the main server. Prompts are in `apps/mcp-server/src/rejeki_mcp/prompts/`.

| Module | Responsibility |
| ------ | -------------- |
| `tools/accounts.py` | Bank accounts, e-wallets, cash |
| `tools/transactions.py` | Income/expense/transfer records |
| `tools/envelopes.py` | Envelope categories and groups |
| `tools/scheduled.py` | Recurring/scheduled transactions |
| `tools/analytics.py` | Summaries, ready-to-assign, monthly comparison |
| `tools/wishlist.py` | Personal shopping list |
| `tools/apps.py` | Budget Allocator interactive UI (HTML resource) |
| `prompts/budget.py` | Budget review and monthly planning prompts |
| `prompts/onboarding.py` | First-time setup guidance |

### Database Schema

8 tables in `apps/mcp-server/src/rejeki_mcp/schema.sql`: `accounts`, `envelope_groups`, `envelopes`, `budget_periods`, `transactions`, `scheduled_transactions`, `wishlist`. Budget allocation is tracked per-envelope per-month in `budget_periods` with `assigned` and `carryover` columns.

## Key Design Decisions

- **`users.json`** (gitignored) maps usernames to `{password, db_path}`. `USERS_CONFIG` env var must be set explicitly — there is no fallback default.
- **`*.db` files** are gitignored. Each user's financial data lives in their own SQLite file.
- The `apps/mcp-server/server.py` is a thin re-export shim for deployment entrypoints; real logic is in `src/rejeki_mcp/server.py`.
- There are no tests or linting configs in this project currently.
