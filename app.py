"""네이버 검색광고 리포트 정리 - Streamlit 웹 앱"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st


def _app_root() -> Path:
    if getattr(sys, "frozen", False):
        internal = Path(sys.executable).parent / "_internal"
        return internal if internal.exists() else Path(sys.executable).parent
    return Path(__file__).resolve().parent


ROOT = _app_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from naver_ad_report.parser import merge_uploaded_files
from naver_ad_report.report_data import ReportBundle
from naver_ad_report.metrics import extract_monthly_metrics, previous_report_month
from naver_ad_report.report_generator import (
    build_campaign_report,
    build_daily_report_from_bundle,
    build_keyword_report,
    build_mom_comparison,
    build_region_report_from_bundle,
    build_summary_overview,
    build_summary_table,
    build_weekday_report_from_bundle,
    build_weekly_report_from_bundle,
    generate_excel_report,
    infer_report_month,
)
from naver_ad_report.storage import (
    delete_report,
    get_previous_month_summary,
    list_reports,
    load_report_file,
    save_report,
)

PREVIEW_ROW_LIMIT = 80

st.set_page_config(
    page_title="네이버 검색광고 리포트",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _inject_styles() -> None:
    st.markdown(
        """
        <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
        <style>
          /* Material 아이콘 폰트 미로드 시 깨진 텍스트 숨김 */
          [data-testid="stSidebarCollapseButton"] span {
            font-family: 'Material Icons' !important;
            font-size: 1.25rem !important;
            overflow: hidden;
            max-width: 1.5rem;
          }
          [data-testid="stFileUploaderDropzone"] [data-testid="stMarkdownContainer"] p {
            font-size: 0.95rem;
            margin: 0;
          }
          [data-testid="stFileUploaderDropzone"] span {
            font-family: 'Material Icons' !important;
          }
          section[data-testid="stSidebar"] .stRadio label {
            padding: 0.45rem 0.25rem;
          }
          div[data-testid="stMetric"] {
            background: #f8fafc;
            padding: 0.75rem;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
          }
          .block-container { padding-top: 1.5rem; max-width: 1100px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _expected_password() -> str:
    env_pwd = os.environ.get("APP_PASSWORD", "").strip()
    if env_pwd:
        return env_pwd
    try:
        return str(st.secrets.get("APP_PASSWORD", "")).strip()
    except Exception:
        return ""


def require_login() -> None:
    expected = _expected_password()
    if not expected or st.session_state.get("authenticated"):
        return

    st.title("네이버 광고 리포트")
    st.caption("접속 비밀번호를 입력하세요.")
    pwd = st.text_input("비밀번호", type="password", key="login_password")
    if st.button("로그인", type="primary"):
        if pwd == expected:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("비밀번호가 올바르지 않습니다.")
    st.stop()


def init_session() -> None:
    defaults = {
        "bundle": None,
        "warnings": [],
        "excel_bytes": None,
        "company_name": "",
        "report_month": datetime.now().strftime("%Y-%m"),
        "previous_summary": None,
        "current_metrics": None,
        "preview_cache": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _limit_df(df: pd.DataFrame, n: int = PREVIEW_ROW_LIMIT) -> pd.DataFrame:
    if df is None or df.empty or len(df) <= n:
        return df if df is not None else pd.DataFrame()
    return df.head(n).copy()


def _build_preview_cache(bundle: ReportBundle, report_month: str) -> dict:
    """미리보기용 표 — 생성 시 1회만 계산."""
    summary = build_summary_overview(bundle.primary_df)
    total_row = {r["항목"]: r["값"] for _, r in summary.iterrows()}
    cur = st.session_state.get("current_metrics") or extract_monthly_metrics(bundle, report_month)
    mom = build_mom_comparison(cur, st.session_state.get("previous_summary"))

    return {
        "metrics": total_row,
        "period": (bundle.period_start, bundle.period_end, bundle.account_id),
        "summary": _limit_df(build_summary_table(bundle)),
        "mom": mom,
        "daily": _limit_df(build_daily_report_from_bundle(bundle)),
        "keywords": _limit_df(build_keyword_report(bundle.keywords)),
        "region": _limit_df(build_region_report_from_bundle(bundle, detail=True)),
        "weekday": _limit_df(build_weekday_report_from_bundle(bundle)),
        "weekly": _limit_df(build_weekly_report_from_bundle(bundle)),
        "campaign": _limit_df(
            build_campaign_report(bundle.primary_df)
            if not bundle.primary_df.empty
            else build_summary_table(bundle)
        ),
        "keyword_total": len(bundle.keywords) if bundle.has_keywords() else 0,
    }


def _process_upload(company: str, month: str, uploaded) -> None:
    sources = [(f.name, f.getvalue()) for f in uploaded]
    bundle, warnings = merge_uploaded_files(sources)

    if not bundle.has_any_data():
        st.error("처리할 수 있는 데이터가 없습니다. 파일 형식을 확인해 주세요.")
        for w in warnings:
            st.warning(w)
        return

    report_month = month.strip() or infer_report_month(bundle)
    prev = get_previous_month_summary(company.strip(), report_month)
    cur_metrics = extract_monthly_metrics(bundle, report_month)

    with st.spinner("엑셀 리포트 생성 중..."):
        excel_bytes = generate_excel_report(
            bundle.primary_df,
            company.strip(),
            report_month,
            bundle=bundle,
            previous_summary=prev,
            current_metrics=cur_metrics,
        )

    st.session_state.bundle = bundle
    st.session_state.warnings = warnings
    st.session_state.excel_bytes = excel_bytes
    st.session_state.company_name = company.strip()
    st.session_state.report_month = report_month
    st.session_state.previous_summary = prev
    st.session_state.current_metrics = cur_metrics
    st.session_state.preview_cache = _build_preview_cache(bundle, report_month)

    prev_m = previous_report_month(report_month)
    if st.session_state.get("previous_summary"):
        st.caption(f"전월({prev_m}) 데이터로 전월 대비를 반영했습니다.")
    else:
        st.caption(f"전월({prev_m}) 저장 기록 없음 — 이번 달 **저장** 후 다음 달부터 전월 대비 자동 반영.")

    st.success(f"{company.strip()} ({report_month}) 리포트 생성 완료")


def render_upload_tab() -> None:
    st.header("CSV 업로드 및 리포트 생성")
    st.caption("네이버 검색광고 > 키워드 효율 보고서 CSV를 업로드하면 7시트 엑셀 리포트가 생성됩니다.")

    with st.form("report_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            company = st.text_input(
                "업체명",
                value=st.session_state.company_name,
                placeholder="예: 제스트",
            )
        with col2:
            month = st.text_input(
                "리포트 월",
                value=st.session_state.report_month,
                placeholder="2026-05",
            )

        uploaded = st.file_uploader(
            "키워드 효율 보고서 CSV (여러 개 선택)",
            type=["csv", "xlsx", "xls"],
            accept_multiple_files=True,
            help="캠페인·키워드·일별·요일·주별·지역·성별·연령·기기 CSV를 함께 올리세요",
        )
        st.caption("집계 기준별 CSV를 한 번에 선택해 업로드한 뒤 [리포트 생성]을 누르세요.")

        submitted = st.form_submit_button("리포트 생성", type="primary", use_container_width=True)

    if submitted:
        if not uploaded:
            st.error("CSV 파일을 먼저 업로드해 주세요.")
        elif not company.strip():
            st.error("업체명을 입력해 주세요.")
        else:
            with st.spinner("CSV 분석 중..."):
                _process_upload(company, month, uploaded)

    if st.session_state.warnings:
        with st.expander("파일 처리 결과", expanded=False):
            for w in st.session_state.warnings:
                if w.startswith("OK"):
                    st.success(w)
                elif w.startswith("ERR"):
                    st.error(w)
                else:
                    st.warning(w)

    if st.session_state.preview_cache is not None:
        render_preview()
        render_download_and_save()


def render_preview() -> None:
    cache = st.session_state.preview_cache
    if not cache:
        return

    st.divider()
    st.subheader("미리보기")

    m1, m2, m3, m4 = st.columns(4)
    total = cache["metrics"]
    m1.metric("총 노출수", f"{int(total.get('총 노출수', 0)):,}")
    m2.metric("총 클릭수", f"{int(total.get('총 클릭수', 0)):,}")
    m3.metric("총 광고비", f"{int(total.get('총 광고비', 0)):,}원")
    m4.metric("평균 CPC", f"{int(total.get('평균 CPC', 0)):,}원")

    ps, pe, acc = cache["period"]
    if ps and pe:
        st.caption(f"기간: {ps} ~ {pe} | 계정ID: {acc or '-'}")

    view = st.selectbox(
        "표 선택",
        ["요약", "일자별", "키워드별", "지역별", "요일/주차", "캠페인별"],
        label_visibility="collapsed",
    )

    if view == "요약":
        st.dataframe(cache["summary"], use_container_width=True, hide_index=True)
        if not cache["mom"].empty:
            st.markdown("**전월 대비**")
            st.dataframe(cache["mom"], use_container_width=True, hide_index=True)
    elif view == "일자별":
        if cache["daily"].empty:
            st.info("일별 CSV를 업로드하면 표시됩니다.")
        else:
            st.dataframe(cache["daily"], use_container_width=True, hide_index=True)
    elif view == "키워드별":
        if cache["keywords"].empty:
            st.info("키워드 CSV를 업로드하면 표시됩니다.")
        else:
            total_kw = cache.get("keyword_total", 0)
            if total_kw > PREVIEW_ROW_LIMIT:
                st.caption(f"미리보기 {PREVIEW_ROW_LIMIT}행 / 전체 {total_kw:,}행 — 전체는 엑셀 다운로드")
            st.dataframe(cache["keywords"], use_container_width=True, hide_index=True)
    elif view == "지역별":
        if cache["region"].empty:
            st.info("지역 CSV를 업로드하면 표시됩니다.")
        else:
            st.dataframe(cache["region"], use_container_width=True, hide_index=True)
    elif view == "요일/주차":
        c1, c2 = st.columns(2)
        with c1:
            st.caption("요일별")
            st.dataframe(cache["weekday"], use_container_width=True, hide_index=True)
        with c2:
            st.caption("주차별")
            st.dataframe(cache["weekly"], use_container_width=True, hide_index=True)
    else:
        if cache["campaign"].empty:
            st.info("캠페인 요약 CSV를 업로드하면 표시됩니다.")
        else:
            st.dataframe(cache["campaign"], use_container_width=True, hide_index=True)


def render_download_and_save() -> None:
    st.divider()
    col1, col2 = st.columns(2)

    company = st.session_state.company_name
    month = st.session_state.report_month
    filename = f"{company}_{month}_네이버광고리포트.xlsx"

    with col1:
        st.download_button(
            label="정리된 엑셀 다운로드",
            data=st.session_state.excel_bytes,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True,
        )

    with col2:
        if st.button("업체·월별 저장", use_container_width=True):
            metrics = st.session_state.get("current_metrics") or extract_monthly_metrics(
                st.session_state.bundle, month
            )
            path = save_report(company, month, st.session_state.excel_bytes, metrics)
            st.success(f"저장 완료: {path.name}")


def render_history_tab() -> None:
    st.header("저장된 리포트")
    st.caption("업체·월별 저장 목록입니다.")

    reports = list_reports()
    if not reports:
        st.info("저장된 리포트가 없습니다.")
        return

    companies = sorted({r["company_name"] for r in reports})
    selected = st.selectbox("업체 필터", ["전체"] + companies)
    filtered = reports if selected == "전체" else [r for r in reports if r["company_name"] == selected]

    labels = [f"{r['company_name']} · {r['report_month']}" for r in filtered]
    pick = st.selectbox("리포트 선택", labels, index=0 if labels else None)
    if not pick:
        return

    r = filtered[labels.index(pick)]
    summary = r.get("summary", {})
    cost = summary.get("광고비", summary.get("총 광고비", "-"))
    imp = summary.get("노출수", "-")
    if isinstance(cost, (int, float)) and isinstance(imp, (int, float)):
        st.caption(f"노출 {imp:,} | 광고비 {cost:,}원 | 저장 {r['updated_at'][:10]}")
    else:
        st.caption(f"저장 {r['updated_at'][:10]}")

    c1, c2 = st.columns(2)
    with c1:
        loaded = load_report_file(r["id"])
        if loaded:
            st.download_button(
                "다운로드",
                data=loaded[0],
                file_name=Path(r["file_path"]).name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"dl_{r['id']}",
                use_container_width=True,
            )
        else:
            st.error("파일 없음")
    with c2:
        if st.button("삭제", key=f"del_{r['id']}", use_container_width=True):
            delete_report(r["id"])
            st.rerun()


def render_guide_tab() -> None:
    st.header("사용 가이드")
    st.markdown(
        """
**1. 네이버에서 CSV 다운로드** — 키워드 효율 보고서를 집계 기준만 바꿔 각각 저장

| CSV | 1열 | 생성 시트 |
|-----|-----|-----------|
| 캠페인 | 캠페인 | 요약리포트 |
| 키워드 | 검색어 | 키워드별 · TOP10 |
| 일별·요일별 | 일별·요일별 | 일자별&요일별 |
| 주별 | 주별 | 주차별 |
| 지역 | 지역 | 지역별 |
| 성별·연령·기기 | 각각 | 성별&연령별&기기별 |

**2. CSV 업로드 → 리포트 생성 → 엑셀 다운로드**

**3. 전월 대비** — 매월 [업체·월별 저장] 후 다음 달 생성 시 자동 반영
        """
    )


def main() -> None:
    _inject_styles()
    init_session()
    require_login()

    with st.sidebar:
        st.title("네이버 광고 리포트")
        st.caption("키워드 효율 CSV → 엑셀 리포트")
        page = st.radio(
            "메뉴",
            ["리포트 생성", "저장된 리포트", "사용 가이드"],
            label_visibility="collapsed",
        )

    if page == "리포트 생성":
        render_upload_tab()
    elif page == "저장된 리포트":
        render_history_tab()
    else:
        render_guide_tab()


if __name__ == "__main__":
    main()
