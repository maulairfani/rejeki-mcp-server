import { useCallback, useMemo, useState } from "react"
import { Loader2 } from "lucide-react"
import {
  DndContext,
  type DragEndEvent,
  type DragOverEvent,
  type DragStartEvent,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from "@dnd-kit/core"
import {
  SortableContext,
  arrayMove,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable"
import { useQueryClient } from "@tanstack/react-query"
import {
  useEnvelopes,
  useReorderEnvelopes,
  useReorderEnvelopeGroups,
  applyCover,
  type Envelope,
  type EnvelopeBudget,
  type EnvelopeGroupWithBudgets,
} from "@/hooks/useEnvelopes"
import { PeriodPicker, currentPeriod } from "@/components/shared/PeriodPicker"
import { PageHeader } from "@/components/shared/PageHeader"
import { AmountText } from "@/components/shared/AmountText"
import { EnvelopeGroupSection } from "@/components/envelopes/EnvelopeGroupSection"
import { EnvelopeDetailDialog } from "@/components/envelopes/EnvelopeDetailDialog"

export function EnvelopesPage({ showNominal }: { showNominal: boolean }) {
  const [period, setPeriod] = useState(currentPeriod)
  const { groups: initialGroups, allEnvelopes, isLoading } = useEnvelopes(period)
  const queryClient = useQueryClient()
  const reorderEnvelopes = useReorderEnvelopes(period)
  const reorderGroups = useReorderEnvelopeGroups(period)

  const [overrides, setOverrides] = useState<Map<number, EnvelopeBudget>>(
    new Map()
  )
  const [targetOverrides, setTargetOverrides] = useState<
    Map<number, Envelope["target"]>
  >(new Map())
  const [selectedEnvelopeId, setSelectedEnvelopeId] = useState<number | null>(
    null
  )

  const handlePeriodChange = useCallback((p: string) => {
    setPeriod(p)
    setOverrides(new Map())
  }, [])

  const groups: EnvelopeGroupWithBudgets[] = useMemo(() => {
    if (overrides.size === 0 && targetOverrides.size === 0) return initialGroups
    return initialGroups.map((g) => {
      const items = g.items.map((item) => ({
        envelope: targetOverrides.has(item.envelope.id)
          ? { ...item.envelope, target: targetOverrides.get(item.envelope.id)! }
          : item.envelope,
        budget: overrides.get(item.envelope.id) ?? item.budget,
      }))
      return {
        ...g,
        items,
        totalAssigned: items.reduce((s, i) => s + i.budget.assigned, 0),
        totalAvailable: items.reduce((s, i) => s + i.budget.available, 0),
      }
    })
  }, [initialGroups, overrides, targetOverrides])

  const currentItems = useMemo(
    () =>
      allEnvelopes.map((item) => ({
        envelope: targetOverrides.has(item.envelope.id)
          ? { ...item.envelope, target: targetOverrides.get(item.envelope.id)! }
          : item.envelope,
        budget: overrides.get(item.envelope.id) ?? item.budget,
      })),
    [allEnvelopes, overrides, targetOverrides]
  )

  const totalAvailable = useMemo(
    () => currentItems.reduce((s, i) => s + i.budget.available, 0),
    [currentItems]
  )

  const donors = useMemo(
    () =>
      currentItems.filter(
        (i) => i.budget.available > 0 && i.envelope.id !== selectedEnvelopeId
      ),
    [currentItems, selectedEnvelopeId]
  )

  const selectedItem = useMemo(
    () => currentItems.find((i) => i.envelope.id === selectedEnvelopeId) ?? null,
    [currentItems, selectedEnvelopeId]
  )

  function handleCover(fromEnvelopeId: number, amount: number) {
    if (!selectedEnvelopeId) return
    const budgetMap = new Map<number, EnvelopeBudget>()
    for (const item of currentItems) {
      budgetMap.set(item.envelope.id, item.budget)
    }
    const updated = applyCover(budgetMap, {
      fromEnvelopeId,
      toEnvelopeId: selectedEnvelopeId,
      amount,
    })
    setOverrides(updated)
  }

  function handleTargetChange(envelopeId: number, target: Envelope["target"]) {
    setTargetOverrides((prev) => {
      const next = new Map(prev)
      next.set(envelopeId, target)
      return next
    })
  }

  // ── Drag & drop ───────────────────────────────────────
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } })
  )
  const [activeType, setActiveType] = useState<"group" | "envelope" | null>(null)

  const groupIds = useMemo(
    () => groups.map((g) => `group:${g.group.id ?? "null"}`),
    [groups]
  )

  const setGroupsInCache = useCallback(
    (nextGroups: EnvelopeGroupWithBudgets[]) => {
      queryClient.setQueryData<unknown[]>(
        ["envelopes", period],
        // Rebuild the flat row list in the exact order the UI expects.
        () => {
          const rows: Record<string, unknown>[] = []
          nextGroups.forEach((g, gIdx) => {
            g.items.forEach((item, eIdx) => {
              rows.push({
                id: item.envelope.id,
                name: item.envelope.name,
                icon: item.envelope.icon,
                group_id: g.group.id,
                group_name: g.group.name,
                group_sort: gIdx,
                sort_order: eIdx,
                target_type: item.envelope.target?.type ?? null,
                target_amount: item.envelope.target?.amount ?? null,
                target_deadline: item.envelope.target?.deadline ?? null,
                assigned: item.budget.assigned,
                carryover: item.budget.carryover,
                activity: item.budget.activity,
                available: item.budget.available,
                pct:
                  item.budget.assigned > 0
                    ? Math.min(100, (item.budget.activity / item.budget.assigned) * 100)
                    : 0,
                overspent: item.budget.available < 0,
              })
            })
          })
          return rows
        }
      )
    },
    [queryClient, period]
  )

  function handleDragStart(e: DragStartEvent) {
    const data = e.active.data.current as { type?: string } | undefined
    setActiveType(data?.type === "group" ? "group" : "envelope")
  }

  function handleDragOver(e: DragOverEvent) {
    const { active, over } = e
    if (!over) return
    const activeData = active.data.current as { type?: string } | undefined
    if (activeData?.type !== "envelope") return

    const activeId = String(active.id)
    const overId = String(over.id)
    if (activeId === overId) return

    const overData = over.data.current as
      | { type?: string; groupId?: number | null }
      | undefined

    // Resolve target group: hovering over a row → its group; over a dropzone → that group.
    let targetGroupIdx = -1
    if (overData?.type === "group-dropzone") {
      targetGroupIdx = groups.findIndex((g) => g.group.id === overData.groupId)
    } else if (overId.startsWith("env:")) {
      const overEnvId = Number(overId.slice(4))
      targetGroupIdx = groups.findIndex((g) =>
        g.items.some((i) => i.envelope.id === overEnvId)
      )
    }
    if (targetGroupIdx === -1) return

    const sourceGroupIdx = groups.findIndex((g) =>
      g.items.some((i) => `env:${i.envelope.id}` === activeId)
    )
    if (sourceGroupIdx === -1 || sourceGroupIdx === targetGroupIdx) return

    // Cross-group move: optimistically migrate the envelope.
    const activeEnvId = Number(activeId.slice(4))
    const nextGroups = groups.map((g) => ({ ...g, items: [...g.items] }))
    const source = nextGroups[sourceGroupIdx]
    const target = nextGroups[targetGroupIdx]
    const itemIdx = source.items.findIndex(
      (i) => i.envelope.id === activeEnvId
    )
    if (itemIdx === -1) return
    const [moving] = source.items.splice(itemIdx, 1)

    let insertIdx = target.items.length
    if (overId.startsWith("env:")) {
      const overEnvId = Number(overId.slice(4))
      insertIdx = target.items.findIndex((i) => i.envelope.id === overEnvId)
      if (insertIdx === -1) insertIdx = target.items.length
    }
    // Update envelope's groupId to the target group's id
    const movedItem = {
      ...moving,
      envelope: { ...moving.envelope, groupId: target.group.id },
    }
    target.items.splice(insertIdx, 0, movedItem)

    setGroupsInCache(nextGroups)
  }

  function handleDragEnd(e: DragEndEvent) {
    const { active, over } = e
    setActiveType(null)
    if (!over) return

    const activeData = active.data.current as { type?: string } | undefined
    const activeId = String(active.id)
    const overId = String(over.id)

    if (activeData?.type === "group") {
      if (activeId === overId) return
      const oldIdx = groups.findIndex((g) => `group:${g.group.id ?? "null"}` === activeId)
      const newIdx = groups.findIndex((g) => `group:${g.group.id ?? "null"}` === overId)
      if (oldIdx === -1 || newIdx === -1) return
      const reordered = arrayMove(groups, oldIdx, newIdx)
      setGroupsInCache(reordered)
      // Only persist real groups (skip Uncategorized with null id).
      const items = reordered
        .filter((g) => g.group.id !== null)
        .map((g, idx) => ({ id: g.group.id!, sort_order: idx }))
      reorderGroups.mutate(items)
      return
    }

    if (activeData?.type === "envelope") {
      // Find current group of the (possibly already-migrated) active envelope.
      const activeEnvId = Number(activeId.slice(4))
      const activeGroupIdx = groups.findIndex((g) =>
        g.items.some((i) => i.envelope.id === activeEnvId)
      )
      if (activeGroupIdx === -1) return

      let nextGroups = groups
      if (activeId !== overId && overId.startsWith("env:")) {
        const overEnvId = Number(overId.slice(4))
        const activeItems = groups[activeGroupIdx].items
        const from = activeItems.findIndex((i) => i.envelope.id === activeEnvId)
        const to = activeItems.findIndex((i) => i.envelope.id === overEnvId)
        if (from !== -1 && to !== -1 && from !== to) {
          const reorderedItems = arrayMove(activeItems, from, to)
          nextGroups = groups.map((g, idx) =>
            idx === activeGroupIdx ? { ...g, items: reorderedItems } : g
          )
          setGroupsInCache(nextGroups)
        }
      }

      // Persist envelope order for every envelope across all groups so sort_order is consistent.
      const payload = nextGroups.flatMap((g) =>
        g.items.map((item, idx) => ({
          id: item.envelope.id,
          group_id: g.group.id,
          sort_order: idx,
        }))
      )
      reorderEnvelopes.mutate(payload)
    }
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <PageHeader title="Envelopes">
        <PeriodPicker period={period} onChange={handlePeriodChange} />
      </PageHeader>

      <div className="flex flex-shrink-0 items-center justify-between border-b border-border bg-card px-7 py-3">
        <div>
          <p className="mb-0.5 text-[11px] font-medium text-text-muted">
            Total available
          </p>
          <AmountText
            amount={totalAvailable}
            showNominal={showNominal}
            size="xl"
            tone={totalAvailable < 0 ? "auto" : "neutral"}
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="size-5 animate-spin text-text-muted" />
          </div>
        ) : (
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragStart={handleDragStart}
            onDragOver={handleDragOver}
            onDragEnd={handleDragEnd}
          >
            <SortableContext
              items={groupIds}
              strategy={verticalListSortingStrategy}
              disabled={activeType === "envelope"}
            >
              {groups.map((g) => (
                <EnvelopeGroupSection
                  key={g.group.id ?? "uncat"}
                  data={g}
                  showNominal={showNominal}
                  onEnvelopeClick={setSelectedEnvelopeId}
                />
              ))}
            </SortableContext>
            <div className="h-10" />
          </DndContext>
        )}
      </div>

      <EnvelopeDetailDialog
        envelope={selectedItem?.envelope ?? null}
        budget={selectedItem?.budget ?? null}
        open={selectedEnvelopeId !== null}
        onOpenChange={(open) => {
          if (!open) setSelectedEnvelopeId(null)
        }}
        donors={donors}
        onCover={handleCover}
        onTargetChange={handleTargetChange}
      />
    </div>
  )
}
