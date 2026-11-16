import "leaflet/dist/leaflet.css";
import {
  ArrowLeft,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  Expand,
  FileText,
  Flag,
  Loader2,
  MapPin,
  Maximize2,
  Minimize2,
  RotateCw,
  Shrink,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { useEffect, useState } from "react";
import { CircleMarker, MapContainer, TileLayer, Tooltip } from "react-leaflet";
import { getDocuments, getPages } from "../api/documents.js";
import { pageImageUrl } from "../api/map.js";
import { startPageTranscription } from "../api/transcription.js";
import { useFetch } from "../libraray/useFetch.js";
import { usePageTranscription } from "../libraray/usePageTranscription.js";
import { ReportCollectionModal } from "./ReportCollectionModal.jsx";

// On large screens the viewer fills the window below the 76px header (minus
// the 2rem App padding), so page and transcription show without scrolling.
// Smaller screens stack the panels, each 70% of the window high.
const VIEWER_HEIGHT = "lg:h-[calc(100dvh-76px-2rem)]";
const PANEL =
  "flex h-[70vh] min-h-0 flex-col overflow-hidden rounded-xl border border-[#e0e6e0] bg-white lg:h-full";
const PANEL_BAR =
  "flex h-11 shrink-0 items-center justify-between gap-3 border-b border-[#edf0ed] px-3";
const ICON_BUTTON =
  "rounded p-1.5 text-[#55615b] transition-colors hover:bg-[#edf1ed] disabled:opacity-30";
const ZOOM_STEPS = [1, 1.5, 2, 3];

/** Maximize one panel, or go back to both side by side. */
function FocusButton({ isFocused, onToggle, label }) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className={`${ICON_BUTTON} hidden lg:block`}
      title={
        isFocused
          ? "Show page and transcription side by side"
          : `Maximize ${label}`
      }
      aria-label={
        isFocused
          ? "Show page and transcription side by side"
          : `Maximize ${label}`
      }
    >
      {isFocused ? (
        <Minimize2 className="size-4" />
      ) : (
        <Maximize2 className="size-4" />
      )}
    </button>
  );
}

/** Row of documents to switch between. */
function DocumentTabs({ documents, selectedId, onSelect }) {
  return (
    <div
      className="flex shrink-0 gap-2 overflow-x-auto pb-1"
      role="tablist"
      aria-label="Documents"
    >
      {documents.map((doc) => {
        const isSelected = doc.id === selectedId;
        return (
          <button
            key={doc.id}
            type="button"
            role="tab"
            aria-selected={isSelected}
            onClick={() => onSelect(doc.id)}
            className={`flex shrink-0 items-center gap-2 rounded-lg border px-3 py-1.5 text-sm transition-colors ${
              isSelected
                ? "border-[#1e3b35] bg-[#1e3b35] text-white"
                : "border-[#dfe5df] bg-white text-[#55615b] hover:border-[#c3d2c7] hover:bg-[#f7f9f6]"
            }`}
          >
            <FileText className="size-4 shrink-0" />
            <span className="max-w-[200px] truncate">
              {doc.original_filename}
            </span>
            <span
              className={`text-[10px] font-semibold tracking-wide ${isSelected ? "text-white/70" : "text-[#8a9790]"}`}
            >
              {doc.file_type.toUpperCase()}
            </span>
          </button>
        );
      })}
    </div>
  );
}

