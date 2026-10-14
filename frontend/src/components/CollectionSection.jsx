import { useEffect, useState } from 'react'
import { ArrowUpRight, FileText, Search } from 'lucide-react'
import { getCollectionDocuments, getDocumentPages, getDocumentPreview } from '../api/documents.js'

function CollectionCard({ collection, selected, onSelect }) {
  return (
    <button type="button" onClick={onSelect} aria-pressed={selected}
      className={`group w-full rounded-xl border bg-white p-5 text-left transition hover:-translate-y-0.5 hover:shadow-[0_12px_30px_rgba(35,55,45,0.07)] ${selected ? 'border-[#6f8e7b] ring-2 ring-[#d9e4dc]' : 'border-[#e0e6e0] hover:border-[#c3d2c7]'}`}>
      <div className="mb-5 flex h-32 items-end rounded-lg bg-[#d9e4dc] p-4">
        <div className="w-full rounded-md border border-black/5 bg-[#fbfaf5]/70 p-3 backdrop-blur-sm">
          <div className="h-1 w-1/2 rounded bg-[#53645b]/35" />
          <div className="mt-2 h-1 w-4/5 rounded bg-[#53645b]/20" />
          <div className="mt-2 h-1 w-2/3 rounded bg-[#53645b]/20" />
        </div>
      </div>
      <h3 className="font-serif text-[19px] leading-tight">{collection.name}</h3>
      <p className="mt-1 text-xs text-[#8a9790]">{collection.description || 'No description'}</p>
      <div className="mt-5 flex items-center justify-between border-t border-[#edf0ed] pt-4 text-xs text-[#8a9790]">
        <span>{selected ? 'Selected collection' : 'Open collection'}</span>
        <ArrowUpRight className="size-4 text-[#6f8e7b]" />
      </div>
    </button>
  )
}

