import { FileText } from "lucide-react";
import { countryDisplayName } from "../libraray/countries.js";

/**
 * Right-hand list: every place found in the selected country, grouped by
 * document. Clicking "Open page" tells the parent which page to show.
 */
export function CountryMentionsPanel({
  countryCode,
  mentions,
  loading,
  error,
  onOpenPage,
}) {
  if (!countryCode) {
    return (
      <p className="text-sm text-[#7e8b85]">
        Click a coloured country on the map to see where it appears in your
        manuscripts.
      </p>
    );
  }

  // Group the flat list by document so the reader sees "letter_001.pdf: p.2, p.5".
  const byDocument = new Map();
  for (const m of mentions) {
    if (!byDocument.has(m.document_id))
      byDocument.set(m.document_id, { name: m.document_name, items: [] });
    byDocument.get(m.document_id).items.push(m);
  }

  return (
    <div>
      <h3 className="font-serif text-xl tracking-[-0.02em]">
        {countryDisplayName(countryCode)}
      </h3>
      <p className="mb-4 text-sm text-[#7e8b85]">
        {loading
          ? "Loading…"
          : `${mentions.length} mention${mentions.length === 1 ? "" : "s"}`}
      </p>

      {error && <p className="mb-3 text-sm text-red-700">{error}</p>}

      <div className="max-h-[360px] space-y-5 overflow-y-auto pr-1">
        {[...byDocument.entries()].map(([documentId, doc]) => (
          <div key={documentId}>
            <p className="mb-2 flex items-center gap-2 text-sm font-medium text-[#314b3e]">
              <FileText className="size-4" /> {doc.name}
            </p>
            <ul className="space-y-2">
              {doc.items.map((m) => (
                <li key={m.mention_id}>
                  <button
                    type="button"
                    onClick={() => onOpenPage(m)}
                    className="w-full rounded-lg border border-[#e0e6e0] bg-white px-3 py-2 text-left transition-colors hover:bg-[#edf1ed]"
                  >
                    <span className="block text-sm font-semibold">
                      {m.place_name}{" "}
                      <span className="font-normal text-[#7e8b85]">
                        · page {m.page_number}
                      </span>
                    </span>
                    {m.snippet && (
                      <span className="mt-1 block text-xs text-[#6e7975]">
                        “{m.snippet}”
                      </span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
