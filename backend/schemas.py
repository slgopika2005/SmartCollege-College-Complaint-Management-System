from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

# Auth schemas
class StudentSignupRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=5, max_length=120)
    roll_number: str = Field(..., min_length=2, max_length=50)
    department: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)

class LoginRequest(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    roll_number: Optional[str] = None
    department: Optional[str] = None
    role: str
    created_at: datetime

    class Config:
        from_attributes = True

class AuthResponse(BaseModel):
    token: str
    user: UserResponse
    message: str

# Complaint schemas
class ComplaintCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    category: str = Field(..., min_length=2, max_length=100)
    priority: str = Field(default="Medium")
    location: Optional[str] = Field(default="", max_length=150)
    description: str = Field(..., min_length=5)

class ComplaintStatusUpdateRequest(BaseModel):
    status: str = Field(..., pattern="^(Pending|Under Review|In Progress|Resolved|Rejected)$")
    admin_remarks: Optional[str] = Field(default="")

class ComplaintResponse(BaseModel):
    id: int
    ticket_id: str
    student_id: int
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    student_roll: Optional[str] = None
    student_dept: Optional[str] = None
    title: str
    category: str
    priority: str
    location: Optional[str] = None
    description: str
    status: str
    admin_remarks: Optional[str] = None
    verified_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AdminStatsResponse(BaseModel):
    total: int
    pending: int
    under_review: int
    in_progress: int
    resolved: int
    rejected: int
