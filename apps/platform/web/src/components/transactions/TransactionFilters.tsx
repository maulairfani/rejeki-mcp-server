import { Search, X } from "lucide-react"
import type { TransactionType } from "@/hooks/useTransactions"

export interface FilterState {
  type: TransactionType | "all"
  search: string
  account: string | "all"
  envelope: string | "all"
}

const TYPE_OPTIONS: { value: TransactionType | "all"; label: string }[] = [
  { value: "all", label: "All" },
  { value: "expense", label: "Expense" },
  { value: "income", label: "Income" },
  { value: "transfer", label: "Transfer" },
]

interface TransactionFiltersProps {
  filters: FilterState
  onChange: (filters: FilterState) => void
  accounts: string[]
  envelopes: string[]
  resultCount: number
}

export function TransactionFilters({
  filters,
  onChange,
  accounts,
  envelopes,
  resultCount,
}: TransactionFiltersProps) {
  const hasActiveFilters =
    filters.type !== "all" ||
    filters.search !== "" ||
    filters.account !== "all" ||
    filters.envelope !== "all"

  return (
    <div className="flex flex-col gap-3">
      {/* Search bar */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search payee, memo, envelope..."
          value={filters.search}
          onChange={(e) => onChange({ ...filters, search: e.target.value })}
          className="h-9 w-full rounded-lg border border-input bg-background pl-9 pr-3 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40"
        />
        {filters.search && (
          <button
            onClick={() => onChange({ ...filters, search: "" })}
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded-sm p-0.5 text-muted-foreground hover:text-foreground"
          >
            <X className="size-3.5" />
          </button>
        )}
      </div>

      {/* Filter row */}
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1.5">
        {/* Type pills */}
        <div className="flex gap-1 shrink-0" role="group" aria-label="Filter by type">
          {TYPE_OPTIONS.map((opt) => {
            const active = filters.type === opt.value
            return (
              <button
                key={opt.value}
                onClick={() => onChange({ ...filters, type: opt.value })}
                aria-pressed={active}
                className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                  active
                    ? "bg-primary/10 text-primary border-primary/20"
                    : "text-muted-foreground hover:text-foreground hover:border-foreground/20"
                }`}
              >
                {opt.label}
              </button>
            )
          })}
        </div>

        {/* Account filter */}
        <select
          value={filters.account}
          onChange={(e) => onChange({ ...filters, account: e.target.value })}
          className="h-7 rounded-lg border border-input bg-background px-2 text-xs text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40"
        >
          <option value="all">All accounts</option>
          {accounts.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>

        {/* Envelope filter */}
        <select
          value={filters.envelope}
          onChange={(e) => onChange({ ...filters, envelope: e.target.value })}
          className="h-7 rounded-lg border border-input bg-background px-2 text-xs text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40"
        >
          <option value="all">All envelopes</option>
          {envelopes.map((e) => (
            <option key={e} value={e}>
              {e}
            </option>
          ))}
        </select>

        {/* Clear filters */}
        {hasActiveFilters && (
          <button
            onClick={() =>
              onChange({ type: "all", search: "", account: "all", envelope: "all" })
            }
            className="flex items-center gap-1 rounded-full px-2 py-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="size-3" />
            Clear
          </button>
        )}

        {/* Result count */}
        <span className="ml-auto text-xs text-muted-foreground tabular-nums">
          {resultCount} transactions
        </span>
      </div>
    </div>
  )
}
