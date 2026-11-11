import { useRef, useState } from 'react'
import { AlertTriangle, FileText, Loader2, Send } from 'lucide-react'
import { askQuestion } from '../api/ask.js'
import { useCountdown } from '../library/useCountdown.js'

const MAX_QUESTION_LENGTH = 500 // the backend refuses longer questions

/** Where the original page image can be opened. */
function pageImageUrl(pageId) {
  return `/api/pages/${pageId}/image`
}

/**
 * Ask a question about one collection. The answer comes with the transcript lines
 * it is based on, and each line links to its page image.
 */
export function AskSection({ collections }) {
  const [collectionId, setCollectionId] = useState('')
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null) // { message, limited, daily }
  const { secondsLeft, start } = useCountdown()
  const latestRequest = useRef(0)

  // Use the chosen collection, or the first one until the user chooses.
  const activeId = collections.some((c) => c.id === collectionId) ? collectionId : collections[0]?.id ?? ''
  const waiting = secondsLeft > 0
  const trimmed = question.trim()
  const canAsk = Boolean(activeId) && trimmed.length > 0 && !loading && !waiting

  function changeCollection(event) {
    latestRequest.current += 1 // an answer still on its way belongs to the old collection
    setCollectionId(event.target.value)
    setResult(null)
    setError(null)
    setLoading(false)
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (!canAsk) return

    const requestNumber = ++latestRequest.current
    setLoading(true)
    setResult(null)
    setError(null)
    try {
      const data = await askQuestion(activeId, trimmed)
      if (requestNumber !== latestRequest.current) return
      setResult(data)
    } catch (caught) {
      if (requestNumber !== latestRequest.current) return
      const limited = caught.status === 429
      if (limited && caught.retryAfterSeconds) start(caught.retryAfterSeconds)
      setError({ message: caught.message, limited, daily: caught.daily })
    } finally {
      if (requestNumber === latestRequest.current) setLoading(false)
    }
  }

  const limitMessage = error?.limited
    ? error.daily
      ? error.message
      : waiting
        ? `The question limit is reached. Please wait ${secondsLeft} ${secondsLeft === 1 ? 'second' : 'seconds'}.`
        : 'The limit has been reset. You can ask again.'
    : null

  return (
    <section id="ask" className="grid gap-6 border-t border-[#dfe5df] pt-12">
      <div className="overflow-hidden rounded-xl border border-[#e0e6e0] bg-white">
        <div className="border-b border-[#edf0ed] px-6 py-5">
          <h2 className="font-serif text-2xl tracking-[-0.03em]">Ask your documents</h2>
          <p className="mt-1 text-sm text-[#7e8b85]">
            Answers use only the transcribed lines of the collection. Every claim links to its page.
          </p>
        </div>

        {collections.length === 0 ? (
          <p className="px-6 py-8 text-sm text-[#7e8b85]">Create a collection and upload documents first.</p>
        ) : (
          <form onSubmit={handleSubmit} className="grid gap-4 px-6 py-5">
            <label className="grid gap-1 text-sm font-medium text-[#314b3e]">
              Collection
              <select
                value={activeId}
                onChange={changeCollection}
                className="rounded-lg border border-[#d5ddd7] bg-white px-3 py-2 font-normal"
              >
                {collections.map((collection) => (
                  <option key={collection.id} value={collection.id}>
                    {collection.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="grid gap-1 text-sm font-medium text-[#314b3e]">
              Your question
              <textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                maxLength={MAX_QUESTION_LENGTH}
                rows={3}
                placeholder="For example: Which letters mention Wirtemberg?"
                className="resize-y rounded-lg border border-[#d5ddd7] px-3 py-2 font-normal"
              />
              <span className="text-xs font-normal text-[#7e8b85]">
                {question.length}/{MAX_QUESTION_LENGTH}. The search matches spellings, not meaning, so use
                words as they appear in the text.
              </span>
            </label>

            <div>
              <button
                type="submit"
                disabled={!canAsk}
                className="inline-flex items-center gap-2 rounded-lg bg-[#476d5b] px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
              >
                {loading ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
                {loading ? 'Asking…' : waiting ? `Wait ${secondsLeft} s` : 'Ask'}
              </button>
            </div>

            {error && (
              <div
                role="alert"
                className={`flex gap-2 rounded-lg border px-4 py-3 text-sm ${
                  error.limited
                    ? 'border-[#e6d3a3] bg-[#fbf5e4] text-[#6b5313]'
                    : 'border-[#e8c5c5] bg-[#fbeeee] text-[#7a2d2d]'
                }`}
              >
                <AlertTriangle className="mt-0.5 size-4 shrink-0" />
                <span>{limitMessage ?? error.message}</span>
              </div>
            )}

            {result && (
              <div aria-live="polite" className="grid gap-4">
                <div className="rounded-lg bg-[#f3f6f3] px-4 py-3 text-sm leading-relaxed whitespace-pre-line">
                  {result.answer}
                </div>

                {result.grounded ? (
                  <div>
                    <h3 className="mb-2 text-sm font-semibold text-[#314b3e]">Sources</h3>
                    <ul className="grid gap-2">
                      {result.sources.map((source) => (
                        <li key={source.id} className="rounded-lg border border-[#e0e6e0] px-4 py-3 text-sm">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <span className="font-semibold text-[#314b3e]">
                              [{source.label}]
                              {source.page_number ? ` Page ${source.page_number}` : ''}
                              {source.language ? ` · ${source.language}` : ''}
                            </span>
                            <a
                              href={pageImageUrl(source.page_id)}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 text-[#476d5b] hover:underline"
                            >
                              <FileText className="size-4" />
                              Open page
                            </a>
                          </div>
                          <blockquote className="mt-1 text-[#4a5a53]">{source.text}</blockquote>
                        </li>
                      ))}
                    </ul>
                    <p className="mt-2 text-xs text-[#7e8b85]">
                      Lines were read from handwriting by software and may contain mistakes. Check the page.
                    </p>
                  </div>
                ) : (
                  <p className="text-xs text-[#7e8b85]">No source lines. This is not an answer from the documents.</p>
                )}
              </div>
            )}
          </form>
        )}
      </div>
    </section>
  )
}