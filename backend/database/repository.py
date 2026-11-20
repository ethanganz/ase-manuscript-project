"""Data-access layer.

Routes and services only talk to the ``Repository`` interface.
Production uses
``SupabaseRepository``;
tests use ``InMemoryRepository`` .
The repository is the only place that touches the database.
"""

import unicodedata
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid4, uuid5

from database.paging import fetch_all


class Repository:
    """Common interface for data access."""

    def create_user(
        self, email: str, password_hash: str, first_name: str | None, last_name: str | None
    ) -> dict: ...
    def get_user(self, user_id: str) -> dict | None: ...
    def get_user_by_email(self, email: str) -> dict | None: ...
    def mark_email_verified(self, user_id: str) -> dict | None: ...

    def create_collection(
        self, name: str, description: str | None, owner_id: str, is_public: bool = True
    ) -> dict: ...
    def list_collections(self) -> list[dict]: ...
    def get_collection(self, collection_id: str) -> dict | None: ...
    def update_collection(self, collection_id: str, fields: dict) -> dict | None: ...

    def create_document(self, doc: dict) -> dict: ...
    def delete_document(self, document_id: str) -> None: ...
    def get_document(self, document_id: str) -> dict | None: ...
    def list_documents(self, collection_id: str) -> list[dict]: ...

    def create_pages(self, pages: list[dict]) -> None: ...
    def get_page(self, page_id: str) -> dict | None: ...
    def list_pages(self, document_id: str) -> list[dict]: ...
    def upsert_text_lines(self, rows: list[dict]) -> None: ...
    def search_text_lines(self, words: list[str], collection_id: str, limit: int) -> list[dict]: ...
    def list_text_lines(self, collection_id: str, limit: int) -> list[dict]: ...
    def list_mention_details(self, collection_id: str) -> list[dict]: ...

    def set_page_status(self, page_id: str, status: str, error: str | None = None) -> None: ...
    def save_page_lines(
        self, page_id: str, lines: list[dict], width: int | None, height: int | None
    ) -> None: ...
    def list_page_lines(self, page_id: str) -> list[dict]: ...
    def list_stuck_pages(self) -> list[dict]: ...
    def replace_page_mentions(self, page_id: str, mentions: list[dict]) -> None: ...

    def create_report(
        self, collection_id: str, reporter_id: str, reason: str, details: str | None
    ) -> dict: ...
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
        self.mention_details: list[dict] = []  # tests put rows here
        self.page_lines: dict[str, list[dict]] = {}  # page_id -> lines
        self.reports: dict[str, dict] = {}
        self.text_lines: dict[str, dict] = {}  # keyed by source_line_id

    @staticmethod
    def _now() -> str:
        """Return the current UTC timestamp."""
        return datetime.now(timezone.utc).isoformat()

    def create_user(self, email, password_hash, first_name, last_name):
        """Create and store a user."""
        row = {
            "id": str(uuid4()),
            "email": email,
            "password_hash": password_hash,
            "first_name": first_name,
            "last_name": last_name,
            "created_at": self._now(),
            "email_verified": False,
            "email_verified_at": None,
        }
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
        row = {
            "id": str(uuid4()),
            "name": name,
            "description": description,
            "owner_id": owner_id,
            "is_public": is_public,
            "created_at": self._now(),
        }
        self.collections[row["id"]] = row
        return dict(row)

    def list_collections(self):
        """Return all collections, newest first."""
        return sorted(
            (dict(c) for c in self.collections.values()),
            key=lambda c: c["created_at"],
            reverse=True,
        )

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
        rows = [dict(d) for d in self.documents.values() if d["collection_id"] == collection_id]
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

    def set_page_status(self, page_id, status, error=None):
        """Change how far the recognition of a page is."""
        row = self.pages.get(page_id)
        if row is not None:
            row.update(status=status, htr_error=error)

    def save_page_lines(self, page_id, lines, width, height):
        """Replace the stored lines of a page and mark it complete."""
        self.page_lines[page_id] = [dict(line) for line in lines]
        row = self.pages.get(page_id)
        if row is not None:
            row.update(
                status="complete",
                htr_error=None,
                htr_width=width,
                htr_height=height,
                htr_finished_at=self._now(),
            )

    def list_page_lines(self, page_id):
        """Return the lines of a page, top to bottom."""
        rows = [dict(line) for line in self.page_lines.get(page_id, [])]
        return sorted(rows, key=lambda r: r["line_index"])

    def list_stuck_pages(self):
        """Pages that were queued or running (the server stopped meanwhile)."""
        return [dict(p) for p in self.pages.values() if p.get("status") in ("queued", "running")]

    def replace_page_mentions(self, page_id, mentions):
        """Replace the places the map shows for one page."""
        self.mention_details = [r for r in self.mention_details if r["page_id"] != page_id]
        page = self.pages[page_id]
        doc = self.documents[page["document_id"]]
        for m in mentions:
            self.mention_details.append(
                {
                    "mention_id": str(uuid4()),
                    "snippet": m["snippet"],
                    "place_name": m["name"],
                    "country_code": m["country_code"],
                    "lat": m["lat"],
                    "lng": m["lng"],
                    "page_id": page_id,
                    "page_number": page["page_number"],
                    "document_id": doc["id"],
                    "document_name": doc["original_filename"],
                    "collection_id": doc["collection_id"],
                }
            )

    def create_report(self, collection_id, reporter_id, reason, details):
        """Create and store a report."""
        row = {
            "id": str(uuid4()),
            "collection_id": collection_id,
            "reporter_id": reporter_id,
            "reason": reason,
            "details": details,
            "read_at": None,
            "created_at": self._now(),
        }
        self.reports[row["id"]] = row
        return dict(row)

    def has_reported(self, collection_id, reporter_id):
        """Return True if this user already reported this collection."""
        return any(
            r["collection_id"] == collection_id and r["reporter_id"] == reporter_id
            for r in self.reports.values()
        )

    def list_reports_for_collections(self, collection_ids):
        """Return the reports on these collections, newest first."""
        rows = [dict(r) for r in self.reports.values() if r["collection_id"] in collection_ids]
        return sorted(rows, key=lambda r: r["created_at"], reverse=True)

    def mark_reports_read(self, collection_ids):
        """Mark every unread report on these collections as read."""
        for r in self.reports.values():
            if r["collection_id"] in collection_ids and r["read_at"] is None:
                r["read_at"] = self._now()

    def upsert_text_lines(self, rows):
        for row in rows:
            existing = self.text_lines.get(row["source_line_id"])
            if existing:
                existing.update(row)  # columns not in ``row`` (such as page_id) stay as they are
            else:
                self.text_lines[row["source_line_id"]] = {
                    "id": str(uuid4()),
                    "page_id": None,
                    "created_at": self._now(),
                    **row,
                }

    def search_text_lines(self, words, collection_id, limit):
        # Simplified stand-in for the SQL function: a word matches when it appears in the
        # line, ignoring case and accents. It does not tolerate misspellings.
        document_ids = {
            d["id"] for d in self.documents.values() if d["collection_id"] == collection_id
        }
        page_ids = {p["id"] for p in self.pages.values() if p["document_id"] in document_ids}
        folded_words = {_fold(w) for w in words if w.strip()}
        hits = []
        for line in self.text_lines.values():
            if line.get("page_id") not in page_ids:
                continue
            folded = _fold(line["text"])
            score = float(sum(1 for w in folded_words if w in folded))
            if score:
                hits.append({**line, "score": score})
        hits.sort(key=lambda h: (-h["score"], h["source_line_id"]))
        return hits[: max(1, min(limit, 100))]

    def list_text_lines(self, collection_id, limit):
        """Transcript lines of a collection in reading order, without any word matching.

        Uses the imported ``text_lines`` linked to a page and the lines the handwriting
        recognition saved for uploaded pages (``page_lines``).
        """
        document_ids = {
            d["id"] for d in self.documents.values() if d["collection_id"] == collection_id
        }
        page_ids = {p["id"] for p in self.pages.values() if p["document_id"] in document_ids}
        rows = [dict(l) for l in self.text_lines.values() if l.get("page_id") in page_ids]
        rows.sort(key=lambda r: r["source_line_id"])
        for page_id in sorted(page_ids):
            for line in self.list_page_lines(page_id):
                if (line.get("text") or "").strip():
                    rows.append(_page_line_as_text_line(page_id, line))
        return rows[: max(1, limit)]


