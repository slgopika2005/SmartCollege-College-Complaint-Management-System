# 🏛️ Smart College Complaint Management System

A simple, robust, and reliable web-based campus grievance redressal portal built with **FastAPI** on the backend and modern vanilla **HTML, CSS, and JavaScript** on the frontend.

Designed specifically for educational institutions to provide students with a direct channel to lodge complaints and allow campus administrators to verify, assign, track, and update resolution statuses with official remarks.

---

## 🌟 Key Features

### 🎓 Student Portal
- **Registration & Authentication**: Students register with their Name, Roll Number / Student ID, College Department, Email, and Password.
- **Lodge Grievance**: Submit detailed complaints with:
  - Title & Category (*Hostel & Mess, Classrooms, Labs, Electrical/Wi-Fi, Water & Sanitation, Academics, Transport, etc.*)
  - Urgency / Priority (*Low, Medium, High, Urgent*)
  - Specific Location / Block / Room Number
  - Detailed issue description
- **Ticket Tracking**: Automatic sequential Ticket IDs (e.g., `CMP-2026-0001`).
- **Live Status & Official Remarks**: Track resolution stages (`Pending` → `Under Review` → `In Progress` → `Resolved` / `Rejected`) and read real-time remarks posted by verifying administrators.

### 🛡️ Administration Console
- **Backend-Only Admin Provisioning**: Admins **cannot** register through the public web signup API. Admin accounts are created strictly by the server administrator via backend CLI or automated initial seeding.
- **Grievance Verification**: Admins review incoming complaints across all campus departments.
- **Status Updates & Action Notes**: Admins can change status and append official remarks (e.g., technician dispatched, replacement parts ordered, resolution notes).
- **Search & Filter Suite**: Filter by Status, Category, Priority, or live search by Student Name, Roll No, or Ticket ID.
- **Dashboard Analytics**: Real-time counter metrics for Total Grievances, Pending, Under Review, In Progress, Resolved, and Rejected.

---

## 📁 Project Structure

```
foxtech mini project/
├── backend/
│   ├── __init__.py
│   ├── database.py         # SQLAlchemy engine, session maker & Base
│   ├── models.py           # User, Complaint, and AuthToken database models
│   ├── schemas.py          # Pydantic request & response schemas
│   ├── auth.py             # PBKDF2-HMAC password hashing & token security
│   └── main.py             # FastAPI app, API endpoints & static file serving
├── static/
│   ├── index.html          # Single-page application HTML interface
│   ├── css/
│   │   └── style.css       # Clean, modern, responsive CSS styling
│   └── js/
│       └── app.js          # Interactive UI routing, API client & modal dialogs
├── create_admin.py         # Backend CLI tool to create admin accounts
├── run.py                  # Server launcher with smart port detection
├── test_system.py          # Automated end-to-end integration test suite
├── requirements.txt        # Python dependency manifest
└── README.md               # Complete documentation
```

---

## 🚀 Quickstart Guide

### 1. Requirements
Ensure Python 3.10+ is installed on your machine.

Dependencies required:
```bash
pip install fastapi uvicorn sqlalchemy
```
*(No complex external C-extensions or conflicting packages required; standard library PBKDF2 cryptography and SQLite are used for 100% reliability).*

### 2. Start the Server
Run the launcher:
```bash
python run.py
```
Or specify a custom port:
```bash
python run.py --port 8000
```

Open your web browser and navigate to:
```
http://127.0.0.1:8000
```
Interactive Swagger API documentation is available at:
```
http://127.0.0.1:8000/docs
```

---

## 🔑 Default Administrator Credentials

On first run, the system automatically seeds a default administrator:
- **Email**: `admin@college.edu`
- **Password**: `admin123`

### Creating Additional Admin Accounts (Backend Only)
Admins **cannot** sign up through the website. To create a new admin, run the CLI utility in your terminal:

**Interactive mode:**
```bash
python create_admin.py
```
*Prompts for name, email, department, and secure password input.*

**Command line mode:**
```bash
python create_admin.py --name "Dr. Sharma" --email "sharma@college.edu" --password "securePass2026" --dept "Dean of Student Affairs"
```

---

## 🧪 Automated Testing

You can run the end-to-end integration test suite at any time to verify the complete workflow:
```bash
python test_system.py
```

The test checks:
1. Meta options retrieval
2. Student registration & JWT/Token issue
3. Complaint registration with ticket ID generation
4. Student complaint history retrieval
5. Security access verification (blocking students from administrative endpoints)
6. Admin authentication
7. Admin dashboard metric calculations
8. Admin status updates and note verification
9. Student real-time visibility into admin remarks
10. Final resolution verification

---

## 🛡️ Security & Reliability Highlights
- **Cryptographic Password Hashing**: Utilizes Python's `hashlib.pbkdf2_hmac` with SHA-256 and unique 16-byte random salts across 100,000 iterations to withstand rainbow-table and timing attacks (`hmac.compare_digest`).
- **Database Session Isolation**: Session tokens with expiration timestamps managed in SQLite.
- **Role-Based Authorization**: Strict FastAPI dependency guards (`get_current_admin` vs `get_current_user`).
- **Input Validation**: Pydantic models validate all incoming requests.
- **Port Conflict Handling**: `run.py` automatically detects if port 8000 is occupied and switches to 8001 or specified port without crashing.
