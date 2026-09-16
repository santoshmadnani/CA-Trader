import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    html = f.read()

required_ids = [
    'floatingPositionWidget', 'floatingPosHead', 'fpMinBtn', 'floatingPosBodyWrapper',
    'fpAdvisorSection', 'fpAdvisorVerdict', 'fpAdvisorReason', 'fpAdvisorUrgency',
    'fpAdvisorBanner', 'fpPeakPnl', 'fpCurrentPnlTag', 'fpThetaBurn',
    'ordersAdvisorCard', 'ordersAdvisorActiveSymbol', 'ordersAdvisorSyncStatus',
    'ordersAdvisorSyncDot', 'ordersAdvisorSyncText', 'ordersAdvisorVerdict',
    'ordersAdvisorUrgency', 'ordersAdvisorReason', 'ordersAdvisorBanner',
    'ordersPeakPnl', 'ordersCurrentPnlTag', 'ordersPnlRetention',
    'ordersThetaBurn', 'ordersDailyTheta', 'ordersTradeEntryLtp',
    'ordersTradeQtyTag', 'ordersSlTgt', 'ordersSlStatusTag', 'ordersSlAdvice',
    'ordersAdvisorChatBox', 'ordersAdvisorChatLog', 'ordersAdvisorInput'
]

missing_ids = [id_name for id_name in required_ids if f'id="{id_name}"' not in html]
if missing_ids:
    print('ERROR: Missing IDs:', missing_ids)
    sys.exit(1)
else:
    print(f'SUCCESS: All {len(required_ids)} required DOM IDs verified in terminal.html')

required_fns = [
    'toggleFloatingPositionsWidget', 'renderPositionAdvisorData',
    'toggleOrdersAdvisorChat', 'sendOrdersAdvisorQuickQuestion',
    'sendOrdersAdvisorMessage', 'selectAdvisorPositionById',
    'updateFloatingPositionsWidget'
]

missing_fns = [fn for fn in required_fns if fn not in html]
if missing_fns:
    print('ERROR: Missing functions:', missing_fns)
    sys.exit(1)
else:
    print(f'SUCCESS: All {len(required_fns)} JavaScript functions verified in terminal.html')

print('File size:', len(html), 'bytes')
print('Verification PASSED!')

