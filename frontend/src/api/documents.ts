import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, unwrap, type Schemas } from './client'

export type Document = Schemas['DocumentRead']
export type DocumentAnalysis = Schemas['DocumentAnalysisRead']

export const documentKeys = {
  all: ['documents'] as const,
  detail: (id: number) => ['documents', id] as const,
}

export function useDocuments() {
  return useQuery({
    queryKey: documentKeys.all,
    queryFn: async () => unwrap(await api.GET('/api/documents')),
    // An analysis started elsewhere (or before a reload) finishes in the background.
    refetchInterval: (query) =>
      query.state.data?.some((document) => document.status === 'parsing') ? 5000 : false,
  })
}

export function useUploadDocument() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (file: File) =>
      unwrap(
        await api.POST('/api/documents', {
          // The generated type says string (OpenAPI "binary"); a File is what is sent.
          body: { file: file as unknown as string },
          bodySerializer: (body) => {
            const upload = body.file as unknown as File
            const form = new FormData()
            form.append('file', upload, upload.name) // explicit name survives any File polyfill
            return form
          },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: documentKeys.all }),
  })
}

export function useAnalyzeDocument() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ documentId, force = false }: { documentId: number; force?: boolean }) =>
      unwrap(
        await api.POST('/api/documents/{document_id}/analyze', {
          params: { path: { document_id: documentId }, query: { force } },
        }),
      ),
    // Success and failure both change the document's status.
    onSettled: () => queryClient.invalidateQueries({ queryKey: documentKeys.all }),
  })
}
