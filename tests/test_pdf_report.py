import pandas as pd

from dstoolkit.cleaning.rules import CleaningLog
from dstoolkit.reporting import html_report, pdf_report
from dstoolkit.validation.rules import ValidationResult


def test_render_bytes_produces_pdf():
    df = pd.DataFrame({"a": [1, 2, 3]})
    html = html_report.render(df, CleaningLog(), ValidationResult(), title="PDF Test")
    pdf_bytes = pdf_report.render_bytes(html)
    assert pdf_bytes.startswith(b"%PDF")


def test_save_writes_file(tmp_path):
    df = pd.DataFrame({"a": [1, 2, 3]})
    html = html_report.render(df, CleaningLog(), ValidationResult(), title="PDF Test")
    output = tmp_path / "nested" / "report.pdf"
    saved_path = pdf_report.save(html, output)
    assert saved_path.exists()
    assert saved_path.read_bytes().startswith(b"%PDF")
