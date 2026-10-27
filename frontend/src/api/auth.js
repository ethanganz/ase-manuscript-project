// Login state lives in an HttpOnly cookie set by the backend, so the browser
// sends it automatically with every /api request (including <img> tags).

export const SESSION_ENDED_EVENT = "auth:session-ended";

/** fetch() for logged-in calls. Tells the app when the session has ended. */
export async function apiFetch(url, options) {
  const response = await fetch(url, options);
  if (response.status === 401) {
    window.dispatchEvent(new Event(SESSION_ENDED_EVENT));
  }
  return response;
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    // 422 from FastAPI is a list of field errors; show the first one.
    const detail = Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail
    const error = new Error(detail || `Request failed (${response.status})`)
    error.status = response.status
    throw error
  }
  return data;
}

/** The logged-in user, or null if nobody is logged in. */
export async function getCurrentUser() {
  const response = await fetch("/api/auth/me");
  if (response.status === 401) return null;
  if (!response.ok) throw new Error("Unable to check login");
  return response.json();
}

/** Throws an error with status 403 if the email is not verified yet. */
export function login(email, password) {
  return postJson("/api/auth/login", { email, password });
}

/** Creates the account and emails a verification link. Does not log in. */
export function register(firstName, lastName, email, password) {
  return postJson("/api/auth/register", {
    first_name: firstName,
    last_name: lastName,
    email,
    password,
  });
}

/** Confirms the email with the token from the link, and logs in. */
export function verifyEmail(token) {
  return postJson('/api/auth/verify-email', { token })
}

/** Asks for a new verification email. Answers the same whether or not the account exists. */
export function resendVerification(email) {
  return postJson('/api/auth/resend-verification', { email })
}

export async function logout() {
  await fetch("/api/auth/logout", { method: "POST" });
}
