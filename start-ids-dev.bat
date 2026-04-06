@echo off
setlocal

powershell -ExecutionPolicy Bypass -File "%~dp0start-ids-dev.ps1"
if errorlevel 1 (
  echo.
  echo IDS quick start failed.
  pause
)
