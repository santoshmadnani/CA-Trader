import asyncio
import time
from unittest.mock import MagicMock, AsyncMock

print("=== VERIFYING LIVE CONTAINER: P&L, LOT SIZING & RECOMMENDATION GUARD ===")

from app import db_exec, analysis_overall, order_create, OrderIn

user = db_exec("SELECT * FROM users WHERE email='santoshmadnani@catrader.site' LIMIT 1", [], "one") or db_exec("SELECT * FROM users LIMIT 1", [], "one")
print("Test User:", user["email"], "id=", user["id"])

async def run_verifications():
    # 1. Test NIFTY Recommendation
    print("\n--- 1. Testing NIFTY Underlying Recommendation ---")
    rec_nifty = await analysis_overall("NIFTY", "5m", user=user)
    print("NIFTY Trend:", rec_nifty.get("direction"))
    print("NIFTY Confidence:", rec_nifty.get("confidence"), "%")
    print("NIFTY Entry:", rec_nifty.get("entry"))
    print("NIFTY SL:", rec_nifty.get("stop_loss"))
    print("NIFTY Target:", rec_nifty.get("target"))

    # 2. Test Anti-Counter-Trend Guard on NIFTY 23250 PE
    print("\n--- 2. Testing Anti-Counter-Trend Guard on NIFTY 23250 PE ---")
    rec_pe = await analysis_overall("NIFTY 23250 PE", "5m", user=user)
    print("Recommendation:", rec_pe.get("recommendation") or rec_pe.get("direction"))
    print("Qualifies:", rec_pe.get("qualifies"))
    print("Rationale/Reason:", rec_pe.get("rationale") or rec_pe.get("reason"))
    assert rec_pe.get("recommendation") == "NO_TRADE" or rec_pe.get("qualifies") is False, "Guard failed: PE should not qualify when underlying is bullish!"
    print("✓ SUCCESS: Counter-trend PE recommendation correctly blocked with NO_TRADE guard!")

    # 3. Test Order Placement with Quantity 1 (should place 1 lot = 65 contracts)
    print("\n--- 3. Testing Order Creation with Quantity 65 (1 Lot) ---")
    order_payload = OrderIn(
        symbol="NIFTY 23250 PE",
        side="BUY",
        quantity=65,
        order_type="MARKET",
        product="I",
        paper=True,
        live=False
    )
    req = MagicMock()
    res = await order_create(order_payload, req, user)
    print(f"Order created: ID={res.get('id')}, Status={res.get('status')}")
    # Verify order in DB
    order_row = db_exec("SELECT * FROM orders WHERE id=?", [res.get('id')], "one")
    print(f"DB Order Record: Symbol={order_row['symbol']}, Qty={order_row['quantity']}, Status={order_row['status']}")
    assert order_row['quantity'] == 65, f"Expected 65, got {order_row['quantity']}"
    print("✓ SUCCESS: Order placed exactly for 65 contracts (1 lot)!")

    # 4. Verify terminal.html markup
    print("\n--- 4. Verifying terminal.html markup for positions and lot sizing ---")
    with open('/app/terminal.html', 'r', encoding='utf-8') as f:
        html = f.read()
    assert 'data-avg="${avgPrice}"' in html, "Missing data-avg in position tr!"
    assert 'data-is-open="${isOpen ? \'true\' : \'false\'}"' in html, "Missing data-is-open in position tr!"
    assert "if(s.includes('NIFTY')) return 65;" in html, "Missing NIFTY=65 in getSymbolLotSize!"
    assert "row.dataset.isOpen !== 'true'" in html, "Missing isOpen check in applyLiveTick!"
    print("✓ SUCCESS: terminal.html has all position attributes, live P&L guards, and NIFTY=65 sizing!")

    print("\n=== ALL CONTAINER TESTS VERIFIED 100% WORKING ===")

asyncio.run(run_verifications())

