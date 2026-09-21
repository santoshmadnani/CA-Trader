# Agent Workspace Rules (Fast & Lean Mode)

1. **Direct Execution First**:
   - For UI, CSS, HTML, and Python bug fixes or tweaks, apply the changes directly using `replace_file_content` without creating planning artifacts, markdown reports, or background test scripts unless explicitly requested by the user.

2. **Ultra-Concise Output**:
   - Keep replies strictly under 3-4 bullet points.
   - State only: what file changed, the exact modification made, and how to verify (e.g. refresh browser).
   - Do not generate lengthy post-change walkthroughs, artifacts, or summaries unless asked.

3. **Token Conservation**:
   - Do not re-read entire multi-megabyte files when targeting specific sections.
   - Avoid launching headless browser automation or heavy multi-step verification scripts for simple CSS/HTML tweaks.
