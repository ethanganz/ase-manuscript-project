import { Plus } from 'lucide-react'

export function Hero({ onCreateCollection }) {
  return (
    <section className="flex flex-col justify-between gap-8 border-b border-[#dfe5df] pb-14 md:flex-row md:items-end">
      <div>
        <p className="mb-4 text-xs font-semibold uppercase tracking-[0.18em] text-[#8b9c91]">
          A living archive
        </p>
        <h1 className="font-serif text-5xl tracking-[-0.05em] text-[#1e302b] sm:text-6xl">
          Explore the archive.
        </h1>
        <p className="mt-5 max-w-xl text-[15px] leading-7 text-[#71807a]">
          Discover handwritten histories, places, and stories preserved across remarkable collections.
        </p>
      </div>

      <button
        type="button"
        onClick={onCreateCollection}
        className="inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-[#1e3b35] px-5 text-sm font-medium text-white shadow-[0_8px_18px_rgba(30,59,53,0.16)] transition hover:bg-[#294c43]"
      >
        <Plus />
        New collection
      </button>
    </section>
  )
}
