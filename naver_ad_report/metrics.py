"""월별 핵심 지표 추출 (전월 대비·저장용)"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from .report_data import ReportBundle


def format_period_label(start: date | None, end: date | None) -> str:
    if not start or not end:
        return ""
    days = (end - start).days + 1
    return f"{start.strftime('%m/%d')} - {end.strftime('%m/%d')} (총{days}일)"


def _totals_from_bundle(bundle: ReportBundle) -> dict:
    """캠페인 요약 → 일별 → 키워드 순으로 합계 산출."""
    if bundle.has_campaigns():
        df = bundle.campaigns
        conv = int(df["전환수"].sum()) if "전환수" in df.columns else 0
        return {
            "노출수": int(df["노출수"].sum()),
            "클릭수": int(df["클릭수"].sum()),
            "광고비": int(df["광고비"].sum()),
            "전환수": conv,
        }

    if bundle.has_daily():
        df = bundle.daily
        conv = int(df["전환수"].sum()) if "전환수" in df.columns else 0
        return {
            "노출수": int(df["노출수"].sum()),
            "클릭수": int(df["클릭수"].sum()),
            "광고비": int(df["광고비"].sum()),
            "전환수": conv,
        }

    if bundle.has_keywords():
        df = bundle.keywords
        conv = int(df["전환수"].sum()) if "전환수" in df.columns else 0
        return {
            "노출수": int(df["노출수"].sum()),
            "클릭수": int(df["클릭수"].sum()),
            "광고비": int(df["광고비"].sum()),
            "전환수": conv,
        }

    return {"노출수": 0, "클릭수": 0, "광고비": 0, "전환수": 0}


def extract_monthly_metrics(bundle: ReportBundle, report_month: str) -> dict:
    """업체·월별 저장 시 기록할 표준 지표 (다음달 전월 대비용)."""
    t = _totals_from_bundle(bundle)
    imp, clk, cost, conv = t["노출수"], t["클릭수"], t["광고비"], t["전환수"]

    ctr = round(clk / imp, 6) if imp else 0
    cpc = round(cost / clk, 2) if clk else 0
    cvr = round(conv / clk, 6) if clk and conv else 0
    cpa = round(cost / conv, 2) if conv else 0

    start, end = bundle.period_start, bundle.period_end
    if isinstance(start, str) and start:
        start = date.fromisoformat(start)
    if isinstance(end, str) and end:
        end = date.fromisoformat(end)

    return {
        "report_month": report_month,
        "period_start": start.isoformat() if start else "",
        "period_end": end.isoformat() if end else "",
        "period_label": format_period_label(start, end),
        "account_id": bundle.account_id,
        "노출수": imp,
        "클릭수": clk,
        "클릭률": ctr,
        "CPC": cpc,
        "광고비": cost,
        "전환수": conv,
        "전환율": cvr,
        "CPA": cpa,
        "has_conversions": conv > 0,
    }


def previous_report_month(report_month: str) -> str:
    dt = datetime.strptime(f"{report_month.strip()}-01", "%Y-%m-%d")
    prev = dt.replace(day=1) - timedelta(days=1)
    return prev.strftime("%Y-%m")
