"""네이버 검색광고 1차 파일(CSV/엑셀) 파싱 및 정규화"""

from __future__ import annotations

import io
import re
from datetime import date, datetime
from typing import BinaryIO

import pandas as pd

from .config import COLUMN_ALIASES
from .report_data import ReportBundle

# 키워드 효율 보고서 CSV 1열(집계 기준) → 파일 유형
DIMENSION_COLUMN_KIND = {
    "일별": "daily",
    "요일별": "weekday",
    "주별": "weekly",
    "지역": "region",
    "상세지역": "region_detail",
    "성별": "gender",
    "연령대": "age",
}

KIND_LABELS = {
    "keyword_detail": "키워드 상세",
    "keyword_campaign": "캠페인 요약",
    "daily": "일별",
    "weekday": "요일별",
    "weekly": "주차별",
    "region": "지역별",
    "region_detail": "상세지역별",
    "gender": "성별",
    "age": "연령별",
    "device": "기기별(PC/모바일)",
}
TITLE_PATTERN = re.compile(
    r"^(?P<name>.+?)\((?P<start>[\d.]+)\.?\s*~\s*(?P<end>[\d.]+)\.?\)\s*,?\s*(?P<account>\d*)\s*$"
)


def _normalize_header(name: str) -> str:
    return re.sub(r"\s+", "", str(name).strip().lower())


def _find_column(df: pd.DataFrame, aliases: list[str]) -> str | None:
    normalized = {_normalize_header(c): c for c in df.columns}
    for alias in aliases:
        key = _normalize_header(alias)
        if key in normalized:
            return normalized[key]
    return None


def map_columns(df: pd.DataFrame) -> dict[str, str | None]:
    return {field: _find_column(df, aliases) for field, aliases in COLUMN_ALIASES.items()}


def parse_naver_title(title_line: str) -> dict:
    """CSV/엑셀 첫 줄 제목에서 기간·계정ID 추출."""
    text = title_line.strip().strip('"').strip("'")
    m = TITLE_PATTERN.match(text)
    if not m:
        return {"title": text}

    def to_date(s: str) -> date | None:
        s = s.strip().rstrip(".")
        for fmt in ("%Y.%m.%d", "%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
        return None

    return {
        "title": m.group("name").strip(),
        "period_start": to_date(m.group("start")),
        "period_end": to_date(m.group("end")),
        "account_id": m.group("account").strip(),
    }


def detect_report_kind(df: pd.DataFrame, title: str = "") -> str:
    """파일 유형 자동 판별 (키워드 효율 CSV 집계 기준열 우선)."""
    if df.empty:
        return "generic"

    cols = list(df.columns)
    first_norm = _normalize_header(cols[0])
    all_norm = {_normalize_header(c) for c in cols}

    # PC/모바일 매체
    if "pc" in first_norm and "모바일" in first_norm:
        return "device"
    if "매체" in first_norm:
        return "device"

    for dim_name, kind in DIMENSION_COLUMN_KIND.items():
        if _normalize_header(dim_name) == first_norm:
            return kind

    if "검색어" in all_norm or ("키워드" in all_norm and "광고그룹" in all_norm):
        return "keyword_detail"

    if "캠페인" in all_norm and "광고그룹" not in all_norm and "검색어" not in all_norm:
        return "keyword_campaign"

    if "일별" in all_norm or "일자" in all_norm:
        return "daily"
    if "지역" in all_norm:
        return "region"

    return "generic"


def _detect_header_row(raw: pd.DataFrame, max_scan: int = 15) -> int:
    keywords = ["노출", "클릭", "비용", "캠페인", "광고", "일별", "일자", "날짜", "검색어"]
    for i in range(min(max_scan, len(raw))):
        row_text = " ".join(str(v) for v in raw.iloc[i].tolist() if pd.notna(v))
        if sum(1 for kw in keywords if kw in row_text) >= 2:
            return i
    return 0


def _read_raw_table(source: BinaryIO | bytes, filename: str) -> tuple[pd.DataFrame, dict]:
    """CSV 또는 엑셀을 읽어 raw DataFrame + 메타 반환."""
    meta: dict = {"filename": filename}
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if ext == "csv":
        if isinstance(source, bytes):
            text = source.decode("utf-8-sig")
        else:
            text = source.read().decode("utf-8-sig")
            if hasattr(source, "seek"):
                source.seek(0)

        lines = text.splitlines()
        if lines:
            meta.update(parse_naver_title(lines[0]))
        df = pd.read_csv(io.StringIO(text), skiprows=1, encoding="utf-8-sig")
    else:
        if isinstance(source, bytes):
            source = io.BytesIO(source)
        raw = pd.read_excel(source, header=None, engine="openpyxl")
        if len(raw) > 0:
            first = " ".join(str(v) for v in raw.iloc[0].tolist() if pd.notna(v))
            if any(k in first for k in ("보고서", "리포트", "키워드")):
                meta.update(parse_naver_title(first))
        header_row = _detect_header_row(raw)
        if isinstance(source, io.BytesIO):
            source.seek(0)
        df = pd.read_excel(source, header=header_row, engine="openpyxl")

    df = df.dropna(how="all").reset_index(drop=True)
    df.columns = [str(c).strip() for c in df.columns]
    meta["kind"] = detect_report_kind(df, meta.get("title", ""))
    return df, meta


def _to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False).str.replace("%", "", regex=False),
        errors="coerce",
    ).fillna(0)


