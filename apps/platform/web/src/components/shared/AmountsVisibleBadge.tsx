import { Eye, EyeOff } from "lucide-react"
import { useShowNominal } from "@/hooks/useShowNominal"

export function AmountsVisibleBadge() {
  const { showNominal, toggle } = useShowNominal()

  return (
    <button
      onClick={toggle}
      aria-pressed={showNominal}
      aria-label={showNominal ? "Hide amounts" : "Show amounts"}
      className={
        showNominal
          ? "inline-flex items-center gap-1.5 rounded-full bg-brand-light px-3 py-1 text-xs font-semibold text-brand-text transition-colors hover:brightness-95"
          : "inline-flex items-center gap-1.5 rounded-full bg-bg-muted px-3 py-1 text-xs font-semibold text-text-muted transition-colors hover:text-text-secondary"
      }
    >
      {showNominal ? (
        <>
          <span className="inline-block h-[7px] w-[7px] rounded-full bg-brand" />
          <span className="hidden sm:inline">Amounts visible</span>
          <Eye className="size-3.5 sm:hidden" />
        </>
      ) : (
        <>
          <EyeOff className="size-3.5" />
          <span className="hidden sm:inline">Amounts hidden</span>
        </>
      )}
    </button>
  )
}
