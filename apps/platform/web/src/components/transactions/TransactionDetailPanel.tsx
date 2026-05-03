import { useEffect, useState } from "react"
import { Check, Loader2, Trash2, X } from "lucide-react"
import { formatIDR } from "@/lib/format"
import {
  useEditTransaction,
  useDeleteTransaction,
  type Transaction,
} from "@/hooks/useTransactions"
import { useTags, useUpdateTransactionTags } from "@/hooks/useTags"
import { useEnvelopes } from "@/hooks/useEnvelopes"
import { Input } from "@/components/ui/input"

const TYPE_LABEL: Record<Transaction["type"], string> = {
  income: "Income",
  expense: "Expense",
  transfer: "Transfer",
}

const TYPE_COLOR: Record<Transaction["type"], string> = {
  income: "text-[color:var(--success)]",
  expense: "text-[color:var(--danger)]",
  transfer: "text-text-secondary",
}

interface TransactionDetailPanelProps {
  transaction: Transaction | null
  period: string
  onClose: () => void
  onDeleted: () => void
  // empty state
  filteredIncome: number
  filteredExpense: number
  filteredCount: number
}

export function TransactionDetailPanel({
  transaction,
  period,
  onClose,
  onDeleted,
  filteredIncome,
  filteredExpense,
  filteredCount,
}: TransactionDetailPanelProps) {
  if (!transaction) {
    return (
      <EmptyState
        income={filteredIncome}
        expense={filteredExpense}
        count={filteredCount}
      />
    )
  }

  return (
    <SelectedState
      key={transaction.id}
      transaction={transaction}
      period={period}
      onClose={onClose}
      onDeleted={onDeleted}
    />
  )
}

// ── Empty state ───────────────────────────────────────────────────────────────

function EmptyState({
  income,
  expense,
  count,
}: {
  income: number
  expense: number
  count: number
}) {
  const net = income - expense

  return (
    <div className="flex h-full flex-col px-4 py-5">
      <p className="mb-4 text-[10px] font-semibold uppercase tracking-wider text-text-muted">
        Summary
      </p>

      <div className="flex flex-col gap-3">
        <SummaryLine label="Income" value={income} color="text-[color:var(--success)]" />
        <SummaryLine label="Expense" value={-expense} color="text-[color:var(--danger)]" />
        <div className="border-t border-border pt-3">
          <SummaryLine
            label="Net"
            value={net}
            color={net >= 0 ? "text-[color:var(--success)]" : "text-[color:var(--danger)]"}
            bold
          />
        </div>
      </div>

      <p className="mt-4 text-[11.5px] text-text-muted">
        {count === 0
          ? "No transactions match the current filters."
          : `${count} transaction${count !== 1 ? "s" : ""} shown.`}
      </p>

      <div className="mt-auto pt-6 text-center">
        <p className="text-[11.5px] text-text-muted">Click a transaction to view details.</p>
      </div>
    </div>
  )
}

function SummaryLine({
  label,
  value,
  color,
  bold,
}: {
  label: string
  value: number
  color: string
  bold?: boolean
}) {
  return (
    <div className="flex items-center justify-between">
      <span className={`text-[12.5px] ${bold ? "font-semibold text-text-primary" : "text-text-secondary"}`}>
        {label}
      </span>
      <span className={`font-heading text-[15px] font-semibold tabular-nums ${color}`}>
        {formatIDR(value)}
      </span>
    </div>
  )
}

// ── Selected state ────────────────────────────────────────────────────────────

function SelectedState({
  transaction,
  period,
  onClose,
  onDeleted,
}: {
  transaction: Transaction
  period: string
  onClose: () => void
  onDeleted: () => void
}) {
  const dateLabel = new Date(transaction.date + "T00:00:00").toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  })

  const payee =
    transaction.type === "transfer"
      ? `${transaction.account} → ${transaction.toAccount ?? "—"}`
      : transaction.payee ?? "—"

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex flex-shrink-0 items-start gap-2.5 border-b border-border px-4 py-3.5">
        <div className="min-w-0 flex-1">
          <p className="truncate text-[13px] font-semibold text-text-primary">{payee}</p>
          <p className="mt-0.5 text-[11.5px] text-text-muted">
            {dateLabel} · {TYPE_LABEL[transaction.type]}
          </p>
        </div>
        <button
          onClick={onClose}
          className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-md text-text-muted transition-colors hover:bg-bg-muted hover:text-text-secondary"
        >
          <X className="size-3.5" />
        </button>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto">
        {/* Amount highlight */}
        <div className="px-4 pt-4">
          <div className="flex items-center justify-between rounded-xl bg-bg-muted px-4 py-3">
            <span className="text-[12.5px] text-text-secondary">Amount</span>
            <span
              className={`font-heading text-xl font-semibold tabular-nums ${TYPE_COLOR[transaction.type]}`}
            >
              {transaction.type === "expense" ? "-" : ""}
              {formatIDR(transaction.amount)}
            </span>
          </div>
        </div>

        {/* Edit form */}
        {transaction.type !== "transfer" ? (
          <EditForm transaction={transaction} period={period} />
        ) : (
          <TransferDetail transaction={transaction} />
        )}

        {/* Tags */}
        <div className="border-t border-border px-4 py-4">
          <p className="mb-2.5 text-[10px] font-semibold uppercase tracking-wider text-text-muted">
            Tags
          </p>
          <TagEditor transaction={transaction} />
        </div>

        {/* Delete */}
        <div className="border-t border-border px-4 py-4">
          <DeleteButton
            transactionId={transaction.id}
            period={period}
            onDeleted={onDeleted}
          />
        </div>
      </div>
    </div>
  )
}

