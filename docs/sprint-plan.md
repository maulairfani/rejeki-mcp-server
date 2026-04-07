# Sprint Plan: Finance MCP — MVP Launch

**Period**: April 4 – April 30, 2026
**Team**: Solo (+ Claude)
**Sprint length**: 2 days (including weekends)
**Target**: Launch to friends May 1, 2026

---

## Current State

### Done

- MCP server — all tools (accounts, transactions, envelopes, scheduled, analytics, wishlist, prompts)
- Auth server — OAuth 2.1
- Platform — FastAPI + session auth + basic dashboard (Jinja2, to be replaced with React)
- Transaction date column changed to datetime

### To Build (MVP)

- Codebase: English-only migration (all prompts, schema defaults, templates)
- Auth: Replace users.json with SQLite
- Infra: Structured logging
- Platform backend: Refactor to REST API only (remove Jinja2 templates)
- Platform frontend: New React app (Vite + React + TypeScript, Shadcn/ui + Tailwind, Recharts)
- Platform pages: Dashboard, Budget, Transactions, Chat, Settings
- Security: SQLite encryption at rest
- MCP: user_context resource + daily briefing prompt
- Docs site (docs.domain.com)
- Marketing site (domain.com)
- User management
- Integration testing & deploy

### Exploration Backlog (Post-MVP)

- **Push notifications via ntfy.sh (self-hosted)** — scheduled transaction reminders + morning summary; self-host ntfy on VPS, per-user topics, Android via F-Droid (no Firebase), iOS via ntfy.sh upstream relay
- MCP prompt for instructing clients to create skills
- Platform UI/UX deep design exploration
- Subscription/monetization
- MCP Apps

---

## Sprint Overview

| Sprint | Dates | Goal |
| ------ | --------- | ---------------------------------------------------- |
| S1     | Apr 4–5   | English-only migration + schema cleanup              |
| S2     | Apr 6–7   | Auth rework (users.json → SQLite) + logging          |
| S3     | Apr 8–9   | SQLite encryption + security                         |
| S4     | Apr 10–11 | React app scaffold + platform backend API            |
| S5     | Apr 12–13 | Dashboard page                                       |
| S6     | Apr 14–15 | Budget page                                          |
| S7     | Apr 16–17 | Transactions page                                    |
| S8     | Apr 18–19 | Chat page (MCP client in platform)                   |
| S9     | Apr 20–21 | Settings page + MCP enhancements                     |
| S10    | Apr 22–23 | Docs site                                            |
| S11    | Apr 24–25 | Marketing site                                       |
| S12    | Apr 26–27 | Integration testing + bug fixes                      |
| S13    | Apr 28–29 | Deploy + launch prep                                 |
| 🚀    | Apr 30    | **LAUNCH**                                           |

---

## Sprint Details

### Sprint 1 — Apr 4–5

**Goal**: Entire codebase in English, schema cleaned up

| Priority | Item |
| -------- | ---- |
| P0 | Migrate all prompts (prompts/budget.py, prompts/onboarding.py) to English |
| P0 | Migrate schema.sql default data to English (envelope groups, envelope names) |
| P0 | Update MCP tool descriptions and error messages to English |
| P1 | Review all Python docstrings and comments — convert to English |

---

### Sprint 2 — Apr 6–7

**Goal**: Auth on proper database, structured logging in place

| Priority | Item |
| -------- | ---- |
| P0 | Replace users.json with SQLite users table in auth server (username, hashed_password, db_path) |
| P0 | Update add_user.py to work with new SQLite-based users |
| P0 | Setup structured logging (structlog or Python logging + JSON formatter) |
| P0 | Log all MCP tool calls, auth events, and errors |
| P1 | Update CLAUDE.md and README to reflect auth changes |

---

### Sprint 3 — Apr 8–9

**Goal**: User data secure before onboarding anyone

| Priority | Item |
| -------- | ---- |
| P0 | SQLite encryption at rest (SQLCipher or pycryptodome) |
| P0 | Review session security in platform |
| P1 | HTTPS enforcement check |
| P1 | Test auth flow end-to-end (OAuth → MCP → platform) |

---

### Sprint 4 — Apr 10–11

**Goal**: React app running, FastAPI serving as REST API

| Priority | Item |
| -------- | ---- |
| P0 | Scaffold apps/platform-ui/ — Vite + React + TypeScript + Shadcn/ui + Tailwind |
| P0 | Refactor apps/platform/ to REST API only (remove Jinja2 templates, expose JSON endpoints) |
| P0 | API endpoints: auth (login/logout/session), dashboard data, accounts, envelopes, transactions |
| P0 | Setup CORS, proxy config between React dev server and FastAPI |
| P1 | App shell: sidebar navigation, routing for 5 pages, auth guard |

---

### Sprint 5 — Apr 12–13

**Goal**: Dashboard page complete — all analytics on one page

| Priority | Item |
| -------- | ---- |
| P0 | This month's condition: total income vs expenses, Ready to Assign, budget progress per envelope (progress bars), overspent alerts |
| P0 | Spending breakdown: spending by category (donut chart), top spending categories, largest recent transactions |
| P1 | Comparison: month-over-month per envelope, spending trend line chart |
| P1 | Budget insight: envelopes consistently underfunded vs surplus, carryover summary |
| P1 | Age of Money: FIFO calculation from transaction data, display as "Your money is X days old" |

---

### Sprint 6 — Apr 14–15

**Goal**: Budget page — full envelope management

| Priority | Item |
| -------- | ---- |
| P0 | Display all envelope groups and envelopes with assigned / activity / available |
| P0 | Assign money to envelopes (inline edit) |
| P0 | Target tracking with 4 types: monthly_spending, monthly_savings, savings_balance, needed_by_date |
| P1 | Scheduled transactions list (upcoming / recurring) |
| P1 | Wishlist section (if time allows) |

