# INSTRUCTIONS FOR EVERY USER REQUEST

Whenever the user asks to make any change, bug fix, feature addition, or deployment in this application, **ALWAYS** execute the following workflow:

1. **Read Core Files First**:
   - [agent.md](file:///c:/Users/SantoshMadnani/OneDrive%20-%20BDO%20INDIA%20SERVICES%20PRIVATE%20LIMITED/Personal%20files/CA_Trader/agent.md)
   - [CHANGELOG_MEMORY.md](file:///c:/Users/SantoshMadnani/OneDrive%20-%20BDO%20INDIA%20SERVICES%20PRIVATE%20LIMITED/Personal%20files/CA_Trader/CHANGELOG_MEMORY.md)

2. **Execute Changes Strictly According to Mandate**:
   - Make ONLY changes explicitly requested by the user.
   - Do NOT distort or break the existing UI layout; keep the dark theme (`#1890ff`, `#111622`) and typography compact and clean.
   - If an error is pointed out, diagnose root cause, solve it, and update `CHANGELOG_MEMORY.md` immediately with the solution steps.

3. **Verify Locally First**:
   - Start the local server (port 8000).
   - Test and verify ALL sections (Dashboard, Chart, Option Chain, Strategy Builder, Algo Bots, Backtesting, Risk & Journal, Fundamentals, Market Movers).
   - Capture screenshots for desktop and mobile screen widths.
   - Confirm all buttons are clickable and no sections are blank.

4. **Await User Approval Before Live Deployment**:
   - Present local verification findings and screenshots to the user.
   - Wait for explicit user confirmation before deploying to the live production server.

5. **Server Deployment Protocol (ZERO Laptop File Transfers)**:
   - **DO NOT** use SCP, SFTP, or direct laptop file sync tools (manifests/icons trigger Sophos security popups).
   - Commit and push changes to GitHub (`CA-Trader-Bifurcated` branch).
   - SSH into the production server using `ca-trader-key.pem` and run `git pull` followed by the docker restart script.
   - Re-verify live server (`https://catrader.site`) with screenshots to ensure all sections and features remain functional.