def _parse_date_series(series: pd.Series) -> pd.Series:
    def parse_one(val):
        if pd.isna(val):
            return pd.NaT
        text = str(val).strip()
        if "~" in text:
            text = text.split("~")[0].strip()
        text = text.replace(".", "-").replace("/", "-").rstrip("-")
        return pd.to_datetime(text, errors="coerce")

    return series.apply(parse_one)


def _normalize_dimension_dataframe(df: pd.DataFrame, kind: str) -> pd.DataFrame:
    """일별·요일·지역 등 5열짜리 키워드 효율 집계 CSV 정규화."""
    label_col = df.columns[0]
    result = pd.DataFrame()
    labels = df[label_col].astype(str).replace("nan", "")

    field_map = {
        "daily": "일자",
        "weekday": "요일",
        "weekly": "주차",
        "region": "지역",
        "region_detail": "지역",
        "gender": "성별",
        "age": "연령",
        "device": "기기",
    }
    std_field = field_map.get(kind, "구분")
    result[std_field] = labels
    result["구분"] = labels

    if kind == "daily":
        result["일자"] = _parse_date_series(labels)
    else:
        result["일자"] = pd.NaT

    for std_col, field in [
        ("노출수", "impressions"),
        ("클릭수", "clicks"),
        ("광고비", "cost"),
    ]:
        src = _find_column(df, COLUMN_ALIASES[field])
        result[std_col] = _to_numeric(df[src]) if src else 0.0

    result["클릭률"] = 0.0
    result["평균CPC"] = 0.0
    mask = result["노출수"] > 0
    result.loc[mask, "클릭률"] = result.loc[mask, "클릭수"] / result.loc[mask, "노출수"]
    mask = result["클릭수"] > 0
    result.loc[mask, "평균CPC"] = (result.loc[mask, "광고비"] / result.loc[mask, "클릭수"]).round(0)

    for col in ["캠페인", "광고그룹", "키워드", "검색유형", "전환수", "전환율", "전환당비용"]:
        result[col] = "" if col != "전환수" else 0.0

    return result.reset_index(drop=True)


def normalize_dataframe(df: pd.DataFrame, kind: str = "generic") -> tuple[pd.DataFrame, dict[str, str | None]]:
    """원본 DataFrame을 표준 컬럼 구조로 변환."""
    if kind in DIMENSION_COLUMN_KIND.values() or kind == "device":
        normalized = _normalize_dimension_dataframe(df, kind)
        return normalized, {"dimension": kind}

    col_map = map_columns(df)
    result = pd.DataFrame()

    if col_map["date"]:
        result["일자"] = _parse_date_series(df[col_map["date"]])
    else:
        result["일자"] = pd.NaT

    for std_col, field in [
        ("캠페인", "campaign"),
        ("광고그룹", "ad_group"),
        ("키워드", "keyword"),
        ("검색유형", "search_type"),
    ]:
        src = col_map[field]
        result[std_col] = df[src].astype(str).replace("nan", "") if src else ""

    for std_col, field in [
        ("노출수", "impressions"),
        ("클릭수", "clicks"),
        ("클릭률", "ctr"),
        ("평균CPC", "cpc"),
        ("광고비", "cost"),
        ("전환수", "conversions"),
        ("전환율", "conversion_rate"),
        ("전환당비용", "conversion_cost"),
    ]:
        src = col_map[field]
        result[std_col] = _to_numeric(df[src]) if src else 0.0

    # 키워드 상세: 클릭 0인 행도 유지 (TOP 노출 등에 필요), 단 완전 빈 행 제거
    if kind != "keyword_detail":
        has_metrics = (result["노출수"] + result["클릭수"] + result["광고비"]) > 0
        result = result[has_metrics].copy()

    # 클릭률: 최종 리포트 형식 = 소수(0.0052), 퍼센트가 아님
    mask = (result["클릭률"] == 0) & (result["노출수"] > 0) & (result["클릭수"] > 0)
    result.loc[mask, "클릭률"] = result.loc[mask, "클릭수"] / result.loc[mask, "노출수"]
    # 100 초과면 퍼센트로 들어온 것 → 소수로 변환
    pct_mask = result["클릭률"] > 1
    result.loc[pct_mask, "클릭률"] = result.loc[pct_mask, "클릭률"] / 100

    mask = (result["평균CPC"] == 0) & (result["클릭수"] > 0)
    result.loc[mask, "평균CPC"] = (result.loc[mask, "광고비"] / result.loc[mask, "클릭수"]).round(0)

    return result.reset_index(drop=True), col_map


