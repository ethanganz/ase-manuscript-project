import { FileText, FolderOpen } from "lucide-react";
import { useEffect, useState } from "react";
import { getDocuments, getPages } from "../api/documents.js";
import { pageImageUrl } from "../api/map.js";

/**
 * Thumbnail of the first page of a collection's documents.
 *
 * Starts with the first document; if it has no pages or its image can't be
 * loaded, the next document is tried, so one broken upload doesn't hide the
 * preview of the whole collection.
 *
 * Pass `documents` if they are already loaded, otherwise `collectionId` and
 * the documents are fetched here. `className` sets the size and corners.
 */
export function CollectionPreview({ documents, collectionId, className = 'h-20 w-16 rounded-md' }) {
  const [fetchedDocuments, setFetchedDocuments] = useState(undefined)
  const [documentIndex, setDocumentIndex] = useState(0)
  const [pageId, setPageId] = useState(null)
  const [failed, setFailed] = useState(false)

  const allDocuments = documents ?? fetchedDocuments
  const firstDocument = allDocuments?.[0]
  const currentDocument = allDocuments?.[documentIndex]
  const currentDocumentId = currentDocument?.id
  const outOfDocuments = allDocuments && allDocuments.length > 0 && !currentDocument

  const tryNextDocument = () => {
    setPageId(null)
    setDocumentIndex((index) => index + 1)
  }

  useEffect(() => {
    if (documents || !collectionId) return;
    let cancelled = false;

    getDocuments(collectionId)
      .then((loaded) => !cancelled && setFetchedDocuments(loaded))
      .catch(() => !cancelled && setFailed(true));

    return () => {
      cancelled = true;
    };
  }, [documents, collectionId]);

  useEffect(() => {
    if (!currentDocumentId) return
    let cancelled = false

    getPages(currentDocumentId)
      .then((pages) => {
        if (cancelled) return
        if (pages[0]) setPageId(pages[0].id)
        else tryNextDocument()
      })
      .catch(() => !cancelled && tryNextDocument())

    return () => {
      cancelled = true
    }
  }, [currentDocumentId])

  const frame = `flex items-center justify-center overflow-hidden border border-[#e0e6e0] bg-[#eef3ef] ${className}`;

  if (allDocuments && !firstDocument) {
    return (
      <div className={frame} title="No files yet">
        <FolderOpen className="size-5 text-[#a3b3a9]" />
      </div>
    );
  }

  if (failed || outOfDocuments) {
    return (
      <div className={frame} title={firstDocument?.original_filename}>
        <FileText className="size-5 text-[#a3b3a9]" />
      </div>
    );
  }

  if (!pageId) {
    return <div className={`${frame} animate-pulse`} />;
  }

  return (
    <div className={`${frame} bg-white`}>
      <img
        src={pageImageUrl(pageId)}
        alt={`First page of ${currentDocument.original_filename}`}
        loading="lazy"
        onError={tryNextDocument}
        className="size-full object-cover object-top"
      />
    </div>
  );
}

export function formatDate(value) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let size = bytes / 1024;
  let unit = 0;
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024;
    unit += 1;
  }
  return `${size.toFixed(1)} ${units[unit]}`;
}

export function StatCard({ icon: Icon, label, value }) {
  return (
    <div className="rounded-xl border border-[#e0e6e0] bg-white p-5">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-[#8b9c91]">
        <Icon className="size-4" />
        {label}
      </div>
      <p className="mt-3 font-serif text-3xl tracking-[-0.03em] text-[#1e302b]">
        {value}
      </p>
    </div>
  );
}
