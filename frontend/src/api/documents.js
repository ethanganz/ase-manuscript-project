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

export async function uploadFiles(collectionId, files) {
  const formData = new FormData()
  for (const file of files) {
    formData.append('files', file) // same field name repeated = many files
  }

  const response = await fetch(`/api/collections/${collectionId}/uploads`, {
    method: 'POST',
    body: formData, // do not set Content-Type, the browser adds it
  })

  const data = await response.json().catch(() => ({}))

  // 201 = at least one file was accepted
  if (response.ok) return data

  // 422 with a report = every file was rejected
  if (Array.isArray(data.results)) {
    throw new Error(data.results.map((r) => `${r.filename}: ${r.error}`).join('\n'))
  }
  if (response.status === 413) {
    throw new Error('Files are too large to upload')
  }
  throw new Error(
    typeof data.detail === 'string' ? data.detail : `Upload failed (${response.status})`,
  )
}

// Kept so any old code that uploads a single file still works.
export async function uploadDocument(collectionId, file) {
  const report = await uploadFiles(collectionId, [file])
  return { id: report.results[0]?.document_id, ...report }
}

