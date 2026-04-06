@echo off
setlocal

powershell -ExecutionPolicy Bypass -File "%~dp0stop-ids-dev.ps1"
if errorlevel 1 (
  echo.
  echo IDS stop failed.
  pause
)
