import { X } from "lucide-react";
import { useEffect, useRef } from "react";
import { pageImageUrl } from "../api/map.js";
import { usePageTranscription } from "../library/usePageTranscription.js";

// Same length the backend uses when it stores a mention's snippet
// (place_linker.SNIPPET_CHARS). Python cuts by Unicode characters.
const SNIPPET_CHARS = 200;

/** Corner points of a line on the page: its outline, or else its box. */
function linePoints(line) {
  if (line.polygon?.length >= 3) {
    return line.polygon.map(([x, y]) => `${x},${y}`).join(" ");
  }
  if (line.bbox?.length === 4) {
    const [left, top, right, bottom] = line.bbox;
    return `${left},${top} ${right},${top} ${right},${bottom} ${left},${bottom}`;
  }
  return "";
}

const sameText = (a, b) => (a ?? "").toLowerCase() === (b ?? "").toLowerCase();

/**
 * The line(s) of the page the clicked mention came from.
 * The map stores the line's text as the mention's snippet, so we match on
 * that. If nothing matches (older data), fall back to lines that contain a
 * detected place with the same name.
 */
function findMentionLines(lines, mention) {
  const snippet = (mention.snippet ?? "").trim();
  if (snippet) {
    const bySnippet = lines.filter(
      (line) =>
        Array.from((line.text ?? "").trim())
          .slice(0, SNIPPET_CHARS)
          .join("") === snippet,
    );
    if (bySnippet.length > 0) return bySnippet;
  }
  return lines.filter((line) =>
    (line.places ?? []).some((p) => sameText(p.text, mention.place_name)),
  );
}

/**
 * Shows the original manuscript page a mention came from (the "evidence"),
 * with the line that mentions the place highlighted.
 *
 * Props: mention = { page_id, page_number, document_name, place_name, snippet } or null
 */
export function PageViewerModal({ mention, onClose }) {
  const pageId = mention?.page_id ?? "";
  const transcription = usePageTranscription(pageId);
  const highlightRef = useRef(null);

  // Close with the Escape key.
  useEffect(() => {
    if (!mention) return undefined;
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mention, onClose]);

  const data = transcription.data;
  const lines = data?.lines ?? [];
  const highlighted = mention ? findMentionLines(lines, mention) : [];
  const canOverlay = Boolean(data?.width && data?.height);

  // Bring the highlighted line into view once it is known.
  const firstHighlightIndex = highlighted[0]?.line_index;
  useEffect(() => {
    if (firstHighlightIndex == null) return;
    highlightRef.current?.scrollIntoView({
      block: "center",
      inline: "center",
      behavior: "smooth",
    });
  }, [pageId, firstHighlightIndex]);

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
          <div className="relative mx-auto w-fit max-w-full">
            <img
              src={pageImageUrl(mention.page_id)}
              alt={`${mention.document_name}, page ${mention.page_number}`}
              className="block h-auto max-w-full"
            />
            {canOverlay && highlighted.length > 0 && (
              <svg
                viewBox={`0 0 ${data.width} ${data.height}`}
                preserveAspectRatio="none"
                className="pointer-events-none absolute inset-0 size-full"
                aria-hidden="true"
              >
                {highlighted.map((line, i) => {
                  const points = linePoints(line);
                  if (!points) return null;
                  return (
                    <polygon
                      key={line.line_index}
                      ref={i === 0 ? highlightRef : undefined}
                      points={points}
                      vectorEffect="non-scaling-stroke"
                      strokeWidth={2}
                      className="animate-pulse fill-[#d9a520]/30 stroke-[#b8860b]"
                    />
                  );
                })}
              </svg>
            )}
          </div>
          {!transcription.loading &&
            data?.status === "complete" &&
            highlighted.length === 0 && (
              <p className="mt-3 text-center text-xs text-[#7e8b85]">
                Couldn’t locate this mention on the page image.
              </p>
            )}
        </div>
      </div>
    </div>
  );
}
