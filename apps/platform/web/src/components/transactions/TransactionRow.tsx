import { formatIDR } from "@/lib/format"
import type { Transaction } from "@/hooks/useTransactions"

/** Envelope → emoji mapping (mirrors schema.sql defaults) */
const ENVELOPE_ICONS: Record<string, string> = {
  Salary: "💼",
  Freelance: "💻",
  Investments: "📈",
  "Other Income": "💰",
  Rent: "🏡",
  Bills: "📄",
  Subscriptions: "🔄",
  "Family Support": "🏠",
  Food: "🍽️",
  Transport: "🚗",
  Shopping: "🛍️",
  Entertainment: "🎮",
  Health: "🏥",
  Education: "📚",
  "Emergency Fund": "🛡️",
  Savings: "💎",
  Miscellaneous: "💸",
}

const TYPE_STYLE = {
  expense: {
    color: "text-foreground",
    sign: "-",
    fallbackIcon: "💸",
  },
  income: {
    color: "text-emerald-600 dark:text-emerald-400",
    sign: "+",
    fallbackIcon: "💰",
  },
  transfer: {
    color: "text-blue-600 dark:text-blue-400",
    sign: "",
    fallbackIcon: "↔️",
  },
} as const

interface TransactionRowProps {
  transaction: Transaction
  showNominal: boolean
}

export function TransactionRow({ transaction, showNominal }: TransactionRowProps) {
  const style = TYPE_STYLE[transaction.type]

  const icon =
    transaction.type === "expense" && transaction.envelope
      ? ENVELOPE_ICONS[transaction.envelope] ?? style.fallbackIcon
      : style.fallbackIcon

  const payee =
    transaction.type === "transfer"
      ? `${transaction.account} → ${transaction.toAccount}`
      : transaction.payee ?? "—"

  const envelope =
    transaction.type === "expense" ? transaction.envelope : null

  const account =
    transaction.type === "transfer" ? null : transaction.account

  return (
    <div className="flex items-center gap-3 px-3.5 py-2.5 transition-colors hover:bg-muted/50 border-b border-border last:border-b-0">
      {/* Icon */}
      <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-muted/60 text-base leading-none">
        {icon}
      </div>

      {/* Payee + envelope subtitle (mobile) / payee only (desktop) */}
      <div className="flex-1 min-w-0">
        <p className="truncate text-[13px] font-medium">{payee}</p>
        {/* Mobile: show envelope + account as subtitle */}
        <p className="truncate text-[11px] text-muted-foreground md:hidden">
          {[envelope, account].filter(Boolean).join(" · ") || "\u00A0"}
        </p>
      </div>

      {/* Envelope — desktop only */}
      <div className="shrink-0 w-[100px] hidden md:block">
        {envelope ? (
          <p className="truncate text-[12px] text-muted-foreground">{envelope}</p>
        ) : (
          <p className="text-[12px] text-muted-foreground/40">—</p>
        )}
      </div>

      {/* Account — desktop only */}
      <div className="shrink-0 w-[70px] hidden md:block">
        {account ? (
          <p className="truncate text-[12px] text-muted-foreground">{account}</p>
        ) : (
          <p className="text-[12px] text-muted-foreground/40">—</p>
        )}
      </div>

      {/* Amount */}
      <div className="shrink-0 text-right">
        <span className={`text-[13px] font-medium tabular-nums ${style.color}`}>
          {showNominal
            ? `${style.sign}${formatIDR(transaction.amount)}`
            : "•••••"}
        </span>
      </div>
    </div>
  )
}
