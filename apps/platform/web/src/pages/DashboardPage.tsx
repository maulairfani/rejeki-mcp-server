import { useMemo, useState } from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import type { CSSProperties } from "react"
import { PageHeader } from "@/components/shared/PageHeader"
import { AmountText } from "@/components/shared/AmountText"
import { PeriodPicker, currentPeriod } from "@/components/shared/PeriodPicker"
import { useDailyExpenses } from "@/hooks/useAnalytics"
import { useTransactions } from "@/hooks/useTransactions"
import { formatIDRShort } from "@/lib/format"
import { CHART_COLORS } from "@/lib/chart-colors"

const TAG_HUES = [145, 200, 270, 310, 50, 25, 175, 240]
function tagHue(label: string): number {
  let h = 0
  for (const ch of label) h = (h * 31 + ch.charCodeAt(0)) >>> 0
  return TAG_HUES[h % TAG_HUES.length]
}

const MONTHS_LONG = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
]

function periodLabel(period: string): string {
  const [y, m] = period.split("-").map(Number)
  return `${MONTHS_LONG[m - 1]} ${y}`
}

interface TooltipPayloadEntry {
  name: string
  value: number
  color: string
}

function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: TooltipPayloadEntry[]
  label?: string
}) {
  if (!active || !payload?.length) return null
  const total = payload.reduce((s, p) => s + (p.value ?? 0), 0)
  return (
    <div className="min-w-40 rounded-md border border-border bg-bg-elevated px-3 py-2 text-xs shadow-lg">
      <p className="mb-1 font-semibold text-text-primary">{label}</p>
      {payload.map((entry) =>
        entry.value > 0 ? (
          <div key={entry.name} className="flex justify-between gap-4">
            <span style={{ color: entry.color }}>{entry.name}</span>
            <span className="tabular-nums text-text-secondary">
              {formatIDRShort(entry.value)}
            </span>
          </div>
        ) : null
      )}
      <div className="mt-1 flex justify-between gap-4 border-t border-border-muted pt-1 font-semibold">
        <span className="text-text-primary">Total</span>
        <span className="tabular-nums text-text-primary">
          {formatIDRShort(total)}
        </span>
      </div>
    </div>
  )
}

