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
    build_ad_group_report,
    build_campaign_report,
    build_daily_report_from_bundle,
    build_keyword_report,
    build_mom_comparison,
    build_region_report_from_bundle,
    build_summary_overview,
    build_summary_table,
    build_top_keyword_report,
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

st.set_page_config(
    page_title="네이버 검색광고 리포트 정리",
    page_icon="📊",
    layout="wide",
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
    """웹 URL 배포 시 비밀번호 보호 (APP_PASSWORD 설정된 경우만)."""
    expected = _expected_password()
    if not expected:
        return

    if st.session_state.get("authenticated"):
        return

    st.markdown('<p class="main-header">🔐 네이버 광고 리포트</p>', unsafe_allow_html=True)
    st.caption("접속 비밀번호를 입력하세요.")
    pwd = st.text_input("비밀번호", type="password", key="login_password")
    if st.button("로그인", type="primary"):
        if pwd == expected:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("비밀번호가 올바르지 않습니다.")
    st.stop()


st.markdown("""
<style>
    .main-header { font-size: 1.8rem; font-weight: 700; color: #1F4E79; margin-bottom: 0.2rem; }
    .sub-header { color: #666; margin-bottom: 1.5rem; }
    div[data-testid="stMetric"] { background: #f8fafc; padding: 0.8rem; border-radius: 8px; border: 1px solid #e2e8f0; }
</style>
""", unsafe_allow_html=True)


def init_session():
    defaults = {
        "bundle": None,
        "warnings": [],
        "excel_bytes": None,
        "company_name": "",
        "report_month": datetime.now().strftime("%Y-%m"),
        "previous_summary": None,
        "current_metrics": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def render_upload_tab():
    st.markdown('<p class="main-header">📁 1차 CSV 업로드 & 정리</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">네이버 검색광고 &gt; 보고서 &gt; <b>키워드 효율 보고서</b> CSV를 올리면 '
        '요약 · 키워드별 · TOP10 리포트가 자동 생성됩니다.</p>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        company = st.text_input("업체명", value=st.session_state.company_name, placeholder="예: 제스트")
    with col2:
        month = st.text_input("리포트 월", value=st.session_state.report_month, placeholder="2026-05")

    uploaded = st.file_uploader(
        "키워드 효율 보고서 CSV (여러 개 선택 가능)",
        type=["csv", "xlsx", "xls"],
        accept_multiple_files=True,
        help="캠페인 요약 CSV + 키워드 상세 CSV를 함께 업로드하세요",
    )

    st.caption("네이버 **키워드 효율 보고서** CSV를 집계 기준별로 다운받아 한 번에 업로드하세요 (캠페인·키워드·일별·요일·주별·지역·성별·연령·기기)")

    if st.button("🔄 리포트 생성", type="primary", use_container_width=False):
        if not uploaded:
            st.error("CSV 파일을 먼저 업로드해 주세요.")
            return
        if not company.strip():
            st.error("업체명을 입력해 주세요.")
            return

        with st.spinner("CSV 파일 분석 중..."):
            sources = [(f.name, f.getvalue()) for f in uploaded]
            bundle, warnings = merge_uploaded_files(sources)

            if not bundle.has_any_data():
                st.error("처리할 수 있는 데이터가 없습니다. 파일 형식을 확인해 주세요.")
                for w in warnings:
                    st.warning(w)
                return

            inferred = infer_report_month(bundle)
            report_month = month.strip() or inferred
            prev = get_previous_month_summary(company.strip(), report_month)
            cur_metrics = extract_monthly_metrics(bundle, report_month)
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

        if st.session_state.get("previous_summary"):
            prev_m = previous_report_month(st.session_state.report_month)
            st.caption(f"전월({prev_m}) 저장 데이터를 참고해 **전월대비** 시트를 생성했습니다.")
        else:
            prev_m = previous_report_month(st.session_state.report_month)
            st.caption(f"전월({prev_m}) 저장 기록이 없어 전월 대비는 생략됩니다. 이번 달 리포트를 **저장**하면 다음 달부터 자동 반영됩니다.")

        st.success(f"✅ {company} ({st.session_state.report_month}) 리포트 생성 완료!")

    if st.session_state.warnings:
        with st.expander("📋 파일 처리 결과", expanded=True):
            for w in st.session_state.warnings:
                if w.startswith("OK"):
                    st.success(w)
                elif w.startswith("ERR"):
                    st.error(w)
                else:
                    st.warning(w)

    bundle = st.session_state.bundle
    if bundle is not None and bundle.has_any_data():
        render_preview(bundle)
        render_download_and_save()


def render_preview(bundle: ReportBundle):
    st.divider()
    st.subheader("📈 미리보기")

    df = bundle.primary_df
    summary = build_summary_overview(df)
    m1, m2, m3, m4 = st.columns(4)
    total_row = {r["항목"]: r["값"] for _, r in summary.iterrows()}
    m1.metric("총 노출수", f"{int(total_row.get('총 노출수', 0)):,}")
    m2.metric("총 클릭수", f"{int(total_row.get('총 클릭수', 0)):,}")
    m3.metric("총 광고비", f"{int(total_row.get('총 광고비', 0)):,}원")
    m4.metric("평균 CPC", f"{int(total_row.get('평균 CPC', 0)):,}원")

    if bundle.period_start and bundle.period_end:
        st.caption(f"기간: {bundle.period_start} ~ {bundle.period_end} | 계정ID: {bundle.account_id or '-'}")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        ["요약", "일자별", "키워드별", "지역별", "요일/주차", "캠페인별"]
    )

    with tab1:
        st.dataframe(build_summary_table(bundle), use_container_width=True, hide_index=True)
        mom = build_mom_comparison(
            st.session_state.get("current_metrics") or extract_monthly_metrics(bundle, st.session_state.report_month),
            st.session_state.get("previous_summary"),
        )
        if not mom.empty:
            st.markdown("**전월 대비**")
            st.dataframe(mom, use_container_width=True, hide_index=True)
        elif st.session_state.get("report_month"):
            prev_m = previous_report_month(st.session_state.report_month)
            st.caption(f"전월({prev_m}) 저장 기록 없음 — 저장 후 다음달부터 전월 대비가 자동 생성됩니다.")
    with tab2:
        daily = build_daily_report_from_bundle(bundle)
        if daily.empty:
            st.info("일별 CSV를 업로드하면 표시됩니다.")
        else:
            st.dataframe(daily, use_container_width=True, hide_index=True)
    with tab3:
        st.dataframe(build_keyword_report(bundle.keywords), use_container_width=True, hide_index=True)
    with tab4:
        region = build_region_report_from_bundle(bundle, detail=True)
        if region.empty:
            st.info("지역/상세지역 CSV를 업로드하면 표시됩니다.")
        else:
            st.dataframe(region, use_container_width=True, hide_index=True)
    with tab5:
        c1, c2 = st.columns(2)
        with c1:
            st.caption("요일별")
            wd = build_weekday_report_from_bundle(bundle)
            st.dataframe(wd if not wd.empty else pd.DataFrame(), use_container_width=True, hide_index=True)
        with c2:
            st.caption("주차별")
            wk = build_weekly_report_from_bundle(bundle)
            st.dataframe(wk if not wk.empty else pd.DataFrame(), use_container_width=True, hide_index=True)
    with tab6:
        camp = build_campaign_report(bundle.primary_df)
        if camp.empty and bundle.has_campaigns():
            st.dataframe(build_summary_table(bundle), use_container_width=True, hide_index=True)
        elif camp.empty:
            st.info("캠페인 요약 CSV를 업로드하면 표시됩니다.")
        else:
            st.dataframe(camp, use_container_width=True, hide_index=True)


def render_download_and_save():
    st.divider()
    col1, col2 = st.columns(2)

    company = st.session_state.company_name
    month = st.session_state.report_month
    filename = f"{company}_{month}_네이버광고리포트.xlsx"

    with col1:
        st.download_button(
            label="📥 정리된 엑셀 다운로드",
            data=st.session_state.excel_bytes,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True,
        )

    with col2:
        if st.button("💾 업체·월별 저장", use_container_width=True):
            metrics = st.session_state.get("current_metrics") or extract_monthly_metrics(
                st.session_state.bundle, month
            )
            path = save_report(
                company,
                month,
                st.session_state.excel_bytes,
                metrics,
            )
            st.success(
                f"저장 완료: `{path.name}` — 다음달 리포트 생성 시 이번 달({month}) 데이터가 **전월 대비**에 사용됩니다."
            )


def render_history_tab():
    st.markdown('<p class="main-header">🗂️ 저장된 리포트</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">업체·월별로 저장한 리포트를 조회하고 다시 다운로드할 수 있습니다.</p>', unsafe_allow_html=True)

    reports = list_reports()
    if not reports:
        st.info("저장된 리포트가 없습니다. '리포트 생성' 탭에서 먼저 저장해 주세요.")
        return

    # 업체별 필터
    companies = sorted({r["company_name"] for r in reports})
    selected = st.selectbox("업체 선택", ["전체"] + companies)

    filtered = reports if selected == "전체" else [r for r in reports if r["company_name"] == selected]

    for r in filtered:
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 2, 1])
            with c1:
                st.markdown(f"**{r['company_name']}** · `{r['report_month']}`")
            with c2:
                summary = r.get("summary", {})
                cost = summary.get("광고비", summary.get("총 광고비", "-"))
                imp = summary.get("노출수", "-")
                st.caption(
                    f"노출: {imp:,} | 광고비: {cost:,}원"
                    if isinstance(cost, (int, float)) and isinstance(imp, (int, float))
                    else f"광고비: {cost}"
                )
                st.caption(f"저장: {r['updated_at'][:10]}")
            with c3:
                loaded = load_report_file(r["id"])
                if loaded:
                    data, _ = loaded
                    st.download_button(
                        "다운로드",
                        data=data,
                        file_name=Path(r["file_path"]).name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"dl_{r['id']}",
                    )
                if st.button("삭제", key=f"del_{r['id']}"):
                    delete_report(r["id"])
                    st.rerun()


