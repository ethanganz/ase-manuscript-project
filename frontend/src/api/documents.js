export async function getCollections() {
  const response = await fetch('/api/collections')

  if (!response.ok) {
    throw new Error('Unable to load collections')
  }

  return response.json()
}

export async function createCollection(name, description) {
  const response = await fetch('/api/collections', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description }),
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(data.detail || `Could not create collection (${response.status})`)
  }

  return data
}

export async function uploadDocument(collectionId, file) {
  const formData = new FormData()
  formData.append('collection_id', collectionId)
  formData.append('file', file)

  const response = await fetch('/api/documents/upload', {
    method: 'POST',
    body: formData,
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(data.detail || `Upload failed (${response.status})`)
  }

  return data
}
