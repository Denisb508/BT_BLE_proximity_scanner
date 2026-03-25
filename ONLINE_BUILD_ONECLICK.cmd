@echo off
cd /d %~dp0
powershell -ExecutionPolicy Bypass -File "%~dp0prepare_online_oneclick.ps1"
pause
