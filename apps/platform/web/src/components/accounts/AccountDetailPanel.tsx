import { useEffect, useState } from "react"
import { Check, Loader2, Plus, Trash2, X } from "lucide-react"
import { formatIDR } from "@/lib/format"
import {
  useCreateAccount,
  useEditAccount,
  useUpdateAccountBalance,
  useDeleteAccount,
  useAccountTransactions,
  type Account,
  type AccountType,
  type AccountTypeGroup,
} from "@/hooks/useAccounts"

const TYPE_LABELS: Record<AccountType, string> = {
  bank: "Bank Account",
  ewallet: "E-Wallet",
  cash: "Cash",
}

const ACCOUNT_TYPES: { value: AccountType; label: string }[] = [
  { value: "bank", label: "Bank Account" },
  { value: "ewallet", label: "E-Wallet" },
  { value: "cash", label: "Cash" },
]

interface AccountDetailPanelProps {
  account: Account | null
  groups: AccountTypeGroup[]
  totalBalance: number
  showNominal: boolean
  onClose: () => void
  onDeleted: () => void
}

export function AccountDetailPanel({
  account,
  groups,
  totalBalance,
  showNominal,
  onClose,
  onDeleted,
}: AccountDetailPanelProps) {
  if (!account) {
    return <EmptyState groups={groups} totalBalance={totalBalance} showNominal={showNominal} />
  }

  return (
    <SelectedState
      key={account.id}
      account={account}
      showNominal={showNominal}
      onClose={onClose}
      onDeleted={onDeleted}
    />
  )
}

// ── Empty state ───────────────────────────────────────────────────────────────

function EmptyState({
  groups,
  totalBalance,
  showNominal,
}: {
  groups: AccountTypeGroup[]
  totalBalance: number
  showNominal: boolean
}) {
  const [showAddForm, setShowAddForm] = useState(false)

  return (
    <div className="flex h-full flex-col px-4 py-5">
      <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-text-muted">
        Net worth
      </p>
      <p className="mb-5 font-heading text-2xl font-semibold tabular-nums text-text-primary">
        {showNominal ? formatIDR(totalBalance) : "••••••"}
      </p>

      {/* Balance by type */}
      <div className="mb-5 flex flex-col gap-2.5">
        {groups.map((g) => (
          <div key={g.type} className="flex items-center justify-between">
            <span className="text-[12.5px] text-text-secondary">{g.label}</span>
            <span className="text-[12.5px] font-medium tabular-nums text-text-primary">
              {showNominal ? formatIDR(g.totalBalance) : "••••"}
            </span>
          </div>
        ))}
      </div>

      <div className="border-t border-border pt-4">
        {showAddForm ? (
          <AddAccountForm onDone={() => setShowAddForm(false)} />
        ) : (
          <button
            onClick={() => setShowAddForm(true)}
            className="flex w-full items-center justify-center gap-1.5 rounded-xl border border-dashed border-border py-2.5 text-[12.5px] font-medium text-text-muted transition-colors hover:border-brand-text/40 hover:text-brand-text"
          >
            <Plus className="size-3.5" />
            Add account
          </button>
        )}
      </div>
    </div>
  )
}

// ── Add account form ──────────────────────────────────────────────────────────

