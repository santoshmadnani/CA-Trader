with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re

# Check all divs in terminal.html
stack = []
lines = text.splitlines()

for i, line in enumerate(lines):
    for m in re.finditer(r'(</?([a-zA-Z0-9]+)[^>]*>)', line):
        full_tag = m.group(1)
        tag_name = m.group(2).lower()
        if tag_name in ['input', 'img', 'br', 'hr', 'meta', 'link']:
            continue
        if full_tag.endswith('/>'):
            continue
        if full_tag.startswith('</'):
            if not stack:
                print(f"L{i+1}: Stray closing tag </{tag_name}>")
            else:
                last_line, last_tag, last_desc = stack[-1]
                if last_tag == tag_name:
                    stack.pop()
                else:
                    # check if tag matches earlier
                    match_idx = None
                    for si in range(len(stack)-1, -1, -1):
                        if stack[si][1] == tag_name:
                            match_idx = si
                            break
                    if match_idx is not None:
                        # unclosed tags in between!
                        print(f"L{i+1}: Closing </{tag_name}> matched L{stack[match_idx][0]} <{stack[match_idx][1]}>, but skipped {len(stack)-1-match_idx} unclosed tags:")
                        for skip_i in range(match_idx+1, len(stack)):
                            print(f"    Unclosed L{stack[skip_i][0]}: {stack[skip_i][2]}")
                        stack = stack[:match_idx]
                    else:
                        print(f"L{i+1}: Unexpected </{tag_name}> (expected </{last_tag}> from L{last_line})")
        else:
            tag_desc = full_tag[:80].strip()
            stack.append((i+1, tag_name, tag_desc))

print(f"\nRemaining unclosed tags at EOF: {len(stack)}")
for l, t, d in stack:
    print(f"  L{l} <{t}>: {d}")

