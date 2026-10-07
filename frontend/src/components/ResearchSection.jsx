import { ArrowUpRight, Check, Sparkles } from 'lucide-react'

export function ResearchSection({ places }) {
  return (
    <section id="places" className="grid gap-6 border-t border-[#dfe5df] pt-12 xl:grid-cols-[1.2fr_0.8fr]">
      <div className="overflow-hidden rounded-xl border border-[#e0e6e0] bg-white">
        <div className="flex items-start justify-between border-b border-[#edf0ed] px-6 py-5">
          <div>
            <h2 className="font-serif text-2xl tracking-[-0.03em]">A map of your research</h2>
            <p className="mt-1 text-sm text-[#7e8b85]">Places mentioned across your collections.</p>
          </div>

          <button className="text-sm font-medium text-[#476d5b] hover:underline">
            Open map
            <ArrowUpRight className="ml-1 inline size-4" />
          </button>
        </div>

        <div
          className="relative h-[310px] overflow-hidden bg-[#e8eee9]"
          style={{ backgroundImage: 'radial-gradient(#c5d2c8 1px, transparent 1px)', backgroundSize: '18px 18px' }}
        >
          <div className="absolute left-[18%] top-[12%] h-[75%] w-[55%] rotate-[-8deg] rounded-[45%_55%_50%_45%] bg-[#d6e1d8]" />
          <div className="absolute left-[36%] top-[35%] h-[40%] w-[30%] rotate-[22deg] rounded-[45%_55%_45%_55%] bg-[#c5d6c9]" />

          <svg className="absolute inset-0 h-full w-full" viewBox="0 0 600 310" aria-hidden="true">
            <path
              d="M226 99 C287 132 300 163 349 206 S389 242 438 171"
              fill="none"
              stroke="#7f9f8b"
              strokeWidth="2"
              strokeDasharray="5 6"
            />
          </svg>

          {places.map((place) => (
            <button
              key={place.name}
              className="absolute -translate-x-1/2 -translate-y-1/2 text-left"
              style={{ left: place.x, top: place.y }}
            >
              <span className="grid size-8 place-items-center rounded-full border-4 border-white bg-[#517967] shadow-md">
                <span className="size-2 rounded-full bg-white" />
              </span>
              <span className="mt-2 block rounded bg-white/85 px-2 py-1 text-xs font-semibold text-[#314b3e] shadow-sm backdrop-blur-sm">
                {place.name}
              </span>
            </button>
          ))}
        </div>
      </div>
    </section>
  )
}
