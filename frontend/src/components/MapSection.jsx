import { useCallback, useState } from 'react'
import { getCountryMentions, getCountrySummaries } from '../api/map.js'
import { useFetch } from '../lib/useFetch.js'
import { CountryMap } from './CountryMap.jsx'
import { CountryMentionsPanel } from './CountryMentionsPanel.jsx'
import { PageViewerModal } from './PageViewerModal.jsx'

const NO_SUMMARIES = [] // one shared empty list, so React does not see a "new" value each render
const NO_MENTIONS = []

/**
 * The whole "Places" feature: collection picker + map + mentions list + page viewer.
 * It owns the state; the child components only draw things.
 */
export function MapSection({ collections }) {
  const [pickedCollectionId, setPickedCollectionId] = useState('')
  const [selectedCode, setSelectedCode] = useState('')
  const [openMention, setOpenMention] = useState(null)

  // Until the user picks one, use the first collection in the list.
  const collectionId = pickedCollectionId || collections[0]?.id || ''

  // 1) Coloured countries of this collection.
  const loadSummaries = useCallback(() => getCountrySummaries(collectionId), [collectionId])
  const summariesQuery = useFetch(collectionId, loadSummaries)
  const summaries = summariesQuery.data ?? NO_SUMMARIES

  // 2) Mentions of the clicked country. Empty key = nothing clicked yet.
  const loadMentions = useCallback(() => getCountryMentions(collectionId, selectedCode), [collectionId, selectedCode])
  const mentionsQuery = useFetch(
    collectionId && selectedCode ? `${collectionId}/${selectedCode}` : '',
    loadMentions,
  )
  const mentions = mentionsQuery.data ?? NO_MENTIONS

  function handleCollectionChange(id) {
    setPickedCollectionId(id)
    setSelectedCode('') // a country from the old collection makes no sense any more
  }

  const error = summariesQuery.error || mentionsQuery.error

  return (
    <section id="places" className="border-t border-[#dfe5df] pt-12">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="font-serif text-2xl tracking-[-0.03em]">A map of your research</h2>
          <p className="mt-1 text-sm text-[#7e8b85]">Countries mentioned in the selected collection.</p>
        </div>

        <select
          value={collectionId}
          onChange={(e) => handleCollectionChange(e.target.value)}
          className="rounded-lg border border-[#cbdace] bg-white px-3 py-2 text-sm"
          aria-label="Collection"
        >
          {collections.length === 0 && <option value="">No collections yet</option>}
          {collections.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.6fr_1fr]">
        <div className="overflow-hidden rounded-xl border border-[#e0e6e0] bg-white p-2">
          <CountryMap summaries={summaries} selectedCode={selectedCode} onSelectCountry={setSelectedCode} />
          {collectionId && !summariesQuery.loading && summaries.length === 0 && !error && (
            <p className="px-2 py-3 text-sm text-[#7e8b85]">
              No places found yet in this collection. They appear here after transcription and place detection.
            </p>
          )}
        </div>

        <div className="rounded-xl border border-[#e0e6e0] bg-white p-5">
          <CountryMentionsPanel
            countryCode={selectedCode}
            mentions={mentions}
            loading={mentionsQuery.loading}
            error={mentionsQuery.error}
            onOpenPage={setOpenMention}
          />
          {summariesQuery.error && <p className="mt-3 text-sm text-red-700">{summariesQuery.error}</p>}
        </div>
      </div>

      <PageViewerModal mention={openMention} onClose={() => setOpenMention(null)} />
    </section>
  )
}
