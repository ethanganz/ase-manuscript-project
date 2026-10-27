import { Globe, Lock, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

const uploadStages = [
  "Preparing files",
  "Analyzing documents",
  "Indexing manuscript pages",
  "Finalizing collection",
];

export function CreateCollectionModal({
  isOpen,
  collections,
  selectedCollectionId,
  onCollectionChange,
  name,
  description,
  isPublic,
  onIsPublicChange,
  selectedFiles,
  submitting,
  error,
  onNameChange,
  onDescriptionChange,
  onFileChange,
  onClose,
  onSubmit,
}) {
  const [stageIndex, setStageIndex] = useState(0);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (!submitting) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setStageIndex(() => 0);
      setProgress(() => 0);
      return;
    }

    const stageTimer = setInterval(() => {
      setStageIndex((current) => (current + 1) % uploadStages.length);
    }, 900);

    const progressTimer = setInterval(() => {
      setProgress((current) => {
        const next = current + 12;
        return next >= 96 ? 96 : next;
      });
    }, 350);

    return () => {
      clearInterval(stageTimer);
      clearInterval(progressTimer);
    };
  }, [submitting]);

  const activeLabel = useMemo(() => {
    if (!submitting)
      return selectedCollectionId ? "Upload files" : "Create collection";
    return uploadStages[stageIndex];
  }, [selectedCollectionId, stageIndex, submitting]);

  if (!isOpen) return null;

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
              disabled={submitting}
              className="mt-2 w-full rounded-lg border border-[#dfe5df] bg-white px-3 py-2.5 outline-none focus:border-[#6f8e7b] disabled:cursor-not-allowed disabled:bg-[#f4f6f4]"
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
                  disabled={submitting}
                  className="mt-2 w-full rounded-lg border border-[#dfe5df] bg-white px-3 py-2.5 outline-none focus:border-[#6f8e7b] disabled:cursor-not-allowed disabled:bg-[#f4f6f4]"
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
                  disabled={submitting}
                  className="mt-2 min-h-24 w-full resize-y rounded-lg border border-[#dfe5df] bg-white px-3 py-2.5 outline-none focus:border-[#6f8e7b] disabled:cursor-not-allowed disabled:bg-[#f4f6f4]"
                  placeholder="Optional description"
                  maxLength={2000}
                />
              </label>

              <fieldset disabled={submitting}>
                <legend className="text-sm font-medium text-[#374b45]">
                  Visibility
                </legend>
                <div className="mt-2 grid grid-cols-2 gap-2">
                  {[
                    {
                      value: true,
                      icon: Globe,
                      label: "Public",
                      hint: "Everyone can browse it",
                    },
                    {
                      value: false,
                      icon: Lock,
                      label: "Private",
                      hint: "Only you can see it",
                    },
                  ].map(({ value, icon: Icon, label, hint }) => (
                    <label
                      key={label}
                      className={`flex cursor-pointer items-start gap-2.5 rounded-lg border px-3 py-2.5 transition-colors has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-[#6f8e7b] has-[:disabled]:cursor-not-allowed has-[:disabled]:opacity-60 ${
                        isPublic === value
                          ? "border-[#1e3b35] bg-[#f5faf6]"
                          : "border-[#dfe5df] hover:bg-[#fbfcfa]"
                      }`}
                    >
                      <input
                        type="radio"
                        name="visibility"
                        checked={isPublic === value}
                        onChange={() => onIsPublicChange(value)}
                        className="sr-only"
                      />
                      <Icon className="mt-0.5 size-4 shrink-0 text-[#476d5b]" />
                      <span>
                        <span className="block text-sm font-medium text-[#1e302b]">
                          {label}
                        </span>
                        <span className="block text-xs text-[#7e8b85]">
                          {hint}
                        </span>
                      </span>
                    </label>
                  ))}
                </div>
              </fieldset>
            </>
          )}

          <label className="block text-sm font-medium text-[#374b45]">
            Documents to upload
            <input
              type="file"
              multiple
              accept=".pdf,.jpg,.jpeg,.png,.heic,.zip"
              disabled={submitting}
              onChange={(event) =>
                onFileChange(Array.from(event.target.files || []))
              }
              className="mt-2 block w-full rounded-lg border border-dashed border-[#cbd8cc] bg-[#fbfcfa] px-3 py-2.5 text-sm file:mr-4 file:rounded file:border-0 file:bg-[#1e3b35] file:px-3 file:py-2 file:text-white disabled:cursor-not-allowed disabled:opacity-60"
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

          {submitting && (
            <div className="rounded-xl border border-[#dfe5df] bg-[#f5faf6] p-3">
              <div className="flex items-center justify-between text-[10px] font-semibold uppercase tracking-[0.15em] text-[#60716a]">
                <span>Processing</span>
                <span>{progress}%</span>
              </div>

              <div className="mt-3 h-2.5 overflow-hidden rounded-full bg-[#e4ece6]">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-[#1e3b35] via-[#527667] to-[#b9d2c3] transition-all duration-500 ease-out"
                  style={{ width: `${progress}%` }}
                />
              </div>

              <div className="mt-3 flex items-center gap-2 text-sm text-[#355248]">
                <span className="inline-flex h-2.5 w-2.5 animate-pulse rounded-full bg-[#1e3b35]" />
                <span>{uploadStages[stageIndex]}</span>
              </div>
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
              disabled={submitting}
              className="rounded-lg border border-[#cbdace] px-4 py-2.5 text-sm font-medium text-[#476d5b] hover:bg-[#edf1ed] disabled:cursor-not-allowed disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={
                submitting ||
                (selectedCollectionId === "" && name.trim() === "") ||
                selectedFiles.length === 0
              }
              className="rounded-lg bg-[#1e3b35] px-4 py-2.5 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
            >
              {submitting
                ? activeLabel
                : selectedCollectionId
                  ? "Upload files"
                  : "Create collection"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
