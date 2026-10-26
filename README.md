# SmartTravel — AI-Powered Train & Bus Ticket Booking System

A full-stack, database-backed, and AI-powered travel reservation web application built with **Python Flask**, **SQLite**, **Node.js/Express**, and **Google Gemini AI**.

Designed as a software engineering college project and live reservation prototype.

---

## 🌟 Key Highlights & System Features

### 1. Indian Railways & Intercity Bus Search Engine
- **Trains**: Full support for real railway classes:
  - **1A** (AC First Class — Private lockable coupe)
  - **2A** (AC 2-Tier — Curtains & bedroll)
  - **3A** (AC 3-Tier — Air conditioned 3-tier berths)
  - **3E** (AC 3 Economy)
  - **SL** (Sleeper Class — Non-AC open window)
  - **CC / EC** (AC Chair Car / Executive Chair Car for Vande Bharat & Shatabdi)
- **IRCTC Quotas**: General (GN), Tatkal (TQ), Ladies (LD), Senior Citizen (SS).
- **Buses**: Scania Luxury A/C Sleeper, Volvo Multi-Axle A/C Semi-Sleeper, Electric AC (EV), Non-AC Sleeper, Non-AC Seater.
- **Filters**: Real-time AC vs Non-AC toggle, departure time slots, price range slider, and class pills.

### 2. Interactive Coach & Deck Layouts
- **Trains**: Class-specific railway bay layouts (2-Tier LB/UB/SL/SU with no middle berth; 3-Tier LB/MB/UB/SL/SU; 1A Coupes).
- **Buses**: Interactive **Lower Deck** and **Upper Deck** switcher for sleeper coaches with single window berths and double companion bunks.

### 3. Google Gemini AI Integration
- **Floating AI Travel Assistant**: Interactive chatbot available across all pages answering train class differences, bus layouts, cancellation rules, and travel guidelines in **English & Hindi**.
- **AI Journey Recommendations** (`/api/ai/recommend`): Real-time analysis of routes and budget to highlight cheapest, fastest, and best value journeys.
- **AI Travel Planner** (`/api/ai/plan`): Customized multi-day itineraries, daily budget estimates, must-visit sights, and packing tips for any destination.

### 4. Direct Vector PDF E-Ticket Engine
- Native pure-Python PDF generator (`TrainBusBooking/pdf_generator.py`) producing official PDF 1.4 documents.
- Includes Indian Railways ERS / Bus Pass header, verified PNR, route timeline, coach and berth assignment, passenger details, itemized GST fare receipt, and digital boarding barcode.
- One-click direct PDF download (`/download-pdf/<pnr>`) and inline browser preview (`/view-pdf/<pnr>`).

### 5. Passenger Management & Meal Ordering
- Passenger details with Govt photo ID proof selection (Aadhaar, Voter ID, Passport, Driving Licence) and berth preferences.
- Optional onboard catering module (`/food`) with vegetarian thalis, chicken biryani, snack platters, and beverages.

### 6. Demo Payment Gateway
- Simulated UPI QR scanning, Credit/Debit card validation, Net Banking, and Viva/Demo counter confirmation with instant transaction reference generation.

### 7. My Bookings & Cancellation
- User booking dashboard with status filters (Upcoming, Completed, Cancelled).
- One-click cancellation releasing booked seats back to availability with demo refund calculation.

### 8. Operations Admin Portal (`/admin`)
- Operations dashboard displaying total bookings, revenue generated, fleet statistics, and registered users.
- Live vehicle fleet manager with add/delete schedule forms and real-time passenger lookup.

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | Semantic HTML5, CSS3, Vanilla JavaScript, Responsive Design |
| **Backend** | Python Flask, Jinja2 Templates, SQLite3, WSGI |
| **AI Engine** | Google Gemini AI (`gemini-3.8-flash`) via `@google/genai` SDK |
| **PDF Generation** | Custom Python Vector PDF Engine (`pdf_generator.py`) |
| **Server Bridge** | Node.js, Express, `http-proxy-middleware`, Vite |
| **Testing** | Pytest, Python `urllib` automated test harness |

---

## 🚀 Step-by-Step Installation & Local Execution

### Prerequisites
- **Python 3.10+**: [python.org](https://www.python.org/)
- **Node.js 18+**: [nodejs.org](https://nodejs.org/)

### 1. Clone or Extract Project
```bash
cd smarttravel
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
*(Optional: Add your Google Gemini API key to `GEMINI_API_KEY` for AI features)*

### 3. Install Node.js Dependencies
```bash
npm install
```

### 4. Initialize Database
```bash
python3 TrainBusBooking/database.py
```
*(On Windows: `python TrainBusBooking\database.py`)*

### 5. Start Development Server
```bash
npm run dev
```
Open **[http://localhost:3000](http://localhost:3000)** in your browser!

---

## 🔑 Demo Login Credentials

- **Admin Operations Console**:
  - URL: [http://localhost:3000/admin](http://localhost:3000/admin)
  - Email: `admin@smarttravel.com`
  - Password: `admin123`
- **Passenger Account**:
  - Email: `aditi@example.com`
  - Password: `user123`
  *(Or click "Register" on the top navigation bar to create your own account)*

---

## 📁 Project Directory Structure

```
smarttravel/
├── TrainBusBooking/               # Python Flask Web Application
│   ├── app.py                     # Main Flask routes & controllers
│   ├── database.py                # Database schema, migrations & seed data
│   ├── pdf_generator.py           # Native vector PDF ticket generator
│   ├── smarttravel.db             # SQLite relational database
│   ├── templates/                 # Jinja2 HTML5 UI templates
│   │   ├── home.html              # Search portal & popular routes
│   │   ├── search_results.html    # Train & bus cards with class selection
│   │   ├── booking.html           # Boarding point & class overview
│   │   ├── seat_selection.html    # Interactive railway coach & bus deck layouts
│   │   ├── passenger_details.html # Passenger form with berth preferences
│   │   ├── food.html              # Meals & catering selection
│   │   ├── payment.html           # Demo checkout (UPI, Card, NetBanking)
│   │   ├── ticket.html            # E-ticket with QR and PDF download
│   │   ├── bookings.html          # My Bookings & cancellation portal
│   │   ├── admin.html             # Operations administration console
│   │   └── admin_login.html       # Operations authentication
│   └── static/                    # Static assets & scripts
│       ├── style.css              # Master responsive stylesheet
│       └── js/                    # Client-side scripts (AI, seat, ticket)
├── server.ts                      # Full-stack Node/Express bridge & Gemini AI API
├── package.json                   # Node dependencies & build scripts
├── requirements.txt               # Python package dependencies
├── .env.example                   # Sample environment configuration
├── start.bat                      # Windows one-click start script
├── start.sh                       # Linux / macOS start script
└── README.md                      # Complete system documentation
```

---

## 🧪 Running Automated Tests

Run the backend verification suite:
```bash
pytest
```
Or run the endpoint integration test:
```bash
python3 -m unittest discover tests
```

---

## 📄 License & Credits
Developed for academic mini-project demonstration. Powered by **Google Gemini** for intelligent travel reasoning.
