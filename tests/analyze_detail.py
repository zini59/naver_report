# -*- coding: utf-8 -*-
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

files = {
    "부산이비인후과": Path(
        r"d:\박예진\@@@시월기획\204.검색광고\4.부산이비인후과\20260108_부산이비인후과_보고서(12월)\20260108_부산이비인후과_보고서(25년12월).xlsx"
    ),
    "시월기획": Path(
        r"d:\박예진\@@@시월기획\204.검색광고\1.시월기획\20260102_시월기획_보고서(12월)\시월기획 25년 12월 네이버 검색광고 리포트(1201-1231).xlsx"
    ),
}

lines = []


def dump_rows(raw, title, filter_fn=None):
    lines.append(f"\n===== {title} =====")
    for i, row in raw.iterrows():
        vals = [str(v) for v in row.tolist() if pd.notna(v) and str(v).strip()]
        if not vals:
            continue
        if filter_fn and not filter_fn(i, vals):
            continue
        lines.append(f"R{i+1}: " + " | ".join(vals))


for name, fp in files.items():
    dump_rows(pd.read_excel(fp, sheet_name="요약리포트", header=None, engine="openpyxl"), f"{name} - 요약리포트 전체")

    dump_rows(
        pd.read_excel(fp, sheet_name="일자별&요일별", header=None, engine="openpyxl"),
        f"{name} - 일자별&요일별 (후반부/요일)",
        lambda i, vals: i >= 38 or any(k in " ".join(vals) for k in ["요일", "▶", "합계"]),
    )

    dump_rows(
        pd.read_excel(fp, sheet_name="상위 키워드 순위별", header=None, engine="openpyxl"),
        f"{name} - 상위키워드 섹션",
        lambda i, vals: i < 12 or "TOP" in " ".join(vals) or "▶" in " ".join(vals),
    )

    dump_rows(
        pd.read_excel(fp, sheet_name="성별&연령별&기기별", header=None, engine="openpyxl"),
        f"{name} - 성별&연령&기기",
    )

out = Path(__file__).parent.parent / "data" / "detail_analysis.txt"
out.write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
