"""Data-access layer.

Routes and services only talk to the ``Repository`` interface. 
Production uses
``SupabaseRepository``; 
tests use ``InMemoryRepository`` .
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4


class Repository:
    """Common interface for data access."""

    def create_collection(self, name: str, description: Optional[str]) -> dict: ...
    def list_collections(self) -> list[dict]: ...
    def get_collection(self, collection_id: str) -> Optional[dict]: ...

    def create_document(self, doc: dict) -> dict: ...
    def delete_document(self, document_id: str) -> None: ...
    def get_document(self, document_id: str) -> Optional[dict]: ...
    def list_documents(self, collection_id: str) -> list[dict]: ...

    def create_pages(self, pages: list[dict]) -> None: ...
    def get_page(self, page_id: str) -> Optional[dict]: ...
    def list_pages(self, document_id: str) -> list[dict]: ...


class InMemoryRepository(Repository):
    """In-memory repository used for tests."""

    def __init__(self) -> None:
        self.collections: dict[str, dict] = {}
        self.documents: dict[str, dict] = {}
        self.pages: dict[str, dict] = {}

    @staticmethod
    def _now() -> str:
        """Return the current UTC timestamp."""
        return datetime.now(timezone.utc).isoformat()

    def create_collection(self, name, description):
        """Create and store a collection."""
        row = {"id": str(uuid4()), "name": name, "description": description,
               "created_at": self._now()}
        self.collections[row["id"]] = row
        return dict(row)

    def list_collections(self):
        """Return all collections, newest first."""
        return sorted((dict(c) for c in self.collections.values()),
                      key=lambda c: c["created_at"], reverse=True)

    def get_collection(self, collection_id):
        """Return a collection by ID."""
        row = self.collections.get(collection_id)
        return dict(row) if row else None

    def create_document(self, doc):
        """Create and store a document."""
        row = {**doc, "created_at": self._now()}
        self.documents[row["id"]] = row
        return dict(row)

    def delete_document(self, document_id):
        """Delete a document and its pages."""
        self.documents.pop(document_id, None)
        # Mimic ON DELETE CASCADE.
        for pid in [p for p, r in self.pages.items() if r["document_id"] == document_id]:
            del self.pages[pid]

    def get_document(self, document_id):
        """Return a document by ID."""
        row = self.documents.get(document_id)
        return dict(row) if row else None

    def list_documents(self, collection_id):
        """Return documents belonging to a collection."""
        rows = [dict(d) for d in self.documents.values()
                if d["collection_id"] == collection_id]
        return sorted(rows, key=lambda d: d["created_at"])

    def create_pages(self, pages):
        """Create and store document pages."""
        for p in pages:
            self.pages[p["id"]] = dict(p)

    def get_page(self, page_id):
        """Return a page by ID."""
        row = self.pages.get(page_id)
        return dict(row) if row else None

    def list_pages(self, document_id):
        """Return pages belonging to a document."""
        rows = [dict(p) for p in self.pages.values() if p["document_id"] == document_id]
        return sorted(rows, key=lambda p: p["page_number"])


class SupabaseRepository(Repository):
    """Supabase-backed repository used in production."""

    def __init__(self) -> None:
        # Import lazily so tests do not need Supabase credentials.
        from database.database import get_supabase

        self._sb = get_supabase

    def _t(self, name: str):
        """Return a Supabase table client."""
        return self._sb().table(name)

    def create_collection(self, name, description):
        """Create a collection in Supabase."""
        res = self._t("collections").insert(
            {"name": name, "description": description}).execute()
        return res.data[0]

    def list_collections(self):
        """Return all collections, newest first."""
        res = self._t("collections").select("*").order("created_at", desc=True).execute()
        return res.data or []

    def get_collection(self, collection_id):
        """Return a collection by ID."""
        res = self._t("collections").select("*").eq("id", collection_id).limit(1).execute()
        return res.data[0] if res.data else None

    def create_document(self, doc):
        """Create a document in Supabase."""
        return self._t("documents").insert(doc).execute().data[0]

    def delete_document(self, document_id):
        """Delete a document from Supabase."""
        self._t("documents").delete().eq("id", document_id).execute()

    def get_document(self, document_id):
        """Return a document by ID."""
        res = self._t("documents").select("*").eq("id", document_id).limit(1).execute()
        return res.data[0] if res.data else None

    def list_documents(self, collection_id):
        """Return documents belonging to a collection."""
        res = (self._t("documents").select("*").eq("collection_id", collection_id)
               .order("created_at").execute())
        return res.data or []

    def create_pages(self, pages):
        """Create document pages in Supabase."""
        if pages:
            self._t("pages").insert(pages).execute()

    def get_page(self, page_id):
        """Return a page by ID."""
        res = self._t("pages").select("*").eq("id", page_id).limit(1).execute()
        return res.data[0] if res.data else None

    def list_pages(self, document_id):
        """Return pages belonging to a document."""
        res = (self._t("pages").select("*").eq("document_id", document_id)
               .order("page_number").execute())
        return res.data or []

