@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo  네이버 검색광고 리포트 정리 도구
echo ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo https://www.python.org/downloads/ 에서 Python 3.10+ 설치 후 다시 실행하세요.
    echo 설치 시 "Add Python to PATH" 체크 필수!
    pause
    exit /b 1
)

if not exist "venv\Scripts\python.exe" (
    echo 가상환경 생성 중...
    python -m venv venv
    if errorlevel 1 (
        echo [오류] 가상환경 생성 실패
        pause
        exit /b 1
    )
)

echo 패키지 확인 중...
venv\Scripts\python.exe -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo [오류] 패키지 설치 실패
    pause
    exit /b 1
)

echo.
echo 앱 시작 확인 중...
venv\Scripts\python.exe -c "import app" 2>error.log
if errorlevel 1 (
    echo [오류] 앱 로드 실패. error.log 내용:
    type error.log
    pause
    exit /b 1
)

echo.
echo 서버 시작 중... 잠시 후 브라우저가 열립니다.
echo 이 창을 닫으면 앱이 종료됩니다. (종료: Ctrl+C)
echo 주소: http://localhost:8501
echo.

start /MIN cmd /c "timeout /t 4 /nobreak >nul & start http://localhost:8501"
venv\Scripts\python.exe -m streamlit run app.py --server.port 8501 --server.address 127.0.0.1

pause
