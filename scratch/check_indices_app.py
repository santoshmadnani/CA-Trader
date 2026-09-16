with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

# Check where init_db is
idx_init = text.find("def init_db() -> None:")
print("init_db found at:", idx_init)

# Check where recommendation_history is
idx_hist = text.find("def recommendation_history(")
print("recommendation_history found at:", idx_hist)

# Check where overall_recommendation is
idx_reco = text.find("def overall_recommendation(")
print("overall_recommendation found at:", idx_reco)

# Check where position_ai_analysis is
idx_pos = text.find("async def position_ai_analysis(")
print("position_ai_analysis found at:", idx_pos)

# Check where options_summary is
idx_opt = text.find("async def options_summary(")
print("options_summary found at:", idx_opt)

