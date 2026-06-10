"""업체·월별 리포트 저장 및 조회"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from .config import DB_PATH, REPORTS_DIR


def _ensure_dirs():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _get_conn() -> sqlite3.Connection:
    _ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            report_month TEXT NOT NULL,
            file_path TEXT NOT NULL,
            summary_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(company_name, report_month)
        )
    """)
    conn.commit()
    return conn


def save_report(
    company_name: str,
    report_month: str,
    excel_bytes: bytes,
    summary: dict | None = None,
) -> Path:
    """업체·월별 리포트 저장 (덮어쓰기)."""
    _ensure_dirs()
    safe_company = "".join(c if c.isalnum() or c in "._-" else "_" for c in company_name.strip())
    safe_month = report_month.replace("/", "-")
    company_dir = REPORTS_DIR / safe_company
    company_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{safe_company}_{safe_month}_네이버광고리포트.xlsx"
    file_path = company_dir / filename
    file_path.write_bytes(excel_bytes)

    now = datetime.now().isoformat(timespec="seconds")
    summary_json = json.dumps(summary or {}, ensure_ascii=False)

    conn = _get_conn()
    conn.execute(
        """
        INSERT INTO reports (company_name, report_month, file_path, summary_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(company_name, report_month) DO UPDATE SET
            file_path = excluded.file_path,
            summary_json = excluded.summary_json,
            updated_at = excluded.updated_at
        """,
        (company_name.strip(), report_month, str(file_path), summary_json, now, now),
    )
    conn.commit()
    conn.close()
    return file_path


def list_companies() -> list[str]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT DISTINCT company_name FROM reports ORDER BY company_name"
    ).fetchall()
    conn.close()
    return [r["company_name"] for r in rows]


def list_reports(company_name: str | None = None) -> list[dict]:
    conn = _get_conn()
    if company_name:
        rows = conn.execute(
            """
            SELECT id, company_name, report_month, file_path, summary_json, created_at, updated_at
            FROM reports WHERE company_name = ?
            ORDER BY report_month DESC
            """,
            (company_name,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT id, company_name, report_month, file_path, summary_json, created_at, updated_at
            FROM reports ORDER BY company_name, report_month DESC
            """
        ).fetchall()
    conn.close()

    result = []
    for r in rows:
        item = dict(r)
        try:
            item["summary"] = json.loads(item.pop("summary_json") or "{}")
        except json.JSONDecodeError:
            item["summary"] = {}
        result.append(item)
    return result


def load_report_file(report_id: int) -> tuple[bytes, dict] | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    conn.close()
    if not row:
        return None

    path = Path(row["file_path"])
    if not path.exists():
        return None

    meta = dict(row)
    try:
        meta["summary"] = json.loads(meta.get("summary_json") or "{}")
    except json.JSONDecodeError:
        meta["summary"] = {}

    return path.read_bytes(), meta


def get_report_summary(company_name: str, report_month: str) -> dict | None:
    """특정 업체·월의 저장된 지표 조회."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT summary_json, report_month FROM reports WHERE company_name = ? AND report_month = ?",
        (company_name.strip(), report_month.strip()),
    ).fetchone()
    conn.close()
    if not row:
        return None
    try:
        return json.loads(row["summary_json"] or "{}")
    except json.JSONDecodeError:
        return None


def get_previous_month_summary(company_name: str, report_month: str) -> dict | None:
    """직전 월 저장 리포트 지표 (전월 대비용)."""
    from .metrics import previous_report_month

    prev_month = previous_report_month(report_month)
    summary = get_report_summary(company_name, prev_month)
    if summary:
        summary.setdefault("report_month", prev_month)
    return summary


def delete_report(report_id: int) -> bool:
    conn = _get_conn()
    row = conn.execute("SELECT file_path FROM reports WHERE id = ?", (report_id,)).fetchone()
    if not row:
        conn.close()
        return False

    path = Path(row["file_path"])
    conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))
    conn.commit()
    conn.close()

    if path.exists():
        path.unlink()
    return True
