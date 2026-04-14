import { DailyExpensesChart } from "@/components/dashboard/DailyExpensesChart"

export function DashboardPage({ showNominal }: { showNominal: boolean }) {
  return (
    <div className="flex flex-col gap-4">
      <DailyExpensesChart showNominal={showNominal} />
    </div>
  )
}
