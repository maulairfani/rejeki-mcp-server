import { useState } from "react"
import { useDroppable } from "@dnd-kit/core"
import { useSortable, SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import { ChevronRight, GripVertical } from "lucide-react"
import { AmountText } from "@/components/shared/AmountText"
import type { EnvelopeGroupWithBudgets } from "@/hooks/useEnvelopes"
import { EnvelopeRow } from "./EnvelopeRow"

interface EnvelopeGroupSectionProps {
  data: EnvelopeGroupWithBudgets
  showNominal: boolean
  onEnvelopeClick: (envelopeId: number) => void
}

export function EnvelopeGroupSection({
  data,
  showNominal,
  onEnvelopeClick,
}: EnvelopeGroupSectionProps) {
  const [open, setOpen] = useState(true)

  const sortableGroupId = `group:${data.group.id ?? "null"}`
  const {
    attributes,
    listeners,
    setNodeRef: setSortableRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: sortableGroupId,
    // Uncategorized (null id) cannot be reordered — still acts as droppable target for envelopes.
    disabled: data.group.id === null,
    data: { type: "group", group: data.group },
  })

  // Envelope drop target — lets rows land into an empty group.
  const { setNodeRef: setDroppableRef, isOver } = useDroppable({
    id: `dropzone:${data.group.id ?? "null"}`,
    data: { type: "group-dropzone", groupId: data.group.id },
  })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  const envelopeIds = data.items.map((i) => `env:${i.envelope.id}`)

  return (
    <div ref={setSortableRef} style={style}>
      <div
        className="flex w-full items-center justify-between border-t border-border bg-bg-muted pl-2 pr-7 py-2.5 text-left transition-colors hover:brightness-[0.98]"
        style={{
          borderBottom: open ? "none" : "1px solid var(--border)",
        }}
        {...attributes}
      >
        {/* Drag handle for group */}
        <button
          type="button"
          {...listeners}
          className="shrink-0 cursor-grab px-1 text-text-muted opacity-0 transition-opacity hover:text-text-secondary hover:opacity-100 active:cursor-grabbing disabled:cursor-default disabled:opacity-0"
          aria-label="Reorder group"
          disabled={data.group.id === null}
        >
          <GripVertical className="size-4" />
        </button>

        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="flex flex-1 items-center gap-2 text-left"
        >
          <ChevronRight
            className={`size-3 text-text-muted transition-transform ${
              open ? "rotate-90" : ""
            }`}
          />
          <span className="font-heading text-[13px] font-bold text-text-primary">
            {data.group.name}
          </span>
        </button>
        <AmountText
          amount={data.totalAvailable}
          showNominal={showNominal}
          size="sm"
        />
      </div>

      {open && (
        <SortableContext items={envelopeIds} strategy={verticalListSortingStrategy}>
          <div
            ref={setDroppableRef}
            className={isOver ? "bg-brand-light/30" : ""}
          >
            {data.items.length === 0 ? (
              <div className="px-7 py-4 text-center text-xs text-text-muted">
                Drop envelope here
              </div>
            ) : (
              data.items.map((item) => (
                <EnvelopeRow
                  key={item.envelope.id}
                  envelope={item.envelope}
                  budget={item.budget}
                  showNominal={showNominal}
                  onClick={() => onEnvelopeClick(item.envelope.id)}
                />
              ))
            )}
          </div>
        </SortableContext>
      )}
    </div>
  )
}
