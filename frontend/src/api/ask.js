// Calls the "ask a question about one page" endpoint of the backend.
import { apiFetch } from "./auth.js";

/** Error with the extra facts the screen needs to show a good message. */
export class AskError extends Error {
  constructor(
    message,
    { status, code = null, retryAfterSeconds = null, daily = false } = {},
  ) {
    super(message);
    this.name = "AskError";
    this.status = status;
    this.code = code;
    this.retryAfterSeconds = retryAfterSeconds;
    this.daily = daily;
  }
}

/** The backend sends `detail` as a text, a list (bad input) or an object (limit, AI down). */
function readMessage(detail, status) {
  if (typeof detail === "string") return detail;
  if (
    detail &&
    typeof detail === "object" &&
    typeof detail.message === "string"
  )
    return detail.message;
  if (status === 422) return "Please check your question and try again.";
  return `The question could not be answered (error ${status}).`;
}

/**
 * Ask a question about one page.
 *   history: the last chat messages, oldest first: [{ role: "user" | "assistant", text }]
 *   provider: "gemini" | "ollama" | null (null = the server's default)
 * Resolves with { answer, sources, grounded, document_answer, general_answer }.
 * Rejects with an AskError.
 */
export async function askPage(pageId, question, history = [], provider = null) {
  let response;
  try {
    response = await apiFetch(`/api/pages/${encodeURIComponent(pageId)}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, history, provider }),
    });
  } catch {
    throw new AskError(
      "Could not reach the server. Check your connection and try again.",
      { status: 0 },
    );
  }

  const data = await response.json().catch(() => ({}));
  if (response.ok) return data;

  const detail = data.detail;
  const info =
    detail && typeof detail === "object" && !Array.isArray(detail)
      ? detail
      : {};
  const headerSeconds = Number(response.headers.get("Retry-After"));
  throw new AskError(readMessage(detail, response.status), {
    status: response.status,
    code: info.code ?? null,
    retryAfterSeconds:
      response.status === 429
        ? (info.retry_after_seconds ?? (headerSeconds || null))
        : null,
    daily: Boolean(info.daily),
  });
}

/**
 * Which models the chat can use right now.
 * Resolves with { default, providers: [{ id, label, available, reason }] }.
 */
export async function getLlmProviders() {
  const response = await apiFetch("/api/llm/providers");
  if (!response.ok) throw new Error("Unable to load the AI models");
  return response.json();
}
