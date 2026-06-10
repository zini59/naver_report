"""배포용 실행 진입점 (PyInstaller EXE)"""

from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path


def get_exe_dir() -> Path:
    """EXE가 있는 폴더 (data 저장 위치)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def get_bundle_dir() -> Path:
    """app.py 등 번들 리소스 폴더."""
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS)
        for candidate in (
            get_exe_dir() / "_internal",
            get_exe_dir() / "네이버광고리포트" / "_internal",
        ):
            if (candidate / "app.py").exists():
                return candidate
    return get_exe_dir()


def main() -> None:
    exe_dir = get_exe_dir()
    bundle_dir = get_bundle_dir()

    os.chdir(bundle_dir)
    if str(bundle_dir) not in sys.path:
        sys.path.insert(0, str(bundle_dir))

    (exe_dir / "data" / "reports").mkdir(parents=True, exist_ok=True)

    app_py = bundle_dir / "app.py"
    if not app_py.exists():
        print(f"[오류] app.py를 찾을 수 없습니다: {app_py}")
        input("Enter 키를 누르면 종료...")
        sys.exit(1)

    def _open_browser():
        time.sleep(2.5)
        webbrowser.open("http://127.0.0.1:8501")

    threading.Thread(target=_open_browser, daemon=True).start()

    sys.argv = [
        "streamlit",
        "run",
        str(app_py),
        "--server.port=8501",
        "--server.address=127.0.0.1",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--global.developmentMode=false",
    ]

    from streamlit.web import cli as stcli

    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
