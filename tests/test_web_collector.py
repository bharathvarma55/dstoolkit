from dstoolkit.collectors import web_collector


class _FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


def test_collect_table(monkeypatch):
    html = (
        "<html><body><table>"
        "<tr><th>a</th><th>b</th></tr>"
        "<tr><td>1</td><td>2</td></tr>"
        "</table></body></html>"
    )

    def fake_get(url, timeout=None, headers=None):
        return _FakeResponse(html)

    monkeypatch.setattr(web_collector.requests, "get", fake_get)

    result = web_collector.collect("http://example.com")
    assert result.row_count == 1
    assert list(result.df.columns) == ["a", "b"]
    assert result.source_type == "web"


def test_collect_with_selector(monkeypatch):
    html = """
    <html><body>
    <div class="item"><span class="name">Widget</span><span class="price">9.99</span></div>
    <div class="item"><span class="name">Gadget</span><span class="price">19.99</span></div>
    </body></html>
    """

    def fake_get(url, timeout=None, headers=None):
        return _FakeResponse(html)

    monkeypatch.setattr(web_collector.requests, "get", fake_get)

    result = web_collector.collect(
        "http://example.com",
        selector=".item",
        fields={"name": ".name", "price": ".price"},
    )
    assert result.row_count == 2
    assert result.df["name"].tolist() == ["Widget", "Gadget"]


def test_collect_with_selector_matching_nothing_keeps_columns(monkeypatch):
    html = "<html><body><p>no items here</p></body></html>"

    def fake_get(url, timeout=None, headers=None):
        return _FakeResponse(html)

    monkeypatch.setattr(web_collector.requests, "get", fake_get)

    result = web_collector.collect(
        "http://example.com",
        selector=".item",
        fields={"name": ".name", "price": ".price"},
    )
    assert result.row_count == 0
    assert list(result.df.columns) == ["name", "price"]
