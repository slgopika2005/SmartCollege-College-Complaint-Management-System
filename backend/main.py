import os
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from backend.database import engine, Base, get_db
from backend.models import User, Complaint, AuthToken
from backend.schemas import (
    StudentSignupRequest,
    LoginRequest,
    UserResponse,
    AuthResponse,
    ComplaintCreateRequest,
    ComplaintStatusUpdateRequest,
    ComplaintResponse,
    AdminStatsResponse
)
from backend.auth import (
    hash_password,
    verify_password,
    create_access_token,
    revoke_token,
    get_token_from_header,
    get_current_user,
    get_current_admin
)

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Smart College Complaint Management System",
    description="Backend API for student complaint registration and administrative verification",
    version="1.0.0"
)

# Enable CORS for local testing and flexible frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CATEGORIES = [
    "Hostel & Mess",
    "Classrooms & Infrastructure",
    "Laboratories & Equipment",
    "Electrical & Internet / Wi-Fi",
    "Water, Sanitation & Cleanliness",
    "Library & Academics",
    "Campus Transport & Parking",
    "Canteen & Cafeteria",
    "Discipline & Campus Safety",
    "Other Campus Issues"
]

PRIORITIES = ["Low", "Medium", "High", "Urgent"]
VALID_STATUSES = ["Pending", "Under Review", "In Progress", "Resolved", "Rejected"]

def seed_default_admin():
    """Ensure at least one administrator account exists upon initial startup."""
    from backend.database import SessionLocal
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.role == "admin").first()
        if not admin:
            default_admin = User(
                name="College Administrator",
                email="admin@college.edu",
                department="Central Administration",
                role="admin",
                password_hash=hash_password("admin123")
            )
            db.add(default_admin)
            db.commit()
            print("=" * 60)
            print("[INFO] Default Administrator created:")
            print("  Email:    admin@college.edu")
            print("  Password: admin123")
            print("  Note: You can create more admins using: python create_admin.py")
            print("=" * 60)
    finally:
        db.close()

# Run admin seed on startup
seed_default_admin()

def complaint_to_response(complaint: Complaint) -> dict:
    """Helper to format a Complaint with student details."""
    student = complaint.student
    return {
        "id": complaint.id,
        "ticket_id": complaint.ticket_id,
        "student_id": complaint.student_id,
        "student_name": student.name if student else "Unknown",
        "student_email": student.email if student else "Unknown",
        "student_roll": student.roll_number if student else "N/A",
        "student_dept": student.department if student else "N/A",
        "title": complaint.title,
        "category": complaint.category,
        "priority": complaint.priority,
        "location": complaint.location or "",
        "description": complaint.description,
        "status": complaint.status,
        "admin_remarks": complaint.admin_remarks or "",
        "verified_by": complaint.verified_by or "",
        "created_at": complaint.created_at,
        "updated_at": complaint.updated_at
    }

# ==========================================
# Authentication Endpoints
# ==========================================

@app.post("/api/auth/student-signup", response_model=AuthResponse)
def student_signup(payload: StudentSignupRequest, db: Session = Depends(get_db)):
    """
    Public student signup endpoint.
    Strictly forces role to 'student'. Admin accounts can ONLY be created via backend CLI.
    """
    email = payload.email.strip().lower()
    roll_number = payload.roll_number.strip().upper()

    # Check for duplicate email
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address is already registered."
        )

    # Check for duplicate roll number
    if db.query(User).filter(User.roll_number == roll_number).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Roll Number '{roll_number}' is already registered."
        )

    # Create new student user
    student = User(
        name=payload.name.strip(),
        email=email,
        roll_number=roll_number,
        department=payload.department.strip(),
        role="student",  # Guaranteed student role
        password_hash=hash_password(payload.password)
    )
    db.add(student)
    db.commit()
    db.refresh(student)

    # Generate session token immediately for smooth onboarding
    token = create_access_token(db, student.id)

    return {
        "token": token,
        "user": student,
        "message": "Student account registered successfully!"
    }

@app.post("/api/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate both students and admins via email and password."""
    email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please verify your credentials."
        )

    token = create_access_token(db, user.id)
    return {
        "token": token,
        "user": user,
        "message": f"Welcome back, {user.name}!"
    }

@app.get("/api/auth/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get profile of the currently logged-in user."""
    return current_user

@app.post("/api/auth/logout")
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db), req_token: Optional[str] = Depends(get_token_from_header)):
    """Log out current user by invalidating the token."""
    if req_token:
        revoke_token(db, req_token)
    return {"message": "Logged out successfully."}

@app.get("/api/meta/options")
def get_complaint_options():
    """Returns available categories and priority choices for complaint forms."""
    return {
        "categories": CATEGORIES,
        "priorities": PRIORITIES,
        "statuses": VALID_STATUSES
    }

# ==========================================
# Student Complaint Endpoints
# ==========================================

