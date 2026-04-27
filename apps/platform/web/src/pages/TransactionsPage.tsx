import { useMemo, useState } from "react"
import { Loader2 } from "lucide-react"
import {
  useTransactions,
  filterTransactions,
  groupByDay,
} from "@/hooks/useTransactions"
import { useAccounts } from "@/hooks/useAccounts"
import { useEnvelopes } from "@/hooks/useEnvelopes"
import { useTags } from "@/hooks/useTags"
import {
  TransactionFilters,
  type FilterState,
} from "@/components/transactions/TransactionFilters"
import {
  PeriodPicker,
  currentPeriod,
} from "@/components/shared/PeriodPicker"
import { PageHeader } from "@/components/shared/PageHeader"
import { TransactionDayGroup } from "@/components/transactions/TransactionDayGroup"
import { TransactionDetailDialog } from "@/components/transactions/TransactionDetailDialog"

const DEFAULT_FILTERS: FilterState = {
  type: "all",
  search: "",
  account: "all",
  envelope: "all",
  tag: "all",
}

export function TransactionsPage({ showNominal }: { showNominal: boolean }) {
  const [period, setPeriod] = useState(currentPeriod)
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS)
  const [selectedId, setSelectedId] = useState<number | null>(null)

  const { transactions, isLoading } = useTransactions(period)

  const selected = useMemo(
    () => transactions.find((t) => t.id === selectedId) ?? null,
    [transactions, selectedId]
  )
  const { accounts: allAccounts } = useAccounts()
  const { allEnvelopes } = useEnvelopes(period)
  const { tags: allTags } = useTags()

  const accounts = useMemo(
    () => allAccounts.map((a) => a.name).sort(),
    [allAccounts]
  )
  const envelopes = useMemo(
    () => allEnvelopes.map((e) => e.envelope.name).sort(),
    [allEnvelopes]
  )
  const tagNames = useMemo(() => allTags.map((t) => t.name), [allTags])

  const filtered = useMemo(
    () => filterTransactions(transactions, filters),
    [transactions, filters]
  )

  const days = useMemo(() => groupByDay(filtered), [filtered])

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <PageHeader title="Transactions">
        <PeriodPicker period={period} onChange={setPeriod} />
      </PageHeader>

      {/* Filter bar */}
      <div className="flex-shrink-0 border-b border-border bg-card px-7 py-3">
        <TransactionFilters
          filters={filters}
          onChange={setFilters}
          accounts={accounts}
          envelopes={envelopes}
          tags={tagNames}
          resultCount={filtered.length}
        />
      </div>

      {/* Column header strip */}
      <div className="hidden flex-shrink-0 grid-cols-[28px_1fr_1fr_100px_80px_90px] gap-3 border-b border-border bg-bg-muted px-7 py-1.5 md:grid">
        {["", "Payee", "Memo", "Envelope", "Account", "Amount"].map((h, i) => (
          <span
            key={i}
            className={`text-[11px] font-semibold uppercase tracking-wider text-text-muted ${
              i === 5 ? "text-right" : "text-left"
            }`}
          >
            {h}
          </span>
        ))}
      </div>

      {/* Scrollable rows */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="size-5 animate-spin text-text-muted" />
          </div>
        ) : days.length === 0 ? (
          <div className="flex items-center justify-center py-16 text-sm text-text-muted">
            No transactions found
          </div>
        ) : (
          <>
            {days.map((group) => (
              <TransactionDayGroup
                key={group.date}
                group={group}
                showNominal={showNominal}
                onRowClick={setSelectedId}
              />
            ))}
            <div className="h-10" />
          </>
        )}
      </div>

      <TransactionDetailDialog
        transaction={selected}
        open={selectedId !== null}
        onOpenChange={(open) => {
          if (!open) setSelectedId(null)
        }}
        showNominal={showNominal}
      />
    </div>
  )
}
