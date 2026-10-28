from functools import lru_cache

import httpx as _httpx
from supabase import Client, create_client

import config

# Force HTTP/1.1 on every httpx.Client created by supabase-py/storage3.
# HTTP/2 connections get dropped inside Docker containers, causing
# RemoteProtocolError ("Server disconnected") on Supabase requests.
_orig_client_init = _httpx.Client.__init__


def _no_http2_client_init(self, *args, **kwargs):
    kwargs["http2"] = False
    _orig_client_init(self, *args, **kwargs)


_httpx.Client.__init__ = _no_http2_client_init


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Return a singleton Supabase client.

    Uses SUPABASE_URL / SUPABASE_API_KEY from config. Supply your project's
    ``service_role`` key here so server-side writes bypass Row Level Security.
    """
    if not config.SUPABASE_URL or not config.SUPABASE_API_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_API_KEY must be set in backend/.env")
    return create_client(config.SUPABASE_URL, config.SUPABASE_API_KEY)
