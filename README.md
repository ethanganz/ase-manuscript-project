# ase-manuscript-project
A web-based application for recognizing, analysing and understanding historical manuscripts.

## Overview

One application, three cooperating parts:

- **frontend/** — the user interface. A React page where people browse collections of uploaded manuscripts, view page images, and explore places mentioned in the text on an interactive map.
- **backend/** — the server. A FastAPI app that serves the frontend, authenticates users, stores uploaded files and metadata in Supabase, and turns PDFs into page images.
- **HTR-NLP/** — the machine-learning pipeline, run separately. It turns cropped handwritten manuscript lines into text with a trained TrOCR model, then turns that text into place mentions with a GLiNER model plus historical place-name variants.

The frontend calls the backend over HTTP. The backend writes and reads files and rows in Supabase. HTR-NLP reads the transcriptions and page images produced by the rest of the app and writes place mentions back, which the frontend displays on the map.

## Live

The application is live at:

**https://manuscript.ethanganz.com**

It is served from the Docker images built by CI on every push to `main`; see [Deploying to the server](#deploying-to-the-server).


## Codebase organization

### `backend/`

FastAPI (Python) REST API.

- `main.py` — creates the app and registers all routes.
- `config.py` — environment variables (Supabase URL/key, JWT secret, upload limits, mail).
- `schemas.py` — Pydantic request/response shapes.
- `deps.py` — FastAPI dependencies: database, storage, mailer, current-user checks.
- `database/` — the only code that reads/writes the PostgreSQL tables (`collections`, `documents`, `pages`).
- `services/` — auth, email (Resend), file ingestion (PDF/ZIP → page images), and storage (Supabase Storage).
- `routes/` — one file per resource: `auth`, `collections`, `documents`, `map`, `names`, `reports`.
- `tests/` — pytest suite; the repositories and storage have in-memory fakes so they run offline.

### `frontend/`

React 19 + Vite + Tailwind CSS single-page app.

- `src/App.jsx` — root component; owns global state (user, modal, notices).
- `src/main.jsx` — entry point.
- `src/components/` — the screens: `Hero`, `CollectionSection` (list), `MapSection` (country map), `CollectionViewer` (page + transcription), `UploadSection`, `ProfilePage`, `AuthModal`, etc.
- `src/api/` — thin `fetch()` wrappers for each backend resource.
- `src/tools/` and `src/library/` — shared helpers (`useFetch`, page-image URLs, country names).
- `src/data/` — mock transcripts/collections for demoing without uploads.
- `vite.config.js` — Vite + React + Tailwind; `index.html` and `public/` hold static assets.

### `HTR-NLP/`

Handwriting recognition and place-resolution pipeline (Python 3.10).

- `scripts/` — `transcribe_images.py` (TrOCR), `extract_places.py` (GLiNER + historical-aliases), plus download and build helpers.
- `configs/` — inference configs (window size, thresholds, model IDs).
- `models-release/` — the distributed TrOCR checkpoint (delivered as a GitHub Release asset, not in Git).
- `data/splits/` — training/validation/test line manifests.
- `scripts/download_model.py` / `download_htr_checkpoint.py` — fetch pinned model snapshots.
- `docs/` — dataset, reproduction, and evaluation notes.

### `docs/` and root

Project documentation (`docs/tech_stack.md`, `docs/upload_pipeline.md`, …), `docker-compose.yml`, `deploy.sh`, and the GitHub Actions CI workflow that build and push the backend and frontend images to GHCR.


## Deploying to the server

CI (`.github/workflows/docker-build.yml`) builds the images on push to `main`
and pushes them to GHCR tagged with the version in `backend/docker/IMAGE_VERSION`
and `frontend/docker/IMAGE_VERSION`, plus `:latest` and the commit SHA.

**Which tag the server runs is set on the server**, in an `.env` file next to
`docker-compose.yml` (gitignored):

```bash
BACKEND_IMAGE_VERSION=0.0.1
FRONTEND_IMAGE_VERSION=0.0.1
```

Docker Compose reads `.env` automatically, so either:

```bash
./deploy.sh                 # git pull + docker compose pull + up -d
# or manually:
docker compose pull && docker compose up -d
```

`deploy.sh` prefers `.env`, falls back to the `IMAGE_VERSION` files if a
variable isn't set there, and compose falls back to `:latest` if neither exists.

**To deploy a new version:** bump the `IMAGE_VERSION` file(s), push to `main`,
wait for CI, then update the tags in the server's `.env` and run `./deploy.sh`.

**To roll back:** edit the server's `.env` to an older tag (old tags stay in
GHCR) and run `docker compose pull && docker compose up -d`.
