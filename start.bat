@echo off
title SmartTravel - Train and Bus Ticket Booking System
echo ========================================================
echo   SmartTravel - AI-Powered Booking System
echo   Starting Backend & Web Server...
echo ========================================================

cd /d "%~dp0"

REM Check for Node.js
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is required to run the full-stack system.
    echo Please download and install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

REM Check for Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python 3.10+ is required to run Flask backend.
    echo Please install Python from https://python.org/
    pause
    exit /b 1
)

echo Initializing database...
python TrainBusBooking\database.py

echo Starting SmartTravel server on http://localhost:3000 ...
npm run dev

pause
