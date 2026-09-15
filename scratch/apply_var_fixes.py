# -*- coding: utf-8 -*-
from pathlib import Path

path = Path("terminal.html")
code = path.read_text(encoding="utf-8")

# Fix 1: Guard line 7313
assert "void updateChartRecoBanner(null, S);" in code
code = code.replace("void updateChartRecoBanner(null, S);", "if(typeof updateChartRecoBanner === 'function') void updateChartRecoBanner(null, S);", 1)
print("Guarded line 7313")

# Fix 2: Change const to var for helpers in final script
code = code.replace("const $ = id => document.getElementById(id);", "var $ = window.$ || (id => document.getElementById(id));", 1)
code = code.replace("const esc = s => String(s == null ? '' : s).replace(/[&<>\"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'})[c]);", "var esc = window.esc || (s => String(s == null ? '' : s).replace(/[&<>\"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'})[c]));", 1)
code = code.replace("const fmt = v => v == null || !isFinite(Number(v)) ? '—' : Number(v).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });", "var fmt = window.fmt || (v => v == null || !isFinite(Number(v)) ? '—' : Number(v).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));", 1)
code = code.replace("const fmtMoney = v => v == null || !isFinite(Number(v)) ? '₹0.00' : (Number(v) < 0 ? '-₹' : '₹') + Math.abs(Number(v)).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });", "var fmtMoney = window.fmtMoney || (v => v == null || !isFinite(Number(v)) ? '₹0.00' : (Number(v) < 0 ? '-₹' : '₹') + Math.abs(Number(v)).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));", 1)
code = code.replace("const formatTime = t => t ? new Date(t).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '—';", "var formatTime = window.formatTime || (t => t ? new Date(t).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '—');", 1)

path.write_text(code, encoding="utf-8")
print(f"Applied fixes to terminal.html: {len(code):,} bytes")

