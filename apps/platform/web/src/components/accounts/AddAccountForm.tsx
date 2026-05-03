import { useState } from "react"
import { Check, Loader2 } from "lucide-react"
import { useCreateAccount, type AccountType } from "@/hooks/useAccounts"

const TYPES: { value: AccountType; label: string }[] = [
  { value: "bank", label: "Bank" },
  { value: "ewallet", label: "E-wallet" },
  { value: "cash", label: "Cash" },
]

export function AddAccountForm({ onSuccess }: { onSuccess: () => void }) {
  const createMutation = useCreateAccount()

  const [name, setName] = useState("")
  const [type, setType] = useState<AccountType>("bank")
  const [balanceRaw, setBalanceRaw] = useState("")
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle")

  const isPending = status === "loading"
  const canSubmit = !!name.trim()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!canSubmit) return
    setStatus("loading")
    try {
      await createMutation.mutateAsync({
        name: name.trim(),
        type,
        balance: Number(balanceRaw) || 0,
      })
      setStatus("success")
      setTimeout(() => {
        setStatus("idle")
        setName("")
        setBalanceRaw("")
        setType("bank")
        onSuccess()
      }, 700)
    } catch {
      setStatus("error")
      setTimeout(() => setStatus("idle"), 2000)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4 pt-4">
      <div>
        <label className="mb-1 block text-[11px] font-medium text-text-muted">
          Name <span className="text-[color:var(--danger)]">*</span>
        </label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={isPending}
          placeholder="GoPay, Blu, Cash…"
          className="h-10 w-full rounded-xl border border-border bg-bg-muted px-3 text-[13.5px] text-text-primary placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
        />
      </div>

      <div>
        <label className="mb-1 block text-[11px] font-medium text-text-muted">Type</label>
        <div className="flex rounded-xl border border-border bg-bg-muted p-1">
          {TYPES.map((t) => (
            <button
              key={t.value}
              type="button"
              onClick={() => setType(t.value)}
              className={`flex-1 rounded-lg py-1.5 text-[12.5px] font-semibold transition-colors ${
                type === t.value
                  ? "bg-card text-text-primary shadow-sm"
                  : "text-text-muted hover:text-text-secondary"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="mb-1 block text-[11px] font-medium text-text-muted">
          Starting balance (IDR)
        </label>
        <input
          type="number"
          value={balanceRaw}
          onChange={(e) => setBalanceRaw(e.target.value)}
          disabled={isPending}
          placeholder="0"
          className="h-10 w-full rounded-xl border border-border bg-bg-muted px-3 text-[13.5px] tabular-nums text-text-primary placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
        />
      </div>

      <button
        type="submit"
        disabled={isPending || !canSubmit}
        className={`mt-2 flex items-center justify-center gap-2 rounded-xl py-3 text-[13px] font-semibold transition-colors ${
          status === "success"
            ? "bg-[color:var(--success-light)] text-[color:var(--success)]"
            : status === "error"
              ? "bg-danger-light text-[color:var(--danger)]"
              : !canSubmit || isPending
                ? "cursor-not-allowed bg-bg-muted text-text-muted"
                : "bg-brand-text text-white hover:opacity-90"
        }`}
      >
        {status === "loading" ? (
          <><Loader2 className="size-4 animate-spin" /> Creating…</>
        ) : status === "success" ? (
          <><Check className="size-4" /> Created!</>
        ) : status === "error" ? (
          "Failed — try again"
        ) : (
          "Create account"
        )}
      </button>
    </form>
  )
}
