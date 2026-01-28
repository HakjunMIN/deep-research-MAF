"""
Security audit script for dependencies.
This script checks both Python and Node.js dependencies for known vulnerabilities.
It uses `pip-audit` for Python packages and `npm audit` for Node.js packages.

Usage:
    python security_audit.py

Requirements:
    - pip-audit must be installed in your Python environment
    - Node.js and npm must be installed for frontend audit
"""

import subprocess
import sys
from pathlib import Path

def run_command(command, cwd=None):
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=True)
        print(f"[SUCCESS] {' '.join(command)}\n{result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] {' '.join(command)}\n{e.stderr}")

def audit_python():
    print("\n=== Auditing Python Backend Dependencies ===")
    backend_path = Path(__file__).parent
    try:
        run_command([sys.executable, "-m", "pip_audit"], cwd=backend_path)
    except FileNotFoundError:
        print("pip-audit not found. Please install with: pip install pip-audit")

def audit_node():
    print("\n=== Auditing Node.js Frontend Dependencies ===")
    frontend_path = Path(__file__).parent.parent / "frontend"
    try:
        run_command(["npm", "audit"], cwd=frontend_path)
    except FileNotFoundError:
        print("npm not found. Please install Node.js and npm to audit frontend dependencies.")

def main():
    print("Starting security dependency audit...")
    audit_python()
    audit_node()
    print("\nSecurity audit completed.")

if __name__ == "__main__":
    main()
