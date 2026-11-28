import { useRef, useState } from "react";
import {
  AlertTriangle,
  ArrowUp,
  Clock,
  Cloud,
  Cpu,
  Eraser,
  Languages,
  MapPin,
  Quote,
  ScrollText,
  Sparkles,
  Trash2,
  Users,
  X,
} from "lucide-react";
import { askPage, getLlmProviders } from "../api/ask.js";
import { formatWait, useCountdown } from "../library/useCountdown.js";
import { useFetch } from "../library/useFetch.js";

const MAX_QUESTION_LENGTH = 500; // the backend refuses longer questions
const MAX_HISTORY = 4; // earlier messages sent with each new question
const PROVIDER_KEY = "pageChatProvider"; // remembers the chosen model in this browser

function readSavedProvider() {
  try {
    return localStorage.getItem(PROVIDER_KEY);
  } catch {
    return null; // storage can be blocked; the chat works without it
  }
}

const SUGGESTIONS = [
  { icon: ScrollText, text: "Summarize this page" },
  { icon: Users, text: "Who is writing, and to whom?" },
  { icon: MapPin, text: "Which places are mentioned?" },
  { icon: Languages, text: "Translate the first lines into English" },
];

/** Splits "[1][3]" style citations out of an answer and turns them into buttons. */
function CitedText({ text, sources, activeLabel, onCite }) {
  const byLabel = new Map(sources.map((source) => [source.label, source]));
  const pieces = text.split(/(\[\d+(?:\s*,\s*\d+)*\])/g);

  return pieces.map((piece, index) => {
    const match = /^\[(\d+(?:\s*,\s*\d+)*)\]$/.exec(piece);
    if (!match) return <span key={index}>{piece}</span>;
    return (
      <span key={index} className="whitespace-nowrap">
        {match[1].split(",").map((part) => {
          const label = Number(part);
          const source = byLabel.get(label);
          if (!source) {
            return (
              <span key={label} className="text-[#9aa6a0]">
                [{label}]
              </span>
            );
          }
          const active = activeLabel === label;
          return (
            <button
              key={label}
              type="button"
              onClick={() => onCite(source)}
              title={`Show line ${label} on the page`}
              className={`mx-0.5 inline-flex h-[1.3rem] min-w-[1.3rem] items-center justify-center rounded-md px-1 align-baseline text-[11px] leading-none font-semibold transition-colors ${
                active
                  ? "bg-[#476d5b] text-white"
                  : "bg-[#dcebe1] text-[#314b3e] hover:bg-[#c3dccb]"
              }`}
            >
              {label}
            </button>
          );
        })}
      </span>
    );
  });
}

