from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    roll_number = Column(String(50), nullable=True, index=True)  # Populated for students
    department = Column(String(100), nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="student")  # 'student' or 'admin'
    created_at = Column(DateTime(timezone=True), default=utc_now)

    complaints = relationship("Complaint", back_populates="student", cascade="all, delete-orphan")
    tokens = relationship("AuthToken", back_populates="user", cascade="all, delete-orphan")

class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String(32), unique=True, index=True, nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)
    priority = Column(String(20), nullable=False, default="Medium")
    location = Column(String(150), nullable=True)
    description = Column(Text, nullable=False)
    status = Column(String(30), nullable=False, default="Pending")
    admin_remarks = Column(Text, nullable=True)
    verified_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    student = relationship("User", back_populates="complaints")

class AuthToken(Base):
    __tablename__ = "auth_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(64), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    user = relationship("User", back_populates="tokens")
