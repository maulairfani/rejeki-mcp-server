import { Search } from "lucide-react"
import type { WishlistFilter, WishlistSort } from "@/hooks/useWishlist"

interface WishlistFiltersProps {
  filter: WishlistFilter
  sort: WishlistSort
  search: string
  onFilterChange: (f: WishlistFilter) => void
  onSortChange: (s: WishlistSort) => void
  onSearchChange: (q: string) => void
  resultCount: number
}

const FILTER_OPTIONS: { value: WishlistFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "wanted", label: "Wanted" },
  { value: "bought", label: "Bought" },
]

const SORT_OPTIONS: { value: WishlistSort; label: string }[] = [
  { value: "newest", label: "Newest" },
  { value: "priority", label: "Priority" },
  { value: "price_high", label: "Price ↓" },
  { value: "price_low", label: "Price ↑" },
]

function Chip({
  active,
  onClick,
  children,
}: {
  active?: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      className={
        active
          ? "inline-flex items-center rounded-full bg-brand px-3 py-1 text-xs font-semibold text-white transition-all"
          : "inline-flex items-center rounded-full bg-bg-muted px-3 py-1 text-xs font-semibold text-text-secondary transition-all hover:brightness-95"
      }
    >
      {children}
    </button>
  )
}

export function WishlistFilters({
  filter,
  sort,
  search,
  onFilterChange,
  onSortChange,
  onSearchChange,
  resultCount,
}: WishlistFiltersProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="relative w-full max-w-[320px] flex-1 min-w-[200px]">
        <Search className="absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-text-muted" />
        <input
          type="text"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search wishlist…"
          className="h-9 w-full rounded-md border border-border bg-bg px-3 pl-9 text-[13.5px] text-text-primary placeholder:text-text-placeholder focus:border-brand focus:outline-none"
        />
      </div>

      <div className="flex gap-1.5" role="group" aria-label="Filter by status">
        {FILTER_OPTIONS.map((opt) => (
          <Chip
            key={opt.value}
            active={filter === opt.value}
            onClick={() => onFilterChange(opt.value)}
          >
            {opt.label}
          </Chip>
        ))}
      </div>

      <select
        value={sort}
        onChange={(e) => onSortChange(e.target.value as WishlistSort)}
        className="h-7 rounded-md border border-border bg-bg px-2 text-xs text-text-secondary focus:border-brand focus:outline-none"
      >
        {SORT_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>

      <span className="text-xs font-medium text-text-muted">
        {resultCount} item{resultCount !== 1 ? "s" : ""}
      </span>
    </div>
  )
}
