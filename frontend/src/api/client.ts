import createClient from 'openapi-fetch'

import type { components, paths } from './schema'

export type Schemas = components['schemas']

// Same origin as the page (Vite proxies /api to the backend). An absolute base URL is needed
// because Request objects outside the browser reject relative URLs. fetch is resolved per
// call, not once at import, so tests can stub globalThis.fetch.
export const api = createClient<paths>({
  baseUrl: globalThis.location?.origin ?? '',
  fetch: (request) => globalThis.fetch(request),
})

/** The backend's error body: {"error": {code, message, details}}. */
interface AppErrorBody {
  error: { code: string; message: string; details?: Record<string, unknown> }
}

/** FastAPI's request-validation body: {"detail": [{msg, loc}, ...]}. */
interface ValidationErrorBody {
  detail: { msg: string; loc: (string | number)[] }[]
}

// Learner-facing texts are Turkish; the API's own messages are English.
const MESSAGES: Record<string, string> = {
  unsupported_media_type: 'Yalnızca PDF dosyaları yüklenebilir.',
  payload_too_large: 'Dosya çok büyük.',
  empty_file: 'Dosya boş.',
  missing_file_name: 'Dosyanın adı yok.',
  invalid_pdf: 'Dosya okunabilir bir PDF değil (bozuk veya şifreli olabilir).',
  not_found: 'Aranan kayıt bulunamadı.',
  document_file_missing: 'Belgenin dosyası sunucuda bulunamadı.',
  document_not_analyzable: 'Bu belge zaten analiz edildi veya şu anda analiz ediliyor.',
  no_text_layer: 'PDF’te okunabilir metin yok. Taranmış PDF’lerin önce OCR’dan geçmesi gerekir.',
  ai_provider_error: 'Yapay zekâ servisine ulaşılamadı. Lütfen biraz sonra tekrar deneyin.',
  ai_invalid_response: 'Yapay zekâ geçerli bir yanıt vermedi. Lütfen tekrar deneyin.',
  ai_not_configured: 'Yapay zekâ servisi yapılandırılmamış (GEMINI_API_KEY eksik).',
  no_new_vocabulary: 'Bu bölümdeki bütün kelimeler çalışıldı.',
  batch_locked: 'Yeni kelimelere geçmeden önce öğrendiğin kelimeleri tekrar et.',
  nothing_to_review: 'Bu bölümde tekrar edilecek kelime yok.',
  question_already_answered: 'Bu soru zaten cevaplandı.',
  validation_error: 'Girilen bilgiler geçersiz.',
  network_error: 'Sunucuya bağlanılamadı. Backend çalışıyor mu?',
}

export class ApiError extends Error {
  readonly code: string
  readonly status: number
  readonly details: Record<string, unknown>

  constructor(code: string, message: string, status: number, details = {}) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.details = details
  }

  /** The Turkish text to show to the learner. */
  get userMessage(): string {
    return MESSAGES[this.code] ?? this.message
  }

  static from(body: unknown, response: Response): ApiError {
    if (isAppError(body)) {
      const { code, message, details } = body.error
      return new ApiError(code, message, response.status, details)
    }
    if (isValidationError(body)) {
      const message = body.detail.map((item) => item.msg).join(' ')
      return new ApiError('validation_error', message, response.status)
    }
    return new ApiError('http_error', `HTTP ${response.status}`, response.status)
  }
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.userMessage
  if (error instanceof TypeError) return MESSAGES.network_error
  return 'Beklenmeyen bir hata oluştu.'
}

/** Turns an openapi-fetch result into its data, or throws ApiError. */
export function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (result.error !== undefined || result.data === undefined) {
    throw ApiError.from(result.error, result.response)
  }
  return result.data
}

function isAppError(body: unknown): body is AppErrorBody {
  return typeof body === 'object' && body !== null && 'error' in body
}

function isValidationError(body: unknown): body is ValidationErrorBody {
  return typeof body === 'object' && body !== null && 'detail' in body && Array.isArray(body.detail)
}
