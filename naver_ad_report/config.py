"""네이버 검색광고 리포트 정리 도구 설정"""

import sys
from pathlib import Path


def get_base_dir() -> Path:
    """개발/배포(EXE) 환경 모두에서 프로젝트 루트 반환."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = DATA_DIR / "reports"
DB_PATH = DATA_DIR / "reports.db"
# 네이버 검색광고 엑셀에서 자주 쓰이는 컬럼명 (다양한 내보내기 형식 대응)
COLUMN_ALIASES = {
    "date": [
        "일별", "일자", "날짜", "기간", "Date", "date", "노출일", "집계일",
    ],
    "campaign": [
        "캠페인", "캠페인명", "캠페인 이름", "Campaign", "campaign",
    ],
    "ad_group": [
        "광고그룹", "광고그룹명", "광고 그룹", "Ad group", "ad group", "그룹",
    ],
    "keyword": [
        "키워드", "검색어", "Keyword", "keyword",
    ],
    "search_type": [
        "검색 유형", "검색유형", "매치유형", "매치 유형",
    ],
    "impressions": [
        "노출수", "노출", "Impressions", "impressions", "Imp.",
    ],
    "clicks": [
        "클릭수", "클릭", "Clicks", "clicks",
    ],
    "ctr": [
        "클릭률", "CTR", "ctr", "클릭률(%)",
    ],
    "cpc": [
        "평균클릭비용", "CPC", "cpc", "평균 CPC", "평균 클릭비용",
    ],
    "cost": [
        "총비용", "비용", "광고비", "소진", "Cost", "cost", "총 비용", "광고비(VAT포함)",
    ],
    "conversions": [
        "전환수", "전환", "Conversions", "conversions",
    ],
    "conversion_rate": [
        "전환율", "전환율(%)", "Conversion rate",
    ],
    "conversion_cost": [
        "전환당비용", "CPA", "전환 비용",
    ],
}

KOREAN_WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]
