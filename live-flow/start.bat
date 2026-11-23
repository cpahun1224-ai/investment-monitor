@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo [오류] 설치가 안 되어 있습니다. setup.bat 을 먼저 실행하세요.
  pause
  exit /b 1
)
if not exist .env (
  echo [오류] .env 파일이 없습니다. setup.bat 을 다시 실행하세요.
  pause
  exit /b 1
)
echo 30초 수급 대시보드 실행 중... 이 창을 닫으면 수집이 멈춥니다.
echo 이 PC에서:  http://localhost:8501
echo 휴대폰에서(Tailscale): http://%COMPUTERNAME%:8501
echo.
.venv\Scripts\python -m uvicorn live_flow.app:app --host 0.0.0.0 --port 8501
echo.
echo [멈춤] 서버가 종료되었습니다. 위 메시지를 캡처해서 경자에게 보내 주세요.
pause
