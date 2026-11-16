// Calls to the transcription endpoints of the backend.
import { apiFetch } from "./auth.js";

/**
 * What the model read on one page, line by line, and how far it is:
 * { page_id, status, error, width, height,
 *   lines: [{ line_index, text, bbox, polygon, places: [mention] }] }
 *
 * status: "pending" | "queued" | "running" | "complete" | "failed"
 * mention: { start, end, text, place_link_status, official_place_candidates }
 *   start/end count Unicode characters (not UTF-16 units), end exclusive.
 */
export async function getPageTranscription(pageId) {
  const response = await apiFetch(`/api/pages/${pageId}/transcription`);
  if (!response.ok) {
    throw new Error("Unable to load the transcription");
  }
  return response.json();
}

/** Ask the server to read a page (also retries a failed one). Owner only. */
export async function startPageTranscription(pageId) {
  const response = await apiFetch(`/api/pages/${pageId}/transcribe`, {
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
