from pathlib import Path

def fix_minor():
    path = Path('app.py')
    code = path.read_text(encoding='utf-8')

    # 1. Fix article_key in news_unified
    code = code.replace("k = article_key(item)", "k = str(item.get('url') or item.get('headline') or item.get('event') or id(item))")

    # 2. Attach id if existing_reco in analysis_overall
    old_existing = """            if not existing_reco:
                rid = secrets.token_hex(12)"""

    new_existing = """            if existing_reco:
                rec["id"] = existing_reco["id"]
                rec["saved"] = True
            else:
                rid = secrets.token_hex(12)"""

    code = code.replace(old_existing, new_existing, 1)

    path.write_text(code, encoding='utf-8')
    print("Fixed article_key and existing_reco id attachment")

if __name__ == '__main__':
    fix_minor()

