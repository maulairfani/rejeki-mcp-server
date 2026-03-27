# Rejeki

AI personal finance agent powered by Claude + MCP. Instead of manually categorizing transactions in a spreadsheet, you just talk to Claude naturally.

> "Bisa afford PS5 gak bulan ini?"
> "Berapa yang udah aku keluarin buat makan minggu ini?"
> "Catat transfer 500 ribu ke GoPay"

## Core Concept: True Available Money

Most finance apps show your account balance. Rejeki shows what you can **actually** spend:

```
True Available = Total Saldo
              − Kewajiban tetap yang belum jatuh tempo bulan ini
              − Upcoming expenses yang belum dibayar
              − Saving goal allocations
```

## How It Works

Rejeki is an [MCP](https://modelcontextprotocol.io) server. Claude Desktop connects to it and gains access to your financial data through tools. Claude is the brain — Rejeki is just the data layer.

```
You ──── (natural language) ──── Claude Desktop
                                       │
                                  MCP tools
                                       │
                                   Rejeki
                                       │
                                    SQLite
```

## Setup

**Requirements:** Python 3.11+, [miniconda](https://docs.conda.io/en/latest/miniconda.html) or any Python env, Claude Desktop

**1. Install dependencies**
```bash
pip install -e .
```

**2. Add to Claude Desktop config**

File: `%AppData%\Claude\claude_desktop_config.json` (or the equivalent path on your machine)

```json
{
  "mcpServers": {
    "rejeki": {
      "command": "C:\\path\\to\\python.exe",
      "args": ["-m", "rejeki.server"],
      "cwd": "C:\\path\\to\\rejeki"
    }
  }
}
```

**3. Restart Claude Desktop** (quit from system tray, not just close window)

**4. Verify** — click the "+" icon in Claude Desktop → hover "Connectors" → `rejeki` should appear.

## Environment Variables

```bash
cp .env.example .env
```

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///rejeki.db` | Database path. Use `sqlite:///` prefix or PostgreSQL URL |

## Available Tools (21)

| Tool | Description |
|---|---|
| `finance_add_account` | Tambah rekening (bank / ewallet / cash) |
| `finance_get_accounts` | List semua rekening + saldo |
| `finance_add_transaction` | Catat pemasukan, pengeluaran, atau transfer |
| `finance_get_transactions` | Query transaksi dengan filter |
| `finance_set_budget` | Set budget per kategori per bulan |
| `finance_get_budget_status` | Cek sisa budget bulan ini |
| `finance_add_saving_goal` | Buat saving goal baru |
| `finance_get_saving_goals` | List semua saving goals + progress |
| `finance_update_saving_goal` | Update progress saving goal |
| `finance_add_fixed_expense` | Catat kewajiban tetap bulanan (kos, cicilan, dll) |
| `finance_get_fixed_expenses` | List kewajiban tetap |
| `finance_add_upcoming_expense` | Catat pengeluaran yang akan datang |
| `finance_get_upcoming_expenses` | List upcoming expenses |
| `finance_mark_upcoming_paid` | Tandai upcoming expense sebagai lunas |
| `finance_manage_wishlist` | Kelola wishlist (list / add / remove) |
| `finance_add_asset` | Catat aset berdasarkan cost basis |
| `finance_get_assets` | List semua aset |
| `finance_get_true_available` | Hitung True Available Money |
| `finance_can_afford` | Cek apakah bisa afford sejumlah uang |
| `finance_get_summary` | Ringkasan keuangan bulanan |
| `finance_get_spending_trend` | Tren pengeluaran N bulan ke belakang |

## Default Categories

Income: Gaji, Freelance, Investasi, Lainnya

Expense: Makan, Transport, Belanja, Hiburan, Kesehatan, Pendidikan, Tagihan, Langganan, Kirim Ortu, Kos/Sewa, Lainnya

## Stack

- **Python** + [FastMCP](https://github.com/jlowin/fastmcp)
- **SQLite** (dev) → PostgreSQL (prod)
- **Transport:** stdio (dev) → HTTP + OAuth (prod)
