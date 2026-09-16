with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if "ach = evaluate_achievable_option_move(" in l:
        print(f"evaluate_achievable_option_move at line {i+1}")
        for j in range(i, min(i+40, len(lines))):
            print(f"{j+1}: {lines[j]}", end="")
        break

