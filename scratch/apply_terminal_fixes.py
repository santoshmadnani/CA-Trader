# Script to fix terminal.html
with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Remove duplicate Ask CA AI button and duplicate editUIBtn in profile dropdown
old_profile_btn = '<button class="btn ghost small mobile-profile-ai" id="caAiOpenMobile" style="margin-top:10px;width:100%;justify-content:center;">Ask CA AI</button>'
if old_profile_btn in text:
    text = text.replace(old_profile_btn, '')
    print("Replaced old_profile_btn")
else:
    print("old_profile_btn not found")

# Remove duplicate editUIBtn if present
duplicate_edit_ui = '<button class="btn ghost small" id="editUIBtn" style="margin-top:7px;width:100%;justify-content:center;">Edit UI</button>\n        <button class="btn ghost small" id="editUIBtn" style="margin-top:10px;width:100%;justify-content:center;">Edit UI</button>'
if duplicate_edit_ui in text:
    text = text.replace(duplicate_edit_ui, '<button class="btn ghost small" id="editUIBtn" style="margin-top:10px;width:100%;justify-content:center;">Edit UI</button>')
    print("Removed duplicate editUIBtn")

# 2. Fix the fatal syntax error at lines 8314-8316 in Script #4
# Find the broken section:
broken_fmt = """  const fmt = v => v == null || !isFinite(Number(v)) ? '—' : Number(v).toLocaleString('en-IN',{minimumFractionDigits:2,maximumFractionDigits:2});
  const fmtMoney = v => v == null || !isFinite(Number(v)) ? '—' : '₹'+N
... [truncated for diff preview]
  const fmtMoney = v => v == null || !isFinite(Number(v)) ? '—' : '₹'+Number(v).toLocaleString('en-IN',{maximumFractionDigits:0});"""

clean_fmt = """  const fmt = v => v == null || !isFinite(Number(v)) ? '—' : Number(v).toLocaleString('en-IN',{minimumFractionDigits:2,maximumFractionDigits:2});
  const fmtMoney = v => v == null || !isFinite(Number(v)) ? '—' : '₹'+Number(v).toLocaleString('en-IN',{maximumFractionDigits:0});"""

if broken_fmt in text:
    text = text.replace(broken_fmt, clean_fmt)
    print("Fixed broken_fmt in Script #4")
else:
    print("Searching with regex for broken fmtMoney...")
    import re
    text = re.sub(
        r"const fmtMoney = v => v == null \|\| !isFinite\(Number\(v\)\) \? '—' : '₹'\+N\s*\.\.\.\s*\[truncated for diff preview\]\s*",
        "",
        text
    )
    print("Regex replacement applied")

# 3. Enhance api timeout default to 8000ms instead of 4500ms
text = text.replace(
    "const timeoutMs = Math.max(1200, Number(options.timeoutMs || 4500));",
    "const timeoutMs = Math.max(1200, Number(options.timeoutMs || 8000));"
)

# 4. Enhance loadChartAiSuggestions in Script #3
old_load_ai = """    if(S){
      try {
        const d = await A(`/api/analysis/chart-ai-suggestions/${encodeURIComponent(S)}?timeframe=${encodeURIComponent(state.tf)}&days=${state.history || 7}`, {timeoutMs: 12000});"""

new_load_ai = """    const activeSym = S || (typeof selectedSymbol === 'function' ? selectedSymbol() : null) || window.CATraderSymbol || 'NIFTY';
    if(activeSym){
      try {
        const d = await A(`/api/analysis/chart-ai-suggestions/${encodeURIComponent(activeSym)}?timeframe=${encodeURIComponent(state.tf || '5m')}&days=${state.history || 5}`, {timeoutMs: 6000});"""

if old_load_ai in text:
    text = text.replace(old_load_ai, new_load_ai)
    print("Updated loadChartAiSuggestions with activeSym fallback")
else:
    print("old_load_ai pattern not matched directly, searching...")

# 5. Enhance sendAiChat in Script #4 to provide instant typing indicator and robust error handling
old_send_ai = """  async function sendAiChat(){ const input=$('aiChatInput'); const text=(input?.value||'').trim(); if(!text)return; addAiMessage(text,'user'); input.value=''; try{const sym=String(window.CATraderSymbol||selectedSymbol()||'NIFTY').toUpperCase(); const q=await api('/api/market/quote/'+encodeURIComponent(sym)).catch(()=>null); const r=await api('/api/ai/chat',{method:'POST',body:JSON.stringify({message:text,symbol:sym,current_setup:window.__caCurrentChartReco||{},context:{symbol:sym,quote:q}})}); addAiMessage(r.message||r.reply||r.response||r.reason||'CA AI response received.','ai');}catch(e){addAiMessage('CA AI Error: '+(e.message||'Service unavailable'),'ai')} }"""

new_send_ai = """  async function sendAiChat(){
    const input = $('aiChatInput');
    const text = (input?.value || '').trim();
    if(!text) return;
    addAiMessage(text, 'user');
    input.value = '';
    const placeholder = addAiMessage('✦ CA AI thinking…', 'ai');
    try {
      const sym = String(window.CATraderSymbol || selectedSymbol() || 'NIFTY').toUpperCase();
      const q = await api('/api/market/quote/' + encodeURIComponent(sym), {timeoutMs: 3000}).catch(() => null);
      const r = await api('/api/ai/chat', {
        method: 'POST',
        timeoutMs: 12000,
        body: JSON.stringify({
          message: text,
          symbol: sym,
          current_setup: window.__caCurrentChartReco || {},
          context: {symbol: sym, quote: q}
        })
      });
      if(placeholder && placeholder.parentNode) placeholder.remove();
      addAiMessage(r.message || r.reply || r.response || r.reason || 'CA AI response received.', 'ai');
    } catch(e) {
      if(placeholder && placeholder.parentNode) placeholder.remove();
      addAiMessage('CA AI Error: ' + (e.message || 'Service unavailable'), 'ai');
    }
  }"""

if old_send_ai in text:
    text = text.replace(old_send_ai, new_send_ai)
    print("Enhanced sendAiChat with thinking indicator and timeout")
else:
    print("old_send_ai not matched directly")

with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("terminal.html updated successfully")

