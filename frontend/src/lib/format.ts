const dateTime = new Intl.DateTimeFormat('tr-TR', { dateStyle: 'medium', timeStyle: 'short' })

export function formatDateTime(value: string): string {
  return dateTime.format(new Date(value))
}
