# ase-manuscript-project
A web-based application for recognizing, analysing and understanding historical manuscripts.

## Database setup

Apply the SQL files in `backend/database/migrations` in number order in the Supabase SQL editor. Migration `003_page_transcriptions.sql` adds optional text to each manuscript page; the reader displays that text beside the page image when it is available.

Uploaded originals and page images use a private Supabase Storage bucket named `documents` (or the name set by `SUPABASE_BUCKET`). The backend needs a server-side secret/service-role key in `SUPABASE_API_KEY` to read that bucket. A publishable key can list the database records but cannot supply private file previews.

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
