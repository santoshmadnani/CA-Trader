with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re

# 1. Check watchlist AT button
m_wl = re.search(r'<button[^>]+class=["\']wl-at["\'][^>]*>AT</button>', text)
print("Watchlist AT button found:", bool(m_wl))

# 2. Check chartFullscreen button
m_fs = re.search(r'<button[^>]+id=["\']chartFullscreen["\'][^>]*>', text)
print("chartFullscreen button found:", bool(m_fs))
if m_fs:
    print("chartFullscreen snippet:", text[m_fs.start()-50:m_fs.start()+150].encode('ascii', errors='replace').decode('ascii'))

# 3. Check applyLiveTick
m_alt = re.search(r'function\s+applyLiveTick\s*\(', text)
print("applyLiveTick found:", bool(m_alt))
if m_alt:
    print("applyLiveTick snippet:", text[m_alt.start():m_alt.start()+600].encode('ascii', errors='replace').decode('ascii'))

