from functools import lru_cache

from supabase import Client, create_client

import config


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Return a singleton Supabase client.

    Uses SUPABASE_URL / SUPABASE_API_KEY from config. Supply your project's
    ``service_role`` key here so server-side writes bypass Row Level Security.
    """
    if not config.SUPABASE_URL or not config.SUPABASE_API_KEY:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_API_KEY must be set in backend/.env"
        )
    return create_client(config.SUPABASE_URL, config.SUPABASE_API_KEY)