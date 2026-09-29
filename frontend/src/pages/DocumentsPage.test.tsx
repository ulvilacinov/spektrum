import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { File as NodeFile } from 'node:buffer'
import { describe, expect, it, vi } from 'vitest'

import type { Document } from '../api/documents'
import { apiError, json, mockApi, renderRoute } from '../test/utils'

function doc(overrides: Partial<Document> = {}): Document {
  return {
    id: 1,
    user_id: 1,
    original_file_name: 'spektrum_b1.pdf',
    file_name: 'abc.pdf',
    status: 'uploaded',
    uploaded_at: '2026-09-27T18:12:38Z',
    processed_at: null,
    error_message: null,
    ...overrides,
  }
}

/**
 * A PDF as the file input would give it (a jsdom File). vitest's jsdom→Node fetch bridge
 * rebuilds the multipart body with the *global* File, and newer Node versions (undici) accept
 * only their own, so Node's File is the global while the request is made.
 */
function pdf() {
  const file = new File(['%PDF-1.7'], 'Wortschatz.pdf', { type: 'application/pdf' })
  vi.stubGlobal('File', NodeFile)
  return file
}

describe('DocumentsPage', () => {
  it('lists the documents with their status', async () => {
    mockApi({
      'GET /api/documents': () =>
        json([doc(), doc({ id: 2, original_file_name: 'b2.pdf', status: 'parsed' })]),
    })

    renderRoute()

    const items = await screen.findAllByRole('listitem')
    expect(items).toHaveLength(2)
    expect(within(items[0]).getByText('spektrum_b1.pdf')).toBeInTheDocument()
    expect(within(items[0]).getByText('Yüklendi')).toBeInTheDocument()
    expect(within(items[0]).getByRole('button', { name: 'Analiz et' })).toBeInTheDocument()
    expect(within(items[1]).getByText('Hazır')).toBeInTheDocument()
    expect(within(items[1]).getByRole('button', { name: 'Yeniden analiz et' })).toBeInTheDocument()
  })

  it('shows an empty state', async () => {
    mockApi({ 'GET /api/documents': () => json([]) })

    renderRoute()

    expect(await screen.findByText(/Henüz belge yok/)).toBeInTheDocument()
  })

  it('uploads the chosen PDF as multipart form data', async () => {
    let documents: Document[] = []
    const requests = mockApi({
      'GET /api/documents': () => json(documents),
      'POST /api/documents': () => {
        documents = [doc({ original_file_name: 'Wortschatz.pdf' })]
        return json(documents[0], 201)
      },
    })
    // jsdom's File loses its name when Node's Request serializes it, so check what our
    // code appends; a browser sends the name as given.
    const append = vi.spyOn(FormData.prototype, 'append')
    renderRoute()

    const file = pdf()
    await userEvent.upload(await screen.findByLabelText('PDF dosyası'), file)
    await userEvent.click(screen.getByRole('button', { name: 'Yükle' }))

    expect(await screen.findByText(/Yüklendi. Şimdi analiz edebilirsin/)).toBeInTheDocument()
    expect(await screen.findByText('Wortschatz.pdf')).toBeInTheDocument()
    expect(append).toHaveBeenCalledWith('file', file, 'Wortschatz.pdf')
    const upload = requests.find((request) => request.method === 'POST')!
    expect(upload.headers.get('content-type')).toMatch(/^multipart\/form-data; boundary=/)
    const sent = (await upload.formData()).get('file') // a Node File, not jsdom's Blob class
    expect(sent).toMatchObject({ size: file.size, type: 'application/pdf' })
  })

  it('rejects non-PDF files before uploading', async () => {
    const requests = mockApi({ 'GET /api/documents': () => json([]) })
    renderRoute()

    const notes = new File(['hello'], 'notes.txt', { type: 'text/plain' })
    await userEvent.upload(await screen.findByLabelText('PDF dosyası'), notes, {
      applyAccept: false,
    })

    expect(screen.getByRole('alert')).toHaveTextContent('Yalnızca PDF dosyaları yüklenebilir.')
    expect(screen.getByRole('button', { name: 'Yükle' })).toBeDisabled()
    expect(requests.every((request) => request.method === 'GET')).toBe(true)
  })

  it('shows API errors in Turkish', async () => {
    mockApi({
      'GET /api/documents': () => json([]),
      'POST /api/documents': () => apiError('invalid_pdf', 422, 'The file is not a readable PDF.'),
    })
    renderRoute()

    await userEvent.upload(await screen.findByLabelText('PDF dosyası'), pdf())
    await userEvent.click(screen.getByRole('button', { name: 'Yükle' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('okunabilir bir PDF değil')
  })

  it('analyzes a document and shows the result', async () => {
    let status: Document['status'] = 'uploaded'
    const requests = mockApi({
      'GET /api/documents': () => json([doc({ status })]),
      'POST /api/documents/1/analyze': () => {
        status = 'parsed'
        return json({
          document: doc({ status }),
          chapter_count: 12,
          vocabulary_count: 738,
          rejected_item_count: 0,
          chapters: [],
        })
      },
    })
    renderRoute()

    await userEvent.click(await screen.findByRole('button', { name: 'Analiz et' }))

    expect(await screen.findByText('12 bölüm ve 738 kelime bulundu.')).toBeInTheDocument()
    expect(await screen.findByText('Hazır')).toBeInTheDocument()
    const analyze = requests.find((request) => request.method === 'POST')!
    expect(new URL(analyze.url).searchParams.get('force')).toBe('false')
  })

  it('asks for confirmation before re-analyzing, because progress is deleted', async () => {
    const requests = mockApi({ 'GET /api/documents': () => json([doc({ status: 'parsed' })]) })
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    renderRoute()

    await userEvent.click(await screen.findByRole('button', { name: 'Yeniden analiz et' }))

    expect(confirm).toHaveBeenCalledWith(expect.stringContaining('öğrenme ilerlemen silinir'))
    expect(requests.some((request) => request.method === 'POST')).toBe(false)
  })

  it('re-analyzes with force after confirmation', async () => {
    const requests = mockApi({
      'GET /api/documents': () => json([doc({ status: 'parsed' })]),
      'POST /api/documents/1/analyze': () => apiError('ai_provider_error', 502),
    })
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderRoute()

    await userEvent.click(await screen.findByRole('button', { name: 'Yeniden analiz et' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Yapay zekâ servisine ulaşılamadı')
    const analyze = requests.find((request) => request.method === 'POST')!
    expect(new URL(analyze.url).searchParams.get('force')).toBe('true')
  })

  it('shows a running analysis and the last failure', async () => {
    mockApi({
      'GET /api/documents': () =>
        json([
          doc({ status: 'parsing' }),
          doc({ id: 2, status: 'failed', error_message: 'The AI service request failed.' }),
        ]),
    })
    renderRoute()

    const [running, failed] = await screen.findAllByRole('listitem')
    expect(within(running).getByRole('status')).toHaveTextContent('birkaç dakika sürebilir')
    expect(within(running).queryByRole('button')).not.toBeInTheDocument()
    expect(within(failed).getByText(/Son analiz başarısız/)).toBeInTheDocument()
  })

  it('explains when the backend is not reachable', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'))

    renderRoute()

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('Sunucuya bağlanılamadı'),
    )
  })
})