/** Left side: the page image, fitted to the panel, with page and zoom controls. */
function PageImagePanel({
  document,
  pages,
  pageIndex,
  onPageChange,
  loading,
  isFocused,
  onToggleFocus,
}) {
  const [zoom, setZoom] = useState(1); // 1 = whole page fits the panel
  const page = pages[pageIndex];
  const zoomStep = ZOOM_STEPS.indexOf(zoom);

  return (
    <div className={PANEL}>
      <div className={PANEL_BAR}>
        <p className="min-w-0 truncate text-sm font-medium text-[#1e302b]">
          {document.original_filename}
        </p>

        <div className="flex shrink-0 items-center gap-0.5 text-xs text-[#6e7975]">
          {pages.length > 1 && (
            <>
              <button
                type="button"
                onClick={() => onPageChange(pageIndex - 1)}
                disabled={pageIndex === 0}
                className={ICON_BUTTON}
                aria-label="Previous page"
              >
                <ChevronLeft className="size-4" />
              </button>
              <span className="px-1 tabular-nums">
                {pageIndex + 1} / {pages.length}
              </span>
              <button
                type="button"
                onClick={() => onPageChange(pageIndex + 1)}
                disabled={pageIndex === pages.length - 1}
                className={ICON_BUTTON}
                aria-label="Next page"
              >
                <ChevronRight className="size-4" />
              </button>
              <span className="mx-1 h-4 w-px bg-[#e0e6e0]" />
            </>
          )}
          <button
            type="button"
            onClick={() => setZoom(ZOOM_STEPS[zoomStep - 1])}
            disabled={zoomStep === 0}
            className={ICON_BUTTON}
            aria-label="Zoom out"
          >
            <ZoomOut className="size-4" />
          </button>
          <button
            type="button"
            onClick={() => setZoom(1)}
            className="w-11 rounded py-1 tabular-nums hover:bg-[#edf1ed]"
            title="Fit page"
          >
            {zoom === 1 ? "Fit" : `${zoom * 100}%`}
          </button>
          <button
            type="button"
            onClick={() => setZoom(ZOOM_STEPS[zoomStep + 1])}
            disabled={zoomStep === ZOOM_STEPS.length - 1}
            className={ICON_BUTTON}
            aria-label="Zoom in"
          >
            <ZoomIn className="size-4" />
          </button>
          <FocusButton
            isFocused={isFocused}
            onToggle={onToggleFocus}
            label="page"
          />
        </div>
      </div>

      <div
        className={`min-h-0 flex-1 overflow-auto bg-[#f2f4f1] p-3 ${
          zoom === 1 ? "flex items-center justify-center" : ""
        }`}
      >
        {loading ? (
          <div className="mx-auto h-full w-2/3 animate-pulse rounded bg-[#e4ece5]" />
        ) : page ? (
          <img
            key={page.id}
            src={pageImageUrl(page.id)}
            alt={`${document.original_filename}, page ${page.page_number}`}
            style={
              zoom === 1
                ? undefined
                : { width: `${zoom * 100}%`, maxWidth: "none" }
            }
            className={`mx-auto shadow-[0_4px_16px_rgba(30,42,39,0.12)] ${
              zoom === 1 ? "max-h-full max-w-full object-contain" : "h-auto"
            }`}
          />
        ) : (
          <p className="text-sm text-[#7e8b85]">
            No pages available for this file.
          </p>
        )}
      </div>
    </div>
  );
}

/**
 * Highlights the place mentions of one line.
 * Offsets from the server count Unicode characters (not UTF-16 units),
 * so the text is split with Array.from before cutting.
 */
function highlightPlaces(text, mentions) {
  if (!mentions?.length) return text;
  const chars = Array.from(text);

  // Merge overlapping mentions so every character is shown once.
  const spans = [];
  for (const { start, end } of [...mentions].sort(
    (a, b) => a.start - b.start || a.end - b.end,
  )) {
    const last = spans[spans.length - 1];
    if (last && start <= last[1]) last[1] = Math.max(last[1], end);
    else spans.push([start, end]);
  }

  const parts = [];
  let cursor = 0;
  spans.forEach(([start, end], index) => {
    parts.push(chars.slice(cursor, start).join(""));
    parts.push(
      <mark key={index} className="rounded bg-[#e3ece5] px-0.5 text-[#1e3b35]">
        {chars.slice(start, end).join("")}
      </mark>,
    );
    cursor = end;
  });
  parts.push(chars.slice(cursor).join(""));
  return parts;
}

