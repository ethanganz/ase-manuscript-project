"""Object storage for originals and page images.
one small place that talks to Supabase Storage. 
so tests can use a fake in-memory version

Production: Supabase Storage (private bucket). Tests: in-memory.
Keys look like  <collection_id>/<document_id>/original.pdf
                <collection_id>/<document_id>/pages/0001.png
"""
from pathlib import Path
from typing import Optional

import config


class ObjectStorage:
    def upload(self, key: str, path: Path, content_type: str) -> None: ...
    def download(self, key: str) -> Optional[bytes]: ...
    def remove(self, keys: list[str]) -> None: ...


class SupabaseStorage(ObjectStorage):
    def __init__(self) -> None:
        # Imported lazily so tests never need Supabase credentials.
        from database.database import get_supabase

        self._sb = get_supabase

    def _bucket(self):
        return self._sb().storage.from_(config.SUPABASE_BUCKET)

    def upload(self, key, path, content_type):
        with open(path, "rb") as f:  # streamed, not loaded into memory
            self._bucket().upload(
                path=key, file=f,
                file_options={"content-type": content_type, "upsert": "false"})

    def download(self, key):
        try:
            return self._bucket().download(key)
        except Exception:
            return None

    def remove(self, keys):
        if keys:
            self._bucket().remove(keys)


class InMemoryStorage(ObjectStorage):
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    def upload(self, key, path, content_type):
        self.objects[key] = (Path(path).read_bytes(), content_type)

    def download(self, key):
        item = self.objects.get(key)
        return item[0] if item else None

    def remove(self, keys):
        for k in keys:
            self.objects.pop(k, None)