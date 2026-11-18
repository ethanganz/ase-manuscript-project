import { useEffect, useState } from "react";
import { getPageTranscription } from "../api/transcription.js";

const POLL_MS = 3000;

/**
 * Loads the transcription of one page and keeps checking every few seconds
 * while the server is still working on it ("queued" or "running").
 *
 *   const { data, error, loading, reload } = usePageTranscription(pageId)
 *
 * Pass an empty pageId to say "nothing to load yet". Call reload() after you
 * asked the server to start (or retry) a page.
 */
export function usePageTranscription(pageId) {
  const [result, setResult] = useState({ pageId: "", data: null, error: "" });
  const [reloadCount, setReloadCount] = useState(0);

  useEffect(() => {
    if (!pageId) return undefined;
    let cancelled = false;
    let timer;

    async function load() {
      try {
        const data = await getPageTranscription(pageId);
        if (cancelled) return;
        setResult({ pageId, data, error: "" });
        if (data.status === "queued" || data.status === "running") {
          timer = setTimeout(load, POLL_MS);
        }
      } catch (e) {
        if (!cancelled) setResult({ pageId, data: null, error: e.message });
      }
    }

    load();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [pageId, reloadCount]);

  // Only show an answer that belongs to the page on screen right now.
  const isCurrent = result.pageId === pageId;

  return {
    data: isCurrent ? result.data : null,
    error: isCurrent ? result.error : "",
    loading: Boolean(pageId) && !isCurrent,
    reload: () => setReloadCount((count) => count + 1),
  };
}
