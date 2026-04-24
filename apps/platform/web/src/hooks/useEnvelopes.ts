import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"

// ── Types ────────────────────────────────────────────────

export type TargetType =
  | "monthly_spending"
  | "monthly_savings"
  | "savings_balance"
  | "needed_by_date"

export interface EnvelopeTarget {
  type: TargetType
  amount: number
  deadline?: string
}

export interface Envelope {
  id: number
  name: string
  icon: string
  type: "income" | "expense"
  groupId: number | null
  sortOrder: number
  target: EnvelopeTarget | null
}

export interface EnvelopeGroup {
  id: number | null
  name: string
  sortOrder: number
}

export interface EnvelopeBudget {
  envelopeId: number
  assigned: number
  carryover: number
  activity: number
  available: number
}

export interface EnvelopeGroupWithBudgets {
  group: EnvelopeGroup
  items: {
    envelope: Envelope
    budget: EnvelopeBudget
  }[]
  totalAssigned: number
  totalAvailable: number
}

// ── API response row ────────────────────────────────────

interface EnvelopeRow {
  id: number
  name: string
  icon: string
  group_id: number | null
  group_name: string
  group_sort: number
  sort_order: number
  target_type: string | null
  target_amount: number | null
  target_deadline: string | null
  assigned: number
  carryover: number
  activity: number
  available: number
  pct: number
  overspent: boolean
}

// ── Transform API → frontend types ──────────────────────

function transformRows(rows: EnvelopeRow[]): {
  groups: EnvelopeGroupWithBudgets[]
  allEnvelopes: { envelope: Envelope; budget: EnvelopeBudget }[]
} {
  const allEnvelopes = rows.map((r) => ({
    envelope: {
      id: r.id,
      name: r.name,
      icon: r.icon || "📦",
      type: "expense" as const,
      groupId: r.group_id,
      sortOrder: r.sort_order,
      target: r.target_type
        ? {
            type: r.target_type as TargetType,
            amount: r.target_amount ?? 0,
            deadline: r.target_deadline ?? undefined,
          }
        : null,
    },
    budget: {
      envelopeId: r.id,
      assigned: r.assigned,
      carryover: r.carryover,
      activity: r.activity,
      available: r.available,
    },
  }))

  // Group by group_id (null → Uncategorized). Preserve backend order (rows come sorted).
  const groupMap = new Map<
    string,
    { id: number | null; name: string; sort: number; items: (typeof allEnvelopes)[number][] }
  >()

  for (const r of rows) {
    const key = r.group_id === null ? "null" : String(r.group_id)
    if (!groupMap.has(key)) {
      groupMap.set(key, {
        id: r.group_id,
        name: r.group_name,
        sort: r.group_sort,
        items: [],
      })
    }
    const item = allEnvelopes.find((e) => e.envelope.id === r.id)!
    groupMap.get(key)!.items.push(item)
  }

  const groups: EnvelopeGroupWithBudgets[] = Array.from(groupMap.values())
    .sort((a, b) => a.sort - b.sort)
    .map(({ id, name, sort, items }) => ({
      group: { id, name, sortOrder: sort },
      items,
      totalAssigned: items.reduce((s, i) => s + i.budget.assigned, 0),
      totalAvailable: items.reduce((s, i) => s + i.budget.available, 0),
    }))

  return { groups, allEnvelopes }
}

// ── Hook ────────────────────────────────────────────────

export function useEnvelopes(period: string) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["envelopes", period],
    queryFn: () => api<EnvelopeRow[]>(`/api/envelopes?period=${period}`),
  })

  const { groups, allEnvelopes } = data ? transformRows(data) : { groups: [], allEnvelopes: [] }

  return { groups, allEnvelopes, isLoading, error }
}

// ── Reorder mutations ───────────────────────────────────

export interface EnvelopeReorderItem {
  id: number
  group_id: number | null
  sort_order: number
}

export interface GroupReorderItem {
  id: number
  sort_order: number
}

export function useReorderEnvelopes(period: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (items: EnvelopeReorderItem[]) =>
      api("/api/envelopes/reorder", {
        method: "PATCH",
        body: JSON.stringify({ items }),
      }),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["envelopes", period] })
    },
  })
}

export function useReorderEnvelopeGroups(period: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (items: GroupReorderItem[]) =>
      api("/api/envelopes/groups/reorder", {
        method: "PATCH",
        body: JSON.stringify({ items }),
      }),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["envelopes", period] })
    },
  })
}

// ── Cover overspent helper ──────────────────────────────

export interface CoverAction {
  fromEnvelopeId: number
  toEnvelopeId: number
  amount: number
}

export function applyCover(
  budgets: Map<number, EnvelopeBudget>,
  action: CoverAction
): Map<number, EnvelopeBudget> {
  const next = new Map(budgets)
  const from = { ...next.get(action.fromEnvelopeId)! }
  const to = { ...next.get(action.toEnvelopeId)! }

  from.assigned -= action.amount
  from.available -= action.amount
  to.assigned += action.amount
  to.available += action.amount

  next.set(from.envelopeId, from)
  next.set(to.envelopeId, to)
  return next
}
