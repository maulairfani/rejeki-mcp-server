import type { CSSProperties } from "react"
import { AmountText } from "@/components/shared/AmountText"
import type { Transaction } from "@/hooks/useTransactions"

const TYPE_FALLBACK: Record<string, string> = {
  expense: "💸",
  income: "💰",
  transfer: "↔️",
}

/**
 * Deterministic hue per label. Actual colors are resolved by the
 * `.hue-pill` class in index.css so light/dark themes stay in sync.
 */
const PILL_HUES = [145, 200, 270, 310, 50, 25, 175, 240]
function pillHue(label: string): number {
  let h = 0
  for (const ch of label) h = (h * 31 + ch.charCodeAt(0)) >>> 0
  return PILL_HUES[h % PILL_HUES.length]
}

interface TransactionRowProps {
  transaction: Transaction
  showNominal: boolean
  onClick?: () => void
}

export function TransactionRow({ transaction, showNominal, onClick }: TransactionRowProps) {
  const icon =
    transaction.type !== "transfer" && transaction.envelopeIcon
      ? transaction.envelopeIcon
      : TYPE_FALLBACK[transaction.type]

  const payee =
    transaction.type === "transfer"
      ? `${transaction.account} → ${transaction.toAccount ?? "—"}`
      : transaction.payee ?? "—"

  const memo = transaction.memo ?? ""

  const envelope = transaction.type === "expense" ? transaction.envelope : null
  const account = transaction.type === "transfer" ? null : transaction.account

  const signed =
    transaction.type === "income"
      ? transaction.amount
      : transaction.type === "expense"
        ? -Math.abs(transaction.amount)
        : transaction.amount // transfer: neutral

  const tags = transaction.tags

  return (
    <button
      type="button"
      onClick={onClick}
      className="grid w-full cursor-pointer grid-cols-[28px_1fr_80px] gap-3 border-b border-border-muted px-7 py-2.5 text-left transition-colors hover:bg-bg-muted md:grid-cols-[28px_1fr_1fr_100px_80px_90px]"
    >
      {/* Icon */}
      <div className="flex size-7 shrink-0 items-center justify-center rounded-md bg-bg-muted text-[13px]">
        {icon}
      </div>

      {/* Payee + tag badges (+ mobile subtitle) */}
      <div className="min-w-0">
        <div className="flex min-w-0 items-center gap-1.5">
          <p
            className={`min-w-0 truncate text-[13.5px] font-medium ${
              payee === "—" ? "text-text-muted" : "text-text-primary"
            }`}
          >
            {payee}
          </p>
          {tags.map((tag) => (
            <span
              key={tag}
              className="hue-pill inline-flex shrink-0 items-center rounded-full px-1.5 py-px text-[10.5px] font-semibold"
              style={{ "--pill-h": pillHue(tag) } as CSSProperties}
            >
              #{tag}
            </span>
          ))}
        </div>
        <p className="truncate text-[11.5px] text-text-muted md:hidden">
          {[memo || envelope, account].filter(Boolean).join(" · ") || "\u00A0"}
        </p>
      </div>

      {/* Memo (desktop) */}
      <div className="hidden min-w-0 md:block">
        <span className="truncate text-[12.5px] text-text-muted">
          {memo || "—"}
        </span>
      </div>

      {/* Envelope pill (desktop) */}
      <div className="hidden md:block">
        {envelope ? (
          <span
            className="hue-pill inline-flex items-center rounded-full px-2 py-0.5 text-[11.5px] font-semibold"
            style={{ "--pill-h": pillHue(envelope) } as CSSProperties}
          >
            {envelope}
          </span>
        ) : (
          <span className="text-[11.5px] text-text-muted/60">—</span>
        )}
      </div>

      {/* Account pill (desktop) */}
      <div className="hidden md:block">
        {account ? (
          <span
            className="hue-pill inline-flex items-center rounded-full px-2 py-0.5 text-[11.5px] font-semibold"
            style={{ "--pill-h": pillHue(account) } as CSSProperties}
          >
            {account}
          </span>
        ) : (
          <span className="text-[11.5px] text-text-muted/60">—</span>
        )}
      </div>

      {/* Amount */}
      <div className="text-right">
        <AmountText
          amount={signed}
          showNominal={showNominal}
          size="sm"
          tone={
            transaction.type === "income"
              ? "positive"
              : transaction.type === "transfer"
                ? "neutral"
                : "auto"
          }
        />
      </div>
    </button>
  )
}
