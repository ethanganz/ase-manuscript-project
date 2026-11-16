import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from the .env file next to this module.
load_dotenv(BASE_DIR / ".env")


# --- Supabase (server-side only - never expose the API key to the client) ---
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY", "")

JWT_SECRET = os.getenv("JWT_SECRET") or secrets.token_urlsafe(48)

JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", str(7 * 24 * 60)))

AUTH_COOKIE_NAME = "access_token"
AUTH_COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true"

# --- Email verification (sent with Resend) ----------------------------------
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")

# Resend only delivers from a domain verified in your Resend account. The
# default test sender (onboarding@resend.dev) can only send to the email of
# the Resend account owner.
EMAIL_FROM = os.getenv("EMAIL_FROM", "Manuscript Archive <onboarding@resend.dev>")

# Where the app is opened in the browser; the link in the email points here.
# Include any sub-path, e.g. https://example.com/apps/staging
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:5173").rstrip("/")

# How long the link in the email works: 24 hours
EMAIL_VERIFY_EXPIRE_HOURS = int(os.getenv("EMAIL_VERIFY_EXPIRE_HOURS", "24"))

# --- Upload pipeline -------------------------------------------------------
# Permanent files are stored in Supabase Storage.
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "documents")

MB = 1024 * 1024

# Maximum size of one uploaded file: 40 MB
MAX_FILE_BYTES = int(os.getenv("MAX_FILE_MB", "40")) * MB

# Maximum number of files inside a ZIP: 500
MAX_ZIP_ENTRIES = int(os.getenv("MAX_ZIP_ENTRIES", "500"))

# Maximum total uncompressed ZIP size: 1 GB
MAX_ZIP_UNCOMPRESSED_BYTES = int(os.getenv("MAX_ZIP_UNCOMPRESSED_MB", "1000")) * MB

# Maximum PDF pages: 500
MAX_PDF_PAGES = int(os.getenv("MAX_PDF_PAGES", "500"))

# PDF pages are rendered at 200 DPI
PDF_RENDER_DPI = int(os.getenv("PDF_RENDER_DPI", "200"))

# --- Handwriting recognition (HTR-NLP pipeline) ------------------------------
# The pipeline needs PyTorch and about 3 GB of model files, so it is NOT part of
# this backend's own dependencies. It runs as a separate Python program
# (HTR-NLP/scripts/run_page_pipeline.py) that this backend starts for each page.
# Off by default: uploads then just wait with status "pending".
HTR_ENABLED = os.getenv("HTR_ENABLED", "false").lower() == "true"

# Folder that holds scripts/run_page_pipeline.py and models/.
HTR_PIPELINE_DIR = Path(os.getenv("HTR_PIPELINE_DIR") or BASE_DIR.parent / "HTR-NLP")

# Python that has the HTR-NLP requirements installed (see HTR-NLP/README.md).
# Empty = use .venv-nlp inside HTR_PIPELINE_DIR if it exists, else this Python.
HTR_PYTHON = os.getenv("HTR_PYTHON", "")

# "auto" picks CUDA when there is a GPU, otherwise CPU. Or: cpu, cuda, mps.
HTR_DEVICE = os.getenv("HTR_DEVICE", "auto")

# One page may take several minutes on a CPU. After this it is marked failed.
HTR_TIMEOUT_SECONDS = int(os.getenv("HTR_TIMEOUT_SECONDS", "1800"))
