import { ArrowUpRight, MoreHorizontal, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { CollectionPreview } from "../tools/helpers.jsx";

const COLLECTIONS_PER_PAGE = 6;

function CollectionCard({ collection }) {
  return (
    <article className="group relative rounded-xl border border-[#e0e6e0] bg-white p-5 transition hover:-translate-y-0.5 hover:border-[#c3d2c7] hover:shadow-[0_12px_30px_rgba(35,55,45,0.07)]">
      <CollectionPreview
        collectionId={collection.id}
        className="mb-5 h-32 w-full rounded-lg"
      />

      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-serif text-[19px] leading-tight">
            {/* The ::after makes the whole card clickable. */}
            <a
              href={`#collection/${collection.id}`}
              className="after:absolute after:inset-0 after:rounded-xl"
            >
              {collection.name}
            </a>
          </h3>
          <p className="mt-1 text-xs text-[#8a9790]">
            {collection.description || "No description"}
          </p>
        </div>

        <button
          className="relative z-10 text-[#99a39e] opacity-0 transition group-hover:opacity-100"
          aria-label={`More options for ${collection.name}`}
        >
          <MoreHorizontal />
        </button>
      </div>

      <div className="mt-5 flex items-center justify-between border-t border-[#edf0ed] pt-4 text-xs text-[#8a9790]">
        <span>Open collection</span>
        <ArrowUpRight className="size-4 text-[#6f8e7b]" />
      </div>
    </article>
  );
}

function CollectionSkeletonCard() {
  return (
    <div className="animate-pulse rounded-xl border border-[#e0e6e0] bg-white p-5">
      <div className="mb-5 h-32 rounded-lg bg-[#e4ece5]" />
      <div className="h-5 w-2/3 rounded bg-[#e4ece5]" />
      <div className="mt-3 h-3 w-full rounded bg-[#edf1ee]" />
      <div className="mt-2 h-3 w-4/5 rounded bg-[#edf1ee]" />
      <div className="mt-6 h-px bg-[#edf1ee]" />
      <div className="mt-4 h-3 w-1/3 rounded bg-[#edf1ee]" />
    </div>
  );
}

export function CollectionSection({
  collections,
  search,
  onSearchChange,
  isLoading,
}) {
  const [page, setPage] = useState(1);

  const filteredCollections = useMemo(
    () =>
      collections.filter(
        (collection) =>
          // Private collections are never listed here, not even for their owner.
          collection.is_public !== false &&
          collection.name.toLowerCase().includes(search.toLowerCase()),
      ),
    [collections, search],
  );

  const totalPages = Math.max(
    1,
    Math.ceil(filteredCollections.length / COLLECTIONS_PER_PAGE),
  );

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPage(() => 1);
  }, [search, filteredCollections.length]);

  const currentPage = Math.min(page, totalPages);
  const startIndex = (currentPage - 1) * COLLECTIONS_PER_PAGE;
  const visibleCollections = filteredCollections.slice(
    startIndex,
    startIndex + COLLECTIONS_PER_PAGE,
  );

  return (
    <section id="collections" className="py-12">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-[#8b9c91]">
            The archive
          </p>
          <h2 className="font-serif text-3xl tracking-[-0.04em]">
            Collections
          </h2>
          <p className="mt-2 text-sm text-[#7e8b85]">
            Historical materials you are currently exploring.
          </p>
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

      {isLoading ? (
        <div className="mt-7 grid gap-5 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <CollectionSkeletonCard key={`skeleton-${index}`} />
          ))}
        </div>
      ) : (
        <>
          <div className="mt-7 grid gap-5 xl:grid-cols-3">
            {visibleCollections.map((collection) => (
              <CollectionCard key={collection.id} collection={collection} />
            ))}
          </div>

          {filteredCollections.length === 0 && (
            <p className="mt-6 text-sm text-[#7e8b85]">No collections found.</p>
          )}

          {filteredCollections.length > COLLECTIONS_PER_PAGE && (
            <div className="mt-8 flex items-center justify-between gap-3 rounded-xl border border-[#e0e6e0] bg-white px-4 py-3 text-sm text-[#55615b]">
              <button
                type="button"
                onClick={() => setPage((current) => Math.max(1, current - 1))}
                disabled={currentPage === 1}
                className="rounded-md border border-[#dfe5df] px-3 py-1.5 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Previous
              </button>

              <span>
                Page {currentPage} of {totalPages}
              </span>

              <button
                type="button"
                onClick={() =>
                  setPage((current) => Math.min(totalPages, current + 1))
                }
                disabled={currentPage === totalPages}
                className="rounded-md border border-[#dfe5df] px-3 py-1.5 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </section>
  );
}
