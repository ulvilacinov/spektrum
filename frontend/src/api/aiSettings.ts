import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { ApiError, api, unwrap, type Schemas } from './client'

export type AISettings = Schemas['AISettingsRead']
export type AIDraft = Schemas['AIDraftIn']
export type AIProviderKind = Schemas['AIProviderKind']

export const aiSettingsKeys = {
  settings: ['ai-settings'] as const,
}

export function useAISettings() {
  return useQuery({
    queryKey: aiSettingsKeys.settings,
    queryFn: async () => unwrap(await api.GET('/api/ai-settings')),
  })
}

export function useSaveAISettings() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: AIDraft) => unwrap(await api.PUT('/api/ai-settings', { body })),
    onSuccess: (settings) => queryClient.setQueryData(aiSettingsKeys.settings, settings),
  })
}

export function useDeleteAISettings() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const { response } = await api.DELETE('/api/ai-settings')
      if (!response.ok) throw new ApiError('http_error', `HTTP ${response.status}`, response.status)
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: aiSettingsKeys.settings }),
  })
}

/** The models the entered (or saved) key can use. */
export function useListModels() {
  return useMutation({
    mutationFn: async (body: AIDraft) =>
      unwrap(await api.POST('/api/ai-settings/models', { body })).models,
  })
}

/** One tiny request with the form's values; nothing is saved. */
export function useTestAI() {
  return useMutation({
    mutationFn: async (body: AIDraft) =>
      unwrap(await api.POST('/api/ai-settings/test', { body })).reply,
  })
}
