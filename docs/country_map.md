# Feature: Country map

A world map for one collection. Countries that are mentioned in the manuscripts are coloured.
Click a country to see every place mentioned there, then click a place to open the original page.

## What it does
1. A collection picker chooses what the map shows.
2. Countries with mentions are coloured green. More mentions give a darker green. Other countries are not clickable.
3. Hovering shows "Switzerland · 2 mentions".
4. Clicking a country lists its mentions, grouped by document, with a short text snippet.
5. Clicking a mention opens the page image (the evidence). Escape or a click outside closes it.

Leaflet and OpenStreetMap are used. Google Maps needs a billing account.

## Data it reads
Two tables are filled by the place detection step, and a view joins them:
- `places`: `name`, `country_code` (2 letters such as `CH`), `lat`, `lng`
- `place_mentions`: `place_id`, `page_id`, `snippet`
- view `mention_details`: one row per mention with page, document and collection (only the backend key can read it)

## API
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/collections/{id}/map/countries` | Countries with `mention_count` and `place_count` |
| GET | `/api/collections/{id}/map/countries/{CH}/mentions` | Mentions in one country, each with `page_id` |

## Files
Backend: `services/map_data.py` (counting), `database/paging.py` (Supabase returns at most 1000 rows per request), `routes/map.py`, two classes in `schemas.py`, and `list_mention_details` in `database/repository.py`.

Frontend:
| File | Job |
|---|---|
| `src/api/map.js` | The calls to the two endpoints |
| `src/lib/countries.js` | Country code from a shape, colour shades |
| `src/lib/useFetch.js` | Loads data and ignores late answers (click France, then Italy quickly) |
| `src/components/MapSection.jsx` | Owns the state, puts everything together |
| `src/components/CountryMap.jsx` | The map |
| `src/components/CountryMentionsPanel.jsx` | The list on the right |
| `src/components/PageViewerModal.jsx` | The page viewer. |
| `public/data/countries.geojson` | Country borders (Natural Earth) |

`App.jsx` renders `<MapSection collections={...} />`.

## Run and test
```bash
cd frontend && npm install leaflet react-leaflet && npm run dev
cd backend && pytest -v 
```

## Limits
- The border file is the 110m version. It has no Monaco, Liechtenstein, Vatican, San Marino, Malta or Singapore. Use `ne_50m_admin_0_countries.geojson` (about 3 MB, same URL with `50m`) to include them.