export function getCountryCode(feature) {
  const properties = feature.properties || {}
  return properties.ISO_A2 !== '-99' ? properties.ISO_A2 : properties.ISO_A2_EH
}

export function countryDisplayName(code) {
  try {
    return new Intl.DisplayNames(['en'], { type: 'region' }).of(code) || code
  } catch {
    return code
  }
}

export function indexByCode(summaries) {
  return Object.fromEntries(summaries.map((summary) => [summary.country_code, summary]))
}

export function countryStyle(summary, maxCount, selected) {
  const strength = summary && maxCount ? summary.mention_count / maxCount : 0
  return {
    color: selected ? '#1e3b35' : '#aabbb0',
    weight: selected ? 2.5 : 1,
    fillColor: summary ? '#557d64' : '#e8eee9',
    fillOpacity: summary ? 0.35 + strength * 0.5 : 0.55,
  }
}
