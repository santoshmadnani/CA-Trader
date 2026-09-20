with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix the extra </div> in reports toolbar
old_chunk = """            <button class="btn ghost small" onclick="clearAllTradeHistory()" style="color:var(--sell);font-size:11px;padding:2px 8px;height:26px;" title="Clear Trade History">🗑️ Clear All</button>
          </div>
        </div>
      </div>

      <!-- Reports Subtabs (Item 23) -->"""

new_chunk = """            <button class="btn ghost small" onclick="clearAllTradeHistory()" style="color:var(--sell);font-size:11px;padding:2px 8px;height:26px;" title="Clear Trade History">🗑️ Clear All</button>
          </div>
        </div>

      <!-- Reports Subtabs (Item 23) -->"""

if old_chunk in text:
    text = text.replace(old_chunk, new_chunk)
    print("Fixed extra </div> in reports header")

# Fix extra </div> before panel-quiz
old_quiz_before = """        </div>
      </div>
    </div>
  </div>

    <!-- ============ TRADER QUIZ (Item 23) ============ -->
    <div class="panel" id="panel-quiz" style="display:none !important;\">"""

new_quiz_before = """        </div>
      </div>
    </div>

    <!-- ============ TRADER QUIZ (Item 23) ============ -->
    <div class="panel" id="panel-quiz" style="display:none !important;\">"""

if old_quiz_before in text:
    text = text.replace(old_quiz_before, new_quiz_before)
    print("Fixed extra </div> before panel-quiz")

with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("Saved.")
