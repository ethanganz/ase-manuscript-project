import { useCallback, useEffect, useState } from 'react'
import './App.css'

const API_BASE = import.meta.env.VITE_API_BASE || '/api'

function App() {
  const [name, setName] = useState('')
  const [names, setNames] = useState([])
  const [status, setStatus] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const loadNames = useCallback(
    () =>
      fetch(`${API_BASE}/names`)
        .then((res) => {
          if (!res.ok) throw new Error(`Request failed (${res.status})`)
          return res.json()
        })
        .then((data) => {
          setNames(Array.isArray(data) ? data : [])
        })
        .catch((err) => {
          console.error('Failed to load names:', err)
        }),
    [],
  )

  useEffect(() => {
    loadNames()
  }, [loadNames])

  async function handleSubmit(event) {
    event.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) return

    setSubmitting(true)
    setStatus(null)
    try {
      const res = await fetch(`${API_BASE}/names`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: trimmed }),
      })

      if (!res.ok) {
        const body = await res.json().catch(() => null)
        const detail = body?.detail
        const message =
          typeof detail === 'string'
            ? detail
            : Array.isArray(detail)
              ? detail.map((item) => item?.msg ?? JSON.stringify(item)).join(', ')
              : `Request failed (${res.status})`
        throw new Error(message)
      }

      setName('')
      setStatus({ type: 'success', message: `Saved "${trimmed}"` })
      await loadNames()
    } catch (err) {
      setStatus({ type: 'error', message: err?.message || 'Something went wrong' })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="container">
      <h1>Submit your name</h1>
      <p className="subtitle">Your name is saved to the Supabase database.</p>

      <form className="name-form" onSubmit={handleSubmit}>
        <input
          type="text"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Your name"
          aria-label="Your name"
          maxLength={200}
        />
        <button type="submit" disabled={submitting || name.trim() === ''}>
          {submitting ? 'Saving…' : 'Submit'}
        </button>
      </form>

      {status && (
        <p className={`status ${status.type}`} role="status">
          {status.message}
        </p>
      )}

      <section className="saved">
        <h2>Saved names</h2>
        {names.length === 0 ? (
          <p className="empty">No names yet.</p>
        ) : (
          <ul>
            {names.map((entry, index) => (
              <li key={index}>{entry.name}</li>
            ))}
          </ul>
        )}
      </section>
    </main>
  )
}

export default App