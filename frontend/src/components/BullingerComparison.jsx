import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, Pause, Play } from "lucide-react";
import example from "../data/bullinger/example.json";
import additionalExamples from "../data/bullinger/additionalExamples.json";
import imageUrl from "../data/bullinger/611_01_r1l31.png";
import { compareTranscriptions } from "../tools/transcriptionComparison.js";

const examples = [
  {
    ...example,
    imageUrl,
    title: "Letter 611 / Latin / Line 31",
    sourceUrl: "https://www.bullinger-digital.ch/letter/611",
    sourcePath: "TRAIN 0–2000, Latin",
  },
  ...additionalExamples.map((item) => ({
    ...item,
    imageUrl: new URL(`../data/bullinger/${item.imageFile}`, import.meta.url)
      .href,
  })),
];
const slides = examples.map((item) => item.title);
const controlClass =
  "inline-flex items-center justify-center gap-2 rounded-lg border border-[#dfe5df] bg-white px-3 py-2 text-sm text-[#1e3b35] hover:bg-[#edf1ed] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#476d5b]";

function Transcript({ title, parts, highlight }) {
  return (
    <div className="rounded-xl border border-[#dfe5df] bg-white p-5">
      <h3 className="text-sm font-medium text-[#476d5b]">{title}</h3>
      <p className="mt-4 whitespace-pre-wrap break-words font-serif text-xl leading-9">
        {parts.map((part, index) =>
          highlight && part.changed ? (
            <mark
              key={index}
              className="rounded bg-amber-200 text-[#1e2a27] underline decoration-amber-700 decoration-2 underline-offset-4"
            >
              {part.text}
            </mark>
          ) : (
            <span key={index}>{part.text}</span>
          ),
        )}
      </p>
    </div>
  );
}

