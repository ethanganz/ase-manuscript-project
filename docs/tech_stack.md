# Tech stack
## How the pieces fit

```
Browser (React) ──> nginx ──> FastAPI (Python) ──> Supabase (database + file storage)
                                   │
                                   ├── PyMuPDF / Pillow: turn uploads into page images
                                   └── place resolution code: word -> real place

Map: Leaflet draws OpenStreetMap + country borders
```

## Backend

| Technology | What it does | Why we use it | Where it came from |
|---|---|---|---|
| Python | The language of the backend and the place resolution code | Easy to read, and the machine learning world uses it. |
| FastAPI | Web framework: turns Python functions into API endpoints and checks the data | Short code, automatic checks. |
| Uvicorn | The server that runs FastAPI | The standard server for FastAPI. |
| Pydantic | Defines and checks the shape of the data (`schemas.py`) | FastAPI uses it for every request and answer | Installed together with FastAPI. |
| python-multipart | Lets FastAPI receive uploaded files | FastAPI cannot read file uploads without it | Community project. `pip`. |
| PyMuPDF | Opens PDFs and renders each page to an image | Fast, and needs no extra programs installed |  built on their MuPDF engine. `pip`. |
| Pillow | Opens and checks JPG and PNG images, reads their size | The standard Python image library | A maintained fork of the old PIL. `pip`. |
| pillow-heif | Lets Pillow read iPhone HEIC photos | Browsers cannot show HEIC, so we convert the page image to JPEG | `pip`. |
| python-dotenv | Reads secrets from the `.env` file | Keeps keys out of the code | `pip`. |
| supabase (Python library) | Talks to the database and file storage from the backend | One library for both | By Supabase. `pip`. |

## Database and storage

| Technology | What it does | Why we use it | Where it came from |
|---|---|---|---|
| Supabase | Hosted service with a database, file storage and access rules | no server to run, and storage is in the same place as the data. |
| PostgreSQL | The database inside Supabase (collections, documents, pages, places) | Reliable, and Supabase is built on it | Open source, by the PostgreSQL Global Development Group. Comes with Supabase. |
| Supabase Storage | Keeps the original files and page images (bucket `documents`) | Files do not belong in the database | Part of Supabase. |
| Row Level Security | Locks tables so only the backend key can use them | Keeps the data from being read directly with the public key | A PostgreSQL feature. |

## Frontend

| Technology | What it does | Why we use it | Where it came from |
|---|---|---|---|
| React | Builds the web pages from components | Components fit our screens (map, list, upload window) | `npm`. |
| Vite | Runs the page while developing and builds the final files | Very fast | `npm`. |
| Tailwind CSS | Styling with short class names | By Tailwind Labs. `npm`. |
| lucide-react | Icons | Open source icon set (a fork of Feather icons). `npm`. |
| Node.js and npm | Runs the build and installs the frontend libraries | Needed by Vite and React | Used in the Docker build. |

## Map

| Technology | What it does | Why we use it | Where it came from |
|---|---|---|---|
| Leaflet | Draws the interactive map, zoom and country shapes | `npm`. |
| react-leaflet | Lets React control Leaflet | The rest of the page is React | `npm`. |
| OpenStreetMap tiles | The map pictures under the countries | Free for development | Made by the OpenStreetMap community. Loaded in the browser from `tile.openstreetmap.org`. The attribution text on the map is required. |
| Natural Earth country borders | The shapes of all countries, so we can colour them | Free and in the public domain | Made by Natural Earth volunteers. We downloaded `ne_110m_admin_0_countries.geojson` from the `nvkelso/natural-earth-vector` repository on GitHub into `public/data/`. |

## Testing

| Technology | What it does | Why we use it | Where it came from |
|---|---|---|---|
| pytest | Runs the backend tests | The standard Python test tool | `pip`, in `requirements-dev.txt`. |
| httpx | Lets the tests call the API like a browser would | Needed by FastAPI's test client | `pip`. |

## Deployment

| Technology | What it does | Why we use it | Where it came from |
|---|---|---|---|
| Docker and Docker Compose | Packs the backend and frontend into containers and starts both | Runs the same on every computer | By Docker, Inc. |
| nginx | Serves the web page and forwards `/api` requests to the backend | Standard, small, and handles big uploads when configured | . We use the `nginxinc/nginx-unprivileged` image. We added the larger upload limit. |
| GitHub Actions | Builds the images when code reaches `main` | Automatic | By GitHub. |
| GitHub Container Registry | Stores the built images | Free with GitHub | By GitHub. |

## Machine learning and data (outside this repository)

| Technology | What it does | Why we use it | Where it came from |
|---|---|---|---|
| Handwriting recognition model | Turns a picture of a handwritten line into text | The first step of the whole chain. |
| GLiNER (`urchade/gliner_multi-v2.1`) | Finds words that may be places in the text | Already trained, handles many languages, no training needed | A published model by Urchade Zaratiana and co-authors, available on Hugging Face. |
| Historical name dictionary | Old spellings of place names | The model only knows modern text. |
| Bullinger corpus (TEI) | The letters, with editors' place tags, and the official place list `localities.xml` (about 3,000 places with coordinates) | Gives us old Latin spellings and real coordinates for free | Published by the University of Zürich (Institut für Computerlinguistik, Volk et al.) at `github.com/stazh/bullinger-korpus-tei`. We use `data/index/localities.xml` and the `<placeName ref="...">` tags in the letters. |
| TEI (Text Encoding Initiative) | The XML format the letters are written in | It is how the corpus comes | An international standard for encoding texts. |
| Plain Python rules (`services/`) | Country codes, merging candidates, building and using the spelling dictionary | With few labelled examples, simple rules are safer and can be explained | Written by us. |