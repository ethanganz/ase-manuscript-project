import { useEffect, useRef, useState } from 'react'

/**
 * Loads data when `key` changes and tells you if it is still loading.
 *
 *   const { data, error, loading } = useFetch(`${id}`, () => getSomething(id))
 *
 * - `key`     : a string that identifies WHAT is being loaded. Use an empty
 *               string to say "nothing to load yet".
 * - `fetcher` : function that returns a Promise.
 *
 * Why not just useEffect + setState? When the key changes quickly (user
 * clicks country A, then B) the answer for A may arrive after B. We remember
 * which key each answer belongs to, so a late, stale answer is never shown.
 */
export function useFetch(key, fetcher) {
  const [result, setResult] = useState({ key: '', data: null, error: '' })
  const fetcherRef = useRef(fetcher)

  useEffect(() => {
    fetcherRef.current = fetcher
  })

  useEffect(() => {
    if (!key) return undefined
    let cancelled = false
    fetcherRef
      .current()
      .then((data) => !cancelled && setResult({ key, data, error: '' }))
      .catch((e) => !cancelled && setResult({ key, data: null, error: e.message }))
    return () => {
      cancelled = true
    }
  }, [key])

  const isCurrent = result.key === key // does the stored answer belong to the current key?????
  
  return {
    data: isCurrent ? result.data : null,
    error: isCurrent ? result.error : '',
    loading: Boolean(key) && !isCurrent,
  }
}