function Avatar() {
  return (
    <div className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-full bg-gradient-to-br from-[#5f8a74] to-[#2f5645] text-white shadow-sm ring-4 ring-[#eef4ef]">
      <Sparkles className="size-4" />
    </div>
  );
}

function UserMessage({ message }) {
  return (
    <div className="flex justify-end animate-in fade-in slide-in-from-bottom-2 duration-300">
      <div className="max-w-[85%] rounded-2xl rounded-br-md bg-gradient-to-br from-[#4f7a65] to-[#365d4a] px-4 py-2.5 text-sm leading-relaxed whitespace-pre-line text-white shadow-sm">
        {message.text}
      </div>
    </div>
  );
}

function AssistantMessage({ message, onJumpToLine }) {
  const [activeLabel, setActiveLabel] = useState(null);
  const activeSource = message.sources.find((s) => s.label === activeLabel);

  function cite(source) {
    setActiveLabel(source.label);
    if (source.line_index != null) onJumpToLine?.(source.line_index);
  }

  return (
    <div className="flex gap-3 animate-in fade-in slide-in-from-bottom-2 duration-300">
      <Avatar />
      <div className="grid min-w-0 flex-1 gap-2">
        {message.documentAnswer && (
          <div className="rounded-2xl rounded-tl-md border border-[#cfe0d4] bg-white px-4 py-3 text-sm leading-relaxed shadow-sm">
            <div className="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold tracking-wider text-[#476d5b] uppercase">
              <ScrollText className="size-3.5" />
              From this page
            </div>
            <p className="whitespace-pre-line text-[#26332d]">
              <CitedText
                text={message.documentAnswer}
                sources={message.sources}
                activeLabel={activeLabel}
                onCite={cite}
              />
            </p>
            {activeSource && (
              <div className="mt-3 flex gap-2 rounded-xl bg-[#f3f6f3] px-3 py-2.5 text-[13px] text-[#4a5a53] animate-in fade-in duration-200">
                <Quote className="mt-0.5 size-3.5 shrink-0 text-[#7aa08b]" />
                <div className="min-w-0">
                  <div className="text-[11px] font-semibold text-[#314b3e]">
                    Line {activeSource.label}
                    {activeSource.language ? ` · ${activeSource.language}` : ""}
                  </div>
                  <p className="mt-0.5 italic">{activeSource.text}</p>
                </div>
              </div>
            )}
            <p className="mt-2 text-[11px] text-[#97a39d]">
              Read from handwriting by software. It may contain mistakes.
            </p>
          </div>
        )}

        {message.generalAnswer && (
          <div
            className={`border border-[#ead9ad] bg-[#fdf8ea] px-4 py-3 text-sm leading-relaxed shadow-sm ${
              message.documentAnswer
                ? "rounded-2xl"
                : "rounded-2xl rounded-tl-md"
            }`}
          >
            <div className="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold tracking-wider text-[#8a6d1c] uppercase">
              <Sparkles className="size-3.5" />
              AI&apos;s own knowledge
            </div>
            <p className="whitespace-pre-line text-[#3d3520]">
              {message.generalAnswer}
            </p>
            <p className="mt-2 text-[11px] text-[#a8955a]">
              Not from your page, so there are no sources.
            </p>
          </div>
        )}
        {message.providerLabel && (
          <p className="px-1 text-[11px] text-[#a0aba5]">
            Answered by {message.providerLabel}
          </p>
        )}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex gap-3 animate-in fade-in duration-200">
      <Avatar />
      <div className="flex items-center gap-1.5 rounded-2xl rounded-tl-md border border-[#cfe0d4] bg-white px-4 py-3.5 shadow-sm">
        {[0, 150, 300].map((delay) => (
          <span
            key={delay}
            className="size-2 animate-bounce rounded-full bg-[#7aa08b]"
            style={{ animationDelay: `${delay}ms` }}
          />
        ))}
      </div>
    </div>
  );
}

function EmptyState({ onPick, disabled }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 py-8 text-center animate-in fade-in duration-500">
      <div className="grid size-16 place-items-center rounded-3xl bg-gradient-to-br from-[#5f8a74] to-[#2f5645] text-white shadow-lg shadow-[#476d5b]/25">
        <Sparkles className="size-7" />
      </div>
      <h3 className="mt-5 font-serif text-2xl tracking-[-0.03em] text-[#1e302b]">
        Ask about this page
      </h3>
      <p className="mt-1.5 max-w-xs text-sm text-[#7e8b85]">
        Answers say what comes from the page, with the lines they are based on,
        and what the AI adds on its own.
      </p>
      <div className="mt-6 grid w-full max-w-sm gap-2">
        {SUGGESTIONS.map(({ icon: Icon, text }) => (
          <button
            key={text}
            type="button"
            disabled={disabled}
            onClick={() => onPick(text)}
            className="group flex items-center gap-3 rounded-xl border border-[#dfe8e1] bg-white px-4 py-2.5 text-left text-sm text-[#314b3e] transition-all hover:-translate-y-px hover:border-[#9dbfab] hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Icon className="size-4 shrink-0 text-[#7aa08b] transition-colors group-hover:text-[#476d5b]" />
            {text}
          </button>
        ))}
      </div>
    </div>
  );
}

/** Dialog that asks before the chat is deleted. */
function ConfirmDelete({ mode, onCancel, onConfirm }) {
  const closing = mode === "close";
  return (
    <div
      className="absolute inset-0 z-10 grid place-items-center bg-[#1e302b]/40 p-6 backdrop-blur-[2px] animate-in fade-in duration-200"
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="chat-delete-title"
    >
      <div className="w-full max-w-xs rounded-2xl bg-white p-5 text-center shadow-2xl animate-in zoom-in-95 duration-200">
        <div className="mx-auto grid size-11 place-items-center rounded-full bg-[#fbeeee] text-[#b4503f]">
          <Trash2 className="size-5" />
        </div>
        <h3
          id="chat-delete-title"
          className="mt-3 font-serif text-xl tracking-[-0.02em] text-[#1e302b]"
        >
          {closing ? "Close and delete chat?" : "Clear this chat?"}
        </h3>
        <p className="mt-1.5 text-sm text-[#7e8b85]">
          {closing
            ? "Closing the chat deletes the conversation. It cannot be restored."
            : "All messages in this chat will be deleted. It cannot be restored."}
        </p>
        <div className="mt-5 grid grid-cols-2 gap-2">
          <button
            type="button"
            autoFocus
            onClick={onCancel}
            className="rounded-xl border border-[#dfe5df] px-3 py-2 text-sm font-medium text-[#55615b] transition-colors hover:bg-[#f7f9f6]"
          >
            Keep chat
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="rounded-xl bg-[#b4503f] px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-[#9c4132]"
          >
            {closing ? "Delete & close" : "Delete chat"}
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * A chat about the page that is open, as a panel on the right.
 *
 * The chat lives only in this component, so it is gone when the panel closes (the
 * user is asked first). The last MAX_HISTORY messages are sent with each question;
 * the server puts the page text in front of them. Each page has its own chat while
 * the panel is open.
 *
 * Props:
 *   pageId, pageNumber, documentName - the page that is open
 *   ready         - false while the page has no transcription yet
 *   onClose()     - called after the chat was deleted
 *   onJumpToLine(index) - highlight a cited line on the page (optional)
 */
export function PageChat({
  pageId,
  pageNumber,
  documentName,
  ready,
  onClose,
  onJumpToLine,
}) {
  const [chats, setChats] = useState({}); // pageId -> messages
  const [input, setInput] = useState("");
  const [loadingPageId, setLoadingPageId] = useState("");
  const [rawError, setError] = useState(null); // { message, daily, provider }
  const [limitedProvider, setLimitedProvider] = useState(null);
  const [picked, setPicked] = useState(readSavedProvider);
  const providersQuery = useFetch("llm-providers", getLlmProviders);
  const [confirm, setConfirm] = useState(null); // null | "clear" | "close"
  const { secondsLeft, totalSeconds, start } = useCountdown();
  const nextId = useRef(0);
  const scroller = useRef(null);
  const textarea = useRef(null);

  const messages = chats[pageId] ?? [];
  const loading = loadingPageId !== "";

  // The model that answers: the user's choice if it can be used, else the server's default.
  const providers = providersQuery.data?.providers ?? [];
  const usable = (id) => providers.some((p) => p.id === id && p.available);
  const activeProvider = !providersQuery.data
    ? picked
    : usable(picked)
      ? picked
      : usable(providersQuery.data.default)
        ? providersQuery.data.default
        : (providers.find((p) => p.available)?.id ?? null);
  const providerLabel = (id) =>
    providers.find((p) => p.id === id)?.label ?? "AI";
  const alternative = providers.find(
    (p) => p.id !== activeProvider && p.available,
  );

  // A wait only blocks the model that hit its limit.
  const waiting = secondsLeft > 0 && limitedProvider === activeProvider;
  const error =
    rawError && rawError.provider === activeProvider ? rawError : null;
  const trimmed = input.trim();
  const canSend = ready && trimmed.length > 0 && !loading && !waiting;

  function chooseProvider(id) {
    setPicked(id);
    try {
      localStorage.setItem(PROVIDER_KEY, id);
    } catch {
      // not saved; the choice still works until the panel closes
    }
  }

  function scrollToEnd() {
    // after React has drawn the new message
    requestAnimationFrame(() =>
      scroller.current?.scrollTo({
        top: scroller.current.scrollHeight,
        behavior: "smooth",
      }),
    );
  }

  function resizeTextarea() {
    const element = textarea.current;
    if (!element) return;
    element.style.height = "auto";
    element.style.height = `${Math.min(element.scrollHeight, 128)}px`;
  }

  function addMessage(forPage, message) {
    setChats((previous) => ({
      ...previous,
      [forPage]: [
        ...(previous[forPage] ?? []),
        { id: nextId.current++, ...message },
      ],
    }));
  }

  async function send(text) {
    const question = text.trim();
    if (!ready || !question || loading || waiting) return;

    const forPage = pageId;
    const provider = activeProvider;
    // The last MAX_HISTORY messages of this page's chat, before the new question.
    const history = messages.slice(-MAX_HISTORY).map((message) => ({
      role: message.role,
      text: message.role === "user" ? message.text : message.answer,
    }));

    addMessage(forPage, { role: "user", text: question });
    setInput("");
    setError(null);
    setLoadingPageId(forPage);
    requestAnimationFrame(resizeTextarea);
    scrollToEnd();

    try {
      const data = await askPage(forPage, question, history, provider);
      addMessage(forPage, {
        role: "assistant",
        answer: data.answer,
        documentAnswer: data.document_answer,
        generalAnswer: data.general_answer,
        sources: data.sources ?? [],
        providerLabel: providerLabel(provider),
      });
    } catch (caught) {
      // Take the question back out of the chat and into the box, so nothing is lost.
      setChats((previous) => ({
        ...previous,
        [forPage]: (previous[forPage] ?? []).slice(0, -1),
      }));
      setInput(question);
      if (caught.status === 429 && caught.retryAfterSeconds && !caught.daily) {
        start(caught.retryAfterSeconds);
        setLimitedProvider(provider);
      }
      setError({
        provider,
        message: caught.message,
        limited: caught.status === 429,
        daily: caught.daily,
      });
    } finally {
      setLoadingPageId("");
      scrollToEnd();
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    send(input);
  }

  function handleKeyDown(event) {
    if (
      event.key === "Enter" &&
      !event.shiftKey &&
      !event.nativeEvent.isComposing
    ) {
      event.preventDefault();
      send(input);
    }
  }

  function requestClose() {
    // Nothing to lose when no question was asked on any page.
    const hasChat = Object.values(chats).some((list) => list.length > 0);
    if (hasChat) setConfirm("close");
    else onClose();
  }

  function confirmDelete() {
    if (confirm === "close") {
      setChats({});
      setConfirm(null);
      onClose();
      return;
    }
    setChats((previous) => ({ ...previous, [pageId]: [] }));
    setError(null);
    setConfirm(null);
  }

  const progress =
    totalSeconds > 0 ? Math.min(100, (secondsLeft / totalSeconds) * 100) : 0;

  return (
    <aside
      className="fixed inset-y-0 right-0 z-[3100] flex w-full flex-col overflow-hidden bg-[#f7f9f6] shadow-[0_0_60px_-10px_rgba(30,48,43,0.45)] animate-in slide-in-from-right duration-300 sm:w-[28rem] sm:rounded-l-3xl"
      aria-label="Chat about this page"
    >
      {/* Header */}
      <header className="relative shrink-0 overflow-hidden bg-gradient-to-br from-[#1e3b35] via-[#2b5243] to-[#476d5b] px-5 py-4 text-white">
        <div className="pointer-events-none absolute -top-10 -right-10 size-40 rounded-full bg-white/10 blur-2xl" />
        <div className="relative flex items-center gap-3">
          <div className="grid size-10 shrink-0 place-items-center rounded-2xl bg-white/15 ring-1 ring-white/25 backdrop-blur">
            <Sparkles className="size-5" />
          </div>
          <div className="min-w-0 flex-1">
            <h2 className="font-serif text-xl leading-tight tracking-[-0.02em]">
              Ask this page
            </h2>
            <p className="truncate text-xs text-white/70">
              {documentName ? `${documentName} · ` : ""}Page {pageNumber}
            </p>
          </div>
          {messages.length > 0 && (
            <button
              type="button"
              onClick={() => setConfirm("clear")}
              title="Clear chat"
              aria-label="Clear chat"
              className="grid size-9 place-items-center rounded-xl text-white/80 transition-colors hover:bg-white/15 hover:text-white"
            >
              <Eraser className="size-[18px]" />
            </button>
          )}
          <button
            type="button"
            onClick={requestClose}
            title="Close chat"
            aria-label="Close chat"
            className="grid size-9 place-items-center rounded-xl text-white/80 transition-colors hover:bg-white/15 hover:text-white"
          >
            <X className="size-5" />
          </button>
        </div>
      </header>

      {/* Model selector */}
      {providers.length > 0 && (
        <div className="flex shrink-0 items-center gap-3 border-b border-[#e3eae4] bg-white/70 px-4 py-2">
          <span className="text-[11px] font-semibold tracking-wider text-[#7e8b85] uppercase">
            Model
          </span>
          <div
            role="radiogroup"
            aria-label="AI model"
            className="flex flex-1 gap-1 rounded-xl bg-[#eaf0eb] p-1"
          >
            {providers.map((provider) => {
              const active = provider.id === activeProvider;
              const Icon = provider.id === "ollama" ? Cpu : Cloud;
              return (
                <button
                  key={provider.id}
                  type="button"
                  role="radio"
                  aria-checked={active}
                  disabled={!provider.available}
                  title={provider.available ? "" : provider.reason}
                  onClick={() => chooseProvider(provider.id)}
                  className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg px-2 py-1.5 text-xs font-medium transition-all ${
                    active
                      ? "bg-white text-[#1e3b35] shadow-sm"
                      : "text-[#6b7a72] hover:text-[#1e3b35]"
                  } disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:text-[#6b7a72]`}
                >
                  <Icon className="size-3.5" />
                  {provider.label}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Messages */}
      <div
        ref={scroller}
        aria-live="polite"
        className="flex min-h-0 flex-1 flex-col overflow-y-auto"
      >
        {!ready ? (
          <div className="flex flex-1 flex-col items-center justify-center px-8 text-center">
            <div className="grid size-14 place-items-center rounded-2xl bg-[#eaf0eb] text-[#7aa08b]">
              <ScrollText className="size-6" />
            </div>
            <p className="mt-4 text-sm text-[#7e8b85]">
              This page has not been transcribed yet. Transcribe it first, then
              ask your questions here.
            </p>
          </div>
        ) : messages.length === 0 && !loading ? (
          <EmptyState onPick={send} disabled={waiting} />
        ) : (
          <div className="grid gap-4 px-4 py-5">
            {messages.map((message) =>
              message.role === "user" ? (
                <UserMessage key={message.id} message={message} />
              ) : (
                <AssistantMessage
                  key={message.id}
                  message={message}
                  onJumpToLine={onJumpToLine}
                />
              ),
            )}
            {loadingPageId === pageId && <TypingIndicator />}
          </div>
        )}
      </div>

      {/* Composer */}
      <div className="shrink-0 border-t border-[#e3eae4] bg-white/80 px-4 pt-3 pb-4 backdrop-blur">
        {error && (
          <div
            role="alert"
            className={`mb-3 overflow-hidden rounded-xl border text-sm animate-in fade-in slide-in-from-bottom-1 duration-200 ${
              error.limited
                ? "border-[#ead9ad] bg-[#fdf8ea] text-[#6b5313]"
                : "border-[#e8c5c5] bg-[#fbeeee] text-[#7a2d2d]"
            }`}
          >
            <div className="flex items-center gap-2.5 px-3.5 py-2.5">
              {error.limited && !error.daily ? (
                <Clock className="size-4 shrink-0" />
              ) : (
                <AlertTriangle className="size-4 shrink-0" />
              )}
              <span className="flex-1">
                {error.limited && !error.daily
                  ? waiting
                    ? "Question limit reached. You can ask again in"
                    : "The limit has been reset. You can ask again."
                  : error.message}
              </span>
              {error.limited && !error.daily && waiting && (
                <span className="rounded-lg bg-white/70 px-2 py-0.5 font-mono text-base font-semibold tabular-nums">
                  {formatWait(secondsLeft)}
                </span>
              )}
            </div>
            {error.limited && alternative && (
              <button
                type="button"
                onClick={() => chooseProvider(alternative.id)}
                className="mr-3.5 mb-2.5 ml-[2.4rem] text-xs font-medium underline underline-offset-2"
              >
                Use {alternative.label} instead
              </button>
            )}
            {error.limited && !error.daily && waiting && (
              <div className="h-1 bg-[#ead9ad]/60">
                <div
                  className="h-full bg-[#c9a33a] transition-[width] duration-300 ease-linear"
                  style={{ width: `${progress}%` }}
                />
              </div>
            )}
          </div>
        )}

        <form
          onSubmit={handleSubmit}
          className={`flex items-end gap-2 rounded-2xl border bg-white p-2 shadow-sm transition-all focus-within:border-[#7aa08b] focus-within:shadow-md focus-within:ring-4 focus-within:ring-[#476d5b]/10 ${
            ready ? "border-[#d5ddd7]" : "border-[#e6ebe7] opacity-60"
          }`}
        >
          <textarea
            ref={textarea}
            value={input}
            rows={1}
            maxLength={MAX_QUESTION_LENGTH}
            disabled={!ready}
            onChange={(event) => {
              setInput(event.target.value);
              resizeTextarea();
            }}
            onKeyDown={handleKeyDown}
            placeholder={
              ready ? "Ask about this page…" : "Transcribe the page first"
            }
            aria-label="Your question"
            className="max-h-32 min-h-[2.5rem] flex-1 resize-none bg-transparent px-2.5 py-2 text-sm text-[#26332d] outline-none placeholder:text-[#9aa6a0]"
          />
          <button
            type="submit"
            disabled={!canSend}
            aria-label="Send"
            title={waiting ? `Wait ${formatWait(secondsLeft)}` : "Send"}
            className="grid size-10 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-[#4f7a65] to-[#2f5645] text-white shadow-sm transition-all hover:shadow-md enabled:active:scale-95 disabled:cursor-not-allowed disabled:from-[#c9d4cd] disabled:to-[#c9d4cd] disabled:shadow-none"
          >
            {waiting ? (
              <span className="font-mono text-[11px] font-semibold tabular-nums">
                {formatWait(secondsLeft)}
              </span>
            ) : (
              <ArrowUp className="size-5" />
            )}
          </button>
        </form>

        <div className="mt-2 flex items-center justify-between px-1 text-[11px] text-[#97a39d]">
          <span>
            Enter to send · Shift+Enter for a new line · remembers the last{" "}
            {MAX_HISTORY} messages
          </span>
          {input.length > MAX_QUESTION_LENGTH - 100 && (
            <span className="tabular-nums">
              {input.length}/{MAX_QUESTION_LENGTH}
            </span>
          )}
        </div>
      </div>

      {confirm && (
        <ConfirmDelete
          mode={confirm}
          onCancel={() => setConfirm(null)}
          onConfirm={confirmDelete}
        />
      )}
    </aside>
  );
}
