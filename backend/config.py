import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from the .env file next to this module.
load_dotenv(BASE_DIR / ".env")


# --- Upload pipeline -------------------------------------------------------
# Permanent files are stored in Supabase Storage.

# --- Supabase (server-side only - never expose the API key to the client) ---
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY", "")


MB = 1024 * 1024

# Maximum size of one uploaded file: 40 MB
MAX_FILE_BYTES = int(os.getenv("MAX_FILE_MB", "40")) * MB

# Maximum number of files inside a ZIP: 500
MAX_ZIP_ENTRIES = int(os.getenv("MAX_ZIP_ENTRIES", "500"))

# Maximum total uncompressed ZIP size: 1 GB
MAX_ZIP_UNCOMPRESSED_BYTES = int(
    os.getenv("MAX_ZIP_UNCOMPRESSED_MB", "1000")
) * MB

# Maximum PDF pages: 500
MAX_PDF_PAGES = int(os.getenv("MAX_PDF_PAGES", "500"))

# PDF pages are rendered at 200 DPI
PDF_RENDER_DPI = int(os.getenv("PDF_RENDER_DPI", "200"))