@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist logs mkdir logs
echo 30초 수급 대시보드 실행 중... 이 창을 닫으면 수집이 멈춥니다.
echo 이 PC에서:  http://localhost:8501
echo 휴대폰에서(Tailscale): http://%COMPUTERNAME%:8501
.venv\Scripts\python -m uvicorn live_flow.app:app --host 0.0.0.0 --port 8501 >> logs\live_flow.log 2>&1
