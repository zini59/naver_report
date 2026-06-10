"""네이버 검색광고 리포트 정리 도구 - 데이터 모델"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd


@dataclass
class ReportBundle:
    """업로드된 1차 파일들을 통합한 리포트 데이터."""

    keywords: pd.DataFrame = field(default_factory=pd.DataFrame)
    campaigns: pd.DataFrame = field(default_factory=pd.DataFrame)
    daily: pd.DataFrame = field(default_factory=pd.DataFrame)
    weekday: pd.DataFrame = field(default_factory=pd.DataFrame)
    weekly: pd.DataFrame = field(default_factory=pd.DataFrame)
    region: pd.DataFrame = field(default_factory=pd.DataFrame)
    region_detail: pd.DataFrame = field(default_factory=pd.DataFrame)
    gender: pd.DataFrame = field(default_factory=pd.DataFrame)
    age: pd.DataFrame = field(default_factory=pd.DataFrame)
    device: pd.DataFrame = field(default_factory=pd.DataFrame)

    period_start: date | None = None
    period_end: date | None = None
    account_id: str = ""
    source_files: list[str] = field(default_factory=list)

    @property
    def primary_df(self) -> pd.DataFrame:
        if not self.keywords.empty:
            return self.keywords
        if not self.daily.empty:
            return self.daily
        return self.campaigns

    def has_daily(self) -> bool:
        return not self.daily.empty

    def has_weekday(self) -> bool:
        return not self.weekday.empty

    def has_weekly(self) -> bool:
        return not self.weekly.empty

    def has_keywords(self) -> bool:
        return not self.keywords.empty

    def has_campaigns(self) -> bool:
        return not self.campaigns.empty

    def has_region(self) -> bool:
        return not self.region.empty or not self.region_detail.empty

    def has_demographic(self) -> bool:
        return not self.gender.empty or not self.age.empty or not self.device.empty

    def has_any_data(self) -> bool:
        return (
            self.has_keywords()
            or self.has_campaigns()
            or self.has_daily()
            or self.has_weekday()
            or self.has_weekly()
            or self.has_region()
            or self.has_demographic()
        )
