import { apiFetch } from "./auth.js";

/** Reasons a collection can be reported for, as sent to the backend. */
export const REPORT_REASONS = [
  { value: "spam", label: "Spam or junk files" },
  { value: "inappropriate", label: "Inappropriate or offensive content" },
  { value: "copyright", label: "Copyright violation" },
  { value: "misleading", label: "Misleading name or description" },
  { value: "other", label: "Something else" },
];

export function reportReasonLabel(value) {
  return (
    REPORT_REASONS.find((reason) => reason.value === value)?.label ?? value
  );
}

async function errorMessage(response, fallback) {
  const data = await response.json().catch(() => ({}));
  // 422 from FastAPI is a list of field errors; show the first one.
  const detail = Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail;
  return detail || `${fallback} (${response.status})`;
}

/** Report someone else's collection. Each user can report a collection once. */
export async function reportCollection(collectionId, reason, details) {
  const response = await apiFetch(`/api/collections/${collectionId}/reports`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason, details: details || null }),
  });
  if (!response.ok)
    throw new Error(await errorMessage(response, "Could not send the report"));
  return response.json();
}

/** Reports on the logged-in user's own collections, newest first. */
export async function getReceivedReports() {
  const response = await apiFetch("/api/reports/received");
  if (!response.ok) throw new Error("Unable to load notifications");
  return response.json();
}

export async function markReportsRead() {
  const response = await apiFetch("/api/reports/received/read", {
    method: "POST",
  });
  if (!response.ok) throw new Error("Unable to mark notifications as read");
}
