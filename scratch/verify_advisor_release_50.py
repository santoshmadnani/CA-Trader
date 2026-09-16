import os, sys, json, asyncio

from app import (
    app,
    db_exec,
    position_live_advisor_api,
    position_advisor_chat_api,
    positions
)

print('=== 1. TEST CA AI LIVE POSITION ADVISOR & THETA DECAY SENTINEL ===')
async def run_tests():
    real_users = db_exec("SELECT id, username FROM users", fetch="all")
    user = {'id': real_users[0]['id'], 'username': real_users[0]['username'], 'role': 'admin'} if real_users else {'id': 1, 'username': 'admin', 'role': 'admin'}

    # 1. Test live advisor endpoint
    adv = await position_live_advisor_api(position_id=None, user=user)
    print("Advisor Verdict:", adv.get("verdict"))
    print("Decision:", adv.get("decision"))
    print("Reason:", adv.get("reason")[:180] + "..." if adv.get("reason") else "")
    print(f"Peak PnL: ₹{adv.get('peak_pnl')} | Current PnL: ₹{adv.get('current_pnl')}")
    print(f"Theta Decay Hourly: -₹{adv.get('theta_decay_hourly')}/hr | Daily: -₹{adv.get('theta_decay_daily')}/day")
    assert "decision" in adv and "verdict" in adv, "Advisor missing key fields"

    # 2. Test advisor chat endpoint
    from starlette.requests import Request
    chat_body = json.dumps({"message": "Should I hold this option or exit due to Theta decay?"}).encode("utf-8")
    chat_req = Request({
        "type": "http",
        "method": "POST",
        "headers": [(b"content-type", b"application/json")],
    })
    # Mock receive for request.json()
    async def receive():
        return {"type": "http.request", "body": chat_body}
    chat_req._receive = receive

    chat_res = await position_advisor_chat_api(request=chat_req, user=user)
    print("\nAdvisor Chat Reply Preview:")
    print(chat_res.get("reply")[:250] + "...")
    assert "reply" in chat_res, "Chat response missing reply"

    # 3. Test positions endpoint mapping
    dummy_req = Request({"type": "http", "query_string": b""})
    pos_res = await positions(request=dummy_req, user=user)
    print("\nPositions Keys:", list(pos_res.keys()))
    print("Open positions count:", len(pos_res.get("open_positions", [])))
    print("Closed today count:", len(pos_res.get("closed_today", [])))
    assert "open_positions" in pos_res and "closed_today" in pos_res, "Positions missing enhanced lists"

asyncio.run(run_tests())

print('\n=== 2. VERIFY FRONTEND DOM ELEMENTS IN CONTAINER ===')
with open('terminal.html', 'r', encoding='utf-8') as f:
    th = f.read()

assert 'fpAdvisorSection' in th, 'fpAdvisorSection missing'
assert 'fpAdvisorBanner' in th, 'fpAdvisorBanner missing'
assert 'fpPeakPnl' in th, 'fpPeakPnl missing'
assert 'fpThetaBurn' in th, 'fpThetaBurn missing'
assert 'executePositionSquareOff' in th, 'executePositionSquareOff missing'
assert 'switchFpSubTab' in th, 'switchFpSubTab missing'
assert 'refreshPositionAdvisor' in th, 'refreshPositionAdvisor missing'
print("All frontend elements (advisor section, theta burn meter, 1-click square off, subtabs, chat) VERIFIED in container!")

print('\n=== ALL RELEASE 50 INTEGRATION TESTS COMPLETED SUCCESSFULLY ===')

