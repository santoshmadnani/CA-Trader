with open('terminal.html', 'r', encoding='utf-8') as f:
    html = f.read()

import re
scripts = [m.group(1) for m in re.finditer(r'<script\b[^>]*>(.*?)</script>', html, re.DOTALL)]
s2_lines = scripts[2].split('\n')

with open('scratch/s2_lines_3900_3920.txt', 'w', encoding='utf-8') as out:
    for idx in range(3890, min(len(s2_lines), 3925)):
        out.write(f"{idx} (file {4060+idx}): {s2_lines[idx]}\n")

print("Saved lines to scratch/s2_lines_3900_3920.txt")

