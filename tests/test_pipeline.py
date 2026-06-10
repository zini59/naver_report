"""샘플 네이버 광고 엑셀 생성 및 파이프라인 테스트"""

import io
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys_path = str(ROOT)
import sys
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)

from naver_ad_report.parser import merge_uploaded_files
from naver_ad_report.report_generator import (
    build_ad_group_report,
    build_daily_report,
    build_weekday_report,
    generate_excel_report,
)


def make_sample_excel() -> bytes:
    """네이버 검색광고 형식과 유사한 샘플 데이터."""
    rows = []
    ad_groups = ["브랜드키워드", "일반키워드", "지역키워드"]
    campaigns = ["검색광고_메인", "검색광고_서브"]

    for day in range(1, 29):
        date = f"2025-05-{day:02d}"
        for ag_idx, ag in enumerate(ad_groups):
            camp = campaigns[ag_idx % 2]
            imp = 1000 + day * 50 + ag_idx * 200
            clk = int(imp * 0.03) + ag_idx * 5
            cost = clk * (800 + ag_idx * 100)
            rows.append({
                "일별": date,
                "캠페인": camp,
                "광고그룹": ag,
                "노출수": imp,
                "클릭수": clk,
                "클릭률(%)": round(clk / imp * 100, 2),
                "평균클릭비용": round(cost / clk, 0) if clk else 0,
                "총비용": cost,
                "전환수": max(1, clk // 10),
            })

    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    buf.seek(0)
    return buf.getvalue()


def test_pipeline():
    sample = make_sample_excel()
    df, warnings = merge_uploaded_files([("sample.xlsx", sample)])

    assert not df.empty, "DataFrame should not be empty"
    assert len(warnings) == 0, f"Unexpected warnings: {warnings}"
    assert df["광고그룹"].nunique() == 3
    assert df["일자"].notna().all()

    ag = build_ad_group_report(df)
    assert len(ag) == 3

    daily = build_daily_report(df)
    assert len(daily) == 28

    weekday = build_weekday_report(df)
    assert len(weekday) == 7

    excel = generate_excel_report(df, "테스트업체", "2025-05")
    assert len(excel) > 5000

    out = ROOT / "data" / "test_output.xlsx"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(excel)
    print(f"OK - test passed, sample output: {out}")
    print(f"  rows: {len(df)}, ad groups: {len(ag)}, days: {len(daily)}")


if __name__ == "__main__":
    test_pipeline()