def _page_line_as_text_line(page_id: str, line: dict) -> dict:
    """A recognised page line in the same shape as a ``text_lines`` row."""
    return {
        "id": line.get("id") or str(uuid5(NAMESPACE_URL, f"{page_id}/{line['line_index']}")),
        "page_id": page_id,
        "source_line_id": f"{page_id}-{line['line_index']:05d}",
        "language": None,
        "text": line["text"],
    }


def _fold(text: str) -> str:
    """Lower case without accents: "Zürich" becomes "zurich"."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


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
        res = (
            self._t("users")
            .insert(
                {
                    "email": email,
                    "password_hash": password_hash,
                    "first_name": first_name,
                    "last_name": last_name,
                }
            )
            .execute()
        )
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
        res = (
            self._t("users")
            .update(
                {
                    "email_verified": True,
                    "email_verified_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", user_id)
            .execute()
        )
        return res.data[0] if res.data else None

    def create_collection(self, name, description, owner_id, is_public=True):
        """Create a collection in Supabase."""
        res = (
            self._t("collections")
            .insert(
                {
                    "name": name,
                    "description": description,
                    "owner_id": owner_id,
                    "is_public": is_public,
                }
            )
            .execute()
        )
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
        res = (
            self._t("documents")
            .select("*")
            .eq("collection_id", collection_id)
            .order("created_at")
            .execute()
        )
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
        res = (
            self._t("pages")
            .select("*")
            .eq("document_id", document_id)
            .order("page_number")
            .execute()
        )
        return res.data or []

    def list_mention_details(self, collection_id):
        # order() gives a stable order, which paging needs to avoid skipping rows.
        return fetch_all(
            lambda: (
                self._t("mention_details")
                .select("*")
                .eq("collection_id", collection_id)
                .order("mention_id")
            )
        )

    def set_page_status(self, page_id, status, error=None):
        """Change how far the recognition of a page is."""
        self._t("pages").update({"status": status, "htr_error": error}).eq("id", page_id).execute()

    def save_page_lines(self, page_id, lines, width, height):
        """Replace the stored lines of a page and mark it complete."""
        self._t("page_lines").delete().eq("page_id", page_id).execute()
        rows = [{**line, "page_id": page_id} for line in lines]
        for start in range(0, len(rows), 200):  # keep each request small
            self._t("page_lines").insert(rows[start : start + 200]).execute()
        (
            self._t("pages")
            .update(
                {
                    "status": "complete",
                    "htr_error": None,
                    "htr_width": width,
                    "htr_height": height,
                    "htr_finished_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", page_id)
            .execute()
        )

    def list_page_lines(self, page_id):
        """Return the lines of a page, top to bottom."""
        res = self._t("page_lines").select("*").eq("page_id", page_id).order("line_index").execute()
        return res.data or []

    def list_stuck_pages(self):
        """Pages that were queued or running (the server stopped meanwhile)."""
        res = self._t("pages").select("*").in_("status", ["queued", "running"]).execute()
        return res.data or []

    def replace_page_mentions(self, page_id, mentions):
        """Replace the places the map shows for one page."""
        self._t("place_mentions").delete().eq("page_id", page_id).execute()
        if not mentions:
            return
        # One places row per official place, however many times it is mentioned.
        places = {
            m["official_place_id"]: {
                "official_place_id": m["official_place_id"],
                "name": m["name"],
                "country_code": m["country_code"],
                "lat": m["lat"],
                "lng": m["lng"],
            }
            for m in mentions
        }
        saved = (
            self._t("places")
            .upsert(list(places.values()), on_conflict="official_place_id")
            .execute()
        )
        ids = {row["official_place_id"]: row["id"] for row in saved.data}
        rows = [
            {"place_id": ids[m["official_place_id"]], "page_id": page_id, "snippet": m["snippet"]}
            for m in mentions
        ]
        for start in range(0, len(rows), 200):
            self._t("place_mentions").insert(rows[start : start + 200]).execute()

    def create_report(self, collection_id, reporter_id, reason, details):
        """Create a report in Supabase."""
        res = (
            self._t("reports")
            .insert(
                {
                    "collection_id": collection_id,
                    "reporter_id": reporter_id,
                    "reason": reason,
                    "details": details,
                }
            )
            .execute()
        )
        return res.data[0]

    def has_reported(self, collection_id, reporter_id):
        """Return True if this user already reported this collection."""
        res = (
            self._t("reports")
            .select("id")
            .eq("collection_id", collection_id)
            .eq("reporter_id", reporter_id)
            .limit(1)
            .execute()
        )
        return bool(res.data)

    def list_reports_for_collections(self, collection_ids):
        """Return the reports on these collections, newest first."""
        if not collection_ids:
            return []
        return fetch_all(
            lambda: (
                self._t("reports")
                .select("*")
                .in_("collection_id", collection_ids)
                .order("created_at", desc=True)
                .order("id")
            )
        )

    def mark_reports_read(self, collection_ids):
        """Mark every unread report on these collections as read."""
        if collection_ids:
            (
                self._t("reports")
                .update({"read_at": datetime.now(timezone.utc).isoformat()})
                .in_("collection_id", collection_ids)
                .is_("read_at", "null")
                .execute()
            )

    def upsert_text_lines(self, rows):
        # In chunks of 500, so one request never gets too large. Columns missing
        # from a row are left unchanged when the line already exists.
        for start in range(0, len(rows), 500):
            self._t("text_lines").upsert(
                rows[start : start + 500], on_conflict="source_line_id"
            ).execute()

    def list_text_lines(self, collection_id, limit):
        """Transcript lines of a collection in reading order, without any word matching.

        Uses the imported ``text_lines`` linked to a page and the lines the handwriting
        recognition saved for uploaded pages (``page_lines``).
        """
        page_ids = [
            page["id"]
            for document in self.list_documents(collection_id)
            for page in self.list_pages(document["id"])
        ]
        if not page_ids:
            return []
        rows: list[dict] = []
        for start in range(0, len(page_ids), 100):  # chunks keep the request URL short
            chunk = page_ids[start : start + 100]
            res = (
                self._t("text_lines")
                .select("id,page_id,source_line_id,language,text")
                .in_("page_id", chunk)
                .order("source_line_id")
                .limit(limit)
                .execute()
            )
            rows.extend(res.data or [])
            res = (
                self._t("page_lines")
                .select("id,page_id,line_index,text")
                .in_("page_id", chunk)
                .order("page_id")
                .order("line_index")
                .limit(limit)
                .execute()
            )
            rows.extend(
                _page_line_as_text_line(line["page_id"], line)
                for line in (res.data or [])
                if (line.get("text") or "").strip()
            )
            if len(rows) >= limit:
                break
        return rows[:limit]

    def search_text_lines(self, words, collection_id, limit):
        # Calls the SQL function search_text_lines (see the migration file).
        res = (
            self._sb()
            .rpc(
                "search_text_lines",
                {
                    "query_words": words,
                    "collection": collection_id,
                    "max_results": limit,
                },
            )
            .execute()
        )
        return res.data or []