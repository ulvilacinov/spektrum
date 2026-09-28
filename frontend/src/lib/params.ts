import { useParams } from 'react-router'

/** A positive integer route parameter, or null if it is missing or malformed. */
export function useIdParam(name: string): number | null {
  const value = useParams()[name]
  if (!value || !/^\d+$/.test(value)) return null
  const id = Number(value)
  return id > 0 ? id : null
}