/** Message shown in the transcription panel instead of text. */
function TranscriptionNotice({ icon: Icon, spin, title, children, action }) {
  return (
    <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-2 px-6 text-center">
      <Icon className={`size-6 text-[#8a9790] ${spin ? "animate-spin" : ""}`} />
      <p className="text-sm font-medium text-[#1e302b]">{title}</p>
      {children && (
        <p className="max-w-sm text-sm text-[#7e8b85]">{children}</p>
      )}
      {action}
    </div>
  );
}

/** Right side: what the model read on the current page, one row per line. */
function TranscriptionPanel({
  transcription,
  loading,
  error,
  pageNumber,
  canTranscribe,
  onTranscribe,
  isStarting,
  startError,
  isFocused,
  onToggleFocus,
}) {
  const status = transcription?.status;
  const lines = transcription?.lines ?? [];

  const startButton = (label) =>
    canTranscribe && (
      <button
        type="button"
        onClick={onTranscribe}
        disabled={isStarting}
        className="mt-2 flex items-center gap-2 rounded-lg bg-[#1e3b35] px-4 py-2 text-sm text-white transition-colors hover:bg-[#2a4d45] disabled:opacity-50"
      >
        {isStarting ? (
          <Loader2 className="size-4 animate-spin" />
        ) : (
          <RotateCw className="size-4" />
        )}
        {label}
      </button>
    );

  let body;
  if (loading) {
    body = (
      <div className="space-y-3 p-4">
        {[80, 95, 70, 90, 60].map((width) => (
          <div
            key={width}
            style={{ width: `${width}%` }}
            className="h-4 animate-pulse rounded bg-[#e4ece5]"
          />
        ))}
      </div>
    );
  } else if (error) {
    body = (
      <TranscriptionNotice icon={FileText} title="Could not load the text">
        {error}
      </TranscriptionNotice>
    );
  } else if (status === "queued" || status === "running") {
    body = (
      <TranscriptionNotice
        icon={Loader2}
        spin
        title={
          status === "queued" ? "Waiting in line…" : "Reading the handwriting…"
        }
      >
        This can take a few minutes. The text appears here as soon as it is
        ready.
      </TranscriptionNotice>
    );
  } else if (status === "failed") {
    body = (
      <TranscriptionNotice
        icon={FileText}
        title="This page could not be transcribed"
        action={startButton("Try again")}
      >
        {transcription.error}
      </TranscriptionNotice>
    );
  } else if (status === "complete" && lines.length === 0) {
    body = (
      <TranscriptionNotice icon={FileText} title="No text lines were found">
        The page was processed, but no handwritten lines were detected.
      </TranscriptionNotice>
    );
  } else if (status === "complete") {
    body = (
      <ol className="min-h-0 flex-1 overflow-auto px-4 py-4 font-serif text-[16px] leading-8 text-[#2a3833]">
        {lines.map((line) => (
          <li key={line.line_index} className="grid grid-cols-[2rem_1fr] gap-3">
            <span className="select-none text-right font-sans text-xs leading-8 text-[#b0bab5]">
              {line.line_index + 1}
            </span>
            <span>
              {line.text ? highlightPlaces(line.text, line.places) : " "}
            </span>
          </li>
        ))}
      </ol>
    );
  } else {
    body = (
      <TranscriptionNotice
        icon={FileText}
        title="Not transcribed yet"
        action={startButton("Transcribe this page")}
      >
        {canTranscribe
          ? "Start the handwriting recognition for this page."
          : "The text of this page is not available yet."}
      </TranscriptionNotice>
    );
  }

  return (
    <div className={PANEL}>
      <div className={PANEL_BAR}>
        <p className="truncate text-sm font-medium text-[#1e302b]">
          Transcription · page {pageNumber}
          {status === "complete" && lines.length > 0 && (
            <span className="font-normal text-[#8a9790]">
              {" "}
              · {lines.length} {lines.length === 1 ? "line" : "lines"}
            </span>
          )}
        </p>
        <div className="flex shrink-0 items-center gap-2">
          <FocusButton
            isFocused={isFocused}
            onToggle={onToggleFocus}
            label="transcription"
          />
        </div>
      </div>
      {startError && (
        <p className="shrink-0 bg-[#fbf3f1] px-4 py-2 text-xs text-[#a04a3a]">
          {startError}
        </p>
      )}
      {body}
    </div>
  );
}

