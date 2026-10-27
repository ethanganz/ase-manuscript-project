import { MailCheck, X } from "lucide-react";
import { useState } from "react";
import { login, register, resendVerification } from "../api/auth.js";

const inputClass =
  "mt-2 w-full rounded-lg border border-[#dfe5df] bg-white px-3 py-2.5 outline-none focus:border-[#6f8e7b] disabled:cursor-not-allowed disabled:bg-[#f4f6f4]";

/** Sends a new verification email to `email` and shows when it is on its way. */
function ResendButton({ email }) {
  const [state, setState] = useState("idle"); // idle | sending | sent | failed

  async function handleClick() {
    setState("sending");
    try {
      await resendVerification(email);
      setState("sent");
    } catch {
      setState("failed");
    }
  }

  if (state === "sent") {
    return <p className="text-sm text-[#476d5b]">A new link is on its way.</p>;
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={state === "sending"}
      className="text-sm font-medium text-[#476d5b] hover:underline disabled:opacity-60"
    >
      {state === "sending"
        ? "Sending…"
        : state === "failed"
          ? "Could not send. Try again"
          : "Send the verification email again"}
    </button>
  );
}

/**
 * Login and sign-up popup. Calls onAuthenticated(user) after a login.
 * Signing up does not log in: the user must first open the link in the
 * verification email.
 */
export function AuthModal({ isOpen, onAuthenticated, onClose }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  // Set when the email still has to be verified: after sign-up, or a login
  // refused because the link was not opened yet.
  const [unverifiedEmail, setUnverifiedEmail] = useState("");
  const [justRegistered, setJustRegistered] = useState(false);

  const isRegister = mode === "register";

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    setUnverifiedEmail("");
    try {
      if (isRegister) {
        const user = await register(
          firstName.trim(),
          lastName.trim(),
          email.trim(),
          password,
        );
        setUnverifiedEmail(user.email);
        setJustRegistered(true);
        setPassword("");
      } else {
        onAuthenticated(await login(email.trim(), password));
      }
    } catch (err) {
      setError(err.message);
      if (err.status === 403) setUnverifiedEmail(email.trim());
    } finally {
      setSubmitting(false);
    }
  }

  function switchMode() {
    setMode(isRegister ? "login" : "register");
    setError("");
    setUnverifiedEmail("");
  }

  function handleClose() {
    setJustRegistered(false);
    setUnverifiedEmail("");
    setError("");
    onClose();
  }

  function backToLogin() {
    setJustRegistered(false);
    setUnverifiedEmail("");
    setMode("login");
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-sm rounded-xl border border-[#dfe5df] bg-white p-6 shadow-xl">
        <div className="flex items-start justify-between gap-4">
          <h2 className="font-serif text-2xl tracking-[-0.03em] text-[#1e302b]">
            {justRegistered
              ? "Check your email"
              : isRegister
                ? "Create an account"
                : "Log in"}
          </h2>
          <button
            type="button"
            aria-label="Close"
            onClick={handleClose}
            className="rounded-lg p-2 text-[#6e7975] hover:bg-[#edf1ed]"
          >
            <X className="size-5" />
          </button>
        </div>

        {justRegistered ? (
          <div className="mt-4 space-y-4 text-sm text-[#55615b]">
            <MailCheck className="size-10 text-[#6f8e7b]" />
            <p>
              We sent a verification link to{" "}
              <strong className="text-[#1e302b]">{unverifiedEmail}</strong>.
              Open it to finish creating your account. You will be logged in
              automatically.
            </p>
            <p className="text-xs text-[#8a9790]">
              Can't find it? Check your spam folder.
            </p>
            <ResendButton key={unverifiedEmail} email={unverifiedEmail} />
            <button
              type="button"
              onClick={backToLogin}
              className="w-full rounded-lg border border-[#dfe5df] px-4 py-2.5 font-medium text-[#1e302b] hover:bg-[#f4f6f4]"
            >
              Back to log in
            </button>
          </div>
        ) : (
          <>
            <p className="mt-1 text-sm text-[#7e8b85]">
              {isRegister
                ? "An account lets you create collections and upload documents."
                : "Welcome back to the archive."}
            </p>

            <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
              {isRegister && (
                <div className="grid grid-cols-2 gap-3">
                  <label className="block text-sm font-medium text-[#374b45]">
                    First name
                    <input
                      type="text"
                      value={firstName}
                      onChange={(event) => setFirstName(event.target.value)}
                      disabled={submitting}
                      className={inputClass}
                      autoComplete="given-name"
                      maxLength={100}
                      required
                    />
                  </label>

                  <label className="block text-sm font-medium text-[#374b45]">
                    Last name
                    <input
                      type="text"
                      value={lastName}
                      onChange={(event) => setLastName(event.target.value)}
                      disabled={submitting}
                      className={inputClass}
                      autoComplete="family-name"
                      maxLength={100}
                      required
                    />
                  </label>
                </div>
              )}

              <label className="block text-sm font-medium text-[#374b45]">
                Email
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  disabled={submitting}
                  className={inputClass}
                  autoComplete="email"
                  required
                />
              </label>

              <label className="block text-sm font-medium text-[#374b45]">
                Password
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  disabled={submitting}
                  className={inputClass}
                  autoComplete={
                    isRegister ? "new-password" : "current-password"
                  }
                  minLength={isRegister ? 8 : undefined}
                  maxLength={72}
                  required
                />
                {isRegister && (
                  <span className="mt-1 block text-xs font-normal text-[#8a9790]">
                    At least 8 characters.
                  </span>
                )}
              </label>

              {error && (
                <div className="space-y-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                  <p>{error}</p>
                  {unverifiedEmail && (
                    <ResendButton
                      key={unverifiedEmail}
                      email={unverifiedEmail}
                    />
                  )}
                </div>
              )}

              <button
                type="submit"
                disabled={submitting}
                className="w-full rounded-lg bg-[#1e3b35] px-4 py-2.5 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
              >
                {submitting
                  ? "Please wait…"
                  : isRegister
                    ? "Create account"
                    : "Log in"}
              </button>
            </form>

            <p className="mt-5 text-center text-sm text-[#6e7975]">
              {isRegister ? "Already have an account?" : "New here?"}{" "}
              <button
                type="button"
                onClick={switchMode}
                className="font-medium text-[#476d5b] hover:underline"
              >
                {isRegister ? "Log in" : "Create an account"}
              </button>
            </p>
          </>
        )}
      </div>
    </div>
  );
}
