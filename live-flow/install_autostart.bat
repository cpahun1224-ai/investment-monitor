@echo off
chcp 65001 >nul
cd /d "%~dp0"
schtasks /create /tn "live-flow-dashboard" /tr "\"%~dp0start.bat\"" /sc onlogon /rl limited /f
if errorlevel 1 (echo 자동 시작 등록 실패 & pause & exit /b 1)
echo Windows 로그인할 때마다 대시보드가 자동으로 켜집니다.
echo 해제하려면: schtasks /delete /tn "live-flow-dashboard" /f
pause