export function DashboardPage({ showNominal }: { showNominal: boolean }) {
  const [period, setPeriod] = useState(currentPeriod)
  const { data, loading, error } = useDailyExpenses(period)
  const { transactions: periodTxns } = useTransactions(period)

  const tagBreakdown = useMemo(() => {
    const acc = new Map<string, { total: number; count: number }>()
    for (const t of periodTxns) {
      if (t.type !== "expense" || !t.tags.length) continue
      for (const name of t.tags) {
        const e = acc.get(name) ?? { total: 0, count: 0 }
        e.total += Math.abs(t.amount)
        e.count += 1
        acc.set(name, e)
      }
    }
    return Array.from(acc.entries())
      .map(([name, v]) => ({ name, ...v }))
      .sort((a, b) => b.total - a.total)
  }, [periodTxns])
  const tagBreakdownTotal = tagBreakdown.reduce((s, t) => s + t.total, 0)
  // null = all visible (default). Set = only those envelope IDs are visible.
  const [selected, setSelected] = useState<Set<number> | null>(null)

  const isVisible = (id: number) => selected === null || selected.has(id)

  const totalPeriodExpenses = useMemo(() => {
    if (!data) return 0
    if (selected === null) {
      return data.chartData.reduce((sum, day) => sum + day.total, 0)
    }
    return data.chartData.reduce((sum, day) => {
      for (const env of data.envelopes) {
        if (selected.has(env.id)) sum += (day[env.name] as number) ?? 0
      }
      return sum
    }, 0)
  }, [data, selected])

  const visibleEnvelopes = data?.envelopes.filter((e) => isVisible(e.id)) ?? []
  const lastVisible = visibleEnvelopes.at(-1)

  function toggleEnvelope(id: number) {
    setSelected((prev) => {
      if (prev === null) return new Set([id]) // first tap → solo
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      if (next.size === 0) return null // nothing selected → back to all
      return next
    })
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <PageHeader title="Analytics">
        <PeriodPicker period={period} onChange={setPeriod} />
      </PageHeader>

      <div className="flex-1 overflow-y-auto px-7 py-6">
        {/* Summary */}
        <div className="mb-6 flex items-end justify-between">
          <div>
            <div className="mb-0.5 font-heading text-[17px] font-bold text-text-primary">
              Daily Expenses
            </div>
            <div className="text-[12.5px] text-text-muted">
              {periodLabel(period)} · stacked by envelope
            </div>
          </div>
          <div className="text-right">
            <div className="mb-1 text-[11px] text-text-muted">
              Total · {periodLabel(period)}
            </div>
            <AmountText
              amount={totalPeriodExpenses}
              showNominal={showNominal}
              size="xl"
              tone="neutral"
            />
          </div>
        </div>

        {/* Legend */}
        {data && (
          <div className="mb-5 flex flex-wrap items-center gap-x-4 gap-y-1.5">
            {data.envelopes.map((env, i) => {
              const active = isVisible(env.id)
              const color = CHART_COLORS[i % CHART_COLORS.length]
              return (
                <button
                  key={env.id}
                  onClick={() => toggleEnvelope(env.id)}
                  aria-pressed={active}
                  aria-label={`${active ? "Hide" : "Show"} ${env.name}`}
                  className={`inline-flex items-center gap-1.5 text-[12px] font-medium transition-opacity ${
                    active ? "text-text-secondary" : "text-text-muted opacity-50"
                  }`}
                >
                  <span
                    className="inline-block size-2 rounded-sm transition-opacity"
                    style={{ background: color, opacity: active ? 1 : 0.4 }}
                  />
                  {env.name}
                </button>
              )
            })}
            {selected !== null && (
              <button
                onClick={() => setSelected(null)}
                className="inline-flex items-center gap-1 rounded-full bg-bg-muted px-2.5 py-0.5 text-[11px] font-semibold text-text-secondary transition-colors hover:brightness-95"
              >
                Show all
              </button>
            )}
          </div>
        )}

        {/* Chart */}
        <div className="rounded-xl border border-border bg-card p-4 shadow-xs">
          {error ? (
            <div className="flex h-64 items-center justify-center text-sm text-[color:var(--danger)]">
              Failed to load data: {error}
            </div>
          ) : loading ? (
            <div className="h-[280px] w-full animate-pulse rounded-md bg-bg-muted" />
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart
                data={data?.chartData}
                margin={{ top: 8, right: 8, left: -4, bottom: 0 }}
                barCategoryGap="20%"
              >
                <CartesianGrid
                  vertical={false}
                  strokeDasharray="3 3"
                  stroke="var(--border)"
                />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10, fill: "var(--text-muted)" }}
                  tickLine={false}
                  axisLine={false}
                  interval="preserveStartEnd"
                />
                <YAxis
                  tickFormatter={formatIDRShort}
                  tick={
                    showNominal
                      ? { fontSize: 10, fill: "var(--text-muted)" }
                      : false
                  }
                  tickLine={false}
                  axisLine={false}
                  width={showNominal ? 48 : 8}
                />
                <Tooltip
                  content={showNominal ? <ChartTooltip /> : <></>}
                  cursor={showNominal ? { fill: "var(--bg-muted)", opacity: 0.4 } : false}
                />
                {data?.envelopes.map((env, i) => {
                  if (!isVisible(env.id)) return null
                  return (
                    <Bar
                      key={env.id}
                      dataKey={env.name}
                      stackId="expenses"
                      fill={CHART_COLORS[i % CHART_COLORS.length]}
                      radius={env.id === lastVisible?.id ? [4, 4, 0, 0] : [0, 0, 0, 0]}
                    />
                  )
                })}
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {tagBreakdown.length > 0 && (
          <div className="mt-6 rounded-xl border border-border bg-card p-4 shadow-xs">
            <div className="mb-3 flex items-end justify-between">
              <div>
                <div className="font-heading text-[15px] font-bold text-text-primary">
                  Spending by Tag
                </div>
                <div className="text-[11.5px] text-text-muted">
                  {periodLabel(period)} · expenses only
                </div>
              </div>
              <div className="text-right">
                <div className="text-[10.5px] text-text-muted">Tagged total</div>
                <AmountText
                  amount={tagBreakdownTotal}
                  showNominal={showNominal}
                  size="md"
                  tone="neutral"
                />
              </div>
            </div>
            <div className="flex flex-col gap-2">
              {tagBreakdown.map((t) => {
                const share = tagBreakdownTotal
                  ? (t.total / tagBreakdownTotal) * 100
                  : 0
                return (
                  <div key={t.name} className="flex items-center gap-3">
                    <span
                      className="hue-pill inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-[11.5px] font-semibold"
                      style={{ "--pill-h": tagHue(t.name) } as CSSProperties}
                    >
                      #{t.name}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="h-1.5 overflow-hidden rounded-full bg-bg-muted">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${share}%`,
                            background: `oklch(60% 0.14 ${tagHue(t.name)})`,
                          }}
                        />
                      </div>
                    </div>
                    <div className="shrink-0 text-right">
                      <AmountText
                        amount={t.total}
                        showNominal={showNominal}
                        size="sm"
                        tone="neutral"
                      />
                      <div className="text-[10.5px] text-text-muted tabular-nums">
                        {t.count} tx · {share.toFixed(0)}%
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        <div className="h-10" />
      </div>
    </div>
  )
}
