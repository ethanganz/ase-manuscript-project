import { apiFetch } from "./auth.js";

export async function getCollections() {
  const response = await apiFetch("/api/collections");

  if (!response.ok) {
    throw new Error("Unable to load collections");
  }

  return response.json();
}

export async function getDocuments(collectionId) {
  const response = await apiFetch(`/api/collections/${collectionId}/documents`);

  if (!response.ok) {
    throw new Error("Unable to load documents");
  }

  return response.json();
}

export async function getPages(documentId) {
  const response = await apiFetch(`/api/documents/${documentId}/pages`);

  if (!response.ok) {
    throw new Error("Unable to load pages");
  }

  return response.json();
}

export async function createCollection(name, description, isPublic = true) {
  const response = await apiFetch("/api/collections", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, description, is_public: isPublic }),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      data.detail || `Could not create collection (${response.status})`,
    );
  }

  return data;
}

/** Change a collection's name and/or description. Only the owner may do this. */
export async function updateCollection(collectionId, changes) {
  const response = await apiFetch(`/api/collections/${collectionId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(changes),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    // 422 from FastAPI is a list of field errors; show the first one.
    const detail = Array.isArray(data.detail)
      ? data.detail[0]?.msg
      : data.detail;
    throw new Error(detail || `Could not save changes (${response.status})`);
  }

  return data;
}

/** language: "de" | "la" | "unknown" — helps handwriting recognition. */
export async function uploadFiles(collectionId, files, language = "unknown") {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file); // same field name repeated = many files
  }
  formData.append("language", language);

  const response = await apiFetch(`/api/collections/${collectionId}/uploads`, {
    method: "POST",
    body: formData, // do not set Content-Type, the browser adds it
  });

  const data = await response.json().catch(() => ({}));

  // 201 = at least one file was accepted
  if (response.ok) return data;

  // 422 with a report = every file was rejected
  if (Array.isArray(data.results)) {
    throw new Error(
      data.results.map((r) => `${r.filename}: ${r.error}`).join("\n"),
    );
  }
  if (response.status === 413) {
    throw new Error("Files are too large to upload");
  }
  throw new Error(
    typeof data.detail === "string"
      ? data.detail
      : `Upload failed (${response.status})`,
  );
}

/** Recognized lines of one page: { status, error, language, lines }. */
export async function getPageTranscription(pageId) {
  const response = await apiFetch(`/api/pages/${pageId}/transcription`);

  if (!response.ok) {
    throw new Error("Unable to load transcription");
  }

  return response.json();
}

/** Run handwriting recognition again on every page. Only the owner may do this. */
export async function transcribeDocument(documentId) {
  const response = await apiFetch(`/api/documents/${documentId}/transcribe`, {
    method: "POST",
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : `Could not start transcription (${response.status})`,
    );
  }

  return data;
}

// Kept so any old code that uploads a single file still works.
export async function uploadDocument(collectionId, file) {
  const report = await uploadFiles(collectionId, [file]);
  return { id: report.results[0]?.document_id, ...report };
}
