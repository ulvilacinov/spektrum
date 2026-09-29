import { Fragment, useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'

import { useAskTutor, type ChatMessage } from '../api/chat'
import { errorMessage } from '../api/client'

const STORAGE_KEY = 'spektrum.chat'
const MAX_STORED = 50
// The backend only looks at the recent history anyway.
const MAX_SENT = 20
const MAX_QUESTION_LENGTH = 2000

const SUGGESTIONS = [
  '„Termin“ der mi, die mi, das mı?',
  'Dativ ile Akkusativ farkını örnekle anlatır mısın?',
  'Perfekt’te ne zaman sein kullanılır?',
  '„weil“ ile bir cümle kurar mısın?',
]

function loadMessages(): ChatMessage[] {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]')
    return Array.isArray(stored) ? stored : []
  } catch {
    return []
  }
}

function storeMessages(messages: ChatMessage[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-MAX_STORED)))
  } catch {
    // Storage unavailable (private mode, quota): the chat still works for this visit.
  }
}

/** **bold** inside a line. */
function Inline({ text }: { text: string }) {
  return text
    .split(/\*\*(.+?)\*\*/)
    .map((part, index) =>
      index % 2 === 1 ? (
        <strong key={index}>{part}</strong>
      ) : (
        <Fragment key={index}>{part}</Fragment>
      ),
    )
}

/** The small Markdown subset the tutor is asked to use: paragraphs, "- " bullets, **bold**. */
function Formatted({ text }: { text: string }) {
  const blocks: { list: boolean; lines: string[] }[] = []
  for (const raw of text.split('\n')) {
    const line = raw.trim()
    if (!line) {
      blocks.push({ list: false, lines: [] })
      continue
    }
    const bullet = /^[-*•]\s+(.*)$/.exec(line)
    const last = blocks.at(-1)
    if (bullet) {
      if (last?.list) last.lines.push(bullet[1])
      else blocks.push({ list: true, lines: [bullet[1]] })
    } else if (last && !last.list && last.lines.length > 0) {
      last.lines.push(line)
    } else {
      blocks.push({ list: false, lines: [line] })
    }
  }
  return blocks
    .filter((block) => block.lines.length > 0)
    .map((block, index) =>
      block.list ? (
        <ul key={index}>
          {block.lines.map((line, item) => (
            <li key={item}>
              <Inline text={line} />
            </li>
          ))}
        </ul>
      ) : (
        <p key={index}>
          {block.lines.map((line, item) => (
            <Fragment key={item}>
              {item > 0 && <br />}
              <Inline text={line} />
            </Fragment>
          ))}
        </p>
      ),
    )
}

/** A floating button and side panel for quick questions to the AI tutor, on every page. */
export function ChatPanel() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>(loadMessages)
  const [draft, setDraft] = useState('')
  const ask = useAskTutor()
  const log = useRef<HTMLDivElement>(null)
  // Replies that arrive after "Yeni sohbet" belong to the old conversation.
  const conversation = useRef(0)

  useEffect(() => storeMessages(messages), [messages])

  useEffect(() => {
    log.current?.scrollTo?.({ top: log.current.scrollHeight })
  }, [messages.length, ask.isPending, open])

  function send(history: ChatMessage[]) {
    const current = conversation.current
    ask.mutate(history.slice(-MAX_SENT), {
      onSuccess: ({ reply }) => {
        if (conversation.current === current)
          setMessages((previous) => [...previous, { role: 'assistant', content: reply }])
      },
    })
  }

  function question(text: string) {
    const content = text.trim()
    if (!content || ask.isPending) return
    const next: ChatMessage[] = [...messages, { role: 'user', content }]
    setMessages(next)
    setDraft('')
    send(next)
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    question(draft)
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    // Enter sends, Shift+Enter starts a new line.
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      question(draft)
    }
  }

  function reset() {
    conversation.current += 1
    ask.reset()
    setMessages([])
  }

  const unanswered = messages.at(-1)?.role === 'user'

  return (
    <>
      <button
        type="button"
        className="chat-fab"
        aria-expanded={open}
        aria-controls="chat-panel"
        onClick={() => setOpen((value) => !value)}
      >
        {open ? '✕ Kapat' : '💬 Sor'}
      </button>
      {open && (
        <aside
          id="chat-panel"
          className="chat"
          aria-label="Yapay zekâya sor"
          onKeyDown={(event) => event.key === 'Escape' && setOpen(false)}
        >
          <div className="chat__head">
            <div>
              <h2>💬 Yapay zekâya sor</h2>
              <p className="muted">Almancayla ilgili aklına takılanı sor.</p>
            </div>
            <div className="chat__head-actions">
              <button
                type="button"
                className="secondary"
                onClick={reset}
                disabled={messages.length === 0}
              >
                Yeni sohbet
              </button>
              <button
                type="button"
                className="secondary chat__close"
                aria-label="Sohbeti kapat"
                onClick={() => setOpen(false)}
              >
                ✕
              </button>
            </div>
          </div>

          <div className="chat__log" ref={log} role="log" aria-live="polite">
            {messages.length === 0 && (
              <div className="chat__empty">
                <span className="empty__emoji" aria-hidden>
                  🥨
                </span>
                <p className="muted">
                  Merhaba! Kelimeler, artikeller ya da dilbilgisi… Sor bakalım.
                </p>
                <div className="chat__suggestions">
                  {SUGGESTIONS.map((suggestion) => (
                    <button
                      key={suggestion}
                      type="button"
                      className="secondary"
                      onClick={() => question(suggestion)}
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((message, index) => (
              <div key={index} className={`chat__message chat__message--${message.role}`}>
                <span className="visually-hidden">
                  {message.role === 'user' ? 'Sen:' : 'Yapay zekâ:'}
                </span>
                <Formatted text={message.content} />
              </div>
            ))}
            {ask.isPending && (
              <div className="chat__message chat__message--assistant chat__typing" role="status">
                <span aria-hidden>•</span>
                <span aria-hidden>•</span>
                <span aria-hidden>•</span>
                <span className="visually-hidden">Yazıyor…</span>
              </div>
            )}
            {ask.isError && unanswered && (
              <div className="error chat__error" role="alert">
                <p>{errorMessage(ask.error)}</p>
                <button type="button" onClick={() => send(messages)}>
                  Tekrar dene
                </button>
              </div>
            )}
          </div>

          <form className="chat__form" onSubmit={submit}>
            <textarea
              aria-label="Sorun"
              placeholder="Bir soru yaz…"
              title="Enter: gönder · Shift+Enter: yeni satır"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={onKeyDown}
              rows={2}
              maxLength={MAX_QUESTION_LENGTH}
              autoFocus
            />
            <button type="submit" disabled={!draft.trim() || ask.isPending}>
              Gönder
            </button>
          </form>
        </aside>
      )}
    </>
  )
}
