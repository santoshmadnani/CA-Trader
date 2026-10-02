# Repository-First Memory & Token Optimization Rule

## 1. Zero External Laptop Storage
- All agent definitions, skills, memory notes, and tools must reside strictly within `c:\Users\SantoshMadnani\Documents\CA_Trader\CA_Trader` under `.agents/` or `tools/`.
- No code or agent artifacts may be created outside the repository workspace boundary.
- All modifications must be committed and pushed to `origin CA-Trader-Bifurcated`.

## 2. Token Conservation & Surgical Editing
- Never perform full scans or dumps of `terminal.html` (1.9MB) or `app.py` (1MB).
- Always read `AI_MANIFEST.json` first to look up specific DOM IDs, functions, and line ranges.
- Use surgical, line-bounded `replace_file_content` blocks for all changes.

## 3. Pre-Commit Verification Gate
- Run `python scripts/validate_integrity.py` before any commit to verify Python, CSS, and JS syntax.
- Run `python tools/ui_reviewer.py` to verify baseline alignment, dual-theme styling, section isolation, and non-blank values.