---

### Sprint 7 — Apr 16–17

**Goal**: Transactions page — full history with filtering

| Priority | Item |
| -------- | ---- |
| P0 | Transaction list with date, payee, amount, envelope, account |
| P0 | Filter by date range, category/envelope, account |
| P0 | Search by payee or memo |
| P0 | Accounts overview section (list accounts, balances) |
| P1 | Add/edit transaction form (manual entry from platform) |

---

### Sprint 8 — Apr 18–19

**Goal**: Chat page — built-in MCP client working

| Priority | Item |
| -------- | ---- |
| P0 | Chat UI (input field, message bubbles, auto-scroll) |
| P0 | Backend: proxy messages to MCP server with user auth |
| P0 | Trigger onboarding prompt for new users |
| P1 | Display tool calls and responses readably |
| P1 | Loading states, error handling, chat history per session |

---

### Sprint 9 — Apr 20–21

**Goal**: Settings page done, MCP server enhanced

| Priority | Item |
| -------- | ---- |
| P0 | Settings page: user profile, change password |
| P0 | MCP connection guide in Settings (step-by-step per client: Claude.ai, Cursor) |
| P0 | `user_context` MCP resource — accounts, envelopes, groups summary. Cached by clients |
| P0 | Daily briefing MCP prompt — balance, remaining budget, scheduled transactions, recommendations |
| P1 | Improve onboarding prompt |

---

### Sprint 10 — Apr 22–23

**Goal**: Users can self-serve setup without developer help

| Priority | Item |
| -------- | ---- |
| P0 | Docs site setup (docs.domain.com) — Mintlify, Docusaurus, or static site |
| P0 | Tutorial: how to connect to Claude.ai |
| P0 | Tutorial: how to connect to Cursor |
| P0 | Envelope budgeting methodology explanation |
| P1 | FAQ page |

---

### Sprint 11 — Apr 24–25

**Goal**: Shareable landing page for friends

| Priority | Item |
| -------- | ---- |
| P0 | Marketing site setup (domain.com) |
| P0 | Hero section — clear value proposition |
| P0 | Feature highlights (AI-first, envelope budgeting, all MCP clients) |
| P0 | CTA sign up (manual for now — form or WA link) |
| P1 | Mobile-friendly layout |

---

### Sprint 12 — Apr 26–27

**Goal**: All flows work end-to-end, bugs fixed

| Priority | Item |
| -------- | ---- |
| P0 | Test full user journey: marketing site → signup → platform → connect MCP → onboarding → dashboard |
| P0 | Test on multiple MCP clients (minimum: Claude.ai + one other) |
| P0 | Fix all P0 bugs found |
| P1 | Performance check — dashboard load time, MCP response time |
| P1 | Test on mobile browser |

---

### Sprint 13 — Apr 28–29

**Goal**: Everything live, ready for friends on May 1

| Priority | Item |
| -------- | ---- |
| P0 | Deploy all services to VPS (MCP server, auth server, platform backend, platform frontend) |
| P0 | Setup domains + SSL (marketing, platform, docs) |
| P0 | Nginx config for all subdomains |
| P0 | Smoke test all endpoints on production |
| P0 | Create user accounts for friends |
| P0 | Test login and onboarding as new user on production |
| P0 | Write onboarding instructions to send to friends |
| P1 | Finalize product name (if not decided yet) |
| P1 | Screenshots / screen recordings for setup help |

---

## April 30 — Launch

- Send invitations to first group of friends
- Monitor logs and respond to feedback
- Collect all feedback for next cycle of sprints

---

## Risks & Mitigation

| Risk | Probability | Mitigation |
| ---- | ----------- | ---------- |
| React app scaffold + 5 pages in 6 sprints is tight | Medium | Shadcn/ui provides pre-built components; Claude accelerates development; cut P1 items first |
| SQLite encryption more complex than expected | Medium | Sprint 3 fully allocated; if too heavy, consider filesystem-level encryption first |
| Chat page (MCP client in browser) is technically complex | Medium | Sprint 8 fully dedicated; if blocked, users fall back to external MCP clients |
| English migration breaks existing features | Low | Run full smoke test after Sprint 1 |
| Major bug found during integration testing | Low | Sprint 12 dedicated to testing + fixes |

---

## Known Blockers

- **Product name**: Must be finalized before Sprint 10 (docs site) and Sprint 11 (marketing site)
- **SQLite encryption**: Must be complete (Sprint 3) before onboarding any users
- **Domain setup**: Need domain purchased and DNS configured before Sprint 13 deployment

---

## Design Decisions Log

1. **Transaction datetime**: Schema default changed from `date('now')` to `datetime('now')` for granular tracking. Enables future Age of Money calculation.
2. **Savings rate formula**: `(total income - total expenses) / total income`. Transfers are NOT expenses.
3. **Target tracking**: 4 types — `monthly_spending`, `monthly_savings`, `savings_balance`, `needed_by_date`. All in MVP.
4. **AI memory optimization**: `user_context` MCP resource (not tool) so clients cache data and avoid redundant list calls.
5. **Daily briefing**: Pull-based MCP prompt for MVP. Push-based in Phase 2.
6. **Platform stack**: Vite + React + TypeScript (frontend) + FastAPI REST API (backend). Shadcn/ui + Tailwind for UI, Recharts for charts.
7. **Platform pages**: 5 pages — Dashboard, Budget, Transactions, Chat, Settings. Wishlist folded into Budget or deferred.
8. **No Docker for MVP**: systemd + nginx is sufficient. Docker when team grows or multi-server needed.
