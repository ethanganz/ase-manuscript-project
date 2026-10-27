// MOCK DATA ONLY. Stands in for transcriptions and places until the backend
// produces real ones. Each document always gets the same mock text and places,
// picked from its id, so switching back and forth stays consistent.

const PASSAGES = [
  [
    "Geneva, the 14th of March 1847",
    "",
    "My dear brother,",
    "I write to you from the lodgings on the Rue du Rhône, where the",
    "wind off the lake has not ceased these three days. The boat from",
    "Lausanne arrived late, and I fear the parcel of books you sent",
    "has been delayed at the customs house once more.",
    "Mother is in good health and asks after you daily. She wishes",
    "you would write more often, and so, I confess, do I.",
  ],
  [
    "Lyon, 2nd of June",
    "",
    "We arrived in Lyon late in the evening, after a slow passage",
    "along the Saône. The silk merchants were already closing their",
    "shutters, but Monsieur Ferrand received us kindly and gave us",
    "supper. Tomorrow we continue towards Paris by the post road,",
    "if the weather allows it. The roads are said to be poor after",
    "the rains of last week.",
  ],
  [
    "Notes from the journey, continued",
    "",
    "Crossed into the canton of Bern before noon. The valley here is",
    "narrow and the river very high. At the inn in Thun we were told",
    "that the pass would not be open for another fortnight.",
    "Purchased bread, cheese and a map of the region for two francs.",
    "Weather fair. Spirits good, though the horses are tired.",
  ],
  [
    "Paris, Hôtel de Bourgogne",
    "",
    "Sir,",
    "I have the honour to acknowledge your letter of the 9th instant",
    "concerning the shipment bound for Zurich. The goods were placed",
    "in the care of the carrier on Thursday last and should arrive",
    "within ten days, God willing. I enclose the bill of lading and",
    "remain, Sir, your most obedient servant,",
    "",
    "H. Dupont",
  ],
  [
    "Basel, 21st of October",
    "",
    "The Rhine is low this autumn and the boatmen complain bitterly.",
    "I have spent the morning at the university library copying the",
    "register of births for the years 1790 to 1802. Several entries",
    "are damaged by water and can no longer be read with certainty.",
    "I shall return to Zurich on Saturday with what I have found.",
  ],
];

const PLACES = {
  Geneva: { name: "Geneva", country_code: "CH", lat: 46.2044, lng: 6.1432 },
  Lausanne: { name: "Lausanne", country_code: "CH", lat: 46.5197, lng: 6.6323 },
  Lyon: { name: "Lyon", country_code: "FR", lat: 45.764, lng: 4.8357 },
  Paris: { name: "Paris", country_code: "FR", lat: 48.8566, lng: 2.3522 },
  Bern: { name: "Bern", country_code: "CH", lat: 46.948, lng: 7.4474 },
  Thun: { name: "Thun", country_code: "CH", lat: 46.758, lng: 7.628 },
  Zurich: { name: "Zurich", country_code: "CH", lat: 47.3769, lng: 8.5417 },
  Basel: { name: "Basel", country_code: "CH", lat: 47.5596, lng: 7.5886 },
};

/** Turns any string (a document id) into a stable small number. */
function hashString(value) {
  let hash = 0;
  for (const char of value) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return hash;
}

/** Lines of mock transcription for one page of a document. */
export function getMockTranscription(documentId, pageNumber = 1) {
  return PASSAGES[(hashString(documentId) + pageNumber - 1) % PASSAGES.length];
}

/** Mock places for one page: every known place the mock text mentions. */
export function getMockPlaces(documentId, pageNumber = 1) {
  const text = getMockTranscription(documentId, pageNumber).join(" ");
  return Object.values(PLACES).filter((place) => text.includes(place.name));
}
