import { X } from "lucide-react";
import { useEffect } from "react";
import { pageImageUrl } from "../api/map.js";

/**
 * Shows the original manuscript page a mention came from (the "evidence").
 * This is a simple viewer so the click-through works today. If the team (maybe AM) builds
 * a full document viewer later, replace this component and keep the same props.
 *
 * Props: mention = { page_id, page_number, document_name, place_name, snippet } or null
 */
export function PageViewerModal({ mention, onClose }) {
  // Close with the Escape key.
  useEffect(() => {
    if (!mention) return undefined;
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mention, onClose]);

  if (!mention) return null;

  return (
    <div
      className="fixed inset-0 z-[2000] flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={`${mention.document_name}, page ${mention.page_number}`}
    >
      <div
        className="flex max-h-[92vh] w-full max-w-[900px] flex-col overflow-hidden rounded-xl bg-white"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4 border-b border-[#edf0ed] px-5 py-4">
          <div>
            <p className="font-medium">
              {mention.document_name}{" "}
              <span className="text-[#7e8b85]">
                · page {mention.page_number}
              </span>
            </p>
            <p className="text-sm text-[#6e7975]">
              Mentions <strong>{mention.place_name}</strong>
              {mention.snippet ? <> — “{mention.snippet}”</> : null}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded p-1 hover:bg-[#edf1ed]"
          >
            <X className="size-5" />
          </button>
        </div>

        <div className="overflow-auto bg-[#f2f4f1] p-4">
          <img
            src={pageImageUrl(mention.page_id)}
            alt={`${mention.document_name}, page ${mention.page_number}`}
            className="mx-auto h-auto max-w-full"
          />
        </div>
      </div>
    </div>
  );
}
