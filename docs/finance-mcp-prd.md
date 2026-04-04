# Product Requirements Document: Finance MCP

**Version**: 1.1
**Date**: 2026-04-04
**Author**: Sarah (Product Owner)
**Quality Score**: 93/100
**Status**: Draft — product name TBD

---

## Executive Summary

Finance MCP is an AI-first personal finance platform designed to help young adults in Indonesia — especially fresh graduates and early career professionals — manage their finances using envelope budgeting. Users interact with their finances through natural conversation in any MCP client (Claude, Cursor, etc.), while the MCP server acts as the engine behind the scenes.

This product exists because many young people have clear financial goals — marriage, buying a house, building wealth — but fail to achieve them not because of insufficient income, but because they don't know how to manage money. Finance MCP becomes their smart financial companion, guiding them from zero.

Key differentiators from competitors like YNAB and Money Monarch: AI-first conversational approach, compatibility with all MCP clients (not locked to one AI), and the combination of MCP server + web platform for a complete experience.

---

## Problem Statement

**Current Situation**: Fresh graduates have financial goals (marriage, house, wealth building) but struggle to save consistently because they lack an effective financial management system. Existing finance apps are too rigid, require tedious manual input, or are too complex for beginners.

**Proposed Solution**: A personal finance platform that places AI as the primary interface. Users chat with their MCP client to record transactions, check budgets, or plan finances — while the web platform provides visual dashboards for the big picture.

**Business Impact**: Building healthy financial habits in a young adult segment that has been underserved by conventional financial products.

---

## Success Metrics

**Primary KPI:**

- At least 1 new user (besides the developer) using the product consistently for 1 full month

**Validation**: Monitored from platform usage data.

---

## User Personas

### Primary: Andi — Fresh Graduate (22-26 years old)

- **Role**: New employee / junior professional, first time earning their own income
- **Goals**: Save consistently, build emergency fund, start investing, save for big goals (marriage, house)
- **Pain Points**: Salary runs out before month-end without knowing where it went, doesn't know where to start managing finances, recording expenses feels boring and doesn't last
- **Technical Level**: Intermediate — comfortable with smartphones and modern apps, familiar with AI tools like Claude or Cursor

### Secondary: Budi — Early Career (26-30 years old)

- **Role**: Professional with 2-3 years of experience, starting to have bigger financial responsibilities
- **Goals**: Seriously building wealth, starting to invest, achieving financial clarity
- **Pain Points**: Has tried various finance apps but couldn't stay consistent, feels the need for a better "system"
- **Technical Level**: Advanced — power user, likely already using AI tools daily

---

## User Stories & Acceptance Criteria

### Story 1: Onboarding via MCP Client

**As a** fresh graduate using Finance MCP for the first time
**I want to** be guided by AI to set up my finances from scratch
**So that** I don't feel confused about where to start and can immediately use the system

**Acceptance Criteria:**
- [ ] After connecting MCP server, AI greets user and starts onboarding flow
- [ ] AI asks about user's financial goals (marriage, house, etc.)
- [ ] AI helps user add their bank accounts / e-wallets
- [ ] AI helps user record monthly income
- [ ] AI suggests and helps create envelope groups and envelopes based on user's needs
- [ ] AI helps user allocate budget to each envelope
- [ ] User successfully completes onboarding in one conversation session

### Story 2: Record Transactions via Chat

**As an** active Finance MCP user
**I want to** record expenses just by typing to my MCP client
**So that** recording feels natural and not boring

**Acceptance Criteria:**
- [ ] User can record transactions with natural language ("lunch 45k")
- [ ] AI confirms the recorded transaction (amount, category, envelope)
- [ ] Transaction is saved to database and immediately reflected on platform dashboard
- [ ] User can correct if AI categorization is wrong

### Story 3: Check Budget & Envelope Balance

**As a** user who wants to know their financial condition
**I want to** ask AI about remaining budget for a specific envelope
**So that** I can make informed spending decisions

**Acceptance Criteria:**
- [ ] User can ask "how much is left in my food budget this month?"
- [ ] AI provides accurate answer with remaining budget and context (e.g., how much spent, how many days left)
- [ ] User can request a summary of all envelopes at once

### Story 4: View Dashboard & Analytics

**As a** user who wants to see the big picture of their finances
**I want to** open the platform and immediately see my financial condition
**So that** I have financial clarity without having to ask AI one by one

