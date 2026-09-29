import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from the .env file next to this module.
load_dotenv(Path(__file__).resolve().parent / ".env")

# Supabase connection settings (server-side only - never expose the API key to the client).
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY", "")