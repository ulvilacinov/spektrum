import type { ChatMessage } from '../api/chat'

const STORAGE_KEY = 'spektrum.chat'
const MAX_STORED = 50

export function loadChatHistory(): ChatMessage[] {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]')
    return Array.isArray(stored) ? stored : []
  } catch {
    return []
  }
}

export function storeChatHistory(messages: ChatMessage[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-MAX_STORED)))
  } catch {
    // Storage unavailable (private mode, quota): the chat still works for this visit.
  }
}

/** On logout: the next person on this browser must not see the conversation. */
export function clearChatHistory() {
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    // Nothing stored.
  }
}
