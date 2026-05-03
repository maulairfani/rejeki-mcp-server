import { Search, X } from "lucide-react"
import type { TransactionType } from "@/hooks/useTransactions"

export interface FilterState {
  type: TransactionType | "all"
  search: string
  account: string | "all"
  envelope: string | "all"
  tag: string | "all"
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
  tags: string[]
}

function Chip({
  active,
  onClick,
  children,
}: {
  active?: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      className={
        active
          ? "inline-flex items-center rounded-full bg-brand px-3 py-1 text-xs font-semibold text-white transition-all"
          : "inline-flex items-center rounded-full bg-bg-muted px-3 py-1 text-xs font-semibold text-text-secondary transition-all hover:brightness-95"
      }
    >
      {children}
    </button>
  )
}

export function TransactionFilters({
  filters,
  onChange,
  accounts,
  envelopes,
  tags,
}: TransactionFiltersProps) {
  const hasActiveFilters =
    filters.type !== "all" ||
    filters.search !== "" ||
    filters.account !== "all" ||
    filters.envelope !== "all" ||
    filters.tag !== "all"

  return (
    <div className="flex flex-wrap items-center gap-3">
      {/* Search */}
      <div className="relative w-full max-w-[320px] flex-1 min-w-[200px]">
        <Search className="absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-text-muted" />
        <input
          type="text"
          placeholder="Search payee, memo, envelope…"
          value={filters.search}
          onChange={(e) => onChange({ ...filters, search: e.target.value })}
          className="h-9 w-full rounded-md border border-border bg-bg px-3 pl-9 text-[13.5px] text-text-primary placeholder:text-text-placeholder focus:border-brand focus:outline-none"
        />
        {filters.search && (
          <button
            onClick={() => onChange({ ...filters, search: "" })}
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded-sm p-0.5 text-text-muted hover:text-text-secondary"
          >
            <X className="size-3.5" />
          </button>
        )}
      </div>

      {/* Type chips */}
      <div className="flex gap-1.5" role="group" aria-label="Filter by type">
        {TYPE_OPTIONS.map((opt) => (
          <Chip
            key={opt.value}
            active={filters.type === opt.value}
            onClick={() => onChange({ ...filters, type: opt.value })}
          >
            {opt.label}
          </Chip>
        ))}
      </div>

      {/* Account + envelope selects */}
      <select
        value={filters.account}
        onChange={(e) => onChange({ ...filters, account: e.target.value })}
        className="h-7 rounded-md border border-border bg-bg px-2 text-xs text-text-secondary focus:border-brand focus:outline-none"
      >
        <option value="all">All accounts</option>
        {accounts.map((a) => (
          <option key={a} value={a}>
            {a}
          </option>
        ))}
      </select>
      <select
        value={filters.envelope}
        onChange={(e) => onChange({ ...filters, envelope: e.target.value })}
        className="h-7 rounded-md border border-border bg-bg px-2 text-xs text-text-secondary focus:border-brand focus:outline-none"
      >
        <option value="all">All envelopes</option>
        {envelopes.map((e) => (
          <option key={e} value={e}>
            {e}
          </option>
        ))}
      </select>
      {tags.length > 0 && (
        <select
          value={filters.tag}
          onChange={(e) => onChange({ ...filters, tag: e.target.value })}
          className="h-7 rounded-md border border-border bg-bg px-2 text-xs text-text-secondary focus:border-brand focus:outline-none"
        >
          <option value="all">All tags</option>
          {tags.map((t) => (
            <option key={t} value={t}>
              #{t}
            </option>
          ))}
        </select>
      )}

      {hasActiveFilters && (
        <button
          onClick={() =>
            onChange({ type: "all", search: "", account: "all", envelope: "all", tag: "all" })
          }
          className="inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs text-text-muted transition-colors hover:text-text-secondary"
        >
          <X className="size-3" />
          Clear
        </button>
      )}


    </div>
  )
}
