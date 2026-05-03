import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"

export type TransactionType = "income" | "expense" | "transfer"

export interface Transaction {
  id: number
  amount: number
  type: TransactionType
  envelope: string | null
  envelopeIcon: string | null
  envelopeId: number | null
  account: string
  accountId: number | null
  toAccount: string | null
  payee: string | null
  memo: string | null
  tags: string[]
  date: string // ISO date string
}

export interface DayGroup {
  date: string
  income: number
  expense: number
  transactions: Transaction[]
}

// ── API response row ────────────────────────────────────

interface TransactionRow {
  id: number
  date: string
  type: TransactionType
  amount: number
  payee: string | null
  memo: string | null
  account_id: number | null
  envelope_id: number | null
  account_name: string | null
  to_account_name: string | null
  envelope_name: string | null
  envelope_icon: string | null
  tags: string[]
}

export function transformRow(r: TransactionRow): Transaction {
  return {
    id: r.id,
    amount: r.amount,
    type: r.type,
    envelope: r.envelope_name,
    envelopeIcon: r.envelope_icon,
    envelopeId: r.envelope_id,
    account: r.account_name ?? "—",
    accountId: r.account_id,
    toAccount: r.to_account_name,
    payee: r.payee,
    memo: r.memo,
    tags: r.tags ?? [],
    date: r.date.slice(0, 10), // normalize to YYYY-MM-DD
  }
}

// ── Grouping & filtering ────────────────────────────────

export function groupByDay(transactions: Transaction[]): DayGroup[] {
  const map = new Map<string, Transaction[]>()

  for (const txn of transactions) {
    const list = map.get(txn.date) ?? []
    list.push(txn)
    map.set(txn.date, list)
  }

  const days = Array.from(map.entries()).sort(([a], [b]) =>
    b.localeCompare(a)
  )

  return days.map(([date, txns]) => {
    let income = 0
    let expense = 0
    for (const t of txns) {
      if (t.type === "income") income += t.amount
      else if (t.type === "expense") expense += t.amount
    }
    return { date, income, expense, transactions: txns }
  })
}

export interface TransactionFilters {
  type: TransactionType | "all"
  search: string
  account: string | "all"
  envelope: string | "all"
  tag: string | "all"
}

export function filterTransactions(
  transactions: Transaction[],
  filters: TransactionFilters
): Transaction[] {
  return transactions.filter((txn) => {
    if (filters.type !== "all" && txn.type !== filters.type) return false
    if (filters.account !== "all" && txn.account !== filters.account)
      return false
    if (
      filters.envelope !== "all" &&
      (txn.envelope ?? "") !== filters.envelope
    )
      return false
    if (
      filters.tag !== "all" &&
      !txn.tags.some((t) => t.toLowerCase() === filters.tag.toLowerCase())
    )
      return false
    if (filters.search) {
      const q = filters.search.toLowerCase()
      const haystack = [txn.payee, txn.memo, txn.envelope, txn.account, ...txn.tags]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
      if (!haystack.includes(q)) return false
    }
    return true
  })
}

// ── Hook ────────────────────────────────────────────────

export function useTransactions(period?: string) {
  const params = new URLSearchParams()
  if (period) params.set("period", period)
  params.set("limit", "500")

  const { data, isLoading, error } = useQuery({
    queryKey: ["transactions", period ?? "all"],
    queryFn: () =>
      api<TransactionRow[]>(`/api/transactions?${params.toString()}`),
  })

  const transactions = (data ?? []).map(transformRow)

  return { transactions, isLoading, error }
}

// ── Create mutation ──────────────────────────────────────

export interface TransactionCreatePayload {
  amount: number
  type: TransactionType
  account_id: number
  payee?: string | null
  memo?: string | null
  envelope_id?: number | null
  to_account_id?: number | null
  date?: string
}

export function useCreateTransaction() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: TransactionCreatePayload) =>
      api("/api/transactions", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] })
      queryClient.invalidateQueries({ queryKey: ["envelopes"] })
      queryClient.invalidateQueries({ queryKey: ["accounts"] })
    },
  })
}

// ── Edit / Delete mutations ──────────────────────────────

export interface TransactionEditPayload {
  amount?: number
  payee?: string | null
  memo?: string | null
  date?: string
  envelope_id?: number | null
  clear_envelope?: boolean
}

export function useEditTransaction(period?: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...body }: TransactionEditPayload & { id: number }) =>
      api(`/api/transactions/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] })
      if (period) queryClient.invalidateQueries({ queryKey: ["envelopes", period] })
    },
  })
}

export function useDeleteTransaction(period?: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) =>
      api(`/api/transactions/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] })
      if (period) queryClient.invalidateQueries({ queryKey: ["envelopes", period] })
    },
  })
}
