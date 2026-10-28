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
  LoaderCircle,
  MapPin,
  Maximize2,
  Minimize2,
  ScanText,
  Shrink,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { useEffect, useState } from "react";
import { CircleMarker, MapContainer, TileLayer, Tooltip } from "react-leaflet";
import {
  getDocuments,
  getPageTranscription,
  getPages,
  transcribeDocument,
} from "../api/documents.js";
import { pageImageUrl } from "../api/map.js";
import {
  getMockPlaces,
  getMockTranscription,
} from "../data/mockTranscriptions.js";
import { countryDisplayName } from "../libraray/countries.js";
import { useFetch } from "../libraray/useFetch.js";
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
const IN_PROGRESS = ["queued", "processing"];
const POLL_MS = 5000;

/**
 * The recognized text of one page. While it is still being made (queued or
 * processing), asks again every few seconds. `reload()` starts over.
 */
function usePageTranscription(pageId) {
  const [result, setResult] = useState({ pageId: "", data: null, error: "" });
  const [reloads, setReloads] = useState(0);

  useEffect(() => {
    if (!pageId) return undefined;
    let cancelled = false;
    let timer;
    function load() {
      getPageTranscription(pageId)
        .then((data) => {
          if (cancelled) return;
          setResult({ pageId, data, error: "" });
          if (IN_PROGRESS.includes(data.status)) {
            timer = setTimeout(load, POLL_MS);
          }
        })
        .catch(
          (e) =>
            !cancelled && setResult({ pageId, data: null, error: e.message }),
        );
    }
    load();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [pageId, reloads]);

  const isCurrent = result.pageId === pageId;
  return {
    data: isCurrent ? result.data : null,
    error: isCurrent ? result.error : "",
    loading: Boolean(pageId) && !isCurrent,
    reload: () => setReloads((n) => n + 1),
  };
}

/** Mock lines are plain strings; give them place spans like real lines have. */
function mockLines(lines, places) {
  return lines.map((text) => ({
    text,
    places: places.flatMap(({ name }) =>
      [...text.matchAll(new RegExp(name, "g"))].map((match) => ({
        start: match.index,
        end: match.index + name.length,
      })),
    ),
  }));
}

/** The distinct places in recognized lines, with coordinates when known. */
function placesFromLines(lines) {
  const byName = new Map();
  for (const line of lines) {
    for (const span of line.places) {
      if (byName.has(span.text)) continue;
      const located = span.identities?.find((i) => i.latitude != null);
      byName.set(span.text, {
        name: span.text,
        lat: located?.latitude ?? null,
        lng: located?.longitude ?? null,
      });
    }
  }
  return [...byName.values()];
}

function MockBadge() {
  return (
    <span className="shrink-0 rounded-full bg-[#f6efe1] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[#8a6d3b]">
      Mock data
    </span>
  );
}

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

/** Wraps every place span ({start, end} in the line text) with a highlight. */
function highlightPlaces({ text, places }) {
  const spans = [...places].sort((a, b) => a.start - b.start);
  const parts = [];
  let at = 0;
  for (const { start, end } of spans) {
    if (start < at) continue; // overlaps the previous one
    parts.push(text.slice(at, start));
    parts.push(
      <mark key={start} className="rounded bg-[#e3ece5] px-0.5 text-[#1e3b35]">
        {text.slice(start, end)}
      </mark>,
    );
    at = end;
  }
  parts.push(text.slice(at));
  return parts;
}

/** Shown instead of the lines while there is no text to show. */
function TranscriptionNotice({ transcription, canTranscribe, onTranscribe }) {
  const { data, error, loading } = transcription;
  if (loading) {
    return (
      <div className="space-y-3 p-4">
        {[90, 75, 85, 60].map((width) => (
          <div
            key={width}
            className="h-4 animate-pulse rounded bg-[#edf1ee]"
            style={{ width: `${width}%` }}
          />
        ))}
      </div>
    );
  }
  if (error) return <p className="p-4 text-sm text-[#a04a3a]">{error}</p>;
  if (!data) return null; // no page yet (pages still loading, or the file has none)
  if (IN_PROGRESS.includes(data.status)) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center text-sm text-[#6e7975]">
        <LoaderCircle className="size-6 animate-spin text-[#6f8e7b]" />
        <p className="font-medium text-[#1e302b]">
          {data.status === "queued"
            ? "Waiting for handwriting recognition…"
            : "Recognizing handwriting…"}
        </p>
        <p>The text appears here when it is ready, usually in a few minutes.</p>
      </div>
    );
  }
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 p-6 text-center text-sm text-[#6e7975]">
      <p>
        {data.status === "failed"
          ? `Recognition failed: ${data.error || "unknown error"}`
          : "No lines of text were found on this page."}
      </p>
      {canTranscribe && (
        <button
          type="button"
          onClick={onTranscribe}
          className="flex items-center gap-2 rounded-lg border border-[#dfe5df] px-3 py-1.5 text-[#55615b] hover:bg-[#f7f9f6]"
        >
          <ScanText className="size-4" />
          Try again
        </button>
      )}
    </div>
  );
}

/**
 * Right side: the transcription of the current page. Pages never sent for
 * recognition show mock text, so the viewer can still be tried out.
 */
