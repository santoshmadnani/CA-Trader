import re

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

panel_matches = list(re.finditer(r'<div[^>]*\bid=["\'](panel-[^"\']+)["\'][^>]*>', text))
print(f"Total panel divs: {len(panel_matches)}")

for i in range(len(panel_matches)):
    curr_m = panel_matches[i]
    curr_id = curr_m.group(1)
    start_pos = curr_m.start()
    if i < len(panel_matches) - 1:
        end_pos = panel_matches[i+1].start()
    else:
        end_pos = text.find('</main>')
        if end_pos == -1: end_pos = text.find('<script')

    chunk = text[start_pos:end_pos]
    open_d = len(re.findall(r'<div\b', chunk))
    close_d = len(re.findall(r'</div', chunk))
    diff = open_d - close_d
    print(f"{curr_id:25}: open={open_d:3}, close={close_d:3}, diff={diff:3}")

