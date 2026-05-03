import { useMemo, useState } from "react"
import {
  useWishlist,
  filterWishlist,
  sortWishlist,
  type WishlistFilter,
  type WishlistSort,
} from "@/hooks/useWishlist"
import { PageHeader } from "@/components/shared/PageHeader"
import { WishlistRow } from "@/components/wishlist/WishlistRow"
import { WishlistFilters } from "@/components/wishlist/WishlistFilters"
import { WishlistDetailPanel } from "@/components/wishlist/WishlistDetailPanel"
import { useIsMobile } from "@/hooks/useIsMobile"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"

export function WishlistPage({ showNominal }: { showNominal: boolean }) {
  const { items, totalWanted, wantedCount, boughtCount } = useWishlist()
  const isMobile = useIsMobile()

  const [filter, setFilter] = useState<WishlistFilter>("all")
  const [sort, setSort] = useState<WishlistSort>("priority")
  const [search, setSearch] = useState("")
  const [selectedItemId, setSelectedItemId] = useState<number | null>(null)

  const filtered = useMemo(
    () => sortWishlist(filterWishlist(items, filter, search), sort),
    [items, filter, search, sort]
  )

  const selectedItem = useMemo(
    () => items.find((i) => i.id === selectedItemId) ?? null,
    [items, selectedItemId]
  )

  const panelProps = {
    item: selectedItem,
    onClose: () => setSelectedItemId(null),
    onDeleted: () => setSelectedItemId(null),
    showNominal,
    totalWanted,
    wantedCount,
    boughtCount,
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <PageHeader title="Wishlist" />

      <div className="flex min-h-0 flex-1 flex-row overflow-hidden">
        {/* Left: list */}
        <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
          {/* Filters strip */}
          <div className="flex-shrink-0 border-b border-border bg-card px-7 py-2.5">
            <WishlistFilters
              filter={filter}
              sort={sort}
              search={search}
              onFilterChange={setFilter}
              onSortChange={setSort}
              onSearchChange={setSearch}
              resultCount={filtered.length}
            />
          </div>

          <div className="flex-1 overflow-y-auto">
            {filtered.length === 0 ? (
              <div className="flex items-center justify-center py-16 text-sm text-text-muted">
                No items found
              </div>
            ) : (
              <>
                {filtered.map((item) => (
                  <WishlistRow
                    key={item.id}
                    item={item}
                    showNominal={showNominal}
                    onClick={() => setSelectedItemId(item.id)}
                  />
                ))}
                <div className="h-10" />
              </>
            )}
          </div>
        </div>

        {/* Right panel — desktop */}
        <div className="hidden md:flex w-96 flex-shrink-0 flex-col border-l border-border bg-card">
          <WishlistDetailPanel {...panelProps} />
        </div>
      </div>

      {/* Bottom sheet — mobile */}
      <Sheet
        open={isMobile && selectedItemId !== null}
        onOpenChange={(open) => {
          if (!open) setSelectedItemId(null)
        }}
      >
        <SheetContent
          side="bottom"
          className="flex max-h-[85svh] flex-col rounded-t-2xl px-0 pb-0"
          showCloseButton={false}
        >
          <SheetHeader className="sr-only">
            <SheetTitle>Wishlist item detail</SheetTitle>
          </SheetHeader>
          <div className="flex flex-shrink-0 justify-center py-2">
            <div className="h-1 w-10 rounded-full bg-border" />
          </div>
          <div className="flex-1 overflow-y-auto">
            <WishlistDetailPanel {...panelProps} />
          </div>
        </SheetContent>
      </Sheet>
    </div>
  )
}
