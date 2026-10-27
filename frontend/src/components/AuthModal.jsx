import { X } from "lucide-react";
import { useState } from "react";
import { login, register } from "../api/auth.js";

const inputClass =
  "mt-2 w-full rounded-lg border border-[#dfe5df] bg-white px-3 py-2.5 outline-none focus:border-[#6f8e7b] disabled:cursor-not-allowed disabled:bg-[#f4f6f4]";

/** Login and sign-up popup. Calls onAuthenticated(user) on success. */
export function AuthModal({ isOpen, onAuthenticated, onClose }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const isRegister = mode === "register";

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const user = isRegister
        ? await register(
            firstName.trim(),
            lastName.trim(),
            email.trim(),
            password,
          )
        : await login(email.trim(), password);
      onAuthenticated(user);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  function switchMode() {
    setMode(isRegister ? "login" : "register");
    setError("");
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-sm rounded-xl border border-[#dfe5df] bg-white p-6 shadow-xl">
        <div className="flex items-start justify-between gap-4">
          <h2 className="font-serif text-2xl tracking-[-0.03em] text-[#1e302b]">
            {isRegister ? "Create an account" : "Log in"}
          </h2>
          <button
            type="button"
            aria-label="Close"
            onClick={onClose}
            className="rounded-lg p-2 text-[#6e7975] hover:bg-[#edf1ed]"
          >
            <X className="size-5" />
          </button>
        </div>
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
              autoComplete={isRegister ? "new-password" : "current-password"}
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
            <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {error}
            </p>
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
      </div>
    </div>
  );
}
