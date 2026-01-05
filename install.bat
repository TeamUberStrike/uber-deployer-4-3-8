@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0installWindowsComponents.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setupOpenSsh.ps1"