**Acceptance Criteria:**
- [ ] Dashboard displays all key metrics on a single page
- [ ] Data is always in sync with transactions recorded via MCP client
- [ ] User can navigate to detail pages for budget, transactions, etc.

### Story 5: Connect MCP Server to Client of Choice

**As a** new user who has signed up on the marketing site
**I want to** easily connect Finance MCP to the MCP client I use
**So that** I can start using it without complicated configuration

**Acceptance Criteria:**
- [ ] Platform provides clear instructions for connecting to various popular MCP clients
- [ ] User can log in to MCP server via OAuth from any MCP client
- [ ] Documentation available on docs site for step-by-step setup per MCP client

---

## Functional Requirements

### Core Features

**Feature 1: MCP Server (Engine)**
- FastMCP server exposing financial tools to all MCP clients
- Tools: account management, transaction recording (income/expense/transfer), envelope & budget management, scheduled transactions, analytics & summary, wishlist
- `user_context` MCP resource — returns accounts, envelope names, groups, common patterns. Cached by clients to avoid redundant tool calls
- Daily briefing MCP prompt — pull-based morning summary (today's balance, remaining budget, scheduled transactions, AI recommendations)
- Onboarding prompt guiding new users through financial setup from scratch
- OAuth 2.1 for authentication
- Per-user SQLite database with encryption at rest

**Feature 2: Platform Web (platform.domain.com)**

Frontend: Vite + React + TypeScript, Shadcn/ui + Tailwind CSS, Recharts
Backend: FastAPI (REST API only)

5 pages:

| Page | Content |
|------|---------|
| **Dashboard** | Overview + analytics — all financial metrics on one page (see Feature 3 below) |
| **Budget** | All envelope groups & envelopes, assign money, target tracking, scheduled transactions |
| **Transactions** | Full history, filter by date/category/account, search, accounts overview |
| **Chat** | Built-in MCP chat client for onboarding and daily interaction |
| **Settings** | Profile, password, MCP connection guide, manage accounts |

**Feature 3: Dashboard & Analytics (single page)**

This month's condition ("Am I still on track?"):
- Total income vs expenses this month
- Ready to Assign (unallocated money)
- Budget progress per envelope (assigned vs spent, progress bars)
- Overspent envelopes highlighted with alerts

Spending breakdown ("Where is my money going?"):
- Spending by category (pie/donut chart)
- Top spending categories
- Largest recent transactions

Comparison ("This month vs last month?"):
- Month-over-month comparison per envelope
- Spending trend over recent months (line chart)

Budget insight (helps plan next month):
- Envelopes consistently underfunded vs consistently surplus
- Carryover summary

Age of Money:
- Average age of money when spent (FIFO-based, last 10 transactions)
- Displayed as "Your money is X days old" — higher is better
- Helps users understand if they're living on last month's income or this month's

**Feature 4: Marketing Site (domain.com)**
- Landing page explaining the product's value proposition
- CTA to sign up
- Explanation of envelope budgeting methodology
- Testimonial & social proof (post-launch)

**Feature 5: Docs Site (docs.domain.com)**
- Tutorial for connecting MCP server to various MCP clients (Claude, Cursor, etc.)
- Explanation of envelope budgeting method
- Usage guide for main features
- FAQ

### Out of Scope (MVP)
- Subscription / payment features
- Automatic bank account syncing
- Native mobile app (iOS/Android)
- Multi-currency
- Collaboration features (sharing budget with partner)
- Push notifications / email alerts
- Push-based morning summary (email/notification)

---

## Technical Constraints

### Performance
- MCP server response time < 2 seconds for all tool calls
- Platform dashboard load time < 3 seconds
- Support minimum 100 concurrent users for beta phase

### Security
- OAuth 2.1 for MCP client authentication
- Per-user SQLite database (data isolation between users)
- Encryption at rest for all user databases
- HTTPS required for all communication
- User financial data must never be shared or accessed across users

### Integration
- **MCP Clients**: Compatible with all MCP clients supporting standard MCP protocol (Claude, Cursor, etc.)
- **Nginx**: Reverse proxy for routing between MCP server, auth server, and platform
- **OAuth**: Separate auth server handling token introspection

### Technology Stack
- **MCP Server**: Python, FastMCP, SQLite
- **Auth Server**: Python, OAuth 2.1, SQLite (user credentials)
- **Platform Backend**: Python, FastAPI (REST API only)
- **Platform Frontend**: Vite + React + TypeScript, Shadcn/ui + Tailwind CSS, Recharts
- **Infrastructure**: VPS (Ubuntu 22.04+), Nginx, systemd
- **Database**: SQLite per-user (gitignored, per-instance)
- **Logging**: Structured logging (structlog or Python logging + JSON formatter)

---

## MVP Scope & Phasing

### Phase 1: MVP — "Proper for Friends" (Current Focus)
- MCP server with all financial tools + user_context resource + daily briefing prompt
- Platform web with 5 pages (Dashboard, Budget, Transactions, Chat, Settings)
- Marketing site (landing page)
- Docs site (connection tutorials + methodology explanation)
- Auth server with OAuth 2.1 (SQLite-based, replaces users.json)
- Structured logging across all services
- All content in English
- Free for all users

**MVP Definition**: Product polished enough for friends to try and use consistently for at least 1 month.

### Phase 2: Growth — Post-Launch Refinements
- Improvements based on early user feedback
- More detailed analytics
- Notifications & alerts (email or in-app)
- Smoother onboarding based on learnings
- Collaboration features (sharing budget with partner/family)
- Age of Money calculation
- Expanded target types (4 types like YNAB)

### Phase 3: Monetization
- Subscription model (freemium or fully paid)
- Premium features (bank syncing, advanced analytics, etc.)
- Self-service user management

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation Strategy |
|------|-------------|--------|---------------------|
| User doesn't stay consistent after onboarding | High | High | Highly guided and engaging onboarding; low friction for transaction recording; daily briefing prompt |
| MCP protocol changes / instability | Medium | High | Follow MCP spec developments; abstraction layer for easy updates |
| Data security breach | Low | High | Encryption at rest, per-user isolation, security audit before onboarding first user |
| User struggles to set up MCP in their client | Medium | Medium | Step-by-step docs per client; built-in chat client in platform as fallback |
| SQLite per-user scalability in growth phase | Low | Medium | Acceptable for initial phase; plan migration to PostgreSQL if needed |

---

## Dependencies & Blockers

**Dependencies:**
- MCP protocol SDK (FastMCP) — must be up-to-date with latest spec
- Nginx & VPS setup — infrastructure must be ready before onboarding first user
- Domain & SSL certificate — required for production deployment

**Known Blockers:**
- Product name not finalized — must be decided before launching marketing site and docs
- SQLite encryption at rest not yet implemented — must be completed before onboarding any user
- Auth server migration from users.json to SQLite — must be done before onboarding any user

---

## Design Decisions Log

1. **Transaction datetime**: Schema default changed from `date('now')` to `datetime('now')` for granular tracking. Enables future Age of Money calculation.
2. **Savings rate formula**: `(total income - total expenses) / total income`. Transfers are NOT expenses — money moved to savings accounts doesn't reduce savings rate.
3. **Target tracking**: 4 types like YNAB — `monthly_spending` (spending cap), `monthly_savings` (assign X per month, accumulates), `savings_balance` (save up to X total), `needed_by_date` (need X by date Y, auto-calculates monthly assignment).
4. **AI memory optimization**: `user_context` MCP resource (not tool) so clients cache account/envelope data and avoid redundant list calls.
5. **Daily briefing**: Pull-based MCP prompt for MVP. Push-based (email/notification) in Phase 2.
6. **Platform stack**: Vite + React + TypeScript (frontend), FastAPI REST API (backend). Chose React for rich chat interface and charting ecosystem.
7. **Platform pages**: 5 pages (Dashboard, Budget, Transactions, Chat, Settings). Wishlist folded into Budget page or deferred.

---

## Appendix

### Glossary
- **Envelope Budgeting**: Financial management method where every rupiah is allocated to a specific category "envelope" (food, transport, entertainment, etc.) at the beginning of each month
- **Ready to Assign**: Amount of money received but not yet allocated to any envelope
- **MCP (Model Context Protocol)**: Standard protocol enabling AI clients to communicate with external tool servers
- **MCP Client**: AI application supporting MCP protocol (e.g., Claude, Cursor)
- **Age of Money**: Average number of days between when money is received and when it is spent (FIFO-based). Phase 2 feature.

### References
- [YNAB](https://www.youneedabudget.com/) — envelope budgeting methodology reference
- [Money Monarch](https://moneymonarch.com/) — AI-powered personal finance reference
- [FastMCP Documentation](https://gofastmcp.com/) — MCP server framework
- [MCP Specification](https://modelcontextprotocol.io/) — MCP protocol standard

---

*This PRD was created through interactive requirements gathering with quality scoring to ensure comprehensive coverage across business, functional, UX, and technical dimensions.*