def render_guide_tab():
    st.markdown('<p class="main-header">📖 사용 가이드</p>', unsafe_allow_html=True)

    st.markdown("""
    ### 1. 네이버에서 CSV 다운로드 (키워드 효율 보고서)
    같은 보고서를 **집계 기준**만 바꿔서 CSV로 각각 받습니다:

    | CSV 종류 | 1열(집계 기준) | 생성 시트 |
    |----------|----------------|-----------|
    | 캠페인 요약 | 캠페인 | 요약리포트 |
    | 키워드 상세 | 광고그룹·검색어 | 키워드별 · 상위 키워드 순위별 |
    | 일별 / 요일별 | 일별 · 요일별 | **일자별&요일별** (한 시트) |
    | 주별 | 주별 | 주차별 |
    | 지역 / 상세지역 | 지역 · 상세지역 | **지역별** (한 시트) |
    | 성별 / 연령 / 기기 | 성별 · 연령 · PC/모바일 | **성별&연령별&기기별** (한 시트) |

    **엑셀은 총 7개 시트** (요약리포트, 일자별&요일별, 주차별, 키워드별, 상위 키워드 순위별, 지역별, 성별&연령별&기기별)

    ### 2. 사용법
    - 위 CSV 파일들을 **한 번에** 업로드 → **리포트 생성**
    - 기간·계정ID는 CSV 1행에서 자동 인식
    """)


def main():
    init_session()
    require_login()

    st.sidebar.title("📊 네이버 광고 리포트")
    st.sidebar.caption("키워드 효율 CSV → 정리 리포트")
    page = st.sidebar.radio(
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
