#!/usr/bin/env bash
# SmartTravel - Linux & macOS Startup Script
set -e

echo "========================================================"
echo "  SmartTravel - AI-Powered Booking System"
echo "  Starting Backend & Web Server..."
echo "========================================================"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Initialize SQLite database
python3 TrainBusBooking/database.py

# Start Node & Flask dev server
echo "Starting SmartTravel server on http://localhost:3000 ..."
npm run dev
