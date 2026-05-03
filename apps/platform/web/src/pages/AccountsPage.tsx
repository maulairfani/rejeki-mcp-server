import { useMemo, useState } from "react"
import { Loader2 } from "lucide-react"
import { useAccounts } from "@/hooks/useAccounts"
import { PageHeader } from "@/components/shared/PageHeader"
import { AccountTypeGroup } from "@/components/accounts/AccountTypeGroup"
import { AccountDetailPanel } from "@/components/accounts/AccountDetailPanel"
import { useIsMobile } from "@/hooks/useIsMobile"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"

export function AccountsPage({ showNominal }: { showNominal: boolean }) {
  const { accounts, groups, totalBalance, isLoading } = useAccounts()
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null)
  const isMobile = useIsMobile()

  const selectedAccount = useMemo(
    () => accounts.find((a) => a.id === selectedAccountId) ?? null,
    [accounts, selectedAccountId]
  )

  const panelProps = {
    account: selectedAccount,
    groups,
    totalBalance,
    showNominal,
    onClose: () => setSelectedAccountId(null),
    onDeleted: () => setSelectedAccountId(null),
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <PageHeader title="Accounts" />

      {/* Main content + right panel */}
      <div className="flex flex-1 flex-row overflow-hidden">
        {/* Left: account list */}
        <div className="flex flex-1 flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto">
            {isLoading ? (
              <div className="flex items-center justify-center py-20">
                <Loader2 className="size-5 animate-spin text-text-muted" />
              </div>
            ) : accounts.length === 0 ? (
              <div className="flex items-center justify-center py-16 text-sm text-text-muted">
                No accounts yet
              </div>
            ) : (
              <>
                {groups.map((g) => (
                  <AccountTypeGroup
                    key={g.type}
                    data={g}
                    showNominal={showNominal}
                    onAccountClick={setSelectedAccountId}
                  />
                ))}
                <div className="h-10" />
              </>
            )}
          </div>
        </div>

        {/* Right panel — desktop */}
        <div className="hidden md:flex w-96 flex-shrink-0 flex-col border-l border-border bg-card">
          <AccountDetailPanel {...panelProps} />
        </div>
      </div>

      {/* Bottom sheet — mobile */}
      <Sheet
        open={isMobile && selectedAccountId !== null}
        onOpenChange={(open) => { if (!open) setSelectedAccountId(null) }}
      >
        <SheetContent
          side="bottom"
          className="flex max-h-[85svh] flex-col rounded-t-2xl px-0 pb-0"
          showCloseButton={false}
        >
          <SheetHeader className="sr-only">
            <SheetTitle>Account detail</SheetTitle>
          </SheetHeader>
          <div className="flex flex-shrink-0 justify-center py-2">
            <div className="h-1 w-10 rounded-full bg-border" />
          </div>
          <div className="flex-1 overflow-y-auto">
            <AccountDetailPanel {...panelProps} />
          </div>
        </SheetContent>
      </Sheet>
    </div>
  )
}
