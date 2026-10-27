import { Flag, X } from 'lucide-react'
import { useState } from 'react'
import { REPORT_REASONS, reportCollection } from '../api/reports.js'

/** Popup to report a collection. The owner is told, but not who reported it. */
export function ReportCollectionModal({ collection, onClose }) {
  const [reason, setReason] = useState('')
  const [details, setDetails] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [sent, setSent] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    if (!reason) {
      setError('Choose a reason')
      return
    }
    setSubmitting(true)
    setError('')
    try {
      await reportCollection(collection.id, reason, details.trim())
      setSent(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[3100] flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-xl border border-[#dfe5df] bg-white p-6 shadow-xl">
        <div className="flex items-start justify-between gap-4">
          <h2 className="font-serif text-2xl tracking-[-0.03em] text-[#1e302b]">
            {sent ? 'Report sent' : 'Report collection'}
          </h2>
          <button
            type="button"
            aria-label="Close"
            onClick={onClose}
            className="rounded-lg p-2 text-[#6e7975] hover:bg-[#edf1ed]"
          >
            <X className="size-5" />
          </button>
        </div>

        {sent ? (
          <div className="mt-4 space-y-4 text-sm text-[#55615b]">
            <p>
              Thank you. The owner of <strong className="text-[#1e302b]">{collection.name}</strong> will
              see your report. They will not see who sent it.
            </p>
            <button
              type="button"
              onClick={onClose}
              className="w-full rounded-lg bg-[#1e3b35] px-4 py-2.5 font-medium text-white"
            >
              Done
            </button>
          </div>
        ) : (
          <form className="mt-2 space-y-4" onSubmit={handleSubmit}>
            <p className="text-sm text-[#7e8b85]">
              What is wrong with <strong className="text-[#1e302b]">{collection.name}</strong>? The owner
              is notified, but not told who reported it.
            </p>

            <fieldset className="space-y-2" disabled={submitting}>
              <legend className="sr-only">Reason</legend>
              {REPORT_REASONS.map((option) => (
                <label
                  key={option.value}
                  className={`flex cursor-pointer items-center gap-3 rounded-lg border px-3 py-2.5 text-sm transition-colors ${
                    reason === option.value
                      ? 'border-[#1e3b35] bg-[#eef3ef] text-[#1e302b]'
                      : 'border-[#dfe5df] text-[#55615b] hover:bg-[#f7f9f6]'
                  }`}
                >
                  <input
                    type="radio"
                    name="reason"
                    value={option.value}
                    checked={reason === option.value}
                    onChange={() => setReason(option.value)}
                    className="accent-[#1e3b35]"
                  />
                  {option.label}
                </label>
              ))}
            </fieldset>

            <label className="block text-sm font-medium text-[#374b45]">
              Details <span className="font-normal text-[#8a9790]">(optional)</span>
              <textarea
                value={details}
                onChange={(event) => setDetails(event.target.value)}
                disabled={submitting}
                maxLength={1000}
                rows={3}
                className="mt-2 w-full resize-y rounded-lg border border-[#dfe5df] bg-white px-3 py-2.5 font-normal outline-none focus:border-[#6f8e7b] disabled:bg-[#f4f6f4]"
              />
            </label>

            {error && (
              <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-[#a04a3a] px-4 py-2.5 text-sm font-medium text-white transition hover:bg-[#8a3f31] disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Flag className="size-4" />
              {submitting ? 'Sending…' : 'Send report'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
