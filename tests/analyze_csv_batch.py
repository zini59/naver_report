# -*- coding: utf-8 -*-
"""키워드 효율 보고서 CSV (3)~(10) 구조 분석"""
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

FILES = [
    Path(rf"c:\Users\82103\Downloads\키워드 효율 보고서,861325 ({i}).csv")
    for i in range(3, 11)
]

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from naver_ad_report.parser import _read_raw_table, detect_report_kind, parse_naver_title


def row_preview(raw: pd.DataFrame, n=5):
    lines = []
    for i in range(min(n, len(raw))):
        vals = [str(v) for v in raw.iloc[i].tolist() if pd.notna(v) and str(v).strip()]
        if vals:
            lines.append(f"    R{i+2}: " + " | ".join(vals[:12]))
    return "\n".join(lines)


out = []
for fp in FILES:
    if not fp.exists():
        out.append(f"MISSING: {fp.name}")
        continue

    with open(fp, encoding="utf-8-sig") as f:
        title = f.readline().strip()

    raw, meta = _read_raw_table(fp.read_bytes(), fp.name)
    kind = meta.get("kind", "?")

    out.append("=" * 80)
    out.append(f"FILE: {fp.name}")
    out.append(f"Title: {title}")
    out.append(f"Kind: {kind} | Rows: {len(raw)} | Cols: {len(raw.columns)}")
    out.append(f"Columns: {list(raw.columns)}")
    out.append("Sample:")
    out.append(row_preview(raw))

    if len(raw) <= 20:
        out.append("ALL DATA:")
        for i, row in raw.iterrows():
            vals = [str(v) for v in row.tolist() if pd.notna(v) and str(v).strip()]
            if vals:
                out.append(f"    R{i+2}: " + " | ".join(vals))

    # numeric summary
    num_cols = [c for c in raw.columns if raw[c].dtype in ("int64", "float64") or c in ("노출수", "클릭수", "총비용")]
    if num_cols:
        for c in ["노출수", "클릭수", "총비용"]:
            if c in raw.columns:
                out.append(f"  Sum {c}: {raw[c].sum():,.0f}")

    out.append("")

result = "\n".join(out)
(ROOT / "data" / "csv_batch_analysis.txt").write_text(result, encoding="utf-8")
print(result)
