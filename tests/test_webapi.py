from pathlib import Path

from fastapi.testclient import TestClient

from dstoolkit.webapi.app import app

client = TestClient(app)

DATA_DIR = Path(__file__).parent / "data"


def _upload_sample():
    with open(DATA_DIR / "sample.csv", "rb") as f:
        response = client.post("/api/sessions/upload", files={"file": ("sample.csv", f, "text/csv")})
    assert response.status_code == 200
    return response.json()


def test_upload_returns_preview():
    data = _upload_sample()
    assert "session_id" in data
    preview = data["preview"]
    assert preview["row_count"] == 10
    assert preview["col_count"] == 5
    assert "id" in preview["columns"]


def test_upload_unsupported_format_returns_400():
    response = client.post("/api/sessions/upload", files={"file": ("bad.txt", b"hello", "text/plain")})
    assert response.status_code == 400


def test_full_flow_clean_validate_report():
    session_id = _upload_sample()["session_id"]

    clean_resp = client.post(
        f"/api/sessions/{session_id}/clean",
        json={
            "dedupe": True,
            "missing_value_strategy": "median",
            "missing_value_overrides": {"city": "mode"},
            "string_normalize": True,
            "outlier_strategy": "iqr_cap",
        },
    )
    assert clean_resp.status_code == 200
    clean_data = clean_resp.json()
    assert any("duplicate" in line.lower() for line in clean_data["cleaning_log"])
    assert clean_data["preview"]["row_count"] == 9  # one exact duplicate row removed

    validate_resp = client.post(
        f"/api/sessions/{session_id}/validate",
        json={
            "rules": [
                {"type": "not_null", "column": "name"},
                {"type": "unique", "column": "id"},
            ]
        },
    )
    assert validate_resp.status_code == 200
    validate_data = validate_resp.json()
    assert validate_data["passed"] is True
    assert validate_data["rules_evaluated"] == 2

    report_resp = client.post(f"/api/sessions/{session_id}/report", json={"title": "Test Report"})
    assert report_resp.status_code == 200

    html_resp = client.get(f"/api/sessions/{session_id}/report/html")
    assert html_resp.status_code == 200
    assert "Test Report" in html_resp.text

    pdf_resp = client.get(f"/api/sessions/{session_id}/report/pdf")
    assert pdf_resp.status_code == 200
    assert pdf_resp.content.startswith(b"%PDF")


def test_unknown_session_returns_404():
    response = client.get("/api/sessions/does-not-exist/preview")
    assert response.status_code == 404


def test_report_before_generation_returns_404():
    session_id = _upload_sample()["session_id"]
    response = client.get(f"/api/sessions/{session_id}/report/html")
    assert response.status_code == 404


def test_invalid_cleaning_config_returns_422():
    session_id = _upload_sample()["session_id"]
    response = client.post(
        f"/api/sessions/{session_id}/clean",
        json={"missing_value_strategy": "constant"},  # missing_value_constant not set
    )
    assert response.status_code == 422
