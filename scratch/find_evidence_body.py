import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('terminal.html', encoding='utf-8') as f:
    text = f.read()

pos = text.find('id="recoEvidenceBody"')
if pos != -1:
    print("Found recoEvidenceBody at", pos)
    # find parent card
    card_start = text.rfind('<div class="card"', 0, pos)
    print("Card starts at", card_start)
    print(text[card_start:card_start+500])
