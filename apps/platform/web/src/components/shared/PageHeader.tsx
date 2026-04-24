import type { ReactNode } from "react"
import { Separator } from "@/components/ui/separator"
import { SidebarTrigger } from "@/components/ui/sidebar"
import { AmountsVisibleBadge } from "./AmountsVisibleBadge"

interface PageHeaderProps {
  title: string
  /** Content rendered to the right of the title (e.g., MonthNav) */
  children?: ReactNode
  /** Content rendered on the far right. If omitted, AmountsVisibleBadge is shown. */
  right?: ReactNode
  /** Hide the AmountsVisibleBadge when `right` is not provided. */
  hideAmountsBadge?: boolean
}

export function PageHeader({ title, children, right, hideAmountsBadge }: PageHeaderProps) {
  return (
    <div className="flex h-[60px] flex-shrink-0 items-center justify-between gap-2 border-b border-border bg-card px-3 sm:px-6">
      <div className="flex min-w-0 flex-1 items-center gap-2 sm:gap-3">
        <SidebarTrigger className="-ml-1 flex-shrink-0 text-text-muted" />
        <Separator orientation="vertical" className="flex-shrink-0 data-[orientation=vertical]:h-4" />
        <span
          className={
            children
              ? "hidden font-heading text-[17px] font-bold text-text-primary sm:inline"
              : "truncate font-heading text-[17px] font-bold text-text-primary"
          }
        >
          {title}
        </span>
        {children && (
          <div className="flex min-w-0 items-center gap-3 sm:ml-2">{children}</div>
        )}
      </div>
      <div className="flex flex-shrink-0 items-center gap-2.5">
        {right ?? (!hideAmountsBadge && <AmountsVisibleBadge />)}
      </div>
    </div>
  )
}
