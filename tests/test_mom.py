# -*- coding: utf-8 -*-
"""전월 대비 저장·조회 테스트"""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from naver_ad_report.metrics import extract_monthly_metrics, previous_report_month
from naver_ad_report.parser import merge_uploaded_files
from naver_ad_report.report_generator import build_mom_comparison, generate_excel_report
from naver_ad_report.storage import get_previous_month_summary, save_report

CSV = Path(r"c:\Users\82103\Downloads")


def test_mom_flow():
    assert previous_report_month("2026-05") == "2026-04"

    fp = CSV / "키워드 효율 보고서,861325 (1).csv"
    if not fp.exists():
        print("skip: no sample csv")
        return

    bundle, _ = merge_uploaded_files([(fp.name, fp.read_bytes())])
    may_metrics = extract_monthly_metrics(bundle, "2026-05")
    assert may_metrics["노출수"] > 0

    # 가짜 4월 전월 데이터
    april = {
        **may_metrics,
        "report_month": "2026-04",
        "period_label": "04/01 - 04/30 (총30일)",
        "노출수": int(may_metrics["노출수"] / 2),
        "클릭수": int(may_metrics["클릭수"] / 2),
        "광고비": int(may_metrics["광고비"] / 2),
        "클릭률": may_metrics["클릭률"],
        "CPC": may_metrics["CPC"],
    }

    mom = build_mom_comparison(may_metrics, april)
    assert len(mom) == 3
    assert mom.iloc[1]["집행기간"] == "전월 대비 증감율"
    assert float(mom.iloc[1]["노출"]) > 0.9

    with tempfile.TemporaryDirectory() as tmp:
        import naver_ad_report.storage as storage

        storage.DB_PATH = Path(tmp) / "test.db"
        storage.REPORTS_DIR = Path(tmp) / "reports"

        save_report("테스트업체", "2026-04", b"xlsx", april)
        loaded = get_previous_month_summary("테스트업체", "2026-05")
        assert loaded is not None
        assert loaded["노출수"] == april["노출수"]

        excel = generate_excel_report(
            bundle.primary_df,
            "테스트업체",
            "2026-05",
            bundle=bundle,
            previous_summary=loaded,
            current_metrics=may_metrics,
        )
        assert len(excel) > 1000

    print("OK - mom comparison test passed")


if __name__ == "__main__":
    test_mom_flow()
