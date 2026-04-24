import { useSortable } from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import { GripVertical } from "lucide-react"
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
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: `env:${envelope.id}`, data: { type: "envelope", envelope } })

  const funded = budget.carryover + budget.assigned
  const overspent = budget.available < 0
  const savingsLabel = targetBadge(envelope)

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="group/row flex w-full items-center gap-2 border-b border-border-muted pl-2 pr-7 transition-colors hover:bg-bg-muted"
      {...attributes}
    >
      {/* Drag handle */}
      <button
        type="button"
        {...listeners}
        className="flex h-full shrink-0 cursor-grab items-center px-1 text-text-muted opacity-0 transition-opacity hover:text-text-secondary group-hover/row:opacity-100 active:cursor-grabbing"
        aria-label="Reorder envelope"
      >
        <GripVertical className="size-4" />
      </button>

      <button
        onClick={onClick}
        className="flex flex-1 items-center gap-3 py-2.5 text-left"
      >
        <span className="flex size-7 shrink-0 items-center justify-center rounded-md bg-bg-muted text-[14px] leading-none">
          {envelope.icon}
        </span>

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
    </div>
  )
}
