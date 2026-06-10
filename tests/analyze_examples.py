# -*- coding: utf-8 -*-
"""예시 리포트 엑셀 구조 분석"""
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

files = [
    Path(r"d:\박예진\@@@시월기획\204.검색광고\4.부산이비인후과\20260108_부산이비인후과_보고서(12월)\20260108_부산이비인후과_보고서(25년12월).xlsx"),
    Path(r"d:\박예진\@@@시월기획\204.검색광고\1.시월기획\20260102_시월기획_보고서(12월)\시월기획 25년 12월 네이버 검색광고 리포트(1201-1231).xlsx"),
]

out_lines = []


def row_to_str(row):
    parts = []
    for i, v in enumerate(row):
        if pd.notna(v) and str(v).strip():
            parts.append(f"[{i}]={v}")
    return " | ".join(parts) if parts else "(empty)"


for fp in files:
    out_lines.append("=" * 90)
    out_lines.append(f"FILE: {fp.name}")
    out_lines.append("=" * 90)

    xl = pd.ExcelFile(fp, engine="openpyxl")
    out_lines.append(f"시트 목록 ({len(xl.sheet_names)}개): {xl.sheet_names}")

    for sheet_name in xl.sheet_names:
        raw = pd.read_excel(fp, sheet_name=sheet_name, header=None, engine="openpyxl")
        out_lines.append(f"\n--- [{sheet_name}] shape={raw.shape} ---")

        for r in range(min(18, len(raw))):
            line = row_to_str(raw.iloc[r].tolist())
            if line != "(empty)":
                out_lines.append(f"  R{r+1}: {line}")

        # 헤더 탐색
        for r in range(min(25, len(raw))):
            texts = " ".join(str(x) for x in raw.iloc[r].tolist() if pd.notna(x))
            if ("노출" in texts or "IMP" in texts.upper()) and ("클릭" in texts or "비용" in texts or "CPC" in texts.upper() or "VCPA" in texts.upper()):
                out_lines.append(f"  >> 헤더 R{r+1}: {raw.iloc[r].tolist()}")
                for dr in range(r + 1, min(r + 6, len(raw))):
                    dl = row_to_str(raw.iloc[dr].tolist())
                    if dl != "(empty)":
                        out_lines.append(f"     D R{dr+1}: {dl}")
                break

    out_lines.append("")

result = "\n".join(out_lines)
out_path = Path(__file__).parent.parent / "data" / "example_analysis.txt"
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(result, encoding="utf-8")
print(result)
