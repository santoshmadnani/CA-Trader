with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if "async def position_ai_analysis(" in l:
        print(f"Found at line {i+1}")
        for j in range(i, min(i+70, len(lines))):
            print(f"{j+1}: {lines[j]}", end="")
        break

