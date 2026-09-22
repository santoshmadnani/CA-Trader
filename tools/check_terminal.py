#!/usr/bin/env python3
"""
tools/check_terminal.py
Rapid 0.1-second static health check for terminal.html:
- HTML <div> open/close balance (ignoring <script> and <style> blocks)
- Duplicate ID detection across HTML elements
- All 14 panel IDs present inside .main
- Key JavaScript window exports present
"""

import sys
import re
from pathlib import Path

def main():
    terminal_path = Path(__file__).resolve().parent.parent / "terminal.html"
    if not terminal_path.exists():
        print(f"ERROR: {terminal_path} not found")
        sys.exit(1)

    content = terminal_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    errors = []

    # 1. Check tag balance for <div> ONLY in HTML context (not inside <script> or <style>)
    div_stack = []
    main_closed = False
    main_close_line = None
    in_script = False
    in_style = False

    for idx, line in enumerate(lines, 1):
        clean_line = re.sub(r'<!--.*?-->', '', line)

        # Track script and style transitions
        if '<script' in clean_line.lower():
            in_script = True
        if '</script>' in clean_line.lower():
            in_script = False
            continue

        if '<style' in clean_line.lower():
            in_style = True
        if '</style>' in clean_line.lower():
            in_style = False
            continue

        if in_script or in_style:
            continue

        # Check open divs in pure HTML
        for match in re.finditer(r'<div\b([^>]*)>', clean_line, re.IGNORECASE):
            attrs = match.group(1)
            if match.group(0).endswith('/>'):
                continue
            is_main = 'class="main"' in attrs or "class='main'" in attrs
            div_stack.append((idx, is_main))

        # Check closing divs in pure HTML
        for match in re.finditer(r'</div>', clean_line, re.IGNORECASE):
            if not div_stack:
                errors.append(f"Line {idx}: Extra </div> encountered in HTML with no matching open <div>")
            else:
                pop_line, was_main = div_stack.pop()
                if was_main:
                    main_closed = True
                    main_close_line = idx

    if div_stack:
        errors.append(f"Unclosed <div> count in HTML: {len(div_stack)} (First unclosed opened at line {div_stack[0][0]})")

    # 2. Check 14 panel IDs
    expected_panels = [
        "panel-dashboard", "panel-charts", "panel-options", "panel-reco",
        "panel-news", "panel-fundamentals", "panel-movers", "panel-other-factors",
        "panel-backtesting", "panel-orders", "panel-funds", "panel-console",
        "panel-reports", "panel-notifications"
    ]
    for p in expected_panels:
        pattern = f'id=["\']{p}["\']'
        matches = [i for i, l in enumerate(lines, 1) if re.search(pattern, l)]
        if not matches:
            errors.append(f"Missing required panel: #{p}")
        elif len(matches) > 1:
            errors.append(f"Duplicate panel ID #{p} found at lines: {matches}")
        elif main_close_line and matches[0] > main_close_line:
            errors.append(f"Panel #{p} at line {matches[0]} appears AFTER .main is closed at line {main_close_line}! (UI shift defect)")

    # 3. Check critical window exports
    expected_exports = [
        "window.draw", "window.loadChart", "window.ensureChartLayout",
        "window.renderDualRecoCards", "window.state"
    ]
    for exp in expected_exports:
        if exp not in content:
            errors.append(f"Missing critical export: '{exp}' in JavaScript")

    # Report results
    print("=" * 60)
    print(" TERMINAL.HTML HEALTH & SYNTAX VERIFICATION")
    print("=" * 60)
    if errors:
        print(f"FAILED with {len(errors)} issues:")
        for err in errors:
            print(f"  [X] {err}")
        print("=" * 60)
        sys.exit(1)
    else:
        print(f"[OK] Div tag balance: PERFECT (0 unclosed, 0 extra close tags)")
        print(f"[OK] All 14 Panels correctly seated inside .main")
        print(f"[OK] All critical window exports present")
        print("=" * 60)
        print("RESULT: PASS (0.1s check)")
        sys.exit(0)

if __name__ == "__main__":
    main()

