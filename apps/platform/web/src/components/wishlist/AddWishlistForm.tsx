import { useState } from "react"
import { Check, Loader2 } from "lucide-react"
import { useCreateWishlistItem, type Priority } from "@/hooks/useWishlist"

const PRIORITIES: { value: Priority; label: string }[] = [
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
]

export function AddWishlistForm({ onSuccess }: { onSuccess: () => void }) {
  const createMutation = useCreateWishlistItem()

  const [name, setName] = useState("")
  const [icon, setIcon] = useState("🎁")
  const [priceRaw, setPriceRaw] = useState("")
  const [priority, setPriority] = useState<Priority>("medium")
  const [url, setUrl] = useState("")
  const [notes, setNotes] = useState("")
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
        icon: icon.trim() || "🎁",
        price: priceRaw ? Number(priceRaw) : null,
        priority,
        url: url.trim() || null,
        notes: notes.trim() || null,
      })
      setStatus("success")
      setTimeout(() => {
        setStatus("idle")
        setName("")
        setIcon("🎁")
        setPriceRaw("")
        setPriority("medium")
        setUrl("")
        setNotes("")
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
          placeholder="Camera, headphones…"
          className="h-10 w-full rounded-xl border border-border bg-bg-muted px-3 text-[13.5px] text-text-primary placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
        />
      </div>

      <div className="flex gap-3">
        <div>
          <label className="mb-1 block text-[11px] font-medium text-text-muted">Icon</label>
          <input
            type="text"
            value={icon}
            onChange={(e) => setIcon(e.target.value)}
            disabled={isPending}
            maxLength={4}
            className="h-10 w-20 rounded-xl border border-border bg-bg-muted px-3 text-center text-[16px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
          />
        </div>
        <div className="flex-1">
          <label className="mb-1 block text-[11px] font-medium text-text-muted">Price (IDR)</label>
          <input
            type="number"
            value={priceRaw}
            onChange={(e) => setPriceRaw(e.target.value)}
            disabled={isPending}
            placeholder="0"
            className="h-10 w-full rounded-xl border border-border bg-bg-muted px-3 text-[13.5px] tabular-nums text-text-primary placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
          />
        </div>
      </div>

      <div>
        <label className="mb-1 block text-[11px] font-medium text-text-muted">Priority</label>
        <div className="flex rounded-xl border border-border bg-bg-muted p-1">
          {PRIORITIES.map((p) => (
            <button
              key={p.value}
              type="button"
              onClick={() => setPriority(p.value)}
              className={`flex-1 rounded-lg py-1.5 text-[12.5px] font-semibold transition-colors ${
                priority === p.value
                  ? "bg-card text-text-primary shadow-sm"
                  : "text-text-muted hover:text-text-secondary"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="mb-1 block text-[11px] font-medium text-text-muted">URL</label>
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          disabled={isPending}
          placeholder="https://…"
          className="h-10 w-full rounded-xl border border-border bg-bg-muted px-3 text-[13px] text-text-primary placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
        />
      </div>

      <div>
        <label className="mb-1 block text-[11px] font-medium text-text-muted">Notes</label>
        <input
          type="text"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          disabled={isPending}
          placeholder="—"
          className="h-10 w-full rounded-xl border border-border bg-bg-muted px-3 text-[13px] text-text-primary placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
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
          <><Check className="size-4" /> Added!</>
        ) : status === "error" ? (
          "Failed — try again"
        ) : (
          "Add to wishlist"
        )}
      </button>
    </form>
  )
}
