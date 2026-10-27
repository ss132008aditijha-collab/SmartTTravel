# 🚆 SmartTravel — Train & Bus Ticket Booking System

A full-stack, unified train and bus ticket reservation platform developed for a 5th-semester college mini-project. Engineered with Python Flask, SQLite, vanilla HTML5, CSS3, and modern JavaScript.

---

## 🌟 Key Highlights & Fixes

- **100% Demo & Offline Ready:** Requires zero external transit API keys or payment gateway secrets. Uses a realistic, pre-seeded SQLite database catalog.
- **Dynamic Class Configuration:** Train #20608 (Vande Bharat Express) strictly supports only **CC (AC Chair Car — ₹890)** and **EC (Executive Chair Car — ₹1650)** with no hardcoded fallback.
- **End-to-End Booking Flow:** Search ➔ Vehicle & Class Selection ➔ Interactive Seat Picker ➔ Passenger Details ➔ Meal Ordering ➔ Simulated Demo Checkout ➔ Confirmed Digital E-Ticket.
- **Zero-Dependency Vector PDF Generation:** Generates valid, downloadable PDF 1.4 electronic tickets natively without external C-libraries (WeasyPrint/Cairo).
- **Session & Password Security:** Unified password verification supporting both modern `pbkdf2`/`scrypt` hashes and legacy demo credentials with seamless auto-upgrading.
- **Duplicate Seat Prevention:** Real-time concurrency protection preventing double-booking of any seat on the same train/bus and journey date.
- **SmartTravel AI Assistant:** Built-in offline travel assistant answering questions about train coach classes, quotas, meal add-ons, and cancellation policies without requiring an external Gemini key.
- **Admin Operations Console:** Dedicated management dashboard at `/admin` for tracking confirmed reservations, revenue statistics, and fleet management.

---

## 🚀 Quick Start on Windows (VS Code)

### Prerequisites
- Python 3.10+ installed on Windows (ensure **"Add Python to PATH"** was checked during installation).
- Visual Studio Code.

### Step 1: Open in VS Code
Open the extracted `SmartTravel` project directory in VS Code:
```bash
code .
```

### Step 2: Open Terminal
Press `Ctrl + ~` (or select **Terminal ➔ New Terminal** from the top menu).

### Step 3: (Recommended) Create Virtual Environment
```powershell
python -m venv venv
venv\Scripts\activate
```

### Step 4: Install Dependencies
```bash
pip install -r TrainBusBooking/requirements.txt
```

### Step 5: Launch SmartTravel
Run either command directly from the workspace root:
```bash
python app.py
```
*(Or `python run.py`, or `cd TrainBusBooking && python app.py`)*

### Step 6: Open the Application
Open your web browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 🔑 Demo Accounts

| Role | Email | Password | Access Area |
|---|---|---|---|
| **Passenger User** | `aditi123@gmail.com` | `123456` | Public booking, seat picker, My Bookings, ticket cancellation |
| **Passenger User** | `diya1234@gmail.com` | `123456` | Public booking, My Bookings |
| **Administrator** | `admin@smarttravel.com` | `admin123` | `/admin` operations console, fleet management, revenue stats |

*Guest checkout is also fully supported: guest bookings are automatically linked to registered user accounts using the passenger's email address.*

---

## 🧪 Running Automated Tests

Execute the comprehensive automated test suite covering all 15 critical booking and security flows:
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

### Test Coverage Checklist:
1. `test_01_homepage_and_static_assets`: Verified home rendering, search widgets, CSS and JS static assets.
2. `test_02_train_and_bus_searches`: Verified search results for trains and buses on Bengaluru ➔ Chennai.
3. `test_03_no_results_search`: Verified clean empty search state when route has no services.
4. `test_04_registration_and_login`: Verified registration, login session, and invalid credential rejections.
5. `test_05_train_class_selection`: Verified Vande Bharat #20608 strictly restricts to CC and EC classes.
6. `test_06_seat_selection_and_booked_seats`: Verified interactive seat layout and unavailable seat mapping.
7. `test_07_passenger_details_and_food`: Verified passenger forms and server-side food pricing catalog.
8. `test_08_payment_page_calculations`: Verified server-calculated ticket fare, food total, and grand total.
9. `test_09_complete_demo_booking`: Verified end-to-end booking execution, database write, and E-ticket redirect.
10. `test_10_duplicate_seat_prevention`: Verified that booking an already reserved seat on the same date fails with HTTP 400.
11. `test_11_e_ticket_and_pdf`: Verified ticket view and binary vector PDF download stream (`application/pdf`).
12. `test_12_my_bookings_dashboard`: Verified user booking history listing under `/bookings`.
13. `test_13_cancellation`: Verified cancellation modal, status update to `CANCELLED`, and payment to `REFUNDED`.
14. `test_14_admin_dashboard`: Verified admin access control, unauthorized redirects, and dashboard metrics.
15. `test_15_invalid_input_handling`: Verified 404 on missing bookings and offline AI assistant fallback.

---

## 📂 Project Architecture

```
SmartTravel/
├── app.py                      # Root launcher for single-command start in VS Code
├── run.py                      # Alternative direct launcher
├── README.md                   # This documentation guide
├── tests/
│   ├── test_smarttravel_suite.py # 15-point automated test suite
│   ├── test_vande_bharat_and_fixes.py
│   └── server.test.ts
└── TrainBusBooking/
    ├── app.py                  # Core Flask backend with all booking and AI routes
    ├── database.py             # SQLite schema creation and demo fleet seeder
    ├── demo_service.py         # Dynamic fare engine and route validation
    ├── pdf_generator.py        # Standalone vector PDF ticket generation engine
    ├── requirements.txt        # Python dependency manifest
    ├── smarttravel.db          # SQLite persistent database
    ├── static/
    │   ├── style.css           # Responsive UI stylesheet
    │   └── js/
    │       ├── main.js         # Navigation, mobile menu & shared utilities
    │       ├── search.js       # Auto-complete & search form validation
    │       ├── filters.js      # Transit class & departure time filters
    │       ├── seat-selection.js # Interactive seat/berth layout picker
    │       ├── bookings.js     # Dashboard filter tabs & cancellation modal
    │       └── ai-assistant.js # AI travel assistant floating widget
    └── templates/
        ├── home.html           # Main portal with Train / Bus search tabs
        ├── search_results.html # Service listing with live/demo indicators
        ├── booking.html        # Dynamic train/bus class selection overview
        ├── seat_selection.html # Interactive seat picker for coaches & decks
        ├── passenger_details.html # Passenger details & quota capture
        ├── food.html           # E-catering pre-ordering menu
        ├── payment.html        # Simulated checkout (UPI / Card / Net Banking)
        ├── ticket.html         # Digital boarding slip with QR & PDF download
        ├── bookings.html       # Passenger booking history & cancellation
        ├── login.html          # User authentication portal
        ├── register.html       # User account creation
        ├── forgot_password.html # Password recovery request
        ├── reset_password.html  # Secure password reset
        ├── admin_login.html    # Operator security login
        └── admin.html          # Operations control panel & fleet manager
```

---

## 🔒 Security & Academic Integrity Note

This is an academic college mini-project demonstration system:
- Payment methods (UPI, Card, Net Banking) are fully simulated—no actual money or banking credentials are ever processed.
- Tickets generated are simulated demonstration reservation slips and are not valid for official travel on Indian Railways or state bus transport corporations.