function AddAccountForm({ onDone }: { onDone: () => void }) {
  const createMutation = useCreateAccount()
  const [name, setName] = useState("")
  const [type, setType] = useState<AccountType>("bank")
  const [balanceRaw, setBalanceRaw] = useState("0")
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle")

  const isPending = status === "loading"

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    setStatus("loading")
    try {
      await createMutation.mutateAsync({ name: name.trim(), type, balance: Number(balanceRaw) || 0 })
      setStatus("success")
      setTimeout(() => { setStatus("idle"); onDone() }, 800)
    } catch {
      setStatus("error")
      setTimeout(() => setStatus("idle"), 2000)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-2.5">
      <p className="text-[11px] font-semibold uppercase tracking-wider text-text-muted">
        New account
      </p>

      <input
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
        disabled={isPending}
        placeholder="Account name"
        autoFocus
        className="h-8 rounded-lg border border-border bg-bg-muted px-2 text-[12.5px] text-text-primary placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
      />

      <select
        value={type}
        onChange={(e) => setType(e.target.value as AccountType)}
        disabled={isPending}
        className="h-8 rounded-lg border border-border bg-bg-muted px-2 text-[12.5px] text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
      >
        {ACCOUNT_TYPES.map((t) => (
          <option key={t.value} value={t.value}>{t.label}</option>
        ))}
      </select>

      <div>
        <label className="text-[11px] text-text-muted">Starting balance (IDR)</label>
        <input
          type="number"
          value={balanceRaw}
          onChange={(e) => setBalanceRaw(e.target.value)}
          disabled={isPending}
          className="mt-0.5 h-8 w-full rounded-lg border border-border bg-bg-muted px-2 text-[12.5px] tabular-nums text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
        />
      </div>

      <div className="flex gap-2 pt-1">
        <button
          type="submit"
          disabled={isPending || !name.trim()}
          className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2 text-[12px] font-semibold transition-colors ${
            status === "success"
              ? "bg-[color:var(--success-light)] text-[color:var(--success)]"
              : status === "error"
                ? "bg-danger-light text-[color:var(--danger)]"
                : !name.trim() || isPending
                  ? "cursor-not-allowed bg-bg-muted text-text-muted"
                  : "bg-brand-light text-brand-text hover:brightness-95"
          }`}
        >
          {status === "loading" ? <Loader2 className="size-3.5 animate-spin" /> :
           status === "success" ? <><Check className="size-3.5" /> Saved</> :
           status === "error" ? "Failed" : "Save"}
        </button>
        <button
          type="button"
          onClick={onDone}
          disabled={isPending}
          className="flex-1 rounded-lg py-2 text-[12px] font-semibold bg-bg-muted text-text-secondary hover:brightness-95"
        >
          Cancel
        </button>
      </div>
    </form>
  )
}

// ── Selected state ────────────────────────────────────────────────────────────

function SelectedState({
  account,
  showNominal,
  onClose,
  onDeleted,
}: {
  account: Account
  showNominal: boolean
  onClose: () => void
  onDeleted: () => void
}) {
  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex flex-shrink-0 items-center gap-2.5 border-b border-border px-4 py-3.5">
        <div className="min-w-0 flex-1">
          <p className="truncate text-[13px] font-semibold text-text-primary">{account.name}</p>
          <p className="text-[11.5px] text-text-muted">{TYPE_LABELS[account.type]}</p>
        </div>
        <button
          onClick={onClose}
          className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-md text-text-muted transition-colors hover:bg-bg-muted hover:text-text-secondary"
        >
          <X className="size-3.5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* Balance */}
        <div className="px-4 pt-4">
          <div className="flex items-center justify-between rounded-xl bg-bg-muted px-4 py-3">
            <span className="text-[12.5px] text-text-secondary">Balance</span>
            <span className={`font-heading text-xl font-semibold tabular-nums ${
              account.balance < 0 ? "text-[color:var(--danger)]" : "text-[color:var(--success)]"
            }`}>
              {showNominal ? formatIDR(account.balance) : "••••••"}
            </span>
          </div>
        </div>

        {/* Reconcile */}
        <div className="border-t border-border px-4 py-4 mt-4">
          <ReconcileForm account={account} />
        </div>

        {/* Recent transactions */}
        <div className="border-t border-border px-4 py-4">
          <RecentTransactions accountId={account.id} showNominal={showNominal} />
        </div>

        {/* Edit */}
        <div className="border-t border-border px-4 py-4">
          <EditAccountForm account={account} />
        </div>

        {/* Delete */}
        <div className="border-t border-border px-4 py-4">
          <DeleteAccountButton accountId={account.id} onDeleted={onDeleted} />
        </div>
      </div>
    </div>
  )
}

// ── Reconcile form ────────────────────────────────────────────────────────────

function ReconcileForm({ account }: { account: Account }) {
  const mutation = useUpdateAccountBalance()
  const [raw, setRaw] = useState(String(account.balance))
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle")

  useEffect(() => {
    setRaw(String(account.balance))
    setStatus("idle")
  }, [account.id, account.balance])

  const isPending = status === "loading"
  const newBalance = Number(raw) ?? account.balance
  const unchanged = newBalance === account.balance

  async function handleSave() {
    if (isPending || unchanged) return
    setStatus("loading")
    try {
      await mutation.mutateAsync({ id: account.id, balance: newBalance })
      setStatus("success")
      setTimeout(() => setStatus("idle"), 1500)
    } catch {
      setStatus("error")
      setTimeout(() => setStatus("idle"), 2000)
    }
  }

  return (
    <div>
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-text-muted">
        Reconcile balance
      </p>
      <div className="flex gap-2">
        <input
          type="number"
          value={raw}
          onChange={(e) => setRaw(e.target.value)}
          disabled={isPending}
          className="h-8 flex-1 rounded-lg border border-border bg-bg-muted px-2 text-[12.5px] tabular-nums text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
        />
        <button
          onClick={handleSave}
          disabled={isPending || unchanged}
          className={`flex min-w-[64px] items-center justify-center gap-1.5 rounded-lg px-3 text-[12px] font-semibold transition-colors ${
            status === "success"
              ? "bg-[color:var(--success-light)] text-[color:var(--success)]"
              : status === "error"
                ? "bg-danger-light text-[color:var(--danger)]"
                : isPending || unchanged
                  ? "cursor-not-allowed bg-bg-muted text-text-muted"
                  : "bg-brand-light text-brand-text hover:brightness-95"
          }`}
        >
          {status === "loading" ? <Loader2 className="size-3.5 animate-spin" /> :
           status === "success" ? <><Check className="size-3.5" /> Saved</> :
           status === "error" ? "Error" : "Save"}
        </button>
      </div>
    </div>
  )
}

// ── Recent transactions ───────────────────────────────────────────────────────

function RecentTransactions({
  accountId,
  showNominal,
}: {
  accountId: number
  showNominal: boolean
}) {
  const { transactions, isLoading } = useAccountTransactions(accountId)

  return (
    <div>
      <p className="mb-2.5 text-[10px] font-semibold uppercase tracking-wider text-text-muted">
        Recent transactions
      </p>
      {isLoading ? (
        <div className="flex justify-center py-4">
          <Loader2 className="size-4 animate-spin text-text-muted" />
        </div>
      ) : transactions.length === 0 ? (
        <p className="text-[12px] text-text-muted">No transactions yet.</p>
      ) : (
        <div className="flex flex-col gap-1.5">
          {transactions.map((t) => {
            const label =
              t.type === "transfer"
                ? `→ ${t.toAccount ?? "?"}`
                : t.payee ?? t.memo ?? "—"
            const sign = t.type === "expense" ? -1 : 1
            return (
              <div key={t.id} className="flex items-center justify-between gap-2 py-0.5">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[12px] font-medium text-text-primary">{label}</p>
                  <p className="text-[11px] text-text-muted">{t.date}</p>
                </div>
                <span className={`shrink-0 text-[12px] font-semibold tabular-nums ${
                  t.type === "expense"
                    ? "text-[color:var(--danger)]"
                    : t.type === "income"
                      ? "text-[color:var(--success)]"
                      : "text-text-secondary"
                }`}>
                  {showNominal ? `${sign < 0 ? "-" : "+"}${formatIDR(t.amount)}` : "••••"}
                </span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ── Edit account form ─────────────────────────────────────────────────────────

function EditAccountForm({ account }: { account: Account }) {
  const mutation = useEditAccount()
  const [name, setName] = useState(account.name)
  const [type, setType] = useState<AccountType>(account.type)
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle")

  useEffect(() => {
    setName(account.name)
    setType(account.type)
    setStatus("idle")
  }, [account.id])

  const isPending = status === "loading"
  const unchanged = name === account.name && type === account.type

  async function handleSave() {
    if (isPending || unchanged || !name.trim()) return
    setStatus("loading")
    try {
      await mutation.mutateAsync({ id: account.id, name: name.trim(), type })
      setStatus("success")
      setTimeout(() => setStatus("idle"), 1500)
    } catch {
      setStatus("error")
      setTimeout(() => setStatus("idle"), 2000)
    }
  }

  return (
    <div>
      <p className="mb-2.5 text-[10px] font-semibold uppercase tracking-wider text-text-muted">
        Edit
      </p>
      <div className="flex flex-col gap-2">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={isPending}
          className="h-8 rounded-lg border border-border bg-bg-muted px-2 text-[12.5px] text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
        />
        <select
          value={type}
          onChange={(e) => setType(e.target.value as AccountType)}
          disabled={isPending}
          className="h-8 rounded-lg border border-border bg-bg-muted px-2 text-[12.5px] text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
        >
          {ACCOUNT_TYPES.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>
        <button
          onClick={handleSave}
          disabled={isPending || unchanged || !name.trim()}
          className={`flex items-center justify-center gap-1.5 rounded-lg py-2 text-[12px] font-semibold transition-colors ${
            status === "success"
              ? "bg-[color:var(--success-light)] text-[color:var(--success)]"
              : status === "error"
                ? "bg-danger-light text-[color:var(--danger)]"
                : isPending || unchanged
                  ? "cursor-not-allowed bg-bg-muted text-text-muted"
                  : "bg-brand-light text-brand-text hover:brightness-95"
          }`}
        >
          {status === "loading" ? <><Loader2 className="size-3.5 animate-spin" /> Saving…</> :
           status === "success" ? <><Check className="size-3.5" /> Saved</> :
           status === "error" ? "Failed — try again" : "Save"}
        </button>
      </div>
    </div>
  )
}

// ── Delete button ─────────────────────────────────────────────────────────────

function DeleteAccountButton({
  accountId,
  onDeleted,
}: {
  accountId: number
  onDeleted: () => void
}) {
  const mutation = useDeleteAccount()
  const [confirming, setConfirming] = useState(false)
  const [status, setStatus] = useState<"idle" | "loading">("idle")

  async function handleDelete() {
    setStatus("loading")
    try {
      await mutation.mutateAsync(accountId)
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
          className="flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2 text-[12px] font-semibold bg-[color:var(--danger)] text-white hover:opacity-90 disabled:opacity-50"
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
      className="flex w-full items-center justify-center gap-1.5 rounded-lg py-2 text-[12px] font-semibold text-[color:var(--danger)] bg-danger-light hover:brightness-95"
    >
      <Trash2 className="size-3.5" />
      Delete account
    </button>
  )
}
