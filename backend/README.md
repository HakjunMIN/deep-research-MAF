
# Backend Security Audit Instructions

This backend includes a **security audit** script to check for vulnerabilities in both Python and Node.js dependencies.

## Usage

Run the security audit:
```bash
python security_audit.py
```

### Python Dependency Audit
The script uses **pip-audit** to check Python dependencies for known vulnerabilities.
If you don’t have it installed, run:
```bash
pip install pip-audit
```

### Node.js Dependency Audit
The script runs `npm audit` to check for vulnerabilities in frontend dependencies.
Ensure **Node.js** and **npm** are installed:
```bash
npm install
npm audit
```

## CI/CD Integration
You can integrate this audit into CI/CD by adding a job step to run the audit automatically on every push.

Example (GitHub Actions):
```yaml
name: Security Audit
on: [push]
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: pip install pip-audit
      - name: Run backend security audit
        run: python backend/security_audit.py
```
