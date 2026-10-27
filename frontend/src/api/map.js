// Calls to the two map endpoints of the backend.

async function getJson(url) {
  const response = await fetch(url);
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail =
      data && typeof data.detail === "string"
        ? data.detail
        : `Request failed (${response.status})`;
    throw new Error(detail);
  }
  return data;
}

/** Countries that have mentions in a collection: [{country_code, mention_count, place_count}] */
export function getCountrySummaries(collectionId) {
  return getJson(`/api/collections/${collectionId}/map/countries`);
}

/** Every mention inside one country, each with the page it came from. */
export function getCountryMentions(collectionId, countryCode) {
  return getJson(
    `/api/collections/${collectionId}/map/countries/${countryCode}/mentions`,
  );
}

/** URL of a page image (the backend streams it from Supabase Storage). */
export function pageImageUrl(pageId) {
  return `/api/pages/${pageId}/image`;
}
