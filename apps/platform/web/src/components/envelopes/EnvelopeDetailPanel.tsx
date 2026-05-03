import { useEffect, useState } from "react"
import { Check, CheckCircle2, Loader2, X } from "lucide-react"
import { formatIDR } from "@/lib/format"
import {
  useAssignEnvelope,
  useSetEnvelopeTarget,
  type Envelope,
  type EnvelopeBudget,
  type TargetType,
} from "@/hooks/useEnvelopes"

const TARGET_TYPE_OPTIONS: { value: TargetType | "none"; label: string }[] = [
  { value: "none", label: "No target" },
  { value: "monthly_spending", label: "Monthly spending limit" },
  { value: "monthly_savings", label: "Save per month" },
  { value: "savings_balance", label: "Savings goal" },
  { value: "needed_by_date", label: "Needed by date" },
]

interface EnvelopeDetailPanelProps {
  envelope: Envelope | null
  budget: EnvelopeBudget | null
  period: string
  isPastPeriod: boolean
  onClose: () => void
  donors: { envelope: Envelope; budget: EnvelopeBudget }[]
  onCover: (fromEnvelopeId: number, amount: number) => void
  // empty-state props
  readyToAssign: number
  allItems: { envelope: Envelope; budget: EnvelopeBudget }[]
  onAssign: (envelopeId: number, newAssigned: number) => Promise<void>
}

export function EnvelopeDetailPanel({
  envelope,
  budget,
  period,
  isPastPeriod,
  onClose,
  donors,
  onCover,
  readyToAssign,
  allItems,
  onAssign,
}: EnvelopeDetailPanelProps) {
  if (!envelope || !budget) {
    if (isPastPeriod) return <HistoricalEmptyState />
    return <EmptyState readyToAssign={readyToAssign} allItems={allItems} onAssign={onAssign} />
  }

  const funded = budget.carryover + budget.assigned
  const overspent = budget.available < 0
  const deficit = Math.abs(budget.available)

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex flex-shrink-0 items-center gap-2.5 border-b border-border px-4 py-3.5">
        <span className="text-lg leading-none">{envelope.icon}</span>
        <span className="min-w-0 flex-1 truncate text-[13px] font-semibold text-text-primary">
          {envelope.name}
        </span>
        <button
          onClick={onClose}
          className="flex h-6 w-6 items-center justify-center rounded-md text-text-muted transition-colors hover:bg-bg-muted hover:text-text-secondary"
        >
          <X className="size-3.5" />
        </button>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto">
        {/* Budget breakdown */}
        <div className="px-4 py-4">
          <p className="mb-3 text-[10px] font-semibold uppercase tracking-wider text-text-muted">
            Budget
          </p>
          <div className="flex flex-col gap-2">
            <BudgetLine label="Carryover" value={budget.carryover} />
            <BudgetLine label="Assigned" value={budget.assigned} />
            <BudgetLine label="Funded" value={funded} muted />
            <BudgetLine label="Activity" value={-budget.activity} danger />
          </div>
          <div className="mt-3 flex items-center justify-between border-t border-border pt-3">
            <span className="text-[13px] font-medium text-text-primary">Available</span>
            <span
              className={`font-heading text-xl font-semibold tabular-nums ${
                overspent
                  ? "text-[color:var(--danger)]"
                  : budget.available > 0
                    ? "text-[color:var(--success)]"
                    : "text-text-muted"
              }`}
            >
              {formatIDR(budget.available)}
            </span>
          </div>
        </div>

        {/* Cover overspent */}
        {overspent && (
          <div className="border-t border-border px-4 py-4">
            <p className="mb-2.5 text-[11.5px] font-semibold text-[color:var(--danger)]">
              {formatIDR(deficit)} overspent — cover from:
            </p>
            {donors.length === 0 ? (
              <p className="text-[12px] text-text-muted">
                No envelopes with available balance.
              </p>
            ) : (
              <div className="flex max-h-40 flex-col gap-0.5 overflow-y-auto">
                {donors.map((donor) => {
                  const canCover = Math.min(donor.budget.available, deficit)
                  return (
                    <button
                      key={donor.envelope.id}
                      onClick={() => onCover(donor.envelope.id, canCover)}
                      className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-left transition-colors hover:bg-bg-muted"
                    >
                      <span className="text-sm leading-none">{donor.envelope.icon}</span>
                      <span className="min-w-0 flex-1 truncate text-[12px] font-medium text-text-primary">
                        {donor.envelope.name}
                      </span>
                      <span className="shrink-0 text-[11px] tabular-nums text-[color:var(--success)]">
                        {formatIDR(donor.budget.available)}
                      </span>
                    </button>
                  )
                })}
              </div>
            )}
          </div>
        )}

        {/* Combined assign + target form */}
        <EditForm
          key={`edit-${envelope.id}`}
          envelope={envelope}
          budget={budget}
          period={period}
          isPastPeriod={isPastPeriod}
        />
      </div>
    </div>
  )
}

