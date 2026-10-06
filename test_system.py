import json
import urllib.request
import urllib.error
import socket
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def detect_port():
    for p in [8001, 8000, 8080]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", p)) == 0:
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{p}/api/meta/options", timeout=1) as resp:
                        if resp.status == 200:
                            return p
                except Exception:
                    continue
    return 8001

PORT = detect_port()
BASE_URL = f"http://127.0.0.1:{PORT}"

def request_json(path, method="GET", data=None, token=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            return resp.status, json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        return e.code, json.loads(content) if content else {}

def run_tests():
    print(f"Connecting to test server at {BASE_URL}...")
    print(">>> 1. Testing Options & Static Index...")
    status, options = request_json("/api/meta/options")
    assert status == 200, f"Expected 200, got {status}"
    assert "categories" in options
    print("    [PASS] Meta options fetched successfully.")

    print(">>> 2. Testing Student Signup...")
    student_payload = {
        "name": "Aarav Sharma",
        "email": "aarav.sharma@college.edu",
        "roll_number": "2024CS042",
        "department": "Computer Science & Engineering",
        "password": "studentPassword123"
    }
    status, res = request_json("/api/auth/student-signup", method="POST", data=student_payload)
    if status == 400 and "already registered" in str(res):
        print("    [INFO] Student already registered, logging in...")
        status, res = request_json("/api/auth/login", method="POST", data={
            "email": student_payload["email"],
            "password": student_payload["password"]
        })
    assert status == 200, f"Signup/Login failed: {res}"
    student_token = res["token"]
    student_user = res["user"]
    assert student_user["role"] == "student"
    print(f"    [PASS] Student authenticated: {student_user['name']} (Role: {student_user['role']})")

    print(">>> 3. Testing Student Complaint Submission...")
    complaint_payload = {
        "title": "Wi-Fi access point dead in CS Lab 3",
        "category": "Electrical & Internet / Wi-Fi",
        "priority": "High",
        "location": "Science Block, 2nd Floor, CS Lab 3",
        "description": "The Cisco access point on the ceiling is blinking red and no student can connect to the intranet."
    }
    status, complaint = request_json("/api/complaints", method="POST", data=complaint_payload, token=student_token)
    assert status == 200, f"Failed to create complaint: {complaint}"
    ticket_id = complaint["ticket_id"]
    complaint_id = complaint["id"]
    assert complaint["status"] == "Pending"
    print(f"    [PASS] Complaint lodged: {ticket_id} (Status: {complaint['status']})")

    print(">>> 4. Testing Student Complaints List...")
    status, my_complaints = request_json("/api/complaints/my", token=student_token)
    assert status == 200
    assert any(c["id"] == complaint_id for c in my_complaints)
    print(f"    [PASS] Student retrieved their complaint list (Found {len(my_complaints)} complaints).")

    print(">>> 5. Security Test: Student Attempting Admin Endpoint...")
    status, forbidden_res = request_json("/api/admin/complaints", token=student_token)
    assert status == 403, f"Expected 403 Forbidden for student, got {status}"
    print("    [PASS] Security enforced: Student blocked with 403 Forbidden from admin endpoints.")

    print(">>> 6. Testing Admin Login with Backend Admin...")
    admin_login = {
        "email": "admin@college.edu",
        "password": "admin123"
    }
    status, admin_res = request_json("/api/auth/login", method="POST", data=admin_login)
    assert status == 200, f"Admin login failed: {admin_res}"
    admin_token = admin_res["token"]
    admin_user = admin_res["user"]
    assert admin_user["role"] == "admin"
    print(f"    [PASS] Admin authenticated: {admin_user['name']} (Role: {admin_user['role']})")

    print(">>> 7. Testing Admin Dashboard Stats...")
    status, stats = request_json("/api/admin/stats", token=admin_token)
    assert status == 200
    assert stats["total"] >= 1
    print(f"    [PASS] Admin stats: Total={stats['total']}, Pending={stats['pending']}, InProgress={stats['in_progress']}, Resolved={stats['resolved']}")

    print(">>> 8. Testing Admin Complaint Verification & Status Update...")
    update_payload = {
        "status": "In Progress",
        "admin_remarks": "IT network technician (Mr. Rajesh) has been dispatched with a replacement Cisco switch."
    }
    status, updated_complaint = request_json(
        f"/api/admin/complaints/{complaint_id}/status",
        method="PUT",
        data=update_payload,
        token=admin_token
    )
    assert status == 200
    assert updated_complaint["status"] == "In Progress"
    assert "Rajesh" in updated_complaint["admin_remarks"]
    print(f"    [PASS] Status updated to 'In Progress' with remarks: '{updated_complaint['admin_remarks']}'")

    print(">>> 9. Testing Student Seeing Admin Verification Remarks...")
    status, student_view = request_json(f"/api/complaints/{ticket_id}", token=student_token)
    assert status == 200
    assert student_view["status"] == "In Progress"
    assert student_view["admin_remarks"] == update_payload["admin_remarks"]
    print(f"    [PASS] Student can see real-time status '{student_view['status']}' and admin remarks!")

    print(">>> 10. Testing Admin Resolving the Complaint...")
    resolve_payload = {
        "status": "Resolved",
        "admin_remarks": "Network switch replaced and tested. Wi-Fi signal verified at 150 Mbps."
    }
    status, resolved = request_json(
        f"/api/admin/complaints/{complaint_id}/status",
        method="PUT",
        data=resolve_payload,
        token=admin_token
    )
    assert status == 200
    assert resolved["status"] == "Resolved"
    print(f"    [PASS] Grievance successfully marked 'Resolved' by admin!")

    print("\n========================================================")
    print("[SUCCESS] ALL 10 TESTS PASSED SUCCESSFULLY!")
    print("========================================================")

if __name__ == "__main__":
    run_tests()
