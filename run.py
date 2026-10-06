#!/usr/bin/env python3
"""
Application Launcher for Smart College Complaint Management System
Runs FastAPI backend with Uvicorn server and serves the responsive HTML/CSS/JS frontend.
"""

import sys
import socket
import argparse
import uvicorn

# Ensure UTF-8 output encoding on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0

def get_best_port(preferred: int = 8000) -> int:
    if not is_port_in_use(preferred):
        return preferred
    for fallback in [8001, 8080, 5000, 8888]:
        if not is_port_in_use(fallback):
            return fallback
    return preferred

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Smart College Complaint System.")
    parser.add_argument("--port", type=int, default=None, help="Port to run server on")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface")
    args = parser.parse_args()

    port = args.port if args.port else get_best_port(8000)

    print("=" * 70)
    print("  [*] Starting Smart College Complaint Management System")
    print("=" * 70)
    print(f"  [+] Web Interface:      http://{args.host}:{port}")
    print(f"  [+] Interactive Docs:   http://{args.host}:{port}/docs")
    print("  [+] Default Admin:      admin@college.edu  /  admin123")
    print("  [+] Create Admin CLI:   python create_admin.py")
    print("=" * 70)
    print("Press CTRL+C to stop the server.\n")

    uvicorn.run("backend.main:app", host=args.host, port=port, reload=True)
