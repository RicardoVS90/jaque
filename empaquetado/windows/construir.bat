@echo off
chcp 65001 >nul
title Construir Jaque para Windows
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0construir.ps1" -Iso "%~1"
echo.
pause
