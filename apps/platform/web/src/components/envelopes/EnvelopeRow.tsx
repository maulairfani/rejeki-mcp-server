import { formatIDR } from "@/lib/format"
import { Badge } from "@/components/shared/Badge"
import { AmountText } from "@/components/shared/AmountText"
import { ProgressBar } from "@/components/shared/ProgressBar"
import type { Envelope, EnvelopeBudget } from "@/hooks/useEnvelopes"

function formatDeadline(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number)
  if (!y || !m || !d) return iso
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
  return `${d} ${months[m - 1]} ${y}`
}

function targetBadge(envelope: Envelope): string | null {
  const t = envelope.target
  if (!t) return null
  switch (t.type) {
    case "monthly_spending":
      return `Limit ${formatIDR(t.amount)}/mo`
    case "monthly_savings":
      return `Save ${formatIDR(t.amount)}/mo`
    case "savings_balance":
      return `Goal ${formatIDR(t.amount)}`
    case "needed_by_date":
      return t.deadline
        ? `${formatIDR(t.amount)} by ${formatDeadline(t.deadline)}`
        : `${formatIDR(t.amount)} by deadline`
    default:
      return null
  }
}

interface EnvelopeRowProps {
  envelope: Envelope
  budget: EnvelopeBudget
  showNominal: boolean
  onClick: () => void
}

export function EnvelopeRow({
  envelope,
  budget,
  showNominal,
  onClick,
}: EnvelopeRowProps) {
  const funded = budget.carryover + budget.assigned
  const overspent = budget.available < 0
  const savingsLabel = targetBadge(envelope)

  return (
    <button
      onClick={onClick}
      className="flex w-full items-center gap-3 border-b border-border-muted px-7 py-2.5 text-left transition-colors hover:bg-bg-muted"
    >
      {/* Icon box */}
      <span className="flex size-7 shrink-0 items-center justify-center rounded-md bg-bg-muted text-[14px] leading-none">
        {envelope.icon}
      </span>

      {/* Name + (optional) savings badge + progress bar */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <span className="truncate text-[13.5px] font-medium text-text-primary">
            {envelope.name}
          </span>
          {savingsLabel && (
            <Badge color="brand" size="xs">
              {savingsLabel}
            </Badge>
          )}
        </div>
        {funded > 0 && (
          <div className="mt-1.5">
            <ProgressBar
              value={Math.max(0, funded - budget.available)}
              max={funded}
              danger={overspent}
              height={5}
            />
          </div>
        )}
      </div>

      {/* Available amount */}
      <div className="w-[96px] shrink-0 text-right">
        {funded > 0 || budget.available !== 0 ? (
          <AmountText
            amount={budget.available}
            showNominal={showNominal}
            size="sm"
            tone={budget.available < 0 ? "auto" : "neutral"}
          />
        ) : (
          <span className="text-xs text-text-muted">Rp 0</span>
        )}
      </div>
    </button>
  )
}
