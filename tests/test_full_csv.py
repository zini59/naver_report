# -*- coding: utf-8 -*-
"""전체 CSV (1)~(10) 통합 테스트"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from naver_ad_report.parser import merge_uploaded_files
from naver_ad_report.report_generator import (
    build_daily_report_from_bundle,
    build_region_report_from_bundle,
    build_weekday_report_from_bundle,
    build_weekly_report_from_bundle,
    generate_excel_report,
    infer_report_month,
)

CSV_DIR = Path(r"c:\Users\82103\Downloads")
sources = []
for i in range(1, 11):
    fp = CSV_DIR / f"키워드 효율 보고서,861325 ({i}).csv"
    if fp.exists():
        sources.append((fp.name, fp.read_bytes()))

assert len(sources) >= 8, f"need sample files, found {len(sources)}"

bundle, warnings = merge_uploaded_files(sources)
assert bundle.has_any_data()

assert bundle.has_daily(), "daily missing"
assert bundle.has_weekday(), "weekday missing"
assert bundle.has_weekly(), "weekly missing"
assert bundle.has_region(), "region missing"
assert bundle.has_demographic(), "demographic missing"

assert len(build_daily_report_from_bundle(bundle)) == 31
assert len(build_weekday_report_from_bundle(bundle)) == 7
assert len(build_weekly_report_from_bundle(bundle)) == 4
assert len(build_region_report_from_bundle(bundle, detail=True)) == 32

excel = generate_excel_report(
    bundle.primary_df, "제스트", infer_report_month(bundle), bundle=bundle
)
out = ROOT / "data" / "test_full_output.xlsx"
out.write_bytes(excel)

print(f"OK - {out} ({len(excel):,} bytes)")
print(f"  files: {len(sources)}")
print(f"  daily={len(bundle.daily)} weekday={len(bundle.weekday)} weekly={len(bundle.weekly)}")
print(f"  region={len(bundle.region)} detail={len(bundle.region_detail)}")
print(f"  gender={len(bundle.gender)} age={len(bundle.age)} device={len(bundle.device)}")
for w in warnings:
    print(f"  {w}")
