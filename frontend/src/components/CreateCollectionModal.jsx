import { X } from 'lucide-react'

export function CreateCollectionModal({
  isOpen,
  collections,
  selectedCollectionId,
  onCollectionChange,
  name,
  description,
  selectedFiles,
  submitting,
  error,
  onNameChange,
  onDescriptionChange,
  onFileChange,
  onClose,
  onSubmit,
}) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-xl border border-[#dfe5df] bg-white p-6 shadow-xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="font-serif text-2xl tracking-[-0.03em] text-[#1e302b]">
              Create collection
            </h2>
            <p className="mt-1 text-sm text-[#7e8b85]">
              Add a collection before uploading documents.
            </p>
          </div>

          <button
            type="button"
            aria-label="Close collection form"
            onClick={onClose}
            className="rounded-lg p-2 text-[#6e7975] hover:bg-[#edf1ed]"
          >
            <X className="size-5" />
          </button>
        </div>

        <form className="mt-6 space-y-4" onSubmit={onSubmit}>
          <label className="block text-sm font-medium text-[#374b45]">
            Collection
            <select
              value={selectedCollectionId}
              onChange={(event) => onCollectionChange(event.target.value)}
              className="mt-2 w-full rounded-lg border border-[#dfe5df] bg-white px-3 py-2.5 outline-none focus:border-[#6f8e7b]"
            >
              <option value="">Create a new collection</option>
              {collections.map((collection) => (
                <option key={collection.id} value={collection.id}>
                  {collection.name}
                </option>
              ))}
            </select>
          </label>

          {!selectedCollectionId && (
            <>
              <label className="block text-sm font-medium text-[#374b45]">
                Collection name
                <input
                  type="text"
                  value={name}
                  onChange={(event) => onNameChange(event.target.value)}
                  className="mt-2 w-full rounded-lg border border-[#dfe5df] bg-white px-3 py-2.5 outline-none focus:border-[#6f8e7b]"
                  placeholder="Letters of Henri Dupont"
                  required
                  maxLength={200}
                />
              </label>

              <label className="block text-sm font-medium text-[#374b45]">
                Description
                <textarea
                  value={description}
                  onChange={(event) => onDescriptionChange(event.target.value)}
                  className="mt-2 min-h-24 w-full resize-y rounded-lg border border-[#dfe5df] bg-white px-3 py-2.5 outline-none focus:border-[#6f8e7b]"
                  placeholder="Optional description"
                  maxLength={2000}
                />
              </label>
            </>
          )}

          <label className="block text-sm font-medium text-[#374b45]">
            Documents to upload
            <input
              type="file"
              multiple
              accept=".pdf,.jpg,.jpeg,.png,.heic,.zip"
              onChange={(event) => onFileChange(Array.from(event.target.files || []))}
              className="mt-2 block w-full rounded-lg border border-dashed border-[#cbd8cc] bg-[#fbfcfa] px-3 py-2.5 text-sm file:mr-4 file:rounded file:border-0 file:bg-[#1e3b35] file:px-3 file:py-2 file:text-white"
            />
          </label>

          {selectedFiles.length > 0 && (
            <div className="space-y-1 text-sm text-[#476d5b]">
              <p>Selected files:</p>
              <ul className="max-h-28 list-inside list-disc overflow-y-auto">
                {selectedFiles.map((file) => (
                  <li key={`${file.name}-${file.lastModified}`}>{file.name}</li>
                ))}
              </ul>
            </div>
          )}

          {error && (
            <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {error}
            </p>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-[#cbdace] px-4 py-2.5 text-sm font-medium text-[#476d5b] hover:bg-[#edf1ed]"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || (selectedCollectionId === '' && name.trim() === '') || selectedFiles.length === 0}
              className="rounded-lg bg-[#1e3b35] px-4 py-2.5 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              {submitting ? 'Uploading…' : selectedCollectionId ? 'Upload files' : 'Create collection'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
