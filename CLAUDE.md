# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Finance MCP** is an AI-powered envelope budgeting MCP (Model Context Protocol) server designed to integrate with any MCP client (Claude, Cursor, etc.). It implements envelope budgeting methodology where every rupiah (IDR) is assigned to a specific category.

This is a monorepo with three apps:

- `apps/mcp-server/` — FastMCP server exposing financial tools and prompts (port 8001)
- `apps/auth-server/` — OAuth 2.1 authentication server (port 9004)
- `apps/platform/server/` — FastAPI REST API backend for the platform (port 8002)
- `apps/platform/web/` — React + TypeScript frontend (Vite, Shadcn/ui, Tailwind)

All three apps communicate only via HTTP (token introspection), not via shared Python imports.

## Commands

### Install

```bash
pip install -e apps/mcp-server
pip install -e apps/auth-server
pip install -e apps/platform/server
```

### Run

```bash
# MCP server
envel

# Auth server
envel-auth

# Platform dashboard
envel-platform
```

### Minimal `.env` for local testing

```env
TEST_TOKEN=any-token-value
TEST_DB=./users/test.db
```

With these set, `TestTokenVerifier` activates — no auth server needed.

### Production (VPS)

```bash
systemctl start envel-auth envel-mcp
journalctl -u envel-mcp -f
```

## Architecture

### Request Flow

```text
MCP client → Nginx → /envel/mcp/  → MCP Server  (port 8001)
                   → /envel/auth/ → Auth Server (port 9004)
Browser    → Nginx → /              → Platform    (port 8002)
```

### Per-User Database Isolation

Each user has their own SQLite database. The path is stored in `users.db` (a shared SQLite database with hashed credentials) and injected via a `ContextVar` (`_db_path` in `apps/mcp-server/src/envel_mcp/deps.py`) when a token is verified. All tools access the database through `get_user_db()` context manager in `deps.py`, which also auto-initializes schema from `schema.sql` on first access.

### User Authentication

Users are stored in `users.db` (SQLite, gitignored) with bcrypt-hashed passwords. The `USERS_DB` env var must point to this file. Use `scripts/add_user.py` to manage users:

```bash
python scripts/add_user.py <username> <password> [--db-path PATH]
```

### Token Verification

`apps/mcp-server/src/envel_mcp/server.py` defines two verifiers:

- **`EnvelTokenVerifier`** — production; calls `INTROSPECT_URL` on the auth server to resolve token → DB path
- **`TestTokenVerifier`** — development; accepts `TEST_TOKEN` env var and uses `TEST_DB` path

### Tool Organization

Tools are implemented as FastMCP sub-servers in `apps/mcp-server/src/envel_mcp/tools/` and mounted under a "finance" namespace in the main server. Prompts are in `apps/mcp-server/src/envel_mcp/prompts/`.

All MCP tool wrappers use FastMCP `Context` for logging (`ctx.info()`, `ctx.error()`), which sends log notifications to the MCP client.

| Module | Responsibility |
| ------ | -------------- |
| `tools/accounts.py` | Bank accounts, e-wallets, cash |
| `tools/transactions.py` | Income/expense/transfer records |
| `tools/envelopes.py` | Envelope categories and groups |
| `tools/scheduled.py` | Recurring/scheduled transactions |
| `tools/analytics.py` | Summaries, ready-to-assign, age of money, onboarding status |
| `tools/wishlist.py` | Personal shopping list |
| `tools/apps.py` | Budget Allocator interactive UI (HTML resource) |
| `prompts/budget.py` | Budget review and monthly planning prompts |
| `prompts/onboarding.py` | First-time setup guidance |

### Envelope Target Types

4 target types for expense envelopes:

- `monthly_spending` — spend up to X per month
- `monthly_savings` — assign X every month (accumulates)
- `savings_balance` — save up to X total
- `needed_by_date` — need X by a specific date

### Database Schema

8 tables in `apps/mcp-server/src/envel_mcp/schema.sql`: `accounts`, `envelope_groups`, `envelopes`, `budget_periods`, `transactions`, `scheduled_transactions`, `wishlist`. Budget allocation is tracked per-envelope per-month in `budget_periods` with `assigned` and `carryover` columns.

### Logging

- **MCP server**: FastMCP Context logging (`ctx.info()`) — sent to MCP client as notifications. Server-side logging via stdlib `logging` in token verifier.
- **Auth server**: JSON structured logging via `python-json-logger`. Logs login attempts, token issuance/revocation, introspection.
- **Platform backend**: JSON structured logging via `python-json-logger`. Logs login attempts.
- **Platform frontend**: Vite dev server (`npm run dev` in `apps/platform/web/`). Proxies `/api` to port 8002. Build with `npm run build`.

## Key Design Decisions

- **`users.db`** (gitignored) stores usernames, bcrypt-hashed passwords, and db_path. `USERS_DB` env var must be set explicitly.
- **`*.db` files** are gitignored. Each user's financial data lives in their own SQLite file.
- The `apps/mcp-server/server.py` is a thin re-export shim for deployment entrypoints; real logic is in `src/envel_mcp/server.py`.
- There are no tests or linting configs in this project currently.
