# Feature: Collections and upload pipeline

A user creates a **collection** (for example "Letters of Henri Dupont") and uploads manuscripts into it.
Every file is checked, stored, and turned into **page images** that the later steps (text recognition, places, map) read.

## What it does
1. Accepts many files in one request: PDF, JPG/JPEG, PNG, HEIC, or a ZIP of those.
2. Decides the file type by looking **inside** the file, not at its name (a text file renamed `.jpg` is rejected).
3. Opens ZIPs safely. Each file inside becomes its own document.
4. Splits a PDF into one PNG per page. A HEIC photo is kept as the original and also saved as a JPEG page image.
5. Uploads the original and the page images to Supabase Storage, and saves one `documents` row and one `pages` row per page.
6. If anything fails, everything from that file is removed.
7. Returns a report: each file is `accepted` or `rejected`, with the reason.

## Where files are stored
Bucket `documents`:
```
collections/<collection_id>/documents/<document_id>/original.pdf
collections/<collection_id>/documents/<document_id>/pages/0001.png
```
User file names are never used in storage paths.

## API
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/collections` | Create a collection `{name, description?}` |
| GET | `/api/collections` | List collections |
| GET | `/api/collections/{id}` | One collection |
| POST | `/api/collections/{id}/uploads` | Bulk upload (multipart field `files`, repeat it) |
| GET | `/api/collections/{id}/documents` | Documents of a collection |
| GET | `/api/documents/{id}` | One document |
| GET | `/api/documents/{id}/pages` | Pages of a document |
| GET | `/api/pages/{id}/image` | The page image |
| GET | `/api/health` | Is the server alive |

Upload answers `201` if at least one file was accepted, and `422` if all were rejected.

## Files
| File | Job |
|---|---|
| `backend/config.py` | Settings and limits |
| `backend/main.py` | Starts the app, registers the routes |
| `backend/schemas.py` | Shape of the API answers |
| `backend/deps.py` | Chooses the database and storage (tests use fakes) |
| `backend/database/repository.py` | The only code that reads/writes the tables |
| `backend/services/storage.py` | The only code that uploads/downloads files in Supabase Storage |
| `backend/services/ingest.py` | Checks files, opens ZIPs, makes page images, cleans up on error |
| `backend/routes/collections.py`, `documents.py` | The endpoints |
| `frontend/src/api/documents.js` | `uploadFiles()` sends all selected files in one request |
| `frontend/src/components/CreateCollectionModal.jsx` | File picker (also accepts `.zip`) |

## Setup
- Database: tables `collections`, `documents`, `pages` (row level security on). `pages` has no `collection_id`, `documents` has no `page_count`, and `heic` is an allowed `file_type`.
- `backend/.env` (we never commit these):
  ```
  SUPABASE_URL=https://our-project-id.supabase.co
  SUPABASE_API_KEY=<service_role key>
  SUPABASE_BUCKET=documents
  RESEND_API_KEY
  ```
  The default in `config.py` is `manuscripts`, so set `SUPABASE_BUCKET=documents` (or change the default).
- Optional limits: `MAX_FILE_MB` (50), `MAX_ZIP_ENTRIES` (1000), `MAX_ZIP_UNCOMPRESSED_MB` (2000), `MAX_PDF_PAGES` (500), `PDF_RENDER_DPI` (200).
- nginx (`frontend/docker/nginx.conf`) has a raised upload size limit. Without it every upload fails with 413.

## Test
```bash
cd backend
pip install -r requirements-dev.txt
pytest -v          # upload and collection tests use a fake database and fake storage
```
Then check by hand: upload a PDF, a photo and a ZIP, and look in Supabase Storage and the `documents` and `pages` tables.
