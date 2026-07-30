from dstoolkit.collectors import api_collector


class _FakeResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


def test_collect_from_api_with_json_path(monkeypatch):
    payload = {"data": {"items": [{"id": 1}, {"id": 2}]}}

    def fake_request(method, url, params=None, headers=None, timeout=None):
        return _FakeResponse(payload)

    monkeypatch.setattr(api_collector.requests, "request", fake_request)

    result = api_collector.collect("http://example.com/api", json_path="data.items")
    assert result.row_count == 2
    assert list(result.df["id"]) == [1, 2]
    assert result.source_type == "api"


def test_collect_from_api_without_json_path(monkeypatch):
    payload = [{"id": 1}, {"id": 2}, {"id": 3}]

    def fake_request(method, url, params=None, headers=None, timeout=None):
        return _FakeResponse(payload)

    monkeypatch.setattr(api_collector.requests, "request", fake_request)

    result = api_collector.collect("http://example.com/api")
    assert result.row_count == 3