@app.post("/api/complaints", response_model=ComplaintResponse)
def create_complaint(
    payload: ComplaintCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Register a new complaint for the logged-in student."""
    # Generate unique ticket ID: CMP-<current_year>-<sequential_id>
    current_year = datetime.now().year
    complaint_count = db.query(Complaint).count() + 1
    ticket_id = f"CMP-{current_year}-{complaint_count:04d}"

    # Ensure uniqueness in case of deletes
    while db.query(Complaint).filter(Complaint.ticket_id == ticket_id).first():
        complaint_count += 1
        ticket_id = f"CMP-{current_year}-{complaint_count:04d}"

    priority = payload.priority if payload.priority in PRIORITIES else "Medium"

    complaint = Complaint(
        ticket_id=ticket_id,
        student_id=current_user.id,
        title=payload.title.strip(),
        category=payload.category.strip(),
        priority=priority,
        location=payload.location.strip() if payload.location else "",
        description=payload.description.strip(),
        status="Pending",
        admin_remarks="",
        verified_by=""
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    return complaint_to_response(complaint)

@app.get("/api/complaints/my", response_model=List[ComplaintResponse])
def get_my_complaints(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve all complaints submitted by the logged-in student."""
    query = db.query(Complaint).filter(Complaint.student_id == current_user.id)
    if status_filter and status_filter != "All":
        query = query.filter(Complaint.status == status_filter)

    complaints = query.order_by(desc(Complaint.created_at)).all()
    return [complaint_to_response(c) for c in complaints]

@app.get("/api/complaints/{ticket_or_id}", response_model=ComplaintResponse)
def get_complaint_details(
    ticket_or_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """View details of a specific complaint. Students can only view their own."""
    query = db.query(Complaint)
    if ticket_or_id.isdigit():
        complaint = query.filter(Complaint.id == int(ticket_or_id)).first()
    else:
        complaint = query.filter(Complaint.ticket_id == ticket_or_id).first()

    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    # Access control: students can only see their own tickets
    if current_user.role != "admin" and complaint.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to view this complaint.")

    return complaint_to_response(complaint)

# ==========================================
# Admin Management Endpoints
# ==========================================

@app.get("/api/admin/stats", response_model=AdminStatsResponse)
def get_admin_dashboard_stats(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Provide high-level metrics for the administrator dashboard."""
    total = db.query(Complaint).count()
    pending = db.query(Complaint).filter(Complaint.status == "Pending").count()
    under_review = db.query(Complaint).filter(Complaint.status == "Under Review").count()
    in_progress = db.query(Complaint).filter(Complaint.status == "In Progress").count()
    resolved = db.query(Complaint).filter(Complaint.status == "Resolved").count()
    rejected = db.query(Complaint).filter(Complaint.status == "Rejected").count()

    return {
        "total": total,
        "pending": pending,
        "under_review": under_review,
        "in_progress": in_progress,
        "resolved": resolved,
        "rejected": rejected
    }

@app.get("/api/admin/complaints", response_model=List[ComplaintResponse])
def get_all_complaints_for_admin(
    status_filter: Optional[str] = Query(None, alias="status"),
    category_filter: Optional[str] = Query(None, alias="category"),
    priority_filter: Optional[str] = Query(None, alias="priority"),
    search: Optional[str] = Query(None, alias="search"),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Administrator endpoint: View and filter all complaints submitted across the institution.
    """
    query = db.query(Complaint).join(User, Complaint.student_id == User.id)

    if status_filter and status_filter != "All":
        query = query.filter(Complaint.status == status_filter)

    if category_filter and category_filter != "All":
        query = query.filter(Complaint.category == category_filter)

    if priority_filter and priority_filter != "All":
        query = query.filter(Complaint.priority == priority_filter)

    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Complaint.ticket_id.ilike(search_term),
                Complaint.title.ilike(search_term),
                Complaint.location.ilike(search_term),
                User.name.ilike(search_term),
                User.roll_number.ilike(search_term),
                User.email.ilike(search_term),
                User.department.ilike(search_term)
            )
        )

    complaints = query.order_by(desc(Complaint.created_at)).all()
    return [complaint_to_response(c) for c in complaints]

@app.put("/api/admin/complaints/{complaint_id}/status", response_model=ComplaintResponse)
def update_complaint_status(
    complaint_id: int,
    payload: ComplaintStatusUpdateRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Administrator endpoint: Verify complaint, update resolution status, and add official admin remarks.
    """
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    complaint.status = payload.status
    if payload.admin_remarks is not None:
        complaint.admin_remarks = payload.admin_remarks.strip()
    complaint.verified_by = admin.name
    complaint.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(complaint)

    return complaint_to_response(complaint)

@app.delete("/api/admin/complaints/{complaint_id}")
def delete_complaint_as_admin(
    complaint_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Administrator endpoint: Delete a complaint."""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    db.delete(complaint)
    db.commit()
    return {"message": f"Complaint {complaint.ticket_id} deleted successfully."}

# ==========================================
# Static Files & Frontend Mounting
# ==========================================

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def serve_frontend_index():
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
