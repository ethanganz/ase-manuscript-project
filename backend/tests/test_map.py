from uuid import uuid4

DOC_A, DOC_B = str(uuid4()), str(uuid4())


def mention(collection_id, place, country, doc=DOC_A, doc_name="letter_001.pdf", page=1, snippet="..."):
    """Builds one row shaped like the mention_details view."""
    return {
        "mention_id": str(uuid4()), "place_name": place, "country_code": country,
        "snippet": snippet, "page_id": str(uuid4()), "page_number": page,
        "document_id": doc, "document_name": doc_name, "collection_id": collection_id,
    }


def test_empty_collection_has_no_countries(client, collection):
    assert client.get(f"/api/collections/{collection['id']}/map/countries").json() == []


def test_countries_are_counted_and_sorted(client, collection, repo):
    cid = collection["id"]
    repo.mention_details += [
        mention(cid, "Geneva", "CH"), mention(cid, "Geneva", "CH", page=2),
        mention(cid, "Zurich", "CH", page=3),
        mention(cid, "Paris", "FR"),
    ]
    data = client.get(f"/api/collections/{cid}/map/countries").json()
    assert data == [
        {"country_code": "CH", "mention_count": 3, "place_count": 2},
        {"country_code": "FR", "mention_count": 1, "place_count": 1},
    ]


def test_rows_without_country_are_ignored_and_codes_normalised(client, collection, repo):
    cid = collection["id"]
    repo.mention_details += [
        mention(cid, "Nowhere", None), mention(cid, "Odd", "XYZ"),
        mention(cid, "Paris", " fr "),
    ]
    data = client.get(f"/api/collections/{cid}/map/countries").json()
    assert [c["country_code"] for c in data] == ["FR"]


def test_other_collections_are_not_mixed_in(client, collection, repo):
    other = repo.create_collection("Other", None, repo.get_collection(collection["id"])["owner_id"])
    repo.mention_details += [mention(other["id"], "Rome", "IT")]
    assert client.get(f"/api/collections/{collection['id']}/map/countries").json() == []


def test_country_mentions_point_back_to_the_page(client, collection, repo):
    cid = collection["id"]
    m = mention(cid, "Geneva", "CH", doc=DOC_B, doc_name="b.pdf", page=4, snippet="arrived in Geneva")
    repo.mention_details += [m, mention(cid, "Paris", "FR")]
    data = client.get(f"/api/collections/{cid}/map/countries/ch/mentions").json()  # lower case ok
    assert len(data) == 1
    assert data[0]["page_id"] == m["page_id"] and data[0]["document_id"] == DOC_B
    assert data[0]["page_number"] == 4 and data[0]["snippet"] == "arrived in Geneva"
    assert "collection_id" not in data[0]


def test_mentions_are_in_reading_order(client, collection, repo):
    cid = collection["id"]
    repo.mention_details += [
        mention(cid, "B", "CH", doc=DOC_B, doc_name="b.pdf", page=1),
        mention(cid, "A2", "CH", page=2), mention(cid, "A1", "CH", page=1),
    ]
    data = client.get(f"/api/collections/{cid}/map/countries/CH/mentions").json()
    assert [(d["document_name"], d["page_number"]) for d in data] == [
        ("b.pdf", 1), ("letter_001.pdf", 1), ("letter_001.pdf", 2)]


def test_bad_country_code_is_422(client, collection):
    assert client.get(f"/api/collections/{collection['id']}/map/countries/SWISS/mentions").status_code == 422
    assert client.get(f"/api/collections/{collection['id']}/map/countries/1/mentions").status_code == 422


def test_unknown_collection_is_404(client):
    missing = "00000000-0000-0000-0000-000000000000"
    assert client.get(f"/api/collections/{missing}/map/countries").status_code == 404
    assert client.get(f"/api/collections/{missing}/map/countries/CH/mentions").status_code == 404