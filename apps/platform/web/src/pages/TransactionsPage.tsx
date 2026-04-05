import { useState } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { Plus, Search, X } from "lucide-react"
import { getAccounts, getEnvelopes, getTransactions, postTransaction } from "@/lib/api"
import { cn, formatIDR, formatShortIDR } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

// ─── Types ───────────────────────────────────────────────────────────────────

interface Account {
  id: number
  name: string
  type: string
  balance: number
}

interface Envelope {
  id: number
  name: string
  icon: string | null
  group_name: string
}

interface Transaction {
  id: number
  date: string
  type: string
  amount: number
  payee: string
  memo: string | null
  account_name: string
  envelope_name: string | null
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function currentPeriod(): string {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`
}

function periodToLabel(p: string) {
  const [y, m] = p.split("-")
  return new Date(Number(y), Number(m) - 1).toLocaleString("en-US", { month: "long", year: "numeric" })
}

const TYPE_BADGE: Record<string, string> = {
  income: "text-chart-1",
  expense: "text-foreground",
  transfer: "text-muted-foreground",
}

// ─── Add Transaction Modal ────────────────────────────────────────────────────

function AddTransactionModal({
  accounts,
  envelopes,
  onClose,
  onSaved,
}: {
  accounts: Account[]
  envelopes: Envelope[]
  onClose: () => void
  onSaved: () => void
}) {
  const [form, setForm] = useState({
    type: "expense",
    amount: "",
    payee: "",
    account_id: accounts[0]?.id ?? 0,
    envelope_id: "",
    memo: "",
    date: new Date().toISOString().slice(0, 10),
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")

  const set = (k: string, v: string | number) => setForm((f) => ({ ...f, [k]: v }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.amount || !form.account_id) return
    setSaving(true)
    setError("")
    try {
      await postTransaction({
        type: form.type,
        amount: parseFloat(form.amount),
        payee: form.payee || undefined,
        account_id: Number(form.account_id),
        envelope_id: form.envelope_id ? Number(form.envelope_id) : undefined,
        memo: form.memo || undefined,
        date: form.date || undefined,
      })
      onSaved()
    } catch {
      setError("Failed to save transaction")
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-card border rounded-xl shadow-xl w-full max-w-md p-6 space-y-5">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">Add Transaction</h2>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground"><X size={16} /></button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Type */}
          <div className="flex gap-2">
            {(["expense", "income", "transfer"] as const).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => set("type", t)}
                className={cn(
                  "flex-1 py-1.5 text-sm rounded-md border transition-colors capitalize",
                  form.type === t ? "bg-primary text-primary-foreground border-primary" : "border-border text-muted-foreground hover:bg-muted"
                )}
              >{t}</button>
            ))}
          </div>

          {/* Amount */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Amount</label>
            <Input type="number" placeholder="0" value={form.amount} onChange={(e) => set("amount", e.target.value)} required />
          </div>

          {/* Payee */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Payee</label>
            <Input placeholder="e.g. Alfamart" value={form.payee} onChange={(e) => set("payee", e.target.value)} />
          </div>

          {/* Account */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Account</label>
            <select
              className="w-full border rounded-md px-3 py-2 text-sm bg-background"
              value={form.account_id}
              onChange={(e) => set("account_id", e.target.value)}
              required
            >
              {accounts.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          </div>

          {/* Envelope (expense only) */}
          {form.type === "expense" && (
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Envelope</label>
              <select
                className="w-full border rounded-md px-3 py-2 text-sm bg-background"
                value={form.envelope_id}
                onChange={(e) => set("envelope_id", e.target.value)}
              >
                <option value="">— None —</option>
                {envelopes.map((e) => (
                  <option key={e.id} value={e.id}>{e.icon} {e.name}</option>
                ))}
              </select>
            </div>
          )}

          {/* Date */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Date</label>
            <Input type="date" value={form.date} onChange={(e) => set("date", e.target.value)} />
          </div>

          {/* Memo */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Memo</label>
            <Input placeholder="Optional note" value={form.memo} onChange={(e) => set("memo", e.target.value)} />
          </div>

          {error && <p className="text-destructive text-sm">{error}</p>}

          <div className="flex gap-2 pt-1">
            <Button type="button" variant="outline" className="flex-1" onClick={onClose}>Cancel</Button>
            <Button type="submit" className="flex-1" disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export function TransactionsPage() {
  const [period, setPeriod] = useState(currentPeriod())
  const [search, setSearch] = useState("")
  const [accountFilter, setAccountFilter] = useState("")
  const [envelopeFilter, setEnvelopeFilter] = useState("")
  const [limit, setLimit] = useState(50)
  const [showAdd, setShowAdd] = useState(false)
  const queryClient = useQueryClient()

  const params = {
    period: period || undefined,
    search: search || undefined,
    account_id: accountFilter ? Number(accountFilter) : undefined,
    envelope_id: envelopeFilter ? Number(envelopeFilter) : undefined,
    limit,
  }

  const { data: txData, isLoading } = useQuery<Transaction[]>({
    queryKey: ["transactions", params],
    queryFn: () => getTransactions(params).then((r) => r.data),
  })

  const { data: accountsData } = useQuery<{ accounts: Account[]; total: number }>({
    queryKey: ["accounts"],
    queryFn: () => getAccounts().then((r) => r.data),
  })

  const { data: envelopes = [] } = useQuery<Envelope[]>({
    queryKey: ["envelopes-all"],
    queryFn: () => getEnvelopes().then((r) => r.data),
  })

  const accounts = accountsData?.accounts ?? []
  const transactions = txData ?? []

  const handleSaved = () => {
    setShowAdd(false)
    queryClient.invalidateQueries({ queryKey: ["transactions"] })
    queryClient.invalidateQueries({ queryKey: ["accounts"] })
    queryClient.invalidateQueries({ queryKey: ["dashboard"] })
  }

  // Group transactions by date
  const grouped = transactions.reduce<Record<string, Transaction[]>>((acc, tx) => {
    const day = tx.date.slice(0, 10)
    if (!acc[day]) acc[day] = []
    acc[day].push(tx)
    return acc
  }, {})
  const days = Object.keys(grouped).sort((a, b) => b.localeCompare(a))

  return (
    <div className="space-y-6">
      {/* Accounts overview */}
      {accounts.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {accounts.map((a) => (
            <button
              key={a.id}
              onClick={() => setAccountFilter(String(a.id) === accountFilter ? "" : String(a.id))}
              className={cn(
                "text-left p-4 rounded-xl border bg-card transition-all",
                String(a.id) === accountFilter ? "border-primary ring-1 ring-primary" : "hover:border-muted-foreground/40"
              )}
            >
              <p className="text-xs text-muted-foreground capitalize">{a.type}</p>
              <p className="text-sm font-medium mt-0.5 truncate">{a.name}</p>
              <p className="text-base font-semibold tabular-nums mt-1">{formatShortIDR(a.balance)}</p>
            </button>
          ))}
          <div className="p-4 rounded-xl border border-dashed bg-muted/30 flex flex-col justify-center">
            <p className="text-xs text-muted-foreground">Total</p>
            <p className="text-base font-semibold tabular-nums mt-1">{formatShortIDR(accountsData?.total ?? 0)}</p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-2 items-center">
        <div className="relative flex-1 min-w-48">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-8 h-9"
            placeholder="Search payee or memo…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select
          className="h-9 border rounded-md px-3 text-sm bg-background"
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
        >
          <option value="">All time</option>
          {Array.from({ length: 6 }, (_, i) => {
            const d = new Date()
            d.setMonth(d.getMonth() - i)
            const val = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`
            return <option key={val} value={val}>{periodToLabel(val)}</option>
          })}
        </select>
        <select
          className="h-9 border rounded-md px-3 text-sm bg-background"
          value={envelopeFilter}
          onChange={(e) => setEnvelopeFilter(e.target.value)}
        >
          <option value="">All envelopes</option>
          {envelopes.map((e) => (
            <option key={e.id} value={e.id}>{e.icon} {e.name}</option>
          ))}
        </select>
        {(search || accountFilter || envelopeFilter) && (
          <button
            onClick={() => { setSearch(""); setAccountFilter(""); setEnvelopeFilter("") }}
            className="h-9 px-3 text-sm text-muted-foreground hover:text-foreground border rounded-md flex items-center gap-1.5"
          >
            <X size={12} /> Clear
          </button>
        )}
        <Button size="sm" className="h-9 ml-auto gap-1.5" onClick={() => setShowAdd(true)}>
          <Plus size={14} /> Add
        </Button>
      </div>

      {/* Transaction list */}
      <div className="bg-card rounded-xl border overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-sm text-muted-foreground">Loading…</div>
        ) : transactions.length === 0 ? (
          <div className="p-8 text-center text-sm text-muted-foreground">No transactions found.</div>
        ) : (
          <>
            {days.map((day) => (
              <div key={day}>
                <div className="px-4 py-2 bg-muted/40 border-b border-t first:border-t-0">
                  <span className="text-xs font-medium text-muted-foreground">
                    {new Date(day).toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })}
                  </span>
                </div>
                <div className="divide-y divide-border/50">
                  {grouped[day].map((tx) => (
                    <div key={tx.id} className="flex items-center gap-4 px-4 py-3 hover:bg-muted/30 transition-colors">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{tx.payee || "—"}</p>
                        <p className="text-xs text-muted-foreground truncate">
                          {tx.account_name}
                          {tx.envelope_name && ` · ${tx.envelope_name}`}
                          {tx.memo && ` · ${tx.memo}`}
                        </p>
                      </div>
                      <span className={cn("text-sm tabular-nums font-medium shrink-0", TYPE_BADGE[tx.type])}>
                        {tx.type === "income" ? "+" : tx.type === "expense" ? "−" : ""}
                        {formatIDR(tx.amount)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ))}

            {transactions.length === limit && (
              <div className="p-4 text-center border-t">
                <button
                  className="text-sm text-primary hover:underline"
                  onClick={() => setLimit((l) => l + 50)}
                >
                  Load more
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {/* Add Transaction Modal */}
      {showAdd && (
        <AddTransactionModal
          accounts={accounts}
          envelopes={envelopes}
          onClose={() => setShowAdd(false)}
          onSaved={handleSaved}
        />
      )}
    </div>
  )
}
