PAGE_SIZE = 1000  # Supabase returns at most 1000 rows per request

# Supabase returns at most 1000 rows per request and does not warn us. 
# Without this, a big collection would silently lose mentions

def fetch_all(build_query, page_size: int = PAGE_SIZE) -> list[dict]:
    """Runs a query again and again with .range() until every row is fetched.
    build_query: function returning a fresh query, e.g. lambda: table.select("*").eq(...)"""
    rows: list[dict] = []
    start = 0
    while True:
        batch = build_query().range(start, start + page_size - 1).execute().data or []
        rows.extend(batch)
        if len(batch) < page_size:   # last (partial or empty) page
            return rows
        start += page_size