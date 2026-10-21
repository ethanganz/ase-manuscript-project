import { ArrowLeft, CalendarDays, FileText, FolderOpen, HardDrive, Mail, Plus } from 'lucide-react'
import { useEffect, useState } from 'react'
import { getDocuments } from '../api/documents.js'
import { CollectionPreview, formatBytes, formatDate, StatCard } from '../tools/helpers.jsx'

// Columns of the "My collections" table. Below `sm` only preview, name and size are shown.
const TABLE_COLUMNS =
  'grid grid-cols-[64px_minmax(0,1fr)_auto] items-center gap-4 sm:grid-cols-[64px_minmax(0,1fr)_96px_96px_132px]'

function OwnCollectionRow({ collection, documents }) {
  const documentCount = documents?.length
  const totalSize = documents?.reduce((sum, doc) => sum + doc.size_bytes, 0)
  const fileTypes = [...new Set((documents || []).map((doc) => doc.file_type.toUpperCase()))]

  return (
    <li className={`${TABLE_COLUMNS} px-4 py-3 transition-colors hover:bg-[#f7f9f6]`}>
      <CollectionPreview documents={documents} />

      <div className="min-w-0">
        <h3 className="truncate font-serif text-[18px] leading-tight text-[#1e302b]">
          <a href={`#collection/${collection.id}`} className="hover:underline">{collection.name}</a>
        </h3>
        <p className="mt-1 truncate text-xs text-[#8a9790]">
          {collection.description || 'No description'}
        </p>
        {fileTypes.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {fileTypes.map((type) => (
              <span key={type} className="rounded bg-[#edf1ed] px-1.5 py-0.5 text-[10px] font-semibold tracking-wide text-[#55615b]">
                {type}
              </span>
            ))}
          </div>
        )}
      </div>

      <span className="hidden text-sm text-[#55615b] sm:block">
        {documents ? documentCount : '…'}
      </span>
      <span className="text-right text-sm text-[#55615b] sm:text-left">
        {documents ? formatBytes(totalSize) : '…'}
      </span>
      <span className="hidden text-sm text-[#55615b] sm:block">
        {formatDate(collection.created_at)}
      </span>
    </li>
  )
}

/** Dashboard for the logged-in user: account details and their own collections. */
export function ProfilePage({ user, collections, isLoading, onLogin, onCreateCollection }) {
  // Documents per collection id; a missing key means still loading.
  const [documentsByCollection, setDocumentsByCollection] = useState({})

  const ownCollections = user
    ? collections.filter((collection) => collection.owner_id === user.id)
    : []
  const userId = user?.id

  // Runs again whenever App reloads the collections, e.g. after an upload.
  useEffect(() => {
    if (!userId) return
    let cancelled = false

    const ids = collections
      .filter((collection) => collection.owner_id === userId)
      .map((collection) => collection.id)

    for (const id of ids) {
      getDocuments(id)
        .catch(() => [])
        .then((documents) => {
          if (!cancelled) setDocumentsByCollection((previous) => ({ ...previous, [id]: documents }))
        })
    }

    return () => {
      cancelled = true
    }
  }, [collections, userId])

  if (!user) {
    return (
      <section className="py-24 text-center">
        <h1 className="font-serif text-4xl tracking-[-0.04em]">Your profile</h1>
        <p className="mt-3 text-sm text-[#7e8b85]">Log in to see your account and collections.</p>
        <button
          type="button"
          onClick={onLogin}
          className="mt-6 rounded-lg bg-[#1e3b35] px-5 py-2.5 text-sm font-medium text-white transition hover:bg-[#294c43]"
        >
          Log in
        </button>
      </section>
    )
  }

  const loadedDocuments = ownCollections.map((collection) => documentsByCollection[collection.id])
  const documentsReady = loadedDocuments.every(Boolean)
  const allDocuments = loadedDocuments.flatMap((documents) => documents || [])
  const totalSize = allDocuments.reduce((sum, doc) => sum + doc.size_bytes, 0)

  const fullName = [user.first_name, user.last_name].filter(Boolean).join(' ') || user.email
  const initials = [user.first_name, user.last_name]
    .filter(Boolean)
    .map((name) => name[0].toUpperCase())
    .join('') || user.email[0].toUpperCase()

  return (
    <div>
      <a href="#top" className="inline-flex items-center gap-2 text-sm text-[#6e7975] transition-colors hover:text-[#1e2a27]">
        <ArrowLeft className="size-4" />
        Back to the archive
      </a>

      <section className="mt-8 flex flex-col justify-between gap-8 border-b border-[#dfe5df] pb-12 md:flex-row md:items-end">
        <div className="flex items-center gap-5">
          <div className="flex size-20 shrink-0 items-center justify-center rounded-full bg-[#d9e4dc] font-serif text-3xl text-[#1e3b35]">
            {initials}
          </div>
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-[#8b9c91]">Your profile</p>
            <h1 className="font-serif text-4xl tracking-[-0.05em] text-[#1e302b] sm:text-5xl">{fullName}</h1>
            <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-sm text-[#71807a]">
              <span className="inline-flex items-center gap-1.5"><Mail className="size-4" />{user.email}</span>
              <span className="inline-flex items-center gap-1.5"><CalendarDays className="size-4" />Member since {formatDate(user.created_at)}</span>
            </div>
          </div>
        </div>

        <button
          type="button"
          onClick={onCreateCollection}
          className="inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-[#1e3b35] px-5 text-sm font-medium text-white shadow-[0_8px_18px_rgba(30,59,53,0.16)] transition hover:bg-[#294c43]"
        >
          <Plus />
          New collection
        </button>
      </section>

      <section className="grid gap-5 py-10 sm:grid-cols-3">
        <StatCard icon={FolderOpen} label="Collections" value={isLoading ? '…' : ownCollections.length} />
        <StatCard icon={FileText} label="Documents" value={documentsReady && !isLoading ? allDocuments.length : '…'} />
        <StatCard icon={HardDrive} label="Storage used" value={documentsReady && !isLoading ? formatBytes(totalSize) : '…'} />
      </section>

      <section className="pb-12">
        <h2 className="font-serif text-3xl tracking-[-0.04em]">My collections</h2>
        <p className="mt-2 text-sm text-[#7e8b85]">Collections you own and can upload into.</p>

        {isLoading ? (
          <div className="mt-6 h-40 animate-pulse rounded-xl border border-[#e0e6e0] bg-white" />
        ) : ownCollections.length === 0 ? (
          <p className="mt-6 rounded-xl border border-dashed border-[#cbdace] bg-white px-5 py-10 text-center text-sm text-[#7e8b85]">
            You have not created any collections yet.
          </p>
        ) : (
          <div className="mt-6 overflow-hidden rounded-xl border border-[#e0e6e0] bg-white">
            <div
              className={`${TABLE_COLUMNS} border-b border-[#e0e6e0] bg-[#f7f9f6] px-4 py-2.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#8b9c91]`}
              aria-hidden="true"
            >
              <span>Preview</span>
              <span>Collection</span>
              <span className="hidden sm:block">Files</span>
              <span className="text-right sm:text-left">Size</span>
              <span className="hidden sm:block">Created</span>
            </div>
            <ul className="divide-y divide-[#edf0ed]">
              {ownCollections.map((collection) => (
                <OwnCollectionRow
                  key={collection.id}
                  collection={collection}
                  documents={documentsByCollection[collection.id]}
                />
              ))}
            </ul>
          </div>
        )}
      </section>
    </div>
  )
}
