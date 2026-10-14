import 'leaflet/dist/leaflet.css'
import { useEffect, useMemo, useState } from 'react'
import { GeoJSON, MapContainer, TileLayer } from 'react-leaflet'
import { countryDisplayName, countryStyle, getCountryCode, indexByCode } from '../libraray/countries.js'
// The map itself
// import.meta.env.BASE_URL keeps this working when the app is served under a
// sub-path (VITE_BASE_PATH, e.g. /apps/staging/).
const COUNTRIES_URL = `${import.meta.env.BASE_URL}data/countries.geojson`

/**
 * World map. Countries that appear in the manuscripts are coloured; clicking
 * one calls onSelectCountry("CH").
 *
 * Props:
 *   summaries        - [{country_code, mention_count, place_count}] from the API
 *   selectedCode     - currently selected country code or ""
 *   onSelectCountry  - function(code)
 */
export function CountryMap({ summaries, selectedCode, onSelectCountry }) {
  const [shapes, setShapes] = useState(null) // the GeoJSON with all country borders
  const [loadError, setLoadError] = useState('')

  // Load the borders once.
  useEffect(() => {
    let cancelled = false
    fetch(COUNTRIES_URL)
      .then((r) => {
        if (!r.ok) throw new Error(`Could not load country borders (${r.status})`)
        return r.json()
      })
      .then((json) => !cancelled && setShapes(json))
      .catch((e) => !cancelled && setLoadError(e.message))
    return () => {
      cancelled = true
    }
  }, [])

  const byCode = useMemo(() => indexByCode(summaries), [summaries])
  const maxCount = useMemo(() => Math.max(0, ...summaries.map((s) => s.mention_count)), [summaries])

  // react-leaflet does not re-style a GeoJSON layer when props change, so we
  // give it a new `key` whenever the data or selection changes. A new key makes
  // React rebuild the layer (cheap: ~180 shapes). The map position stays.
  const layerKey = `${selectedCode}|${summaries.map((s) => `${s.country_code}:${s.mention_count}`).join(',')}`

  function styleFeature(feature) {
    const code = getCountryCode(feature)
    return countryStyle(byCode[code], maxCount, code === selectedCode)
  }

  // Runs once per country shape: add hover text and the click handler.
  function onEachFeature(feature, layer) {
    const code = getCountryCode(feature)
    const summary = byCode[code]
    if (!summary) return // countries without mentions are not clickable

    const label = `${countryDisplayName(code)} · ${summary.mention_count} mention${summary.mention_count === 1 ? '' : 's'}`
    layer.bindTooltip(label, { sticky: true })
    layer.on({
      click: () => onSelectCountry(code),
      mouseover: (e) => e.target.setStyle({ weight: 3 }),
      mouseout: (e) => e.target.setStyle(countryStyle(summary, maxCount, code === selectedCode)),
    })
  }

  return (
    <div className="relative">
      <MapContainer
        center={[30, 10]}
        zoom={2}
        minZoom={2}
        maxBounds={[[-85, -200], [85, 200]]}
        worldCopyJump
        scrollWheelZoom
        className="h-[460px] w-full rounded-xl"
      >
        <TileLayer
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />
        {shapes && (
          <GeoJSON key={layerKey} data={shapes} style={styleFeature} onEachFeature={onEachFeature} />
        )}
      </MapContainer>

      {loadError && (
        <p className="absolute left-3 top-3 z-[1000] rounded bg-white px-3 py-2 text-sm text-red-700 shadow">
          {loadError}
        </p>
      )}
    </div>
  )
}