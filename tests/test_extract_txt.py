from pathlib import Path
from app.extract import extract_text_from_txt


def test_extract_text_from_txt(tmp_path: Path):
    p = tmp_path / "sample.txt"
    p.write_text("Claim Number: CLM-TEST\nPolicy Number: POL-XYZ\n")
    text = extract_text_from_txt(p)
    assert "CLM-TEST" in text
    assert "POL-XYZ" in text

