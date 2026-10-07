import { Upload } from 'lucide-react'

export function UploadSection({
  collections,
  selectedCollection,
  onCollectionChange,
  selectedFile,
  onFileChange,
  uploading,
  uploadError,
  uploadResult,
  onSubmit,
}) {
  return (
    <section className="border-t border-[#dfe5df] pt-12">
      <div className="max-w-2xl rounded-xl border border-[#e0e6e0] bg-white p-6">
        <div className="flex items-center gap-3">
          <div className="grid size-10 place-items-center rounded-lg bg-[#eef3ee] text-[#1e3b35]">
            <Upload className="size-5" />
          </div>
          <div>
            <h2 className="font-serif text-2xl tracking-[-0.03em]">Upload a document</h2>
            <p className="mt-1 text-sm text-[#7e8b85]">
              Supported: PDF, JPEG, PNG, and HEIC. The record is created immediately.
            </p>
          </div>
        </div>

        <form className="mt-6 space-y-4" onSubmit={onSubmit}>
          <label className="block text-sm font-medium text-[#374b45]">
            Collection
            <select
              className="mt-2 w-full rounded-lg border border-[#dfe5df] bg-white px-3 py-2.5 outline-none focus:border-[#6f8e7b]"
              value={selectedCollection}
              onChange={(event) => onCollectionChange(event.target.value)}
            >
              <option value="">Select a collection</option>
              {collections.map((collection) => (
                <option key={collection.id} value={collection.id}>
                  {collection.name}
                </option>
              ))}
            </select>
          </label>

          <label className="block text-sm font-medium text-[#374b45]">
            File
            <input
              className="mt-2 block w-full rounded-lg border border-dashed border-[#cbd8cc] bg-[#fbfcfa] px-3 py-2.5 text-sm file:mr-4 file:rounded file:border-0 file:bg-[#1e3b35] file:px-3 file:py-2 file:text-white"
              type="file"
              accept=".pdf,.jpg,.jpeg,.png,.heic"
              onChange={(event) => onFileChange(event.target.files?.[0] || null)}
            />
          </label>

          {uploadError && (
            <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {uploadError}
            </p>
          )}

          {uploadResult && (
            <p className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-700">
              Uploaded successfully. Document ID: {uploadResult.id}
            </p>
          )}

          <button
            type="submit"
            disabled={uploading || !selectedCollection || !selectedFile}
            className="inline-flex items-center justify-center rounded-lg bg-[#1e3b35] px-4 py-2.5 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {uploading ? 'Uploading…' : 'Upload document'}
          </button>
        </form>
      </div>
    </section>
  )
}
