import { useState, type ComponentType } from "react"
import { Link, useLocation } from "react-router-dom"
import {
  Check,
  CreditCard,
  Heart,
  LayoutDashboard,
  List,
  Loader2,
  Plus,
  Settings,
  Wallet,
  X,
} from "lucide-react"
import type { LucideIcon } from "lucide-react"
import { useCreateTransaction, type TransactionType } from "@/hooks/useTransactions"
import { useTags, useUpdateTransactionTags } from "@/hooks/useTags"
import { useAccounts } from "@/hooks/useAccounts"
import { useEnvelopes } from "@/hooks/useEnvelopes"
import { useIsMobile } from "@/hooks/useIsMobile"
import { currentPeriod } from "@/components/shared/PeriodPicker"
import { Input } from "@/components/ui/input"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { AddEnvelopeForm } from "@/components/envelopes/AddEnvelopeForm"
import { AddAccountForm } from "@/components/accounts/AddAccountForm"
import { AddWishlistForm } from "@/components/wishlist/AddWishlistForm"

const NAV_ITEMS: { title: string; url: string; icon: LucideIcon }[] = [
  { title: "Envelopes", url: "/envelopes", icon: Wallet },
  { title: "Transactions", url: "/transactions", icon: List },
  { title: "Analytics", url: "/analytics", icon: LayoutDashboard },
  { title: "Accounts", url: "/accounts", icon: CreditCard },
  { title: "Wishlist", url: "/wishlist", icon: Heart },
  { title: "Settings", url: "/settings", icon: Settings },
]

const TYPES: { value: TransactionType; label: string }[] = [
  { value: "expense", label: "Expense" },
  { value: "income", label: "Income" },
  { value: "transfer", label: "Transfer" },
]

function todayISO() {
  return new Date().toISOString().slice(0, 10)
}

// Per-route FAB config. `hasRightPanel` shifts the button to clear a 24rem panel on desktop.
type FabConfig = {
  label: string
  title: string
  Form: ComponentType<{ onSuccess: () => void }>
  hasRightPanel: boolean
}

const FAB_BY_ROUTE: Record<string, FabConfig> = {
  "/transactions": {
    label: "New transaction",
    title: "Add transaction",
    Form: AddTransactionForm,
    hasRightPanel: true,
  },
  "/envelopes": {
    label: "New envelope",
    title: "Add envelope",
    Form: AddEnvelopeForm,
    hasRightPanel: true,
  },
  "/accounts": {
    label: "New account",
    title: "Add account",
    Form: AddAccountForm,
    hasRightPanel: true,
  },
  "/wishlist": {
    label: "New wishlist item",
    title: "Add wishlist item",
    Form: AddWishlistForm,
    hasRightPanel: true,
  },
}

