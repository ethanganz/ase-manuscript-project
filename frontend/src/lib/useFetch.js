import { useEffect, useState } from 'react'

export function useFetch(key, load) {
  const [result, setResult] = useState({ key: '', data: null, error: '', loading: false })

  useEffect(() => {
    if (!key) return undefined
    let current = true
    Promise.resolve()
      .then(load)
      .then((data) => { if (current) setResult({ key, data, error: '', loading: false }) })
      .catch((error) => { if (current) setResult({ key, data: null, error: error.message, loading: false }) })
    return () => { current = false }
  }, [key, load])

  if (!key) return { data: null, error: '', loading: false }
  if (result.key !== key) return { data: null, error: '', loading: true }
  return result
}