def read_excel_file(source: BinaryIO | str | bytes) -> pd.DataFrame:
    """하위 호환: 엑셀 단독 읽기."""
    if isinstance(source, (str, bytes)):
        name = "upload.xlsx"
    else:
        name = "upload.xlsx"
    df, _ = _read_raw_table(source if isinstance(source, bytes) else source, name)
    return df


def merge_uploaded_files(file_sources: list[tuple[str, BinaryIO | bytes]]) -> tuple[ReportBundle, list[str]]:
    """여러 1차 CSV/엑셀을 ReportBundle로 병합."""
    bundle = ReportBundle()
    warnings: list[str] = []

    for filename, source in file_sources:
        try:
            raw, meta = _read_raw_table(source, filename)
            kind = meta.get("kind", "generic")
            normalized, col_map = normalize_dataframe(raw, kind)

            if normalized.empty and kind not in ("keyword_detail",):
                warnings.append(f"{filename}: 유효한 데이터 행이 없습니다.")
                continue

            if meta.get("period_start") and not bundle.period_start:
                bundle.period_start = meta["period_start"]
            if meta.get("period_end") and not bundle.period_end:
                bundle.period_end = meta["period_end"]
            if meta.get("account_id") and not bundle.account_id:
                bundle.account_id = meta["account_id"]

            bundle.source_files.append(filename)
            normalized["_출처파일"] = filename

            if kind == "keyword_detail":
                bundle.keywords = pd.concat([bundle.keywords, normalized], ignore_index=True)
            elif kind == "keyword_campaign":
                bundle.campaigns = pd.concat([bundle.campaigns, normalized], ignore_index=True)
            elif kind == "daily":
                bundle.daily = pd.concat([bundle.daily, normalized], ignore_index=True)
            elif kind == "weekday":
                bundle.weekday = pd.concat([bundle.weekday, normalized], ignore_index=True)
            elif kind == "weekly":
                bundle.weekly = pd.concat([bundle.weekly, normalized], ignore_index=True)
            elif kind == "region":
                bundle.region = pd.concat([bundle.region, normalized], ignore_index=True)
            elif kind == "region_detail":
                bundle.region_detail = pd.concat([bundle.region_detail, normalized], ignore_index=True)
            elif kind == "gender":
                bundle.gender = pd.concat([bundle.gender, normalized], ignore_index=True)
            elif kind == "age":
                bundle.age = pd.concat([bundle.age, normalized], ignore_index=True)
            elif kind == "device":
                bundle.device = pd.concat([bundle.device, normalized], ignore_index=True)
            else:
                if col_map.get("keyword") or "검색어" in raw.columns:
                    bundle.keywords = pd.concat([bundle.keywords, normalized], ignore_index=True)
                elif col_map.get("date") or "일별" in raw.columns:
                    bundle.daily = pd.concat([bundle.daily, normalized], ignore_index=True)
                elif col_map.get("campaign"):
                    bundle.campaigns = pd.concat([bundle.campaigns, normalized], ignore_index=True)
                else:
                    warnings.append(f"{filename}: 파일 유형을 판별하지 못했습니다. 컬럼: {list(raw.columns)}")

            kind_label = KIND_LABELS.get(kind, kind)
            warnings.append(f"OK {filename} -> {kind_label} ({len(normalized)}행)")

        except Exception as e:
            warnings.append(f"ERR {filename}: 읽기 오류 - {e}")

    if not bundle.has_any_data():
        return bundle, warnings

    return bundle, warnings


# 하위 호환
def merge_uploaded_files_legacy(file_sources: list[tuple[str, BinaryIO | bytes]]) -> tuple[pd.DataFrame, list[str]]:
    bundle, warnings = merge_uploaded_files(file_sources)
    return bundle.primary_df, warnings