export function AddTransactionFAB() {
  const [formOpen, setFormOpen] = useState(false)
  const [hubOpen, setHubOpen] = useState(false)
  const isMobile = useIsMobile()
  const location = useLocation()
  const config = FAB_BY_ROUTE[location.pathname]

  // Desktop: hide if the current page has no create flow
  if (!isMobile && !config) return null

  const desktopRightOffset = config?.hasRightPanel
    ? "md:right-[26rem]"
    : "md:right-6"

  // Mobile FAB is always-on hub: tap to expand into nav + (optional) primary action.
  if (isMobile) {
    return (
      <>
        <Popover open={hubOpen} onOpenChange={setHubOpen}>
          <PopoverTrigger
            render={
              <button
                aria-label={config ? config.label : "Navigate"}
                className="fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-brand-text text-white shadow-lg transition-transform active:scale-95"
              />
            }
          >
            {hubOpen ? <X className="size-6" /> : <Plus className="size-6" />}
          </PopoverTrigger>
          <PopoverContent
            side="top"
            align="end"
            sideOffset={10}
            className="w-60 gap-1 p-2"
          >
            {NAV_ITEMS.map((item) => {
              const isActive = location.pathname === item.url
              return (
                <Link
                  key={item.url}
                  to={item.url}
                  onClick={() => setHubOpen(false)}
                  className={`flex items-center gap-2.5 rounded-md px-3 py-2 text-[13px] font-medium transition-colors ${
                    isActive
                      ? "bg-brand-light text-brand-text"
                      : "text-text-secondary hover:bg-bg-muted"
                  }`}
                >
                  <item.icon className="size-4" />
                  {item.title}
                </Link>
              )
            })}
            {config && (
              <>
                <div className="my-1 h-px bg-border" />
                <button
                  onClick={() => {
                    setHubOpen(false)
                    setFormOpen(true)
                  }}
                  className="flex items-center gap-2 rounded-md bg-brand-text px-3 py-2.5 text-[13px] font-semibold text-white shadow-sm transition-colors hover:opacity-90"
                >
                  <Plus className="size-4" />
                  {config.label}
                </button>
              </>
            )}
          </PopoverContent>
        </Popover>

        {config && (
          <Sheet open={formOpen} onOpenChange={setFormOpen}>
            <SheetContent
              side="bottom"
              className="flex max-h-[90svh] flex-col rounded-t-2xl px-0 pb-0"
              showCloseButton={false}
            >
              <SheetHeader className="px-5 pb-1 pt-5">
                <div className="flex justify-center pb-1">
                  <div className="h-1 w-10 rounded-full bg-border" />
                </div>
                <SheetTitle className="text-[15px]">{config.title}</SheetTitle>
              </SheetHeader>
              <div className="flex-1 overflow-y-auto px-5 pb-8">
                <config.Form onSuccess={() => setFormOpen(false)} />
              </div>
            </SheetContent>
          </Sheet>
        )}
      </>
    )
  }

  // Desktop: existing pill FAB → directly opens form dialog
  const { label, title, Form } = config!
  return (
    <>
      <button
        onClick={() => setFormOpen(true)}
        className={`fixed bottom-6 right-6 ${desktopRightOffset} z-50 flex h-14 items-center gap-2 rounded-full bg-brand-text px-5 text-white shadow-lg transition-transform hover:scale-105 active:scale-95`}
        aria-label={label}
      >
        <Plus className="size-5" />
        <span className="text-[13.5px] font-semibold">{label}</span>
      </button>
      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent className="flex max-h-[85vh] flex-col gap-0 p-0 sm:max-w-[440px]">
          <DialogHeader className="border-b border-border px-5 py-4">
            <DialogTitle className="text-[15px]">{title}</DialogTitle>
          </DialogHeader>
          <div className="flex-1 overflow-y-auto px-5 pb-6">
            <Form onSuccess={() => setFormOpen(false)} />
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}

function AddTransactionForm({ onSuccess }: { onSuccess: () => void }) {
  const createMutation = useCreateTransaction()
  const setTagsMutation = useUpdateTransactionTags()
  const { accounts } = useAccounts()
  const { allEnvelopes } = useEnvelopes(currentPeriod())
  const { tags: allTags } = useTags()

  const [type, setType] = useState<TransactionType>("expense")
  const [amountRaw, setAmountRaw] = useState("")
  const [date, setDate] = useState(todayISO())
  const [accountId, setAccountId] = useState("")
  const [toAccountId, setToAccountId] = useState("")
  const [envelopeId, setEnvelopeId] = useState("")
  const [payee, setPayee] = useState("")
  const [memo, setMemo] = useState("")
  const [tags, setTags] = useState<string[]>([])
  const [tagDraft, setTagDraft] = useState("")
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle")

  const isPending = status === "loading"
  const expenseEnvelopes = allEnvelopes.filter((e) => !e.envelope.archived)

  const draftLower = tagDraft.trim().toLowerCase()
  const tagSuggestions = allTags
    .map((t) => t.name)
    .filter(
      (name) =>
        (!draftLower || name.toLowerCase().includes(draftLower)) &&
        !tags.some((t) => t.toLowerCase() === name.toLowerCase())
    )
    .slice(0, 8)

  function addTag(raw: string) {
    const name = raw.trim()
    if (!name || tags.some((t) => t.toLowerCase() === name.toLowerCase())) {
      setTagDraft("")
      return
    }
    setTags((prev) => [...prev, name])
    setTagDraft("")
  }

  function removeTag(name: string) {
    setTags((prev) => prev.filter((t) => t !== name))
  }

  // Reset to-account when switching away from transfer
  function handleTypeChange(t: TransactionType) {
    setType(t)
    if (t !== "transfer") setToAccountId("")
    if (t !== "expense") setEnvelopeId("")
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const amount = Number(amountRaw)
    if (!amount || !accountId) return
    setStatus("loading")
    try {
      const created = await createMutation.mutateAsync({
        amount,
        type,
        account_id: Number(accountId),
        payee: payee || null,
        memo: memo || null,
        date,
        envelope_id: type === "expense" && envelopeId ? Number(envelopeId) : null,
        to_account_id: type === "transfer" && toAccountId ? Number(toAccountId) : null,
      })
      if (tags.length > 0 && (created as { id: number }).id) {
        await setTagsMutation.mutateAsync({
          transactionId: (created as { id: number }).id,
          tags,
        })
      }
      setStatus("success")
      setTimeout(() => {
        setStatus("idle")
        setAmountRaw("")
        setPayee("")
        setMemo("")
        setEnvelopeId("")
        setToAccountId("")
        setTags([])
        setTagDraft("")
        setDate(todayISO())
        onSuccess()
      }, 800)
    } catch {
      setStatus("error")
      setTimeout(() => setStatus("idle"), 2000)
    }
  }

  const canSubmit = !!amountRaw && Number(amountRaw) > 0 && !!accountId

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4 pt-4">
      {/* Type toggle */}
      <div className="flex rounded-xl border border-border bg-bg-muted p-1">
        {TYPES.map((t) => (
          <button
            key={t.value}
            type="button"
            onClick={() => handleTypeChange(t.value)}
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

      {/* Amount */}
      <div>
        <label className="mb-1 block text-[11px] font-medium text-text-muted">
          Amount (IDR) <span className="text-[color:var(--danger)]">*</span>
        </label>
        <input
          type="number"
          value={amountRaw}
          onChange={(e) => setAmountRaw(e.target.value)}
          disabled={isPending}
          placeholder="0"
          min="1"
          className="h-10 w-full rounded-xl border border-border bg-bg-muted px-3 text-[14px] tabular-nums text-text-primary placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
        />
      </div>

      {/* Date */}
      <div>
        <label className="mb-1 block text-[11px] font-medium text-text-muted">Date</label>
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          disabled={isPending}
          className="h-10 w-full rounded-xl border border-border bg-bg-muted px-3 text-[13px] text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
        />
      </div>

      {/* Account */}
      <div>
        <label className="mb-1 block text-[11px] font-medium text-text-muted">
          {type === "transfer" ? "From account" : "Account"}{" "}
          <span className="text-[color:var(--danger)]">*</span>
        </label>
        <select
          value={accountId}
          onChange={(e) => setAccountId(e.target.value)}
          disabled={isPending}
          className="h-10 w-full rounded-xl border border-border bg-bg-muted px-3 text-[13px] text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
        >
          <option value="">— Select —</option>
          {accounts.map((a) => (
            <option key={a.id} value={String(a.id)}>
              {a.name}
            </option>
          ))}
        </select>
      </div>

      {/* To account (transfer only) */}
      {type === "transfer" && (
        <div>
          <label className="mb-1 block text-[11px] font-medium text-text-muted">To account</label>
          <select
            value={toAccountId}
            onChange={(e) => setToAccountId(e.target.value)}
            disabled={isPending}
            className="h-10 w-full rounded-xl border border-border bg-bg-muted px-3 text-[13px] text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
          >
            <option value="">— Select —</option>
            {accounts
              .filter((a) => String(a.id) !== accountId)
              .map((a) => (
                <option key={a.id} value={String(a.id)}>
                  {a.name}
                </option>
              ))}
          </select>
        </div>
      )}

      {/* Envelope (expense only) */}
      {type === "expense" && (
        <div>
          <label className="mb-1 block text-[11px] font-medium text-text-muted">Envelope</label>
          <select
            value={envelopeId}
            onChange={(e) => setEnvelopeId(e.target.value)}
            disabled={isPending}
            className="h-10 w-full rounded-xl border border-border bg-bg-muted px-3 text-[13px] text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
          >
            <option value="">— None —</option>
            {expenseEnvelopes.map(({ envelope }) => (
              <option key={envelope.id} value={String(envelope.id)}>
                {envelope.icon} {envelope.name}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Payee (income / expense) */}
      {type !== "transfer" && (
        <div>
          <label className="mb-1 block text-[11px] font-medium text-text-muted">Payee</label>
          <input
            type="text"
            value={payee}
            onChange={(e) => setPayee(e.target.value)}
            disabled={isPending}
            placeholder="—"
            className="h-10 w-full rounded-xl border border-border bg-bg-muted px-3 text-[13px] text-text-primary placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
          />
        </div>
      )}

      {/* Memo */}
      <div>
        <label className="mb-1 block text-[11px] font-medium text-text-muted">Memo</label>
        <input
          type="text"
          value={memo}
          onChange={(e) => setMemo(e.target.value)}
          disabled={isPending}
          placeholder="—"
          className="h-10 w-full rounded-xl border border-border bg-bg-muted px-3 text-[13px] text-text-primary placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
        />
      </div>

      {/* Tags */}
      <div>
        <label className="mb-1 block text-[11px] font-medium text-text-muted">Tags</label>
        <div className="mb-2 flex flex-wrap gap-1.5">
          {tags.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center gap-1 rounded-full bg-brand-light px-2 py-0.5 text-[11px] font-semibold text-brand-text"
            >
              #{tag}
              <button type="button" onClick={() => removeTag(tag)} className="text-brand-text/70 hover:text-brand-text">
                <X className="size-3" />
              </button>
            </span>
          ))}
        </div>
        <div className="relative">
          <Input
            value={tagDraft}
            onChange={(e) => { setTagDraft(e.target.value); setShowSuggestions(true) }}
            onFocus={() => setShowSuggestions(true)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
            onKeyDown={(e) => {
              if (e.key === "Enter") { e.preventDefault(); addTag(tagDraft) }
              else if (e.key === ",") { e.preventDefault(); addTag(tagDraft) }
              else if (e.key === "Backspace" && !tagDraft && tags.length) removeTag(tags[tags.length - 1])
            }}
            disabled={isPending}
            placeholder="Add tag…"
            className="h-9 text-[12.5px]"
          />
          {showSuggestions && tagSuggestions.length > 0 && (
            <div className="absolute left-0 right-0 top-full z-10 mt-1 max-h-44 overflow-y-auto rounded-md border bg-popover shadow-md">
              {tagSuggestions.map((name) => (
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

      {/* Submit */}
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
          <><Loader2 className="size-4 animate-spin" /> Saving…</>
        ) : status === "success" ? (
          <><Check className="size-4" /> Saved!</>
        ) : status === "error" ? (
          "Failed — try again"
        ) : (
          "Save transaction"
        )}
      </button>
    </form>
  )
}
