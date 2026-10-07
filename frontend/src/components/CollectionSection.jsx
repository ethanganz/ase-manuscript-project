import { ArrowUpRight, MoreHorizontal, Search } from 'lucide-react'

function CollectionCard({ collection }) {
  return (
    <article className="group rounded-xl border border-[#e0e6e0] bg-white p-5 transition hover:-translate-y-0.5 hover:border-[#c3d2c7] hover:shadow-[0_12px_30px_rgba(35,55,45,0.07)]">
      <div className="mb-5 flex h-32 items-end rounded-lg bg-[#d9e4dc] p-4">
        <div className="w-full rounded-md border border-black/5 bg-[#fbfaf5]/70 p-3 backdrop-blur-sm">
          <div className="h-1 w-1/2 rounded bg-[#53645b]/35" />
          <div className="mt-2 h-1 w-4/5 rounded bg-[#53645b]/20" />
          <div className="mt-2 h-1 w-2/3 rounded bg-[#53645b]/20" />
        </div>
      </div>

      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-serif text-[19px] leading-tight">{collection.name}</h3>
          <p className="mt-1 text-xs text-[#8a9790]">
            {collection.description || 'No description'}
          </p>
        </div>

        <button className="text-[#99a39e] opacity-0 transition group-hover:opacity-100" aria-label={`More options for ${collection.name}`}>
          <MoreHorizontal />
        </button>
      </div>

      <div className="mt-5 flex items-center justify-between border-t border-[#edf0ed] pt-4 text-xs text-[#8a9790]">
        <span>Open collection</span>
        <ArrowUpRight className="size-4 text-[#6f8e7b]" />
      </div>
    </article>
  )
}

export function CollectionSection({ collections, search, onSearchChange }) {
  const filteredCollections = collections.filter((collection) =>
    collection.name.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <section id="collections" className="py-12">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-[#8b9c91]">The archive</p>
          <h2 className="font-serif text-3xl tracking-[-0.04em]">Collections</h2>
          <p className="mt-2 text-sm text-[#7e8b85]">Historical materials you are currently exploring.</p>
        </div>

        <label className="flex h-10 w-full items-center gap-2 rounded-lg border border-[#dfe5df] bg-white px-3 text-sm text-[#89958f] sm:w-64">
          <Search className="size-4" />
          <input
            type="text"
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
            className="w-full bg-transparent outline-none placeholder:text-[#a0aaa5]"
            placeholder="Search collections"
            aria-label="Search collections"
          />
        </label>
      </div>

      <div className="mt-7 grid gap-5 xl:grid-cols-3">
        {filteredCollections.map((collection) => (
          <CollectionCard key={collection.id} collection={collection} />
        ))}
      </div>

      {filteredCollections.length === 0 && (
        <p className="mt-6 text-sm text-[#7e8b85]">No collections found.</p>
      )}
    </section>
  )
}
