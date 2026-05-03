import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { transformRow } from "@/hooks/useTransactions"

export type AccountType = "bank" | "ewallet" | "cash"

export interface Account {
  id: number
  name: string
  type: AccountType
  balance: number
}

export interface AccountTypeGroup {
  type: AccountType
  label: string
  accounts: Account[]
  totalBalance: number
}

interface AccountsResponse {
  accounts: Account[]
  total: number
}

const TYPE_LABELS: Record<AccountType, string> = {
  bank: "Bank Accounts",
  ewallet: "E-Wallets",
  cash: "Cash",
}

export function useAccounts() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["accounts"],
    queryFn: () => api<AccountsResponse>("/api/accounts"),
  })

  const accounts = data?.accounts ?? []
  const totalBalance = data?.total ?? 0

  const groups: AccountTypeGroup[] = (
    ["bank", "ewallet", "cash"] as AccountType[]
  )
    .map((type) => {
      const accs = accounts.filter((a) => a.type === type)
      return {
        type,
        label: TYPE_LABELS[type],
        accounts: accs,
        totalBalance: accs.reduce((s, a) => s + a.balance, 0),
      }
    })
    .filter((g) => g.accounts.length > 0)

  return { accounts, groups, totalBalance, isLoading, error }
}

// ── Recent transactions for one account ──────────────────

export function useAccountTransactions(accountId: number | null) {
  const { data, isLoading } = useQuery({
    queryKey: ["account-transactions", accountId],
    queryFn: () => api<unknown[]>(`/api/accounts/${accountId}/transactions`),
    enabled: accountId !== null,
  })
  const transactions = (data ?? []).map((r) => transformRow(r as Parameters<typeof transformRow>[0]))
  return { transactions, isLoading }
}

// ── Mutations ─────────────────────────────────────────────

export function useCreateAccount() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { name: string; type: string; balance: number }) =>
      api("/api/accounts", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["accounts"] }),
  })
}

export function useEditAccount() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, name, type }: { id: number; name: string; type: string }) =>
      api(`/api/accounts/${id}`, { method: "PATCH", body: JSON.stringify({ name, type }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["accounts"] }),
  })
}

export function useUpdateAccountBalance() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, balance }: { id: number; balance: number }) =>
      api(`/api/accounts/${id}/balance`, { method: "PATCH", body: JSON.stringify({ balance }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["accounts"] }),
  })
}

export function useDeleteAccount() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api(`/api/accounts/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["accounts"] })
      qc.invalidateQueries({ queryKey: ["transactions"] })
    },
  })
}
