import { useEffect, useState } from 'react'
import { CollectionSection } from './components/CollectionSection.jsx'
import { CreateCollectionModal } from './components/CreateCollectionModal.jsx'
import { Header } from './components/Header.jsx'
import { Hero } from './components/Hero.jsx'
import { createCollection, getCollections, uploadFiles } from './api/documents.js'
import { MapSection } from './components/MapSection.jsx'

function App() {
  const [search, setSearch] = useState('')
  const [remoteCollections, setRemoteCollections] = useState([])
  const [collectionsLoading, setCollectionsLoading] = useState(true)
  const [collectionsError, setCollectionsError] = useState('')
  const [selectedCollection, setSelectedCollection] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [collectionName, setCollectionName] = useState('')
  const [collectionDescription, setCollectionDescription] = useState('')
  const [selectedCollectionFiles, setSelectedCollectionFiles] = useState([])
  const [creatingCollection, setCreatingCollection] = useState(false)
  const [collectionError, setCollectionError] = useState('')

  useEffect(() => {
    getCollections()
      .then((collections) => {
        setRemoteCollections(collections)
        if (collections[0]) setSelectedCollection(collections[0].id)
      })
      .catch(() => setCollectionsError('Unable to load collections'))
      .finally(() => setCollectionsLoading(false))
  }, [])

  async function handleCreateCollection(event) {
    event.preventDefault()

    const targetCollectionId = selectedCollection || null

    if (!targetCollectionId && !collectionName.trim()) {
      setCollectionError('Select an existing collection or create a new one')
      return
    }

    if (selectedCollectionFiles.length === 0) {
      setCollectionError('Select at least one file to upload')
      return
    }

    setCreatingCollection(true)
    setCollectionError('')

    try {
      let collectionId = targetCollectionId

      if (!collectionId) {
        const collection = await createCollection(
          collectionName.trim(),
          collectionDescription.trim(),
        )
        collectionId = collection.id
        // Remember it right away, so a retry uploads into it
        // instead of creating a second collection.
        setRemoteCollections((previous) => [collection, ...previous])
        setSelectedCollection(collectionId)
      }

      const report = await uploadFiles(collectionId, selectedCollectionFiles)

      const updatedCollections = await getCollections()
      setRemoteCollections(updatedCollections)
      setRefreshKey((key) => key + 1)
      setSelectedCollection(collectionId)
      setCollectionName('')
      setCollectionDescription('')
      setSelectedCollectionFiles([])
      event.target.reset()

      if (report.rejected > 0) {
        // Some files were saved, some were skipped: keep the window open and say which.
        const skipped = report.results
          .filter((r) => r.status === 'rejected')
          .map((r) => `${r.filename}: ${r.error}`)
          .join('\n')
        setCollectionError(`${report.accepted} uploaded. Skipped:\n${skipped}`)
      } else {
        setIsModalOpen(false)
      }
    } catch (error) {
      setCollectionError(error.message)
    } finally {
      setCreatingCollection(false)
    }
  }

  function openCollectionModal() {
    setCollectionError('')
    setSelectedCollectionFiles([])
    setIsModalOpen(true)
  }

  return (
    <main className="min-h-screen bg-[#f7f8f5] text-[#1e2a27]">
      <Header />

      <div id="top" className="mx-auto max-w-[1120px] px-6 py-14 lg:px-8 lg:py-20">
        <Hero onCreateCollection={openCollectionModal} />
        <CollectionSection
          collections={remoteCollections}
          loading={collectionsLoading}
          error={collectionsError}
          search={search}
          onSearchChange={setSearch}
          refreshKey={refreshKey}
        />
        <MapSection collections={remoteCollections} />
      </div>

      <CreateCollectionModal
        isOpen={isModalOpen}
        collections={remoteCollections}
        selectedCollectionId={selectedCollection}
        onCollectionChange={setSelectedCollection}
        name={collectionName}
        description={collectionDescription}
        selectedFiles={selectedCollectionFiles}
        submitting={creatingCollection}
        error={collectionError}
        onNameChange={setCollectionName}
        onDescriptionChange={setCollectionDescription}
        onFileChange={setSelectedCollectionFiles}
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleCreateCollection}
      />
    </main>
  )
}

export default App
