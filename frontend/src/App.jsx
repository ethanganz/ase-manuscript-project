import { useEffect, useState } from 'react'
import { CollectionSection } from './components/CollectionSection.jsx'
import { CreateCollectionModal } from './components/CreateCollectionModal.jsx'
import { Header } from './components/Header.jsx'
import { Hero } from './components/Hero.jsx'
import { ResearchSection } from './components/ResearchSection.jsx'
import { UploadSection } from './components/UploadSection.jsx'
import { createCollection, getCollections, uploadDocument } from './api/documents.js'
import { collections as sampleCollections, places } from './data/collections.js'

function App() {
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
  const [selectedCollectionFiles, setSelectedCollectionFiles] = useState([])
  const [creatingCollection, setCreatingCollection] = useState(false)
  const [collectionError, setCollectionError] = useState('')

  useEffect(() => {
    getCollections()
      .then((collections) => {
        setRemoteCollections(collections)
        if (collections[0]) setSelectedCollection(collections[0].id)
      })
      .catch(() => setRemoteCollections([]))
  }, [])

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
        )
        collectionId = collection.id
      }

      for (const file of selectedCollectionFiles) {
        await uploadDocument(collectionId, file)
      }

      const updatedCollections = await getCollections()
      setRemoteCollections(updatedCollections)
      setSelectedCollection(collectionId)
      setCollectionName('')
      setCollectionDescription('')
      setSelectedCollectionFiles([])
      event.target.reset()
      setIsModalOpen(false)
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
          search={search}
          onSearchChange={setSearch}
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
        <ResearchSection places={places} />
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