import { Badge } from "@/components/shared/Badge"
import { AmountText } from "@/components/shared/AmountText"
import type { DayGroup } from "@/hooks/useTransactions"
import { TransactionRow } from "./TransactionRow"

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]
const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

function formatDayHeader(iso: string): { label: string; relative: string | null } {
  const [y, m, d] = iso.split("-").map(Number)
  const date = new Date(y, m - 1, d)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const label = `${WEEKDAYS[date.getDay()]}, ${MONTHS[m - 1]} ${d}`
  const diff = Math.round(
    (today.getTime() - date.getTime()) / (1000 * 60 * 60 * 24)
  )
  if (diff === 0) return { label, relative: "Today" }
  if (diff === 1) return { label, relative: "Yesterday" }
  return { label, relative: null }
}

interface TransactionDayGroupProps {
  group: DayGroup
  showNominal: boolean
  onRowClick?: (transactionId: number) => void
}

export function TransactionDayGroup({
  group,
  showNominal,
  onRowClick,
}: TransactionDayGroupProps) {
  const { label, relative } = formatDayHeader(group.date)
  const net = group.income - group.expense

  return (
    <div>
      <div className="flex items-center justify-between border-b border-border bg-card px-7 py-2.5">
        <div className="flex items-center gap-2">
          <span className="font-heading text-[13px] font-bold text-text-primary">
            {label}
          </span>
          {relative && (
            <Badge color="muted" size="xs">
              {relative}
            </Badge>
          )}
        </div>
        <AmountText
          amount={net}
          showNominal={showNominal}
          size="sm"
          tone={net > 0 ? "positive" : net < 0 ? "auto" : "neutral"}
        />
      </div>

      {group.transactions.map((txn) => (
        <TransactionRow
          key={txn.id}
          transaction={txn}
          showNominal={showNominal}
          onClick={onRowClick ? () => onRowClick(txn.id) : undefined}
        />
      ))}
    </div>
  )
}
