with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if "def overall_recommendation(" in l:
        print(f"overall_recommendation starts at line {i+1}")
        for j in range(i, min(i+120, len(lines))):
            print(f"{j+1}: {lines[j]}", end="")
        break

