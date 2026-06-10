@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo  네이버 광고 리포트 - 배포용 EXE 빌드
echo ========================================
echo.
echo 빌드에는 3~10분, 결과물 약 300MB 가량 소요됩니다.
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 필요합니다.
    pause
    exit /b 1
)

if not exist "venv\Scripts\python.exe" (
    python -m venv venv
)

echo [1/3] 패키지 설치...
venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller -q
if errorlevel 1 (
    echo [오류] 패키지 설치 실패
    pause
    exit /b 1
)

echo [2/3] EXE 빌드 중...
venv\Scripts\pyinstaller.exe build.spec --noconfirm
if errorlevel 1 (
    echo [오류] 빌드 실패
    pause
    exit /b 1
)

echo [3/3] 배포 폴더 정리...
set OUT=dist\네이버광고리포트_배포
if exist "%OUT%" rmdir /s /q "%OUT%"
mkdir "%OUT%"
xcopy /E /I /Y "dist\네이버광고리포트" "%OUT%"
copy /Y "배포용_사용설명.txt" "%OUT%\" >nul

echo.
echo ========================================
echo  빌드 완료!
echo  폴더: %OUT%
echo  실행: 네이버광고리포트.exe 더블클릭
echo ========================================
echo.
echo 이 폴더 전체를 USB/공유드라이브에 복사해 배포하세요.
pause
