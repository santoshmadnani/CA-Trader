with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

print('rightSideNotificationContainer in terminal.html:', 'rightSideNotificationContainer' in text)
print('notificationBadge in terminal.html:', 'notificationBadge' in text)
print('floatingPositionWidget in terminal.html:', 'floatingPositionWidget' in text)
print('btnLockDrawings in terminal.html:', 'btnLockDrawings' in text)
print('quickOrderLtp in terminal.html:', 'quickOrderLtp' in text)
print('turboLoadBtn in terminal.html:', 'turboLoadBtn' in text)

