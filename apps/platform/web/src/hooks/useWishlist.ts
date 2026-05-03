import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"

export type Priority = "high" | "medium" | "low"
export type WishlistStatus = "wanted" | "bought"

export interface WishlistItem {
  id: number
  name: string
  icon: string
  price: number | null
  priority: Priority
  url: string | null
  notes: string | null
  status: WishlistStatus
  createdAt: string // ISO date
}

interface WishlistResponse {
  items: WishlistItem[]
  totalWanted: number
  wantedCount: number
  boughtCount: number
}

// ── Filter / Sort helpers ────────────────────────────────

export type WishlistFilter = "all" | "wanted" | "bought"
export type WishlistSort = "newest" | "price_high" | "price_low" | "priority"

const PRIORITY_ORDER: Record<Priority, number> = {
  high: 0,
  medium: 1,
  low: 2,
}

export function filterWishlist(
  items: WishlistItem[],
  filter: WishlistFilter,
  search: string
): WishlistItem[] {
  return items.filter((item) => {
    if (filter !== "all" && item.status !== filter) return false
    if (search) {
      const q = search.toLowerCase()
      const haystack = [item.name, item.notes].filter(Boolean).join(" ").toLowerCase()
      if (!haystack.includes(q)) return false
    }
    return true
  })
}

export function sortWishlist(
  items: WishlistItem[],
  sort: WishlistSort
): WishlistItem[] {
  const sorted = [...items]
  switch (sort) {
    case "newest":
      sorted.sort((a, b) => b.createdAt.localeCompare(a.createdAt))
      break
    case "price_high":
      sorted.sort((a, b) => (b.price ?? 0) - (a.price ?? 0))
      break
    case "price_low":
      sorted.sort((a, b) => (a.price ?? 0) - (b.price ?? 0))
      break
    case "priority":
      sorted.sort(
        (a, b) => PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority]
      )
      break
  }
  return sorted
}

// ── Hook ────────────────────────────────────────────────

export function useWishlist() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["wishlist"],
    queryFn: () => api<WishlistResponse>("/api/wishlist"),
  })

  return {
    items: data?.items ?? [],
    totalWanted: data?.totalWanted ?? 0,
    totalBought: 0,
    wantedCount: data?.wantedCount ?? 0,
    boughtCount: data?.boughtCount ?? 0,
    isLoading,
    error,
  }
}

export function useCreateWishlistItem() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: {
      name: string
      icon?: string
      price?: number | null
      priority?: Priority
      url?: string | null
      notes?: string | null
    }) =>
      api("/api/wishlist", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wishlist"] })
    },
  })
}
