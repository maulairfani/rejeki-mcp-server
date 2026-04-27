import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"

export interface Tag {
  id: number
  name: string
  usage: number
}

export function useTags() {
  const { data, isLoading } = useQuery({
    queryKey: ["tags"],
    queryFn: () => api<Tag[]>("/api/tags"),
  })
  return { tags: data ?? [], isLoading }
}

export function useUpdateTransactionTags() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ transactionId, tags }: { transactionId: number; tags: string[] }) =>
      api<{ tags: string[] }>(`/api/transactions/${transactionId}/tags`, {
        method: "PUT",
        body: JSON.stringify({ tags }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] })
      qc.invalidateQueries({ queryKey: ["tags"] })
    },
  })
}
