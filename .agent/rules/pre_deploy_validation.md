---
name: pre-deploy-validation
description: Mandatory pre-commit and pre-deploy integrity checks for CA Trader to eliminate syntax errors, diff residue, and mobile crashes.
---

# Pre-Commit & Pre-Deploy Validation Guardrails

Whenever modifying `terminal.html`, `app.py`, or any frontend/backend script in CA Trader:

### 1. Mandatory Pre-Commit Validation Gate
Never execute `git commit` or deploy to the server without running and passing these automated checks via:
```bash
python scripts/validate_integrity.py
```
This tool enforces:
1. **Python Compilation**:
   `python -m py_compile app.py backend/routers/*.py`
   Must exit with code 0 (no syntax or import syntax errors).
2. **JavaScript Syntax Verification**:
   Executes automated V8 evaluation across all 21 `<script>` tags in `terminal.html`.
   Must report `0 SyntaxErrors` (prevents duplicate declarations, diff residue, and aborted engines).
3. **CSS Balance Check**:
   Validates all `<style>` tags in `terminal.html` to verify 0 unclosed or malformed curly braces.
4. **Mobile Safety Constraints**:
   - Never set `canvas.width` or `canvas.height` unconditionally in high-frequency rendering loops. Only reassign dimensions when dimensions actually change.
   - Cap `devicePixelRatio` to `Math.min(2, window.devicePixelRatio || 1)` on mobile devices to prevent iOS WebKit memory exhaustion.
   - Never use `void el.offsetWidth;` (forced synchronous reflow) inside high-frequency WebSocket tick handlers. Use `requestAnimationFrame`.

### 2. Corporate IT Directive (Zero Outbound Laptop SSH)
- Strictly observe the corporate mandate on laptop `AMD-122024-0169`: **NEVER** run outbound SSH, SCP, or remote PowerShell scripts to `80.225.236.5` from this machine.
- All deployments are mediated via Git (`git push origin CA-Trader-Bifurcated`).

### 3. Failure Policy
If any verification step fails, immediately fix the underlying code and re-test. Never commit or push broken code to GitHub.
