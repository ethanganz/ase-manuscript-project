"""Data-access layer.

Routes and services only talk to the ``Repository`` interface. 
Production uses
``SupabaseRepository``; 
tests use ``InMemoryRepository`` .
The repository is the only place that touches the database.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4
from database.paging import fetch_all

class Repository:
    """Common interface for data access."""

    def create_user(self, email: str, password_hash: str,
                    first_name: Optional[str], last_name: Optional[str]) -> dict: ...
    def get_user(self, user_id: str) -> Optional[dict]: ...
    def get_user_by_email(self, email: str) -> Optional[dict]: ...
    def mark_email_verified(self, user_id: str) -> Optional[dict]: ...

    def create_collection(self, name: str, description: Optional[str],
                          owner_id: str, is_public: bool = True) -> dict: ...
    def list_collections(self) -> list[dict]: ...
    def get_collection(self, collection_id: str) -> Optional[dict]: ...
    def update_collection(self, collection_id: str, fields: dict) -> Optional[dict]: ...

    def create_document(self, doc: dict) -> dict: ...
    def delete_document(self, document_id: str) -> None: ...
    def get_document(self, document_id: str) -> Optional[dict]: ...
    def list_documents(self, collection_id: str) -> list[dict]: ...

    def create_pages(self, pages: list[dict]) -> None: ...
    def get_page(self, page_id: str) -> Optional[dict]: ...
    def list_pages(self, document_id: str) -> list[dict]: ...
    def list_mention_details(self, collection_id: str) -> list[dict]: ...

    def create_report(self, collection_id: str, reporter_id: str, reason: str,
                      details: Optional[str]) -> dict: ...
    def has_reported(self, collection_id: str, reporter_id: str) -> bool: ...
    def list_reports_for_collections(self, collection_ids: list[str]) -> list[dict]: ...
    def mark_reports_read(self, collection_ids: list[str]) -> None: ...


class InMemoryRepository(Repository):
    """In-memory repository used for tests."""

    def __init__(self) -> None:
        self.users: dict[str, dict] = {}
        self.collections: dict[str, dict] = {}
        self.documents: dict[str, dict] = {}
        self.pages: dict[str, dict] = {}
        self.mention_details: list[dict] = []   # tests put rows here
        self.reports: dict[str, dict] = {}

    @staticmethod
    def _now() -> str:
        """Return the current UTC timestamp."""
        return datetime.now(timezone.utc).isoformat()

    def create_user(self, email, password_hash, first_name, last_name):
        """Create and store a user."""
        row = {"id": str(uuid4()), "email": email, "password_hash": password_hash,
               "first_name": first_name, "last_name": last_name, "created_at": self._now(),
               "email_verified": False, "email_verified_at": None}
        self.users[row["id"]] = row
        return dict(row)

    def get_user(self, user_id):
        """Return a user by ID."""
        row = self.users.get(user_id)
        return dict(row) if row else None

    def get_user_by_email(self, email):
        """Return a user by email."""
        row = next((u for u in self.users.values() if u["email"] == email), None)
        return dict(row) if row else None

    def mark_email_verified(self, user_id):
        """Mark the user's email as verified. Returns the new row, or None if missing."""
        row = self.users.get(user_id)
        if row is None:
            return None
        row.update(email_verified=True, email_verified_at=self._now())
        return dict(row)

    def create_collection(self, name, description, owner_id, is_public=True):
        """Create and store a collection."""
        row = {"id": str(uuid4()), "name": name, "description": description,
               "owner_id": owner_id, "is_public": is_public, "created_at": self._now()}
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

    def update_collection(self, collection_id, fields):
        """Change some fields of a collection. Returns the new row, or None if missing."""
        row = self.collections.get(collection_id)
        if row is None:
            return None
        row.update(fields)
        return dict(row)

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
    
    def list_mention_details(self, collection_id):
        return [dict(r) for r in self.mention_details if r["collection_id"] == collection_id]

    def create_report(self, collection_id, reporter_id, reason, details):
        """Create and store a report."""
        row = {"id": str(uuid4()), "collection_id": collection_id, "reporter_id": reporter_id,
               "reason": reason, "details": details, "read_at": None,
               "created_at": self._now()}
        self.reports[row["id"]] = row
        return dict(row)

    def has_reported(self, collection_id, reporter_id):
        """Return True if this user already reported this collection."""
        return any(r["collection_id"] == collection_id and r["reporter_id"] == reporter_id
                   for r in self.reports.values())

    def list_reports_for_collections(self, collection_ids):
        """Return the reports on these collections, newest first."""
        rows = [dict(r) for r in self.reports.values() if r["collection_id"] in collection_ids]
        return sorted(rows, key=lambda r: r["created_at"], reverse=True)

    def mark_reports_read(self, collection_ids):
        """Mark every unread report on these collections as read."""
        for r in self.reports.values():
            if r["collection_id"] in collection_ids and r["read_at"] is None:
                r["read_at"] = self._now()