function ManuscriptReader({ document }) {
  const [pages, setPages] = useState([])
  const [activePageId, setActivePageId] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [imageError, setImageError] = useState(false)
  const [previewUrl, setPreviewUrl] = useState('')
  const [previewError, setPreviewError] = useState('')
  const [previewLoading, setPreviewLoading] = useState(true)

  useEffect(() => {
    let current = true
    getDocumentPages(document.id)
      .then((result) => {
        if (!current) return
        setPages(result)
        setActivePageId(result[0]?.id || null)
        setError('')
      })
      .catch((failure) => { if (current) setError(failure.message) })
      .finally(() => { if (current) setLoading(false) })
    return () => { current = false }
  }, [document.id])

  useEffect(() => {
    const controller = new AbortController()
    let url

    getDocumentPreview(document.id, controller.signal)
      .then((blob) => {
        if (controller.signal.aborted) return
        url = URL.createObjectURL(blob)
        setPreviewUrl(url)
      })
      .catch((failure) => {
        if (!controller.signal.aborted) setPreviewError(failure.message)
      })
      .finally(() => {
        if (!controller.signal.aborted) setPreviewLoading(false)
      })

    return () => {
      controller.abort()
      if (url) URL.revokeObjectURL(url)
    }
  }, [document.id])

  const activePage = pages.find((page) => page.id === activePageId)

  return (
    <div className="mt-5 rounded-xl border border-[#dfe5df] bg-white p-5 sm:p-6">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#8b9c91]">Selected manuscript</p>
      <h4 className="mt-2 break-words font-serif text-2xl text-[#1e302b]">{document.original_filename}</h4>
      <p className="mt-2 text-sm text-[#7e8b85]">{document.source_archive || 'Archive source not specified'} · {document.file_type.toUpperCase()}</p>
      <div className="mt-6 rounded-lg border border-[#e0e6e0] bg-[#fbfaf5] p-4 sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h5 className="font-serif text-xl text-[#1e302b]">Original file</h5>
            <p className="mt-1 text-sm text-[#7e8b85]">Review the upload before results are available.</p>
          </div>
          {previewUrl && (
            <a href={previewUrl} target="_blank" rel="noreferrer"
              className="text-sm font-medium text-[#476d5b] underline underline-offset-4 hover:text-[#1e3b35]">
              Open full size
            </a>
          )}
        </div>
        {previewLoading && <p className="mt-5 text-sm text-[#7e8b85]">Loading original file…</p>}
        {previewError && <p role="alert" className="mt-5 text-sm text-red-700">{previewError}</p>}
        {previewUrl && (document.file_type === 'pdf' ? (
          <iframe title={`Preview of ${document.original_filename}`} src={previewUrl}
            className="mt-5 h-[520px] w-full rounded border border-[#e0e6e0] bg-white" />
        ) : (
          <div className="mt-5 flex max-h-[520px] justify-center overflow-auto rounded bg-[#f1f3ef] p-3">
            <img src={previewUrl} alt={`Original upload: ${document.original_filename}`}
              className="max-h-[496px] max-w-full object-contain" />
          </div>
        ))}
      </div>
      {loading && <p className="mt-6 text-sm text-[#7e8b85]">Loading pages…</p>}
      {error && <p role="alert" className="mt-6 text-sm text-red-700">{error}</p>}
      {!loading && !error && pages.length === 0 && <p className="mt-6 text-sm text-[#7e8b85]">Analysis pages are not available for this manuscript yet.</p>}
      {activePage && (
        <>
          <div className="mt-6 flex flex-wrap gap-2" aria-label="Manuscript pages">
            {pages.map((page) => (
              <button key={page.id} type="button" aria-pressed={page.id === activePageId}
                onClick={() => { setActivePageId(page.id); setImageError(false) }}
                className={`rounded-lg border px-3 py-1.5 text-sm transition ${page.id === activePageId ? 'border-[#1e3b35] bg-[#1e3b35] text-white' : 'border-[#dfe5df] text-[#476d5b] hover:bg-[#edf1ed]'}`}>
                Page {page.page_number}
              </button>
            ))}
          </div>
          <div className="mt-5 grid gap-5 lg:grid-cols-2">
            <div className="flex min-h-64 items-center justify-center overflow-hidden rounded-lg bg-[#f1f3ef] p-3">
              {imageError ? <p className="text-sm text-[#7e8b85]">Page image is unavailable.</p> : (
                <img key={activePage.id} src={`/api/pages/${activePage.id}/image`}
                  alt={`Page ${activePage.page_number} of ${document.original_filename}`}
                  className="max-h-[520px] w-auto max-w-full object-contain"
                  onError={() => setImageError(true)} />
              )}
            </div>
            <div className="rounded-lg border border-[#e0e6e0] bg-[#fbfaf5] p-5">
              <h5 className="font-serif text-xl text-[#1e302b]">Transcription</h5>
              {activePage.transcription_text ? (
                <p className="mt-4 whitespace-pre-wrap break-words font-serif text-base leading-7 text-[#374b45]">{activePage.transcription_text}</p>
              ) : (
                <p className="mt-4 text-sm text-[#7e8b85]">No transcription is available for this page yet.</p>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function ManuscriptList({ collection, refreshKey }) {
  const [documents, setDocuments] = useState([])
  const [activeDocumentId, setActiveDocumentId] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let current = true
    getCollectionDocuments(collection.id)
      .then((result) => {
        if (!current) return
        setDocuments(result)
        setActiveDocumentId((previous) => result.some((doc) => doc.id === previous) ? previous : null)
        setError('')
      })
      .catch((failure) => { if (current) setError(failure.message) })
      .finally(() => { if (current) setLoading(false) })
    return () => { current = false }
  }, [collection.id, refreshKey])

  const activeDocument = documents.find((doc) => doc.id === activeDocumentId)

  return (
    <div className="mt-8 border-t border-[#dfe5df] pt-7">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#8b9c91]">Collection contents</p>
      <h3 className="mt-2 font-serif text-2xl text-[#1e302b]">{collection.name}</h3>
      {loading && <p className="mt-5 text-sm text-[#7e8b85]">Loading manuscripts…</p>}
      {error && <p role="alert" className="mt-5 text-sm text-red-700">{error}</p>}
      {!loading && !error && documents.length === 0 && <p className="mt-5 text-sm text-[#7e8b85]">There are no manuscripts in this collection yet.</p>}
      {documents.length > 0 && (
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          {documents.map((document) => (
            <button key={document.id} type="button" aria-pressed={document.id === activeDocumentId}
              onClick={() => setActiveDocumentId(document.id)}
              className={`flex items-center gap-3 rounded-lg border bg-white p-4 text-left transition hover:border-[#9bb8a2] ${document.id === activeDocumentId ? 'border-[#6f8e7b] ring-2 ring-[#d9e4dc]' : 'border-[#e0e6e0]'}`}>
              <FileText className="size-5 shrink-0 text-[#6f8e7b]" />
              <span className="min-w-0">
                <span className="block truncate font-medium text-[#1e302b]">{document.original_filename}</span>
                <span className="mt-1 block text-xs text-[#8a9790]">{document.file_type.toUpperCase()} · {document.status}</span>
              </span>
            </button>
          ))}
        </div>
      )}
      {activeDocument && <ManuscriptReader key={activeDocument.id} document={activeDocument} />}
    </div>
  )
}

export function CollectionSection({ collections, loading, error, search, onSearchChange, refreshKey }) {
  const [activeCollectionId, setActiveCollectionId] = useState(null)
  const filteredCollections = collections.filter((collection) =>
    collection.name.toLowerCase().includes(search.toLowerCase())
  )
  const activeCollection = collections.find((collection) => collection.id === activeCollectionId)

  return (
    <section id="collections" className="py-12">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-[#8b9c91]">The archive</p>
          <h2 className="font-serif text-3xl tracking-[-0.04em]">Collections</h2>
          <p className="mt-2 text-sm text-[#7e8b85]">Historical materials you are currently exploring.</p>
        </div>
        <label className="flex h-10 w-full items-center gap-2 rounded-lg border border-[#dfe5df] bg-white px-3 text-sm text-[#89958f] sm:w-64">
          <Search className="size-4" />
          <input type="text" value={search} onChange={(event) => onSearchChange(event.target.value)}
            className="w-full bg-transparent outline-none placeholder:text-[#a0aaa5]"
            placeholder="Search collections" aria-label="Search collections" />
        </label>
      </div>
      <div className="mt-7 grid gap-5 xl:grid-cols-3">
        {filteredCollections.map((collection) => (
          <CollectionCard key={collection.id} collection={collection}
            selected={collection.id === activeCollectionId}
            onSelect={() => setActiveCollectionId(collection.id)} />
        ))}
      </div>
      {loading && <p className="mt-6 text-sm text-[#7e8b85]">Loading collections…</p>}
      {error && <p role="alert" className="mt-6 text-sm text-red-700">{error}</p>}
      {!loading && !error && filteredCollections.length === 0 && <p className="mt-6 text-sm text-[#7e8b85]">No collections found.</p>}
      {activeCollection && (
        <div>
          <button type="button" onClick={() => setActiveCollectionId(null)}
            className="mt-8 text-sm font-medium text-[#476d5b] hover:text-[#1e3b35]">Close collection</button>
          <ManuscriptList key={activeCollection.id} collection={activeCollection} refreshKey={refreshKey} />
        </div>
      )}
    </section>
  )
}