// ── Transfer read-only detail ─────────────────────────────────────────────────

function TransferDetail({ transaction }: { transaction: Transaction }) {
  return (
    <div className="px-4 py-4">
      <div className="flex flex-col gap-2">
        <DetailLine label="From" value={transaction.account} />
        <DetailLine label="To" value={transaction.toAccount ?? "—"} />
        <DetailLine label="Date" value={transaction.date} />
        {transaction.memo && <DetailLine label="Memo" value={transaction.memo} />}
      </div>
    </div>
  )
}

function DetailLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-[12.5px] text-text-secondary">{label}</span>
      <span className="text-[12.5px] font-medium text-text-primary">{value}</span>
    </div>
  )
}

// ── Edit form ─────────────────────────────────────────────────────────────────

function EditForm({
  transaction,
  period,
}: {
  transaction: Transaction
  period: string
}) {
  const editMutation = useEditTransaction(period)
  const { allEnvelopes } = useEnvelopes(period)

  const [payee, setPayee] = useState(transaction.payee ?? "")
  const [memo, setMemo] = useState(transaction.memo ?? "")
  const [amountRaw, setAmountRaw] = useState(String(transaction.amount))
  const [date, setDate] = useState(transaction.date)
  const [envelopeId, setEnvelopeId] = useState<string>(
    transaction.envelopeId != null ? String(transaction.envelopeId) : ""
  )
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle")

  useEffect(() => {
    setPayee(transaction.payee ?? "")
    setMemo(transaction.memo ?? "")
    setAmountRaw(String(transaction.amount))
    setDate(transaction.date)
    setEnvelopeId(transaction.envelopeId != null ? String(transaction.envelopeId) : "")
    setStatus("idle")
  }, [transaction.id])

  const isPending = status === "loading"
  const expenseEnvelopes = allEnvelopes.filter((e) => !e.envelope.archived)

  async function handleSave() {
    if (isPending) return
    setStatus("loading")
    try {
      const selectedEnvId = envelopeId === "" ? null : Number(envelopeId)
      await editMutation.mutateAsync({
        id: transaction.id,
        amount: Number(amountRaw) || transaction.amount,
        payee: payee || null,
        memo: memo || null,
        date,
        envelope_id: selectedEnvId ?? undefined,
        clear_envelope: selectedEnvId === null && transaction.envelopeId !== null,
      })
      setStatus("success")
      setTimeout(() => setStatus("idle"), 1500)
    } catch {
      setStatus("error")
      setTimeout(() => setStatus("idle"), 2000)
    }
  }

  return (
    <div className="px-4 py-4">
      <p className="mb-3 text-[10px] font-semibold uppercase tracking-wider text-text-muted">
        Edit
      </p>
      <div className="flex flex-col gap-2.5">
        {/* Payee */}
        <div>
          <label className="text-[11px] text-text-muted">Payee</label>
          <input
            type="text"
            value={payee}
            onChange={(e) => setPayee(e.target.value)}
            disabled={isPending}
            placeholder="—"
            className="mt-0.5 h-8 w-full rounded-lg border border-border bg-bg-muted px-2 text-[12.5px] text-text-primary placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
          />
        </div>

        {/* Amount */}
        <div>
          <label className="text-[11px] text-text-muted">Amount (IDR)</label>
          <input
            type="number"
            value={amountRaw}
            onChange={(e) => setAmountRaw(e.target.value)}
            disabled={isPending}
            className="mt-0.5 h-8 w-full rounded-lg border border-border bg-bg-muted px-2 text-[12.5px] tabular-nums text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
          />
        </div>

        {/* Date */}
        <div>
          <label className="text-[11px] text-text-muted">Date</label>
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            disabled={isPending}
            className="mt-0.5 h-8 w-full rounded-lg border border-border bg-bg-muted px-2 text-[12.5px] text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
          />
        </div>

        {/* Envelope */}
        <div>
          <label className="text-[11px] text-text-muted">Envelope</label>
          <select
            value={envelopeId}
            onChange={(e) => setEnvelopeId(e.target.value)}
            disabled={isPending}
            className="mt-0.5 h-8 w-full rounded-lg border border-border bg-bg-muted px-2 text-[12.5px] text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
          >
            <option value="">— None —</option>
            {expenseEnvelopes.map(({ envelope }) => (
              <option key={envelope.id} value={String(envelope.id)}>
                {envelope.icon} {envelope.name}
              </option>
            ))}
          </select>
        </div>

        {/* Memo */}
        <div>
          <label className="text-[11px] text-text-muted">Memo</label>
          <input
            type="text"
            value={memo}
            onChange={(e) => setMemo(e.target.value)}
            disabled={isPending}
            placeholder="—"
            className="mt-0.5 h-8 w-full rounded-lg border border-border bg-bg-muted px-2 text-[12.5px] text-text-primary placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
          />
        </div>

        {/* Save */}
        <button
          onClick={handleSave}
          disabled={isPending}
          className={`mt-1 flex items-center justify-center gap-1.5 rounded-lg py-2 text-[12px] font-semibold transition-colors ${
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

// ── Tag editor ────────────────────────────────────────────────────────────────

function TagEditor({ transaction }: { transaction: Transaction }) {
  const { tags: allTags } = useTags()
  const update = useUpdateTransactionTags()
  const [tags, setTags] = useState<string[]>(transaction.tags)
  const [draft, setDraft] = useState("")
  const [showSuggestions, setShowSuggestions] = useState(false)

  useEffect(() => {
    setTags(transaction.tags)
  }, [transaction.id, transaction.tags])

  const commit = (next: string[]) => {
    setTags(next)
    update.mutate({ transactionId: transaction.id, tags: next })
  }

  const addTag = (raw: string) => {
    const name = raw.trim()
    if (!name) return
    if (tags.some((t) => t.toLowerCase() === name.toLowerCase())) {
      setDraft("")
      return
    }
    commit([...tags, name])
    setDraft("")
  }

  const removeTag = (name: string) => commit(tags.filter((t) => t !== name))

  const draftLower = draft.trim().toLowerCase()
  const suggestions = allTags
    .map((t) => t.name)
    .filter(
      (name) =>
        (!draftLower || name.toLowerCase().includes(draftLower)) &&
        !tags.some((t) => t.toLowerCase() === name.toLowerCase())
    )
    .slice(0, 8)

  return (
    <div>
      <div className="mb-2 flex flex-wrap gap-1.5">
        {tags.length === 0 ? (
          <span className="text-[12px] text-text-muted">No tags yet</span>
        ) : (
          tags.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center gap-1 rounded-full bg-brand-light px-2 py-0.5 text-[11px] font-semibold text-brand-text"
            >
              #{tag}
              <button
                type="button"
                onClick={() => removeTag(tag)}
                className="text-brand-text/70 transition-colors hover:text-brand-text"
              >
                <X className="size-3" />
              </button>
            </span>
          ))
        )}
      </div>
      <div className="relative">
        <Input
          value={draft}
          onChange={(e) => { setDraft(e.target.value); setShowSuggestions(true) }}
          onFocus={() => setShowSuggestions(true)}
          onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === ",") { e.preventDefault(); addTag(draft) }
            else if (e.key === "Backspace" && !draft && tags.length) removeTag(tags[tags.length - 1])
          }}
          placeholder="Add tag…"
          className="h-8 text-[12.5px]"
        />
        {showSuggestions && suggestions.length > 0 && (
          <div className="absolute left-0 right-0 top-full z-10 mt-1 max-h-44 overflow-y-auto rounded-md border bg-popover shadow-md">
            {suggestions.map((name) => (
              <button
                key={name}
                type="button"
                onMouseDown={(e) => { e.preventDefault(); addTag(name) }}
                className="block w-full px-2.5 py-1.5 text-left text-[12px] hover:bg-muted"
              >
                #{name}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Delete button ─────────────────────────────────────────────────────────────

function DeleteButton({
  transactionId,
  period,
  onDeleted,
}: {
  transactionId: number
  period: string
  onDeleted: () => void
}) {
  const deleteMutation = useDeleteTransaction(period)
  const [confirming, setConfirming] = useState(false)
  const [status, setStatus] = useState<"idle" | "loading">("idle")

  async function handleDelete() {
    setStatus("loading")
    try {
      await deleteMutation.mutateAsync(transactionId)
      onDeleted()
    } catch {
      setStatus("idle")
    }
  }

  if (confirming) {
    return (
      <div className="flex gap-2">
        <button
          onClick={handleDelete}
          disabled={status === "loading"}
          className="flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2 text-[12px] font-semibold bg-[color:var(--danger)] text-white transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {status === "loading" ? <Loader2 className="size-3.5 animate-spin" /> : "Yes, delete"}
        </button>
        <button
          onClick={() => setConfirming(false)}
          className="flex-1 rounded-lg py-2 text-[12px] font-semibold bg-bg-muted text-text-secondary hover:brightness-95"
        >
          Cancel
        </button>
      </div>
    )
  }

  return (
    <button
      onClick={() => setConfirming(true)}
      className="flex w-full items-center justify-center gap-1.5 rounded-lg py-2 text-[12px] font-semibold text-[color:var(--danger)] bg-danger-light transition-colors hover:brightness-95"
    >
      <Trash2 className="size-3.5" />
      Delete transaction
    </button>
  )
}
