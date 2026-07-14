@echo off
title EcoSort - Bishop Heber College
echo ==========================================================
echo       Bishop Heber College - EcoSort Startup Script
echo ==========================================================
echo.

:: Check if Python virtual environment exists
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment 'venv' not found!
    echo Please make sure you have Python installed and setup the 'venv' directory.
    pause
    exit /b
)

:: Start Flask Backend in a new command prompt window
echo [1/2] Starting Flask backend server on http://127.0.0.1:5000 ...
start "EcoSort Flask Backend" cmd /k "venv\Scripts\python.exe backend\app.py"

:: Wait for a few seconds to let Flask start up
timeout /t 3 /nobreak >nul

:: Open Frontend in the default browser using the local server URL
echo [2/2] Launching EcoSort Frontend on http://127.0.0.1:5000 ...
start "" "http://127.0.0.1:5000"

echo.
echo ==========================================================
echo EcoSort is now running! 
echo Keep the backend console window open while using the app.
echo ==========================================================
echo.
pause
