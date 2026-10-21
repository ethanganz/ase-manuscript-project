import { useEffect, useState } from 'react'
import { CollectionSection } from './components/CollectionSection.jsx'
import { CreateCollectionModal } from './components/CreateCollectionModal.jsx'
import { Header } from './components/Header.jsx'
import { Hero } from './components/Hero.jsx'
// we safely delete these two lines 
// import { ResearchSection } from './components/ResearchSection.jsx'
// import { collections as sampleCollections, places } from './data/collections.js'
import { createCollection, getCollections, uploadDocument, uploadFiles } from './api/documents.js'
import { SESSION_ENDED_EVENT, getCurrentUser, logout } from './api/auth.js'
import { AuthModal } from './components/AuthModal.jsx'

import { MapSection } from './components/MapSection.jsx'
import { ProfilePage } from './components/ProfilePage.jsx'
import { CollectionViewer } from './components/CollectionViewer.jsx'

const PROFILE_HASH = '#profile'
const COLLECTION_HASH_PREFIX = '#collection/'

function App() {
  const [user, setUser] = useState(null)
  const [hash, setHash] = useState(window.location.hash)
  const isProfileOpen = hash === PROFILE_HASH
  const openCollectionId = hash.startsWith(COLLECTION_HASH_PREFIX)
    ? hash.slice(COLLECTION_HASH_PREFIX.length)
    : ''
  const [isAuthOpen, setIsAuthOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [remoteCollections, setRemoteCollections] = useState([])
  const [selectedCollection, setSelectedCollection] = useState('')
  const [selectedFile, setSelectedFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState(null)
  const [uploadError, setUploadError] = useState('')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [collectionName, setCollectionName] = useState('')
  const [collectionDescription, setCollectionDescription] = useState('')
  const [collectionIsPublic, setCollectionIsPublic] = useState(true)
  const [selectedCollectionFiles, setSelectedCollectionFiles] = useState([])
  const [creatingCollection, setCreatingCollection] = useState(false)
  const [collectionError, setCollectionError] = useState('')
  const [loadingCollections, setLoadingCollections] = useState(true)

  useEffect(() => {
    getCurrentUser()
      .then(setUser)
      .catch(() => setUser(null))

    // Any API call answering 401 means the login expired.
    const onSessionEnded = () => setUser(null)
    window.addEventListener(SESSION_ENDED_EVENT, onSessionEnded)
    return () => window.removeEventListener(SESSION_ENDED_EVENT, onSessionEnded)
  }, [])

  // The profile page lives at #profile and a collection at #collection/<id>;
  // any other hash shows the archive.
  useEffect(() => {
    const onHashChange = () => {
      const { hash: newHash } = window.location
      setHash(newHash)
      if (newHash === PROFILE_HASH || newHash.startsWith(COLLECTION_HASH_PREFIX)) {
        window.scrollTo(0, 0)
      } else {
        // The section only exists after the archive renders again.
        requestAnimationFrame(() => {
          const target = window.location.hash && document.querySelector(window.location.hash)
          target?.scrollIntoView()
        })
      }
    }
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  async function handleLogout() {
    await logout()
    setUser(null)
    setIsModalOpen(false)
  }

  function handleAuthenticated(loggedInUser) {
    setUser(loggedInUser)
    setIsAuthOpen(false)
  }

  // Users can only upload into collections they own.
  const ownCollections = user
    ? remoteCollections.filter((collection) => collection.owner_id === user.id)
    : []

  useEffect(() => {
    let timer = null

    getCollections()
      .then((collections) => {
        timer = setTimeout(() => {
          setRemoteCollections(collections)
          if (collections[0]) setSelectedCollection(collections[0].id)
          setLoadingCollections(false)
        }, 400)
      })
      .catch(() => {
        setRemoteCollections([])
        setLoadingCollections(false)
      })

    return () => {
      if (timer) clearTimeout(timer)
    }
    // Reload on login/logout: private collections are only listed for their owner.
  }, [user?.id])

  async function handleUpload(event) {
    event.preventDefault()

    if (!selectedCollection || !selectedFile) {
      setUploadError('Select a collection and choose a file')
      return
    }

    setUploading(true)
    setUploadError('')
    setUploadResult(null)

    try {
      const result = await uploadDocument(selectedCollection, selectedFile)
      setUploadResult(result)
      setSelectedFile(null)
      event.target.reset()
    } catch (error) {
      setUploadError(error.message)
    } finally {
      setUploading(false)
    }
  }

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
          collectionIsPublic,
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
      setSelectedCollection(collectionId)
      setCollectionName('')
      setCollectionDescription('')
      setCollectionIsPublic(true)
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
    if (!user) {
      setIsAuthOpen(true)
      return
    }
    if (!ownCollections.some((collection) => collection.id === selectedCollection)) {
      setSelectedCollection(ownCollections[0]?.id || '')
    }
    setCollectionError('')
    setSelectedCollectionFiles([])
    setIsModalOpen(true)
  }

  return (
    <main className="min-h-screen bg-[#f7f8f5] text-[#1e2a27]">
      <Header user={user} onLogin={() => setIsAuthOpen(true)} onLogout={handleLogout} />

      {/* The collection viewer is a full-height workspace: wider, with less padding. */}
      <div
        id="top"
        className={
          openCollectionId
            ? 'mx-auto max-w-[1600px] px-4 py-4 lg:px-6'
            : 'mx-auto max-w-[1120px] px-6 py-14 lg:px-8 lg:py-20'
        }
      >
        {openCollectionId ? (
          <CollectionViewer
            key={openCollectionId}
            collectionId={openCollectionId}
            collections={remoteCollections}
            isLoadingCollections={loadingCollections}
          />
        ) : isProfileOpen ? (
          <ProfilePage
            user={user}
            collections={remoteCollections}
            isLoading={loadingCollections}
            onLogin={() => setIsAuthOpen(true)}
            onCreateCollection={openCollectionModal}
          />
        ) : (
          <>
            <Hero onCreateCollection={openCollectionModal} />
            <CollectionSection
              collections={remoteCollections}
              search={search}
              onSearchChange={setSearch}
              isLoading={loadingCollections}
            />
            {/* <UploadSection
              collections={remoteCollections}
              selectedCollection={selectedCollection}
              onCollectionChange={setSelectedCollection}
              selectedFile={selectedFile}
              onFileChange={setSelectedFile}
              uploading={uploading}
              uploadError={uploadError}
              uploadResult={uploadResult}
              onSubmit={handleUpload}
            /> */}
            {/* <ResearchSection places={places} /> */}
            <MapSection collections={remoteCollections} />
          </>
        )}
      </div>

      <CreateCollectionModal
        isOpen={isModalOpen}
        collections={ownCollections}
        selectedCollectionId={selectedCollection}
        onCollectionChange={setSelectedCollection}
        name={collectionName}
        description={collectionDescription}
        isPublic={collectionIsPublic}
        onIsPublicChange={setCollectionIsPublic}
        selectedFiles={selectedCollectionFiles}
        submitting={creatingCollection}
        error={collectionError}
        onNameChange={setCollectionName}
        onDescriptionChange={setCollectionDescription}
        onFileChange={setSelectedCollectionFiles}
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleCreateCollection}
      />

      <AuthModal
        isOpen={isAuthOpen}
        onAuthenticated={handleAuthenticated}
        onClose={() => setIsAuthOpen(false)}
      />
    </main>
  )
}

export default App