export function BullingerComparison() {
  const [highlight, setHighlight] = useState(true);
  const [slide, setSlide] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [hovered, setHovered] = useState(false);

  useEffect(() => {
    if (!playing || hovered || examples.length < 2) return undefined;
    const timer = window.setInterval(() => {
      setSlide((current) => (current + 1) % slides.length);
    }, 8000);
    return () => window.clearInterval(timer);
  }, [playing, hovered]);

  function goTo(index) {
    setPlaying(false);
    setSlide((index + slides.length) % slides.length);
  }

  return (
    <section
      aria-labelledby="bullinger-heading"
      aria-roledescription="carousel"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocusCapture={() => setPlaying(false)}
      onKeyDown={(event) => {
        if (event.target instanceof HTMLInputElement) return;
        if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
          event.preventDefault();
          goTo(slide + (event.key === "ArrowRight" ? 1 : -1));
        }
      }}
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-[#476d5b]">
            Bullinger · Latin · Letter 611
          </p>
          <h2
            id="bullinger-heading"
            className="mt-2 font-serif text-3xl tracking-tight"
          >
            Reference and our transcription
          </h2>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-[#6e7975]">
            Each example shows the manuscript image, Bullinger reference and our
            saved transcription together.
          </p>
        </div>
        <span className="rounded-full bg-[#edf1ed] px-3 py-1 text-xs text-[#476d5b]">
          {examples.length} saved examples
        </span>
      </div>
      <div className="mt-6 overflow-hidden rounded-2xl border border-[#dfe5df] bg-[#edf1ed]">
        <div className="flex items-center justify-between gap-4 border-b border-[#dfe5df] px-5 py-4">
          <p className="text-sm font-medium text-[#476d5b]">
            0{slide + 1} / 0{slides.length} · {slides[slide]}
          </p>
        </div>
        <div className="overflow-hidden">
          <div
            className="flex items-stretch transition-transform duration-500 ease-in-out motion-reduce:transition-none"
            style={{ transform: `translateX(-${slide * 100}%)` }}
          >
            {examples.map((item, index) => {
              const comparison = compareTranscriptions(
                item.reference,
                item.prediction,
              );
              return (
                <div
                  key={item.lineId}
                  role="group"
                  aria-roledescription="slide"
                  aria-label={`${index + 1} of ${examples.length}: ${item.title}`}
                  aria-hidden={slide !== index}
                  inert={slide !== index}
                  className="w-full shrink-0 p-5 sm:p-8"
                >
                  <h3 className="font-serif text-2xl">{item.title}</h3>
                  <figure className="my-5 overflow-hidden rounded-xl border border-[#dfe5df] bg-[#f2eee5] p-4">
                    <img
                      src={item.imageUrl}
                      alt={`Original handwritten manuscript: ${item.title}`}
                      className="mx-auto h-auto max-w-full"
                    />
                    <figcaption className="mt-3 text-center text-xs text-[#55615b]">
                      Original line · {item.lineId}
                    </figcaption>
                  </figure>{" "}
                  <label className="mb-4 flex w-fit cursor-pointer items-center gap-2 text-sm text-[#55615b]">
                    <input
                      type="checkbox"
                      checked={highlight}
                      onChange={(event) => setHighlight(event.target.checked)}
                      className="accent-[#1e3b35]"
                    />
                    Highlight differing characters (underlined in amber)
                  </label>{" "}
                  <div className="grid gap-4 md:grid-cols-2">
                    <Transcript
                      title="Bullinger reference transcription"
                      parts={comparison.referenceParts}
                      highlight={highlight}
                    />
                    <Transcript
                      title="Our HTR transcription · unverified"
                      parts={comparison.predictionParts}
                      highlight={highlight}
                    />
                  </div>
                  <p className="mt-4 text-sm text-[#55615b]">
                    Character error rate:{" "}
                    <strong>{(comparison.cer * 100).toFixed(2)}%</strong> ·{" "}
                    {comparison.characterErrors} character edits. Lower is
                    better; 0% is an exact match. Case, accents and punctuation
                    are retained.
                  </p>
                  <p className="mt-3 text-xs leading-6 text-[#6e7975]">
                    <a href={item.sourceUrl} className="underline">
                      View source letter
                    </a>{" "}
                    · {item.sourcePath}. Saved TrOCR CPU prediction with
                    candidate reranking.
                  </p>
                </div>
              );
            })}
          </div>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[#dfe5df] px-5 py-4">
          <button
            type="button"
            className={`${controlClass} disabled:opacity-40`}
            disabled={examples.length < 2}
            onClick={() => goTo(slide - 1)}
            aria-label="Previous slide"
          >
            <ArrowLeft size={16} /> Previous
          </button>
          <div className="flex gap-2" aria-label="Choose slide">
            {slides.map((title, index) => (
              <button
                key={title}
                type="button"
                aria-label={`Slide ${index + 1}: ${title}`}
                aria-current={slide === index ? "step" : undefined}
                onClick={() => goTo(index)}
                className="flex size-9 items-center justify-center rounded-full focus-visible:outline-2 focus-visible:outline-[#476d5b]"
              >
                <span
                  className={`block h-2 rounded-full transition-all motion-reduce:transition-none ${slide === index ? "w-6 bg-[#1e3b35]" : "w-2 bg-[#9aac9f]"}`}
                />
              </button>
            ))}
          </div>
          <button
            type="button"
            className={`${controlClass} disabled:opacity-40`}
            disabled={examples.length < 2}
            onClick={() => goTo(slide + 1)}
            aria-label="Next slide"
          >
            Next <ArrowRight size={16} />
          </button>
        </div>
      </div>
      <p className="mt-3 text-xs leading-6 text-[#6e7975]">
        These training examples demonstrate the comparison; they are not an
        independent accuracy benchmark. Dataset references come from edition or
        provisional transcriptions and may contain alignment errors. Uploaded
        documents require their own matching reference.
      </p>
      <p className="mt-2 text-xs leading-6 text-[#6e7975]">
        Source:{" "}
        <a href="https://github.com/pstroe/bullinger-htr" className="underline">
          Bullinger HTR dataset
        </a>{" "}
        ·{" "}
      </p>
    </section>
  );
}