// ── Combined edit form (assign + target) ─────────────────────────────────────

function EditForm({
  envelope,
  budget,
  period,
  isPastPeriod,
}: {
  envelope: Envelope
  budget: EnvelopeBudget
  period: string
  isPastPeriod: boolean
}) {
  const assignMutation = useAssignEnvelope(period)
  const targetMutation = useSetEnvelopeTarget(period)

  const [assignRaw, setAssignRaw] = useState(String(budget.assigned))
  const [targetType, setTargetType] = useState<TargetType | "none">(
    envelope.target?.type ?? "none"
  )
  const [amount, setAmount] = useState(envelope.target?.amount?.toString() ?? "")
  const [deadline, setDeadline] = useState(envelope.target?.deadline ?? "")
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle")

  useEffect(() => {
    setAssignRaw(String(budget.assigned))
    setTargetType(envelope.target?.type ?? "none")
    setAmount(envelope.target?.amount?.toString() ?? "")
    setDeadline(envelope.target?.deadline ?? "")
    setStatus("idle")
  }, [envelope.id])

  const isPending = status === "loading"
  const newAssigned = Math.max(0, Number(assignRaw) || 0)
  const assignChanged = !isPastPeriod && newAssigned !== budget.assigned

  async function handleSave() {
    if (isPending) return
    setStatus("loading")
    try {
      if (assignChanged) {
        await assignMutation.mutateAsync({ envelopeId: envelope.id, assigned: newAssigned })
      }
      await targetMutation.mutateAsync({
        envelopeId: envelope.id,
        targetType: targetType === "none" ? null : targetType,
        targetAmount: targetType !== "none" ? Number(amount) || 0 : null,
        targetDeadline: targetType === "needed_by_date" ? deadline || null : null,
      })
      setStatus("success")
      setTimeout(() => setStatus("idle"), 1500)
    } catch {
      setStatus("error")
      setTimeout(() => setStatus("idle"), 2000)
    }
  }

  return (
    <div className="border-t border-border px-4 py-4">
      <div className="flex flex-col gap-4">
        {/* Assign input */}
        {!isPastPeriod && (
          <div>
            <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-text-muted">
              Assign
            </p>
            <input
              type="number"
              value={assignRaw}
              onChange={(e) => setAssignRaw(e.target.value)}
              disabled={isPending}
              className="h-8 w-full rounded-lg border border-border bg-bg-muted px-2 text-[12.5px] tabular-nums text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
            />
          </div>
        )}

        {/* Target inputs */}
        <div>
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-text-muted">
            Target
          </p>
          <div className="flex flex-col gap-2">
            <select
              value={targetType}
              onChange={(e) => setTargetType(e.target.value as TargetType | "none")}
              disabled={isPending}
              className="h-8 rounded-lg border border-border bg-bg-muted px-2 text-[12.5px] text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
            >
              {TARGET_TYPE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>

            {targetType !== "none" && (
              <>
                <div>
                  <label className="text-[11px] text-text-muted">Amount (IDR)</label>
                  <input
                    type="number"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    disabled={isPending}
                    placeholder="0"
                    className="mt-0.5 h-8 w-full rounded-lg border border-border bg-bg-muted px-2 text-[12.5px] tabular-nums text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
                  />
                </div>
                {targetType === "needed_by_date" && (
                  <div>
                    <label className="text-[11px] text-text-muted">Deadline</label>
                    <input
                      type="date"
                      value={deadline}
                      onChange={(e) => setDeadline(e.target.value)}
                      disabled={isPending}
                      className="mt-0.5 h-8 w-full rounded-lg border border-border bg-bg-muted px-2 text-[12.5px] text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
                    />
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        {/* Single save button */}
        <button
          onClick={handleSave}
          disabled={isPending}
          className={`flex items-center justify-center gap-1.5 rounded-lg py-2 text-[12px] font-semibold transition-colors ${
            status === "success"
              ? "bg-[color:var(--success-light)] text-[color:var(--success)]"
              : status === "error"
                ? "bg-danger-light text-[color:var(--danger)]"
                : isPending
                  ? "cursor-not-allowed bg-bg-muted text-text-muted"
                  : "bg-brand-light text-brand-text hover:brightness-95"
          }`}
        >
          {status === "loading" ? (
            <><Loader2 className="size-3.5 animate-spin" /> Saving…</>
          ) : status === "success" ? (
            <><Check className="size-3.5" /> Saved</>
          ) : status === "error" ? (
            "Failed — try again"
          ) : (
            "Save"
          )}
        </button>
      </div>
    </div>
  )
}

// ── Historical empty state ────────────────────────────────────────────────────

function HistoricalEmptyState() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center">
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-bg-muted">
        <span className="text-xl">🗓️</span>
      </div>
      <div>
        <p className="text-[13px] font-semibold text-text-primary">Past period</p>
        <p className="mt-1 text-[12px] text-text-muted">
          Click an envelope to view its historical budget breakdown.
        </p>
      </div>
    </div>
  )
}

// ── Empty state ───────────────────────────────────────────────────────────────

function needsAmount(envelope: Envelope, budget: EnvelopeBudget): number {
  if (!envelope.target) return 0
  if (envelope.target.type === "savings_balance") {
    return Math.max(0, envelope.target.amount - budget.available)
  }
  return Math.max(0, envelope.target.amount - budget.assigned)
}

function EmptyState({
  readyToAssign,
  allItems,
  onAssign,
}: {
  readyToAssign: number
  allItems: { envelope: Envelope; budget: EnvelopeBudget }[]
  onAssign: (envelopeId: number, newAssigned: number) => Promise<void>
}) {
  const abs = Math.abs(readyToAssign)
  const isZero = abs < 1
  const isSurplus = readyToAssign > 0

  return (
    <div className="flex h-full flex-col">
      {/* RTA Header */}
      <div className="flex-shrink-0 border-b border-border px-4 py-4">
        <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-text-muted">
          Ready to assign
        </p>
        <p
          className={`font-heading text-2xl font-semibold tabular-nums ${
            isZero
              ? "text-text-muted"
              : isSurplus
                ? "text-brand-text"
                : "text-[color:var(--danger)]"
          }`}
        >
          {formatIDR(readyToAssign)}
        </p>
        <p className="mt-1 text-[11.5px] text-text-muted">
          {isZero
            ? "Every rupiah has a job."
            : isSurplus
              ? "Give this money a job."
              : `Assignments exceed balance by ${formatIDR(abs)}.`}
        </p>
      </div>

      {/* State body */}
      <div className="flex-1 overflow-y-auto">
        {isZero ? (
          <ZeroBody />
        ) : isSurplus ? (
          <SurplusBody readyToAssign={readyToAssign} allItems={allItems} onAssign={onAssign} />
        ) : (
          <DeficitBody deficit={abs} allItems={allItems} onAssign={onAssign} />
        )}
      </div>
    </div>
  )
}

// ── Zero state ────────────────────────────────────────────────────────────────

function ZeroBody() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
      <CheckCircle2 className="size-10 text-[color:var(--success)]" />
      <div>
        <p className="text-[13px] font-semibold text-text-primary">All set!</p>
        <p className="mt-0.5 text-[12px] text-text-muted">
          Every rupiah is assigned to an envelope.
        </p>
      </div>
    </div>
  )
}

// ── Surplus state ─────────────────────────────────────────────────────────────

function SurplusBody({
  readyToAssign,
  allItems,
  onAssign,
}: {
  readyToAssign: number
  allItems: { envelope: Envelope; budget: EnvelopeBudget }[]
  onAssign: (envelopeId: number, newAssigned: number) => Promise<void>
}) {
  const underfunded = allItems
    .filter((i) => !i.envelope.archived && needsAmount(i.envelope, i.budget) > 0)
    .sort((a, b) => needsAmount(b.envelope, b.budget) - needsAmount(a.envelope, a.budget))

  const totalNeeds = underfunded.reduce((s, i) => s + needsAmount(i.envelope, i.budget), 0)
  const canFundAll = underfunded.length > 0 && totalNeeds <= readyToAssign
  const [fundAllStatus, setFundAllStatus] = useState<"idle" | "loading" | "success" | "error">("idle")

  async function handleFundAll() {
    setFundAllStatus("loading")
    try {
      for (const item of underfunded) {
        const gap = needsAmount(item.envelope, item.budget)
        await onAssign(item.envelope.id, item.budget.assigned + gap)
      }
      setFundAllStatus("success")
      setTimeout(() => setFundAllStatus("idle"), 1500)
    } catch {
      setFundAllStatus("error")
      setTimeout(() => setFundAllStatus("idle"), 2000)
    }
  }

  return (
    <div className="px-4 py-4">
      {/* Fund all button */}
      {canFundAll && (
        <button
          onClick={handleFundAll}
          disabled={fundAllStatus === "loading"}
          className={`mb-4 flex w-full items-center justify-center gap-2 rounded-xl py-2.5 text-[12.5px] font-semibold transition-colors ${
            fundAllStatus === "success"
              ? "bg-[color:var(--success-light)] text-[color:var(--success)]"
              : fundAllStatus === "error"
                ? "bg-danger-light text-[color:var(--danger)]"
                : "bg-brand-light text-brand-text hover:brightness-95"
          }`}
        >
          {fundAllStatus === "loading" ? (
            <><Loader2 className="size-3.5 animate-spin" /> Funding…</>
          ) : fundAllStatus === "success" ? (
            <><Check className="size-3.5" /> Done!</>
          ) : fundAllStatus === "error" ? (
            "Failed — try again"
          ) : (
            `Fund all targets — ${formatIDR(totalNeeds)}`
          )}
        </button>
      )}

      <p className="mb-3 text-[10px] font-semibold uppercase tracking-wider text-text-muted">
        Needs funding {underfunded.length > 0 && `(${underfunded.length})`}
      </p>

      {underfunded.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-6 text-center">
          <CheckCircle2 className="size-8 text-[color:var(--success)]" />
          <p className="text-[12.5px] text-text-muted">All targets are funded</p>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {underfunded.map((item) => (
            <FundRow
              key={item.envelope.id}
              item={item}
              maxAssignable={readyToAssign}
              onAssign={onAssign}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function FundRow({
  item,
  maxAssignable,
  onAssign,
}: {
  item: { envelope: Envelope; budget: EnvelopeBudget }
  maxAssignable: number
  onAssign: (envelopeId: number, newAssigned: number) => Promise<void>
}) {
  const gap = needsAmount(item.envelope, item.budget)
  const suggested = Math.min(gap, maxAssignable)
  const [raw, setRaw] = useState(String(suggested))
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle")

  const delta = Math.max(0, Math.min(Number(raw) || 0, maxAssignable))
  const isPending = status === "loading"

  async function handleAssign() {
    if (delta <= 0 || isPending) return
    setStatus("loading")
    try {
      await onAssign(item.envelope.id, item.budget.assigned + delta)
      setStatus("success")
      setTimeout(() => setStatus("idle"), 1500)
    } catch {
      setStatus("error")
      setTimeout(() => setStatus("idle"), 2000)
    }
  }

  return (
    <div className="rounded-xl border border-border bg-bg-muted/40 px-3 py-2.5">
      <div className="mb-2 flex items-center gap-2">
        <span className="text-base leading-none">{item.envelope.icon}</span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-[12.5px] font-medium text-text-primary">
            {item.envelope.name}
          </p>
          <p className="text-[11px] text-text-muted">short {formatIDR(gap)}</p>
        </div>
      </div>
      <div className="flex gap-2">
        <input
          type="number"
          value={raw}
          onChange={(e) => setRaw(e.target.value)}
          disabled={isPending}
          className="h-8 flex-1 rounded-lg border border-border bg-card px-2 text-[12.5px] tabular-nums text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
        />
        <button
          onClick={handleAssign}
          disabled={isPending || delta <= 0}
          className={`flex min-w-[72px] items-center justify-center gap-1.5 rounded-lg px-3 text-[12px] font-semibold transition-colors ${
            status === "success"
              ? "bg-[color:var(--success-light)] text-[color:var(--success)]"
              : status === "error"
                ? "bg-danger-light text-[color:var(--danger)]"
                : isPending || delta <= 0
                  ? "cursor-not-allowed bg-bg-muted text-text-muted"
                  : "bg-brand-light text-brand-text hover:brightness-95"
          }`}
        >
          {status === "loading" ? (
            <Loader2 className="size-3.5 animate-spin" />
          ) : status === "success" ? (
            <><Check className="size-3.5" /> Done</>
          ) : status === "error" ? (
            "Failed"
          ) : (
            "Assign"
          )}
        </button>
      </div>
    </div>
  )
}

// ── Deficit state ─────────────────────────────────────────────────────────────

function DeficitBody({
  deficit,
  allItems,
  onAssign,
}: {
  deficit: number
  allItems: { envelope: Envelope; budget: EnvelopeBudget }[]
  onAssign: (envelopeId: number, newAssigned: number) => Promise<void>
}) {
  const assigned = allItems
    .filter((i) => !i.envelope.archived && i.budget.assigned > 0)
    .sort((a, b) => b.budget.assigned - a.budget.assigned)

  return (
    <div className="px-4 py-4">
      <div className="mb-4 rounded-xl border border-[color:var(--danger)]/20 bg-danger-light px-3 py-2.5">
        <p className="text-[12px] font-medium text-[color:var(--danger)]">
          Reduce assignments by {formatIDR(deficit)} to balance your budget.
        </p>
      </div>

      <p className="mb-3 text-[10px] font-semibold uppercase tracking-wider text-text-muted">
        Reduce from
      </p>

      <div className="flex flex-col gap-2">
        {assigned.map((item) => (
          <ReduceRow key={item.envelope.id} item={item} onAssign={onAssign} />
        ))}
      </div>
    </div>
  )
}

function ReduceRow({
  item,
  onAssign,
}: {
  item: { envelope: Envelope; budget: EnvelopeBudget }
  onAssign: (envelopeId: number, newAssigned: number) => Promise<void>
}) {
  const [raw, setRaw] = useState("")
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle")

  const delta = Math.max(0, Math.min(Number(raw) || 0, item.budget.assigned))
  const newAssigned = item.budget.assigned - delta
  const isPending = status === "loading"

  async function handleReduce() {
    if (delta <= 0 || isPending) return
    setStatus("loading")
    try {
      await onAssign(item.envelope.id, newAssigned)
      setStatus("success")
      setRaw("")
      setTimeout(() => setStatus("idle"), 1500)
    } catch {
      setStatus("error")
      setTimeout(() => setStatus("idle"), 2000)
    }
  }

  return (
    <div className="rounded-xl border border-border bg-bg-muted/40 px-3 py-2.5">
      <div className="mb-2 flex items-center gap-2">
        <span className="text-base leading-none">{item.envelope.icon}</span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-[12.5px] font-medium text-text-primary">
            {item.envelope.name}
          </p>
          <p className="text-[11px] text-text-muted">
            assigned {formatIDR(item.budget.assigned)}
          </p>
        </div>
      </div>
      <div className="flex gap-2">
        <input
          type="number"
          value={raw}
          onChange={(e) => setRaw(e.target.value)}
          disabled={isPending}
          placeholder="amount to remove"
          className="h-8 flex-1 rounded-lg border border-border bg-card px-2 text-[12.5px] tabular-nums text-text-primary placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
        />
        <button
          onClick={handleReduce}
          disabled={isPending || delta <= 0}
          className={`flex min-w-[72px] items-center justify-center gap-1.5 rounded-lg px-3 text-[12px] font-semibold transition-colors ${
            status === "success"
              ? "bg-[color:var(--success-light)] text-[color:var(--success)]"
              : status === "error"
                ? "bg-danger-light text-[color:var(--danger)]"
                : isPending || delta <= 0
                  ? "cursor-not-allowed bg-bg-muted text-text-muted"
                  : "bg-danger-light text-[color:var(--danger)] hover:brightness-95"
          }`}
        >
          {status === "loading" ? (
            <Loader2 className="size-3.5 animate-spin" />
          ) : status === "success" ? (
            <><Check className="size-3.5" /> Done</>
          ) : status === "error" ? (
            "Failed"
          ) : (
            "Reduce"
          )}
        </button>
      </div>
    </div>
  )
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function BudgetLine({
  label,
  value,
  muted,
  danger,
}: {
  label: string
  value: number
  muted?: boolean
  danger?: boolean
}) {
  return (
    <div className="flex items-center justify-between">
      <span className={`text-[12.5px] ${muted ? "text-text-muted" : "text-text-secondary"}`}>
        {label}
      </span>
      <span
        className={`text-[12.5px] font-medium tabular-nums ${
          danger
            ? "text-[color:var(--danger)]"
            : muted
              ? "text-text-muted"
              : "text-text-primary"
        }`}
      >
        {formatIDR(value)}
      </span>
    </div>
  )
}