/**
 * The places on a page: one entry per distinct mention, with coordinates from
 * the first candidate that has them. A single candidate is only a suggestion
 * for review, never a confirmed location, and a mention without coordinates
 * still counts (it just gets no pin).
 */
function collectPlaces(lines) {
  const found = new Map();
  for (const line of lines) {
    for (const mention of line.places ?? []) {
      const key = mention.text.toLowerCase();
      if (found.has(key)) continue;
      const candidates = mention.official_place_candidates ?? [];
      const located = candidates.find(
        (c) => c.latitude != null && c.longitude != null,
      );
      found.set(key, {
        name: mention.text,
        officialName: (located ?? candidates[0])?.canonical_name ?? null,
        candidateCount: candidates.length,
        lat: located?.latitude ?? null,
        lng: located?.longitude ?? null,
      });
    }
  }
  return [...found.values()];
}

/** Bottom bar: the places on this page. Collapsed by default; opens a small map. */
function PlacesBar({ places, mapKey }) {
  const [isOpen, setIsOpen] = useState(false);
  const hasPlaces = places.length > 0;
  // Only places with coordinates can be pinned. Never invent (0, 0).
  const pinned = places.filter((place) => place.lat != null);
  const hasPins = pinned.length > 0;

  return (
    <section className="shrink-0 overflow-hidden rounded-xl border border-[#e0e6e0] bg-white">
      <button
        type="button"
        onClick={() => setIsOpen((open) => !open)}
        disabled={!hasPins}
        aria-expanded={isOpen}
        className="flex h-11 w-full items-center gap-3 px-3 text-left disabled:cursor-default"
      >
        <MapPin className="size-4 shrink-0 text-[#6f8e7b]" />
        <span className="shrink-0 text-sm font-medium text-[#1e302b]">
          Places
        </span>
        <span className="flex min-w-0 flex-1 gap-1.5 overflow-hidden">
          {hasPlaces ? (
            places.map((place) => (
              <span
                key={place.name}
                className="shrink-0 rounded-full bg-[#edf1ed] px-2 py-0.5 text-xs text-[#476d5b]"
              >
                {place.name}
              </span>
            ))
          ) : (
            <span className="text-xs text-[#8a9790]">
              No places mentioned on this page
            </span>
          )}
        </span>
        {hasPins && (
          <span className="flex shrink-0 items-center gap-1 text-xs text-[#6e7975]">
            <span className="hidden sm:inline">
              {isOpen ? "Hide map" : "Show map"}
            </span>
            {isOpen ? (
              <ChevronDown className="size-4" />
            ) : (
              <ChevronUp className="size-4" />
            )}
          </span>
        )}
      </button>

      {isOpen && hasPins && (
        <div className="grid border-t border-[#edf0ed] md:grid-cols-[1fr_260px]">
          {/* `isolate` keeps Leaflet's high z-indexes below the sticky header. */}
          <div className="isolate h-[200px]">
            <MapContainer
              key={mapKey}
              bounds={pinned.map((place) => [place.lat, place.lng])}
              boundsOptions={{ padding: [40, 40], maxZoom: 8 }}
              scrollWheelZoom={false}
              className="size-full"
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              {pinned.map((place) => (
                <CircleMarker
                  key={place.name}
                  center={[place.lat, place.lng]}
                  radius={8}
                  pathOptions={{
                    color: "#1e3b35",
                    fillColor: "#6f8e7b",
                    fillOpacity: 0.85,
                    weight: 2,
                  }}
                >
                  <Tooltip>{place.name}</Tooltip>
                </CircleMarker>
              ))}
            </MapContainer>
          </div>

          <ul className="max-h-[200px] divide-y divide-[#edf0ed] overflow-auto border-t border-[#edf0ed] md:border-l md:border-t-0">
            {places.map((place) => (
              <li key={place.name} className="px-4 py-2.5">
                <p className="text-sm font-medium text-[#1e302b]">
                  {place.name}
                  {place.officialName && place.officialName !== place.name && (
                    <span className="font-normal text-[#6e7975]">
                      {" "}
                      → {place.officialName}
                    </span>
                  )}
                </p>
                <p className="text-xs text-[#8a9790]">
                  {place.candidateCount === 0
                    ? "No match in the place list"
                    : place.candidateCount > 1
                      ? `${place.candidateCount} possible places · to review`
                      : "One possible place · to review"}
                  {place.lat != null
                    ? ` · ${place.lat.toFixed(2)}, ${place.lng.toFixed(2)}`
                    : " · no coordinates"}
                </p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

/**
 * Inside one collection: pick a document, see its page on the left and the
 * transcription on the right, with the places it mentions in a bar below.
 * Everything fits in the window; one panel or the whole viewer can be maximized.
 */
export function CollectionViewer({
  collectionId,
  collections,
  isLoadingCollections,
  user,
  onLogin,
}) {
  const [isReporting, setIsReporting] = useState(false);
  const [pickedDocumentId, setPickedDocumentId] = useState("");
  // Page shown per document, so switching documents keeps your place in each.
  const [pageIndexByDocument, setPageIndexByDocument] = useState({});
  const [focus, setFocus] = useState("both"); // 'both' | 'page' | 'text'
  const [isFullScreen, setIsFullScreen] = useState(false);

  // Full screen: stop the page behind from scrolling, and leave with Escape.
  useEffect(() => {
    if (!isFullScreen) return undefined;
    const onKey = (event) => event.key === "Escape" && setIsFullScreen(false);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKey);
    };
  }, [isFullScreen]);

  const collection = collections.find((item) => item.id === collectionId);

  const documentsQuery = useFetch(collectionId, () =>
    getDocuments(collectionId),
  );
  const documents = documentsQuery.data ?? [];

  const selectedDocument =
    documents.find((doc) => doc.id === pickedDocumentId) ?? documents[0];
  const documentId = selectedDocument?.id ?? "";

  const pagesQuery = useFetch(documentId, () => getPages(documentId));
  const pages = pagesQuery.data ?? [];

  const pageIndex = Math.min(
    pageIndexByDocument[documentId] ?? 0,
    Math.max(0, pages.length - 1),
  );
  const pageNumber = pages[pageIndex]?.page_number ?? 1;
  const pageId = pages[pageIndex]?.id ?? "";

  // What the model read on this page; checked again while it is still working.
  const transcriptionQuery = usePageTranscription(pageId);
  const places = collectPlaces(transcriptionQuery.data?.lines ?? []);

  const [isStarting, setIsStarting] = useState(false);
  const [startError, setStartError] = useState("");
  const canTranscribe = Boolean(
    user && collection && collection.owner_id === user.id,
  );

  async function transcribePage() {
    setIsStarting(true);
    setStartError("");
    try {
      await startPageTranscription(pageId);
      transcriptionQuery.reload();
    } catch (e) {
      setStartError(e.message);
    } finally {
      setIsStarting(false);
    }
  }

  function changePage(index) {
    setPageIndexByDocument((previous) => ({
      ...previous,
      [documentId]: index,
    }));
  }

  function toggleFocus(panel) {
    setFocus((current) => (current === panel ? "both" : panel));
  }

  if (!collection && !isLoadingCollections) {
    return (
      <section className="py-24 text-center">
        <h1 className="font-serif text-4xl tracking-[-0.04em]">
          Collection not found
        </h1>
        <a
          href="#collections"
          className="mt-6 inline-block text-sm text-[#476d5b] underline"
        >
          Back to all collections
        </a>
      </section>
    );
  }

  return (
    <div
      className={
        isFullScreen
          ? "fixed inset-0 z-[3000] flex flex-col gap-3 overflow-auto bg-[#f7f8f5] p-3 lg:overflow-hidden"
          : `flex flex-col gap-3 ${VIEWER_HEIGHT}`
      }
    >
      <div className="flex shrink-0 items-center gap-3">
        <a
          href="#collections"
          className={`${ICON_BUTTON} shrink-0`}
          title="All collections"
          aria-label="All collections"
        >
          <ArrowLeft className="size-5" />
        </a>
        <div className="min-w-0 flex-1">
          <h1 className="truncate font-serif text-2xl leading-tight tracking-[-0.03em] text-[#1e302b]">
            {collection?.name ?? "…"}
          </h1>
          <p className="truncate text-xs text-[#7e8b85]">
            {collection?.description || "No description"}
            {documents.length > 0 &&
              ` · ${documents.length} ${documents.length === 1 ? "document" : "documents"}`}
          </p>
        </div>
        {/* Anyone but the owner can report; visitors are asked to log in first. */}
        {collection && collection.owner_id !== user?.id && (
          <button
            type="button"
            onClick={() => (user ? setIsReporting(true) : onLogin())}
            className="flex shrink-0 items-center gap-2 rounded-lg border border-[#dfe5df] bg-white px-3 py-1.5 text-sm text-[#55615b] transition-colors hover:border-[#e3c1b9] hover:bg-[#fbf3f1] hover:text-[#a04a3a]"
            title="Report this collection"
          >
            <Flag className="size-4" />
            <span className="hidden sm:inline">Report</span>
          </button>
        )}
        <button
          type="button"
          onClick={() => setIsFullScreen((full) => !full)}
          className="flex shrink-0 items-center gap-2 rounded-lg border border-[#dfe5df] bg-white px-3 py-1.5 text-sm text-[#55615b] transition-colors hover:bg-[#f7f9f6]"
          title={isFullScreen ? "Exit full screen (Esc)" : "Full screen"}
        >
          {isFullScreen ? (
            <Shrink className="size-4" />
          ) : (
            <Expand className="size-4" />
          )}
          <span className="hidden sm:inline">
            {isFullScreen ? "Exit full screen" : "Full screen"}
          </span>
        </button>
      </div>

      {documentsQuery.error ? (
        <p className="text-sm text-[#a04a3a]">{documentsQuery.error}</p>
      ) : documentsQuery.loading ? (
        <div className="grid min-h-0 flex-1 gap-3 lg:grid-cols-2">
          <div className="h-[70vh] animate-pulse rounded-xl bg-[#e4ece5] lg:h-full" />
          <div className="h-[70vh] animate-pulse rounded-xl bg-[#edf1ee] lg:h-full" />
        </div>
      ) : documents.length === 0 ? (
        <p className="rounded-xl border border-dashed border-[#cbdace] bg-white px-5 py-10 text-center text-sm text-[#7e8b85]">
          This collection has no files yet.
        </p>
      ) : (
        <>
          {documents.length > 1 && (
            <DocumentTabs
              documents={documents}
              selectedId={documentId}
              onSelect={setPickedDocumentId}
            />
          )}

          <div
            className={`grid min-h-0 flex-1 gap-3 ${focus === "both" ? "lg:grid-cols-2" : ""}`}
          >
            {focus !== "text" && (
              <PageImagePanel
                document={selectedDocument}
                pages={pages}
                pageIndex={pageIndex}
                onPageChange={changePage}
                loading={pagesQuery.loading}
                isFocused={focus === "page"}
                onToggleFocus={() => toggleFocus("page")}
              />
            )}
            {focus !== "page" && (
              <TranscriptionPanel
                transcription={transcriptionQuery.data}
                loading={pagesQuery.loading || transcriptionQuery.loading}
                error={transcriptionQuery.error}
                pageNumber={pageNumber}
                canTranscribe={canTranscribe}
                onTranscribe={transcribePage}
                isStarting={isStarting}
                startError={startError}
                isFocused={focus === "text"}
                onToggleFocus={() => toggleFocus("text")}
              />
            )}
          </div>

          <PlacesBar places={places} mapKey={`${pageId}`} />
        </>
      )}

      {isReporting && collection && (
        <ReportCollectionModal
          collection={collection}
          onClose={() => setIsReporting(false)}
        />
      )}
    </div>
  );
}
