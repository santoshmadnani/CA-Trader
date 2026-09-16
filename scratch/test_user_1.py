import os, sys, json, asyncio

from app import (
    app,
    db_exec,
    position_live_advisor_api,
    positions
)

async def test_user_1():
    user = {'id': 1, 'username': 'admin', 'role': 'admin'}
    adv = await position_live_advisor_api(position_id=None, user=user)
    print("USER 1 Advisor Verdict:", adv.get("verdict"))
    print("USER 1 Decision:", adv.get("decision"))
    print("USER 1 Symbol:", adv.get("symbol"))
    print("USER 1 Reason:", adv.get("reason"))
    print(f"USER 1 Peak PnL: ₹{adv.get('peak_pnl')} | Current PnL: ₹{adv.get('current_pnl')}")
    print(f"USER 1 Theta Decay Hourly: -₹{adv.get('theta_decay_hourly')}/hr | Daily: -₹{adv.get('theta_decay_daily')}/day")

    from starlette.requests import Request
    pos_res = await positions(request=Request({"type": "http", "query_string": b""}), user=user)
    print("USER 1 Closed Today count:", len(pos_res.get("closed_today", [])))
    print("First closed trade:", pos_res.get("closed_today", [{}])[0].get("symbol"), "PnL:", pos_res.get("closed_today", [{}])[0].get("final_pnl"))

asyncio.run(test_user_1())

