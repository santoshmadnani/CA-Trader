# Agent Security, Privacy & Boundary Rules

You must strictly adhere to all rules defined in this file across all sessions and tasks. Read and verify compliance with these rules before executing any command or making any change.

---

## 1. Strict Workspace Boundary
* **Workspace Root**: `c:\Users\SantoshMadnani\Documents\CA_Trader\CA_Trader`
* **Zero External Access**: Never inspect, read, search, list, modify, or execute commands targeting any directory or file outside this workspace root.
* **No Directory Traversal**: Never use parent directory references (`..`), absolute paths outside the workspace, or wildcard scans across parent folders or the user profile.

---

## 2. Explicitly Denied Paths
The following locations are strictly forbidden from being accessed, referenced, or passed as arguments to any tool or shell command:
* Any OneDrive folder (e.g., `OneDrive`, `OneDrive - BDO INDIA SERVICES PRIVATE LIMITED`, `Personal files`, etc.)
* User Profile root (`$HOME`, `$env:USERPROFILE`, `C:\Users\SantoshMadnani\` outside this workspace)
* System, app data, or corporate directories unless explicitly instructed by the user.

---

## 3. Shell & Terminal Execution (`run_command`) Rules
* **Confined Execution**: Every command executed must operate exclusively on paths inside `c:\Users\SantoshMadnani\Documents\CA_Trader\CA_Trader`.
* **Prohibited Cmdlet Arguments**: Never execute PowerShell cmdlets (e.g., `Get-ChildItem`, `Get-Content`, `Test-Path`, `Remove-Item`, `Copy-Item`) targeting paths outside the project directory.
* **No Background Spying**: Do not inspect shell history files (`(Get-PSReadLineOption).HistorySavePath`), global event logs, or global process trees outside the current project scope.

---

## 4. Pre-Action Verification Protocol
Before executing any tool call, file modification, or command:
1. Verify that all target paths are inside the workspace.
2. If any required file, dependency, or configuration resides outside this project boundary, **STOP immediately and ask the user directly** for guidance or explicit permission.

---

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


