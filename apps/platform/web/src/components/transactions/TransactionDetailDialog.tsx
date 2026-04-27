import { useEffect, useState } from "react"
import { X } from "lucide-react"
import { formatIDR } from "@/lib/format"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { useTags, useUpdateTransactionTags } from "@/hooks/useTags"
import type { Transaction } from "@/hooks/useTransactions"

const TYPE_LABEL: Record<Transaction["type"], string> = {
  income: "Income",
  expense: "Expense",
  transfer: "Transfer",
}

interface TransactionDetailDialogProps {
  transaction: Transaction | null
  open: boolean
  onOpenChange: (open: boolean) => void
  showNominal: boolean
}

export function TransactionDetailDialog({
  transaction,
  open,
  onOpenChange,
  showNominal,
}: TransactionDetailDialogProps) {
  if (!transaction) return null

  const dateLabel = new Date(transaction.date).toLocaleDateString("en-US", {
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
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{payee}</DialogTitle>
          <DialogDescription>
            {dateLabel} · {TYPE_LABEL[transaction.type]}
          </DialogDescription>
        </DialogHeader>

        <div className="flex items-center justify-between rounded-xl bg-muted/50 px-4 py-3">
          <span className="text-sm text-muted-foreground">Amount</span>
          <span className="text-lg font-heading font-semibold tabular-nums text-foreground">
            {showNominal ? formatIDR(transaction.amount) : "••••••"}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-y-2 text-sm">
          {transaction.envelope && (
            <>
              <span className="text-[13px] text-muted-foreground">Envelope</span>
              <span className="text-right text-[13px] font-medium">
                {transaction.envelopeIcon ? `${transaction.envelopeIcon} ` : ""}
                {transaction.envelope}
              </span>
            </>
          )}

          <span className="text-[13px] text-muted-foreground">
            {transaction.type === "transfer" ? "From" : "Account"}
          </span>
          <span className="text-right text-[13px] font-medium">
            {transaction.account}
          </span>

          {transaction.type === "transfer" && transaction.toAccount && (
            <>
              <span className="text-[13px] text-muted-foreground">To</span>
              <span className="text-right text-[13px] font-medium">
                {transaction.toAccount}
              </span>
            </>
          )}
        </div>

        {transaction.memo && (
          <div className="border-t pt-3">
            <p className="text-[13px] font-medium mb-1">Memo</p>
            <p className="text-[13px] text-muted-foreground">{transaction.memo}</p>
          </div>
        )}

        <div className="border-t pt-3">
          <p className="text-[13px] font-medium mb-2">Tags</p>
          <TagEditor transaction={transaction} />
        </div>
      </DialogContent>
    </Dialog>
  )
}

interface TagEditorProps {
  transaction: Transaction
}

function TagEditor({ transaction }: TagEditorProps) {
  const { tags: allTags } = useTags()
  const update = useUpdateTransactionTags()

  // Mirror server tags locally so chip changes feel instant.
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

  const removeTag = (name: string) => {
    commit(tags.filter((t) => t !== name))
  }

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
          <span className="text-[12px] text-muted-foreground">No tags yet</span>
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
                aria-label={`Remove ${tag}`}
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
          onChange={(e) => {
            setDraft(e.target.value)
            setShowSuggestions(true)
          }}
          onFocus={() => setShowSuggestions(true)}
          onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === ",") {
              e.preventDefault()
              addTag(draft)
            } else if (e.key === "Backspace" && !draft && tags.length) {
              removeTag(tags[tags.length - 1])
            }
          }}
          placeholder="Add tag and press Enter…"
          className="text-[13px]"
        />
        {showSuggestions && suggestions.length > 0 && (
          <div className="absolute left-0 right-0 top-full z-10 mt-1 max-h-44 overflow-y-auto rounded-md border bg-popover shadow-md">
            {suggestions.map((name) => (
              <button
                key={name}
                type="button"
                onMouseDown={(e) => {
                  e.preventDefault()
                  addTag(name)
                }}
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