function TranscriptionPanel({
  transcription,
  lines,
  isMock,
  pageNumber,
  canTranscribe,
  onTranscribe,
  isFocused,
  onToggleFocus,
}) {
  const showLines = isMock || lines.length > 0;
  return (
    <div className={PANEL}>
      <div className={PANEL_BAR}>
        <p className="truncate text-sm font-medium text-[#1e302b]">
          Transcription · page {pageNumber}
        </p>
        <div className="flex shrink-0 items-center gap-2">
          {isMock && canTranscribe && (
            <button
              type="button"
              onClick={onTranscribe}
              className="flex items-center gap-1.5 rounded-lg border border-[#dfe5df] px-2 py-1 text-xs text-[#55615b] hover:bg-[#f7f9f6]"
              title="Recognize the handwriting on every page of this document"
            >
              <ScanText className="size-3.5" />
              Transcribe
            </button>
          )}
          {isMock ? (
            <MockBadge />
          ) : (
            showLines && (
              <span
                className="shrink-0 rounded-full bg-[#edf1ed] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[#476d5b]"
                title="Machine-read text, not yet checked by a person"
              >
                Unverified
              </span>
            )
          )}
          <FocusButton
            isFocused={isFocused}
            onToggle={onToggleFocus}
            label="transcription"
          />
        </div>
      </div>

      {!showLines && (
        <TranscriptionNotice
          transcription={transcription}
          canTranscribe={canTranscribe}
          onTranscribe={onTranscribe}
        />
      )}
      <ol
        hidden={!showLines}
        className="min-h-0 flex-1 overflow-auto px-4 py-4 font-serif text-[16px] leading-8 text-[#2a3833]"
      >
        {lines.map((line, index) => (
          <li key={index} className="grid grid-cols-[2rem_1fr] gap-3">
            <span className="select-none text-right font-sans text-xs leading-8 text-[#b0bab5]">
              {index + 1}
            </span>
            <span>{line.text ? highlightPlaces(line) : " "}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

/** Bottom bar: the places on this page. Collapsed by default; opens a small map. */
function PlacesBar({ places, isMock, mapKey }) {
  const [isOpen, setIsOpen] = useState(false);
  const hasPlaces = places.length > 0;
  const located = places.filter((place) => place.lat != null);

  return (
    <section className="shrink-0 overflow-hidden rounded-xl border border-[#e0e6e0] bg-white">
      <button
        type="button"
        onClick={() => setIsOpen((open) => !open)}
        disabled={!hasPlaces}
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
        {isMock && <MockBadge />}
        {hasPlaces && (
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

      {isOpen && hasPlaces && (
        <div className="grid border-t border-[#edf0ed] md:grid-cols-[1fr_260px]">
          {/* `isolate` keeps Leaflet's high z-indexes below the sticky header. */}
          <div className="isolate h-[200px]">
            {located.length === 0 ? (
              <p className="grid size-full place-items-center bg-[#f2f4f1] px-4 text-center text-xs text-[#8a9790]">
                None of these places could be located on the map yet.
              </p>
            ) : (
              <MapContainer
                key={mapKey}
                bounds={located.map((place) => [place.lat, place.lng])}
                boundsOptions={{ padding: [40, 40], maxZoom: 8 }}
                scrollWheelZoom={false}
                className="size-full"
              >
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                {located.map((place) => (
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
            )}
          </div>

          <ul className="max-h-[200px] divide-y divide-[#edf0ed] overflow-auto border-t border-[#edf0ed] md:border-l md:border-t-0">
            {places.map((place) => (
              <li key={place.name} className="px-4 py-2.5">
                <p className="text-sm font-medium text-[#1e302b]">
                  {place.name}
                </p>
                <p className="text-xs text-[#8a9790]">
                  {place.country_code &&
                    `${countryDisplayName(place.country_code)} · `}
                  {place.lat == null
                    ? "Not located"
                    : `${place.lat.toFixed(2)}, ${place.lng.toFixed(2)}`}
                  {!isMock && " · unverified"}
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
  const isOwner = Boolean(user) && collection?.owner_id === user.id;

  const transcription = usePageTranscription(pages[pageIndex]?.id ?? "");
  // Never sent for recognition (or no HTR service set up): show mock text.
  const isMock = transcription.data?.status === "pending";
  let lines = [];
  let places = [];
  if (isMock) {
    places = getMockPlaces(documentId, pageNumber);
    lines = mockLines(getMockTranscription(documentId, pageNumber), places);
  } else if (transcription.data?.status === "done") {
    lines = transcription.data.lines;
    places = placesFromLines(lines);
  }

  async function startTranscription() {
    try {
      await transcribeDocument(documentId);
    } catch (error) {
      window.alert(error.message);
    }
    transcription.reload();
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
                transcription={transcription}
                lines={lines}
                isMock={isMock}
                pageNumber={pageNumber}
                canTranscribe={isOwner}
                onTranscribe={startTranscription}
                isFocused={focus === "text"}
                onToggleFocus={() => toggleFocus("text")}
              />
            )}
          </div>

          <PlacesBar
            places={places}
            isMock={isMock}
            mapKey={`${documentId}/${pageNumber}`}
          />
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
