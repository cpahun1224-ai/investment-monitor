@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo [1/3] 파이썬 가상환경 만들기...
set PY=python
where python >nul 2>nul || set PY=py
if "%PY%"=="py" (where py >nul 2>nul || set PY="%USERPROFILE%\anaconda3\python.exe")
if not exist .venv (%PY% -m venv .venv || goto :err)
echo [2/3] 필요한 패키지 설치...
call .venv\Scripts\python -m pip install --upgrade pip >nul
call .venv\Scripts\python -m pip install -r requirements.txt || goto :err
echo [3/3] 설정 파일 준비...
if not exist .env (copy .env.example .env >nul & notepad .env)
echo.
echo 설치 완료. start.bat 을 더블클릭하면 대시보드가 켜집니다.
pause
exit /b 0
:err
echo 설치 중 오류가 났습니다. 이 창을 캡처해서 경자에게 보내 주세요.
pause
exit /b 1
