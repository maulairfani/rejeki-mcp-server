import { useMemo, useState } from "react"
import { Check, Loader2 } from "lucide-react"
import { useCreateEnvelope, useEnvelopes } from "@/hooks/useEnvelopes"
import { currentPeriod } from "@/components/shared/PeriodPicker"

export function AddEnvelopeForm({ onSuccess }: { onSuccess: () => void }) {
  const createMutation = useCreateEnvelope(currentPeriod())
  const { groups } = useEnvelopes(currentPeriod(), { includeArchived: false })

  const [name, setName] = useState("")
  const [icon, setIcon] = useState("📦")
  const [groupId, setGroupId] = useState<string>("")
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle")

  const realGroups = useMemo(
    () => groups.filter((g) => g.group.id !== null),
    [groups]
  )

  const isPending = status === "loading"
  const canSubmit = !!name.trim()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!canSubmit) return
    setStatus("loading")
    try {
      await createMutation.mutateAsync({
        name: name.trim(),
        icon: icon.trim() || "📦",
        type: "expense",
        group_id: groupId ? Number(groupId) : null,
      })
      setStatus("success")
      setTimeout(() => {
        setStatus("idle")
        setName("")
        setIcon("📦")
        setGroupId("")
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
          placeholder="Groceries, Coffee, Rent…"
          className="h-10 w-full rounded-xl border border-border bg-bg-muted px-3 text-[13.5px] text-text-primary placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
        />
      </div>

      <div>
        <label className="mb-1 block text-[11px] font-medium text-text-muted">Icon</label>
        <input
          type="text"
          value={icon}
          onChange={(e) => setIcon(e.target.value)}
          disabled={isPending}
          maxLength={4}
          placeholder="📦"
          className="h-10 w-20 rounded-xl border border-border bg-bg-muted px-3 text-center text-[16px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
        />
        <p className="mt-1 text-[11px] text-text-muted">Paste any emoji.</p>
      </div>

      <div>
        <label className="mb-1 block text-[11px] font-medium text-text-muted">Group</label>
        <select
          value={groupId}
          onChange={(e) => setGroupId(e.target.value)}
          disabled={isPending}
          className="h-10 w-full rounded-xl border border-border bg-bg-muted px-3 text-[13px] text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
        >
          <option value="">Uncategorized</option>
          {realGroups.map((g) => (
            <option key={g.group.id!} value={String(g.group.id)}>
              {g.group.name}
            </option>
          ))}
        </select>
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
          "Create envelope"
        )}
      </button>
    </form>
  )
}
