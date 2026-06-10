# -*- coding: utf-8 -*-
"""키워드 효율 CSV 파이프라인 테스트"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from naver_ad_report.parser import merge_uploaded_files
from naver_ad_report.report_generator import (
    build_keyword_report,
    build_summary_table,
    build_top_keyword_report,
    generate_excel_report,
    infer_report_month,
)

CSV_DIR = Path(r"c:\Users\82103\Downloads")
FILES = [
    CSV_DIR / "키워드 효율 보고서,861325 (1).csv",
    CSV_DIR / "키워드 효율 보고서,861325 (2).csv",
]


def test_csv_pipeline():
    sources = [(f.name, f.read_bytes()) for f in FILES if f.exists()]
    assert sources, "CSV sample files not found"

    bundle, warnings = merge_uploaded_files(sources)
    assert bundle.has_keywords(), "keyword detail required"
    assert bundle.has_campaigns(), "campaign summary required"
    assert bundle.period_start is not None

    summary = build_summary_table(bundle)
    assert "합계" in summary["구분"].values
    assert len(build_keyword_report(bundle.keywords)) > 100
    assert len(build_top_keyword_report(bundle.keywords, "클릭")) == 10

    excel = generate_excel_report(
        bundle.primary_df, "제스트", infer_report_month(bundle), bundle=bundle
    )
    out = ROOT / "data" / "test_csv_output.xlsx"
    out.write_bytes(excel)
    print(f"OK - {out}")
    print(f"  period: {bundle.period_start} ~ {bundle.period_end}")
    print(f"  keywords: {len(bundle.keywords)}, campaigns: {len(bundle.campaigns)}")
    for w in warnings:
        print(f"  {w}")


if __name__ == "__main__":
    test_csv_pipeline()
