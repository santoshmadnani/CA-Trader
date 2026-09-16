import re, ast, sys

with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Fix exp_tag in options_summary
target1 = """            mcx_rows = p_mcx.get("data") or []
            if mcx_rows:
                contract_map = {}"""

repl1 = """            mcx_rows = p_mcx.get("data") or []
            if mcx_rows:
                exp_tag = (data.get("expiry") or "OCT 2026").split()[0] or "OCT"
                contract_map = {}"""

if target1 in text:
    text = text.replace(target1, repl1, 1)
    print("[OK] Defined exp_tag in options_summary")
else:
    print("[FAIL] target1 not found")
    sys.exit(1)

# 2. Add realistic MCX Crude spot guard in generate_option_chain_engine
target2 = """    if root in commodity_configs:
        cfg = commodity_configs[root]
        if spot is None: spot = cfg["spot"]"""

repl2 = """    if root in commodity_configs:
        cfg = commodity_configs[root]
        if spot is None or (root == "CRUDEOIL" and (spot > 8000 or spot < 3000)):
            spot = cfg["spot"]"""

if target2 in text:
    text = text.replace(target2, repl2, 1)
    print("[OK] Added CRUDEOIL domestic spot range guard (3000-8000)")
else:
    print("[FAIL] target2 not found")
    sys.exit(1)

# 3. Add side & display aliases to resolve_option_for_future
target3 = """                return {
                    "symbol": opt_sym,
                    "display_name": opt_sym,
                    "instrument_key": opt_node.get("instrument_key") or opt_sym,
                    "entry": float(opt_node.get("ltp") or 120.0),
                    "strike": float(best_row["strike"]),
                    "option_type": bias_tag,
                    "expiry": exp,
                    "lot_size": 100 if "CRUDE" in root else 1
                }"""

repl3 = """                return {
                    "symbol": opt_sym,
                    "display_name": opt_sym,
                    "display": opt_sym,
                    "instrument_key": opt_node.get("instrument_key") or opt_sym,
                    "entry": float(opt_node.get("ltp") or 120.0),
                    "strike": float(best_row["strike"]),
                    "option_type": bias_tag,
                    "side": bias_tag,
                    "expiry": exp,
                    "lot_size": 100 if "CRUDE" in root else 1
                }"""

if target3 in text:
    text = text.replace(target3, repl3, 1)
    print("[OK] Added side and display aliases to resolve_option_for_future")
else:
    print("[FAIL] target3 not found")
    sys.exit(1)

# Verify AST
try:
    ast.parse(text)
    print("[OK] AST verified cleanly")
except Exception as e:
    print(f"[FAIL] AST error: {e}")
    sys.exit(1)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("app.py updated successfully")

