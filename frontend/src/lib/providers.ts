import type { AIProviderKind } from '../api/aiSettings'

interface ProviderInfo {
  label: string
  /** Where to create an API key. */
  keyUrl?: string
  /** Offered in the model field before the models are fetched with the key. */
  suggestedModels: string[]
}

export const PROVIDERS: Record<AIProviderKind, ProviderInfo> = {
  gemini: {
    label: 'Google Gemini',
    keyUrl: 'https://aistudio.google.com/apikey',
    suggestedModels: ['gemini-3.8-flash'],
  },
  openai: {
    label: 'OpenAI (GPT)',
    keyUrl: 'https://platform.openai.com/api-keys',
    suggestedModels: [],
  },
  anthropic: {
    label: 'Anthropic (Claude)',
    keyUrl: 'https://console.anthropic.com/settings/keys',
    suggestedModels: ['claude-sonnet-5', 'claude-haiku-4-5-20251001', 'claude-opus-5-5'],
  },
  openai_compatible: {
    label: 'OpenAI uyumlu (DeepSeek, OpenRouter, Groq…)',
    suggestedModels: [],
  },
}

export const PROVIDER_ORDER: AIProviderKind[] = [
  'gemini',
  'openai',
  'anthropic',
  'openai_compatible',
]

/** Base URLs of popular OpenAI-compatible services, as examples in the URL field. */
export const COMPATIBLE_EXAMPLES = [
  'https://api.deepseek.com',
  'https://openrouter.ai/api/v1',
  'https://api.groq.com/openai/v1',
]
