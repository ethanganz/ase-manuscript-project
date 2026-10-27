from database.paging import fetch_all


class FakeQuery:
    """Mimics supabase's query: .range(a, b).execute().data"""

    def __init__(self, data):
        self.data, self._slice = data, (0, None)

    def range(self, a, b):
        self._slice = (a, b)
        return self

    def execute(self):
        a, b = self._slice
        self.data = self.data[a : b + 1]
        return self


def test_fetches_everything_across_pages():
    data = [{"i": i} for i in range(2500)]
    assert fetch_all(lambda: FakeQuery(list(data)), page_size=1000) == data


def test_exact_multiple_of_page_size_does_not_loop_forever():
    data = [{"i": i} for i in range(2000)]
    assert len(fetch_all(lambda: FakeQuery(list(data)), page_size=1000)) == 2000


def test_empty():
    assert fetch_all(lambda: FakeQuery([])) == []
