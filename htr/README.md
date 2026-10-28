# HTR: single-line manuscript recognition

Standalone command-line pipeline that reads **one cropped handwritten line** from a
Bullinger letter and finds place names in it:

```
line image ──► transcribe_images.py ──► rerank_htr.py ──► extract_places.py ──► JSONL with text + places
              (TrOCR, 8 candidates)    (pick best, de/la)  (GLiNER + historical name lists)
```

It has its own dependencies (torch, transformers, GLiNER), so it does not affect
the backend Docker image or CI. The scripts take **single cropped lines**; the
[HTTP service](#run-as-a-service-whole-pages-from-the-app) also splits whole pages
into lines and is what the app uses for uploads.

Ported from [Bullinger_htr](https://github.com/sssstong55t-sudo/Bullinger_htr).

## Setup (once)

Python 3.10+. All commands run from this `htr/` folder.

**Windows (PowerShell)**

```powershell
cd htr
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python scripts\download_model.py            # GLiNER + tokenizer, ~1 GB
.venv\Scripts\python scripts\download_htr_checkpoint.py   # TrOCR checkpoint, ~1.3 GB, needs ~4 GB free
```

**macOS / Linux**

```sh
cd htr
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/download_model.py
.venv/bin/python scripts/download_htr_checkpoint.py
```

Models land in `models/` and `.cache/` (both gitignored). When
`models/bullinger_checkpoint/` exists, the model is ready. The leftover
`models/checkpoint_download/` folder can be deleted.

## Run on a line image

Wait for each command to finish (it prints `1/1: ...`) before starting the next one.
Every `--output` must be a new file name.

```powershell
$py = ".venv\Scripts\python"
& $py scripts\transcribe_images.py --model-dir models\bullinger_checkpoint --images examples\611_01_r1l31.png --save-candidates --language la --output outputs\demo_candidates.jsonl --device cpu
& $py scripts\rerank_htr.py --input outputs\demo_candidates.jsonl --output outputs\demo_reranked.jsonl
& $py scripts\extract_places.py --input outputs\demo_reranked.jsonl --output outputs\demo_places.jsonl
```

Expected result for the example: text `Basileę ultimo iulii 1554.` (correct reading
is `1549`), place `Basileę`.

- `--language de` for German lines, `la` for Latin. Several images of the same
  language can be listed after `--images`.
- Mixed or unknown language: drop `--save-candidates --language ...` and skip
  `rerank_htr.py`; pass the transcribe output straight to `extract_places.py`.
- If a step fails it may leave an empty output file; delete it before rerunning.

Optional scoring against a known transcription (`examples/references.jsonl`):

```powershell
& $py scripts\evaluate_htr.py --predictions outputs\demo_reranked.jsonl --references examples\references.jsonl --output outputs\demo_metrics.json
```

## Run as a service (whole pages, from the app)

`service/` wraps the same pipeline in a small HTTP API. It splits each page into
lines (`service/segment.py`, a simple ink-profile split for fairly straight lines),
then reads, reranks and tags places in every line. Models load once at startup.

```powershell
.venv\Scripts\python -m uvicorn service.app:app --port 8000
```

Then set `HTR_SERVICE_URL=http://localhost:8000` in `backend/.env` and restart the
backend. Uploaded pages are sent here in the background; the viewer shows the
text when it is ready. With Docker: `docker compose --profile htr up -d` and
`HTR_SERVICE_URL=http://htr:8000` (models are mounted from `models/` and `.cache/`).

Environment: `HTR_MODEL_DIR` (default `models/bullinger_checkpoint`),
`HTR_DEVICE` (`auto`, `cpu`, `cuda`, `mps`), `HTR_BATCH_SIZE` (lines per batch, 4).

`POST /transcribe` (multipart `image`, `language` = `de` | `la` | `unknown`) returns:

```json
{"language": "la", "reranked": true,
 "lines": [{"bbox": [12, 67, 1230, 176], "text": "Basileę ultimo iulii 1554.", "raw_text": "...",
            "places": [{"start": 0, "end": 7, "text": "Basileę", "sources": ["official_source_variant"],
                        "identities": [{"official_place_id": "...", "canonical_name": "Basel",
                                        "latitude": 47.56, "longitude": 7.59}]}]}],
 "verification_status": "Unverified HTR output", "geographic_identity_status": "Not resolved or verified"}
```

`bbox` is left, top, right, bottom in page pixels.

## Output

One JSON object per line image, e.g.:

```json
{"line_id": "examples/611_01_r1l31.png", "text": "Basileę ultimo iulii 1554.",
 "places": [{"start": 0, "end": 7, "text": "Basileę", "sources": ["official_source_variant"]}],
 "candidates": [...], "geographic_identity_status": "Not resolved or verified"}
```

`start`/`end` are character offsets into `text`. Places are candidates, not
verified locations; GLiNER `score` is not a calibrated probability.

## Contents

| Path | Purpose |
|---|---|
| `scripts/transcribe_images.py` | TrOCR line recognition |
| `scripts/rerank_htr.py` | Pick best of 8 candidates with char/word language statistics |
| `scripts/extract_places.py` | Place spans via GLiNER + historical variant lexicons |
| `scripts/evaluate_htr.py` | CER/WER against reference transcriptions |
| `scripts/download_*.py` | Fetch and verify models |
| `service/` | HTTP service for whole pages: line splitting + the pipeline above |
| `docker/Dockerfile` | Image for the service (models are mounted, not baked in) |
| `scripts/historical_aliases.py`, `nlp_baseline.py` | Lexicon matcher used by `extract_places.py` |
| `configs/` | Decoding and place-extraction settings |
| `data/reranker_char3_word1.json` | Language statistics built from training text only |
| `data/lexicons/` | Historical place-name variants from the official edition |
| `examples/` | Sample line images and a reference transcription |
| `tests/` | Unit tests: `python -m unittest discover -s tests -v` |

## Sources and licenses

- Line images / HTR dataset: [pstroe/bullinger-htr](https://github.com/pstroe/bullinger-htr) —
  see `docs/DATASET_README.md` and `docs/DATASET_LICENSE`.
- Place lexicons derived from [stazh/bullinger-korpus-tei](https://github.com/stazh/bullinger-korpus-tei)
  (Scheurer, Müller, Schroffenegger, Ströbel and Volk 2025, *Bullinger Digital Briefkorpus*,
  University of Zurich; CC BY-NC-ND 3.0 CH).
- Models: TrOCR checkpoint from the Bullinger_htr release `v1.0.0-seed44-de20`;
  `urchade/gliner_multi-v2.1` (pinned revision), pretrained.

Dataset and model terms apply separately from this repository's code.
