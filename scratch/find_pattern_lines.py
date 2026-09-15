with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    for idx, line in enumerate(f):
        if any(w in line for w in ['renderPatterns', 'patternList', 'structureBox', 'chartPatternList']):
            print(f"Line {idx+1}: {line.strip()[:100]}")

