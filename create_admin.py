#!/usr/bin/env python3
"""
Backend Administrative User Creation Tool
Allows server administrators to create or update administrator accounts directly from the backend.
Admins CANNOT register through the public student signup endpoint.
"""

import sys
import argparse
import getpass
from backend.database import SessionLocal, engine, Base
from backend.models import User
from backend.auth import hash_password

def create_or_update_admin(name: str, email: str, password: str, department: str = "College Administration"):
    # Ensure database tables exist
    Base.metadata.create_all(bind=engine)

    email = email.strip().lower()
    name = name.strip()
    department = department.strip()

    if not name or not email or not password:
        print("[ERROR] Name, email, and password cannot be empty.")
        return False

    if len(password) < 6:
        print("[ERROR] Password must be at least 6 characters long.")
        return False

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        hashed = hash_password(password)

        if user:
            print(f"[INFO] User with email '{email}' already exists. Updating to Administrator role & updating password...")
            user.name = name
            user.department = department
            user.role = "admin"
            user.password_hash = hashed
            db.commit()
            print(f"[SUCCESS] Admin account '{email}' updated successfully.")
        else:
            new_admin = User(
                name=name,
                email=email,
                department=department,
                role="admin",
                password_hash=hashed
            )
            db.add(new_admin)
            db.commit()
            print(f"[SUCCESS] New Administrator created successfully!")
            print(f"  - Name: {name}")
            print(f"  - Email: {email}")
            print(f"  - Role: admin")
            print(f"  - Department: {department}")
        return True
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to create admin: {e}")
        return False
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(description="Create a College Complaint System Admin user from backend.")
    parser.add_argument("--name", help="Admin Full Name")
    parser.add_argument("--email", help="Admin Email Address")
    parser.add_argument("--password", help="Admin Password")
    parser.add_argument("--dept", help="Department (default: College Administration)", default="College Administration")

    args = parser.parse_args()

    if args.name and args.email and args.password:
        success = create_or_update_admin(args.name, args.email, args.password, args.dept)
        sys.exit(0 if success else 1)

    print("=" * 60)
    print("  Smart College Complaint System - Backend Admin Creator")
    print("=" * 60)
    print("This utility creates an administrative account with full complaint verification access.")
    print("Admins cannot be created via the public student registration API.\n")

    name = input("Enter Admin Full Name (e.g. Dean of Student Affairs): ").strip()
    email = input("Enter Admin Email (e.g. admin@college.edu): ").strip()
    dept = input("Enter Department [default: College Administration]: ").strip()
    if not dept:
        dept = "College Administration"
    
    password = getpass.getpass("Enter Admin Password (min 6 characters): ")
    confirm_password = getpass.getpass("Confirm Admin Password: ")

    if password != confirm_password:
        print("[ERROR] Passwords do not match. Aborting.")
        sys.exit(1)

    success = create_or_update_admin(name, email, password, dept)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
