// Helpers that connect the country shapes (GeoJSON) with our mention counts.

/**
 * Returns the 2-letter country code of a GeoJSON feature, e.g. "CH", or null.
 *
 * Natural Earth quirk: for some countries (France, Norway, ...) the field
 * ISO_A2 contains the placeholder "-99". The field ISO_A2_EH ("EH" = extra
 * handling) has the real code, so we read that one first.
 */
export function getCountryCode(feature) {
  const props = feature?.properties ?? {}
  for (const value of [props.ISO_A2_EH, props.ISO_A2]) {
    if (typeof value === 'string' && /^[A-Za-z]{2}$/.test(value)) {
      return value.toUpperCase()
    }
  }
  return null
}

/** "CH" -> "Switzerland". Falls back to the code if the browser does not know it. */
export function countryDisplayName(code) {
  try {
    return new Intl.DisplayNames(['en'], { type: 'region' }).of(code) ?? code
  } catch {
    return code
  }
}

/** Turns the API list [{country_code, mention_count, ...}] into { CH: {...}, FR: {...} }. */
export function indexByCode(summaries) {
  const byCode = {}
  for (const item of summaries) byCode[item.country_code] = item
  return byCode
}

// Light -> dark green, so countries with more mentions look stronger.
const SHADES = ['#cfe3d6', '#a8cdb5', '#7fb394', '#4f9170', '#2f6b50']

/**
 * Leaflet "style" for one country.
 *  - no mentions  -> almost invisible (the base map shows through)
 *  - has mentions -> a green shade that grows with the number of mentions
 *  - selected     -> thick dark outline
 */
export function countryStyle(summary, maxCount, isSelected) {
  if (!summary) {
    return { fillColor: '#ffffff', fillOpacity: 0, color: '#9aa7a0', weight: 0.4 }
  }
  const ratio = maxCount > 0 ? summary.mention_count / maxCount : 0
  const shade = SHADES[Math.min(SHADES.length - 1, Math.floor(ratio * SHADES.length))]
  return {
    fillColor: shade,
    fillOpacity: 0.75,
    color: isSelected ? '#14352a' : '#476d5b',
  
   
    weight: isSelected ? 3 : 1,
  }
}