class SupabaseRepository(Repository):
    """Supabase-backed repository used in production."""

    def __init__(self) -> None:
        # Import lazily so tests do not need Supabase credentials.
        from database.database import get_supabase

        self._sb = get_supabase

    def _t(self, name: str):
        """Return a Supabase table client."""
        return self._sb().table(name)

    def create_user(self, email, password_hash, first_name, last_name):
        """Create a user in Supabase."""
        res = self._t("users").insert(
            {"email": email, "password_hash": password_hash,
             "first_name": first_name, "last_name": last_name}).execute()
        return res.data[0]

    def get_user(self, user_id):
        """Return a user by ID."""
        res = self._t("users").select("*").eq("id", user_id).limit(1).execute()
        return res.data[0] if res.data else None

    def get_user_by_email(self, email):
        """Return a user by email."""
        res = self._t("users").select("*").eq("email", email).limit(1).execute()
        return res.data[0] if res.data else None

    def mark_email_verified(self, user_id):
        """Mark the user's email as verified. Returns the new row, or None if missing."""
        res = self._t("users").update(
            {"email_verified": True,
             "email_verified_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", user_id).execute()
        return res.data[0] if res.data else None

    def create_collection(self, name, description, owner_id, is_public=True):
        """Create a collection in Supabase."""
        res = self._t("collections").insert(
            {"name": name, "description": description, "owner_id": owner_id,
             "is_public": is_public}).execute()
        return res.data[0]

    def list_collections(self):
        """Return all collections, newest first."""
        res = self._t("collections").select("*").order("created_at", desc=True).execute()
        return res.data or []

    def get_collection(self, collection_id):
        """Return a collection by ID."""
        res = self._t("collections").select("*").eq("id", collection_id).limit(1).execute()
        return res.data[0] if res.data else None

    def update_collection(self, collection_id, fields):
        """Change some fields of a collection. Returns the new row, or None if missing."""
        res = self._t("collections").update(fields).eq("id", collection_id).execute()
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
    
    def list_mention_details(self, collection_id):
        # order() gives a stable order, which paging needs to avoid skipping rows.
        return fetch_all(lambda: (self._t("mention_details").select("*")
            .eq("collection_id", collection_id)
            .order("mention_id")))

    def create_report(self, collection_id, reporter_id, reason, details):
        """Create a report in Supabase."""
        res = self._t("reports").insert(
            {"collection_id": collection_id, "reporter_id": reporter_id,
             "reason": reason, "details": details}).execute()
        return res.data[0]

    def has_reported(self, collection_id, reporter_id):
        """Return True if this user already reported this collection."""
        res = (self._t("reports").select("id").eq("collection_id", collection_id)
               .eq("reporter_id", reporter_id).limit(1).execute())
        return bool(res.data)

    def list_reports_for_collections(self, collection_ids):
        """Return the reports on these collections, newest first."""
        if not collection_ids:
            return []
        return fetch_all(lambda: (self._t("reports").select("*")
            .in_("collection_id", collection_ids)
            .order("created_at", desc=True).order("id")))

    def mark_reports_read(self, collection_ids):
        """Mark every unread report on these collections as read."""
        if collection_ids:
            (self._t("reports").update({"read_at": datetime.now(timezone.utc).isoformat()})
             .in_("collection_id", collection_ids).is_("read_at", "null").execute())
