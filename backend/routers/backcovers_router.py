"""
backend/routers/backcovers_router.py
FastAPI router for backcovers.ai - AI Phone Back Cover Designer
"""

from fastapi import APIRouter, Request, HTTPException, Response
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from google import genai
import base64, io, json, os, uuid, time, random, math
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
from pathlib import Path

router = APIRouter(tags=["backcovers"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent
BACKCOVERS_HTML_PATH = BASE_DIR / "backcovers.html"

# In-memory stores
generated_images = {}
cart_items = []
reviews_store = {}

PHONE_BRANDS = {
    "Apple": {"models": ["iPhone 18 Pro Max", "iPhone 18 Pro", "iPhone 18 Plus", "iPhone 18", "iPhone 17 Pro Max", "iPhone 17 Pro", "iPhone 16 Pro Max", "iPhone 16 Pro", "iPhone 15 Pro Max", "iPhone 15 Pro", "iPhone 14 Pro Max", "iPhone 13 Pro", "iPhone SE (2024)"]},
    "Samsung": {"models": ["Galaxy S25 Ultra", "Galaxy S25+", "Galaxy S25", "Galaxy S24 Ultra", "Galaxy S24+", "Galaxy S24", "Galaxy S23 Ultra", "Galaxy Z Fold 6", "Galaxy Z Flip 6", "Galaxy A55", "Galaxy A35"]},
    "Google": {"models": ["Pixel 10 Pro XL", "Pixel 10 Pro", "Pixel 10", "Pixel 9 Pro XL", "Pixel 9 Pro", "Pixel 9", "Pixel 8 Pro", "Pixel 8a"]},
    "OnePlus": {"models": ["OnePlus 13", "OnePlus 13R", "OnePlus 12", "OnePlus 12R", "OnePlus 11", "OnePlus Nord 4"]},
    "Xiaomi": {"models": ["Xiaomi 15 Ultra", "Xiaomi 15", "Xiaomi 14 Ultra", "Redmi Note 14 Pro+", "POCO X7 Pro", "POCO F6 Pro"]},
    "Realme": {"models": ["Realme GT 6", "Realme 13 Pro+", "Realme 12 Pro+", "Realme Narzo 70 Pro"]},
    "Nothing": {"models": ["Nothing Phone (3)", "Nothing Phone (2a)", "Nothing Phone (2)", "Nothing CMF Phone 1"]}
}

COVER_STYLES = [
    {"name": "Cyberpunk Neon Matrix", "bg1": (8, 4, 20), "bg2": (35, 12, 55), "primary": (0, 240, 255), "secondary": (255, 0, 128), "pattern": "grid"},
    {"name": "Cosmic Nebula Galaxy", "bg1": (4, 4, 16), "bg2": (22, 10, 48), "primary": (175, 95, 255), "secondary": (45, 140, 255), "pattern": "galaxy"},
    {"name": "Obsidian & Liquid Gold", "bg1": (14, 14, 16), "bg2": (28, 24, 20), "primary": (255, 215, 0), "secondary": (218, 165, 32), "pattern": "gold"},
    {"name": "Anime Aura Energy", "bg1": (16, 5, 12), "bg2": (48, 10, 25), "primary": (255, 50, 90), "secondary": (255, 180, 40), "pattern": "aura"},
    {"name": "Minimalist Topography", "bg1": (18, 22, 28), "bg2": (32, 40, 48), "primary": (90, 220, 180), "secondary": (60, 160, 210), "pattern": "topography"},
    {"name": "Abstract Prismatic Wave", "bg1": (10, 8, 26), "bg2": (45, 18, 60), "primary": (100, 255, 210), "secondary": (255, 90, 190), "pattern": "wave"},
    {"name": "Gothic Phantom Eclipse", "bg1": (6, 6, 10), "bg2": (20, 18, 28), "primary": (170, 170, 210), "secondary": (120, 60, 180), "pattern": "eclipse"},
    {"name": "Hyperdrive Velocity", "bg1": (4, 10, 24), "bg2": (10, 28, 55), "primary": (0, 210, 255), "secondary": (255, 210, 60), "pattern": "speed"},
    {"name": "Emerald Zen Mist", "bg1": (6, 18, 12), "bg2": (14, 38, 28), "primary": (70, 245, 150), "secondary": (160, 255, 200), "pattern": "zen"},
    {"name": "Solar Flare Inferno", "bg1": (22, 7, 4), "bg2": (55, 18, 10), "primary": (255, 110, 20), "secondary": (255, 210, 40), "pattern": "solar"}
]

def generate_procedural_cover(keyword, style_idx, phone_model="iPhone 18 Pro"):
    st = COVER_STYLES[style_idx % len(COVER_STYLES)]
    w, h = 600, 1000
    img = Image.new('RGB', (w, h), st['bg1'])
    draw = ImageDraw.Draw(img)
    for y in range(h):
        interp = y / h
        interp_curve = math.sin(interp * math.pi / 2)
        r = int(st['bg1'][0] * (1 - interp_curve) + st['bg2'][0] * interp_curve)
        g = int(st['bg1'][1] * (1 - interp_curve) + st['bg2'][1] * interp_curve)
        b = int(st['bg1'][2] * (1 - interp_curve) + st['bg2'][2] * interp_curve)
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    cx, cy = w // 2, int(h * 0.48)
    pat = st['pattern']
    if pat == 'grid':
        horizon = int(h * 0.62)
        for rad in range(180, 20, -12):
            draw.ellipse([cx-rad, horizon - rad, cx+rad, horizon + rad], outline=st['primary'], width=2)
        for x in range(0, w + 1, 40):
            draw.line([(x, h), (cx + (x - cx) // 6, horizon)], fill=(*st['primary'], 90), width=1)
    elif pat == 'galaxy':
        rng = random.Random(style_idx * 100 + hash(keyword) % 1000)
        for _ in range(140):
            sx, sy = rng.randint(20, w-20), rng.randint(20, h-20)
            sz = rng.choice([1, 2, 3])
            draw.ellipse([sx-sz, sy-sz, sx+sz, sy+sz], fill=st['primary'])
        for rad in range(240, 30, -18):
            draw.arc([cx-rad, cy-int(rad*0.6), cx+rad, cy+int(rad*0.6)], start=30, end=330, fill=st['secondary'], width=3)
    elif pat == 'gold':
        draw.rectangle([30, 30, w-30, h-30], outline=st['secondary'], width=2)
        d_sz = 130
        draw.polygon([(cx, cy - d_sz), (cx + d_sz, cy), (cx, cy + d_sz), (cx - d_sz, cy)], outline=st['primary'], width=2)
        draw.line([(40, int(h*0.3)), (cx, cy), (w-40, int(h*0.7))], fill=st['primary'], width=3)
    elif pat == 'aura':
        for rad in range(250, 20, -15):
            draw.ellipse([cx-rad, cy-rad, cx+rad, cy+rad], outline=st['primary'], width=3)
        for ang in range(0, 360, 20):
            ra = math.radians(ang)
            draw.line([(cx + int(100*math.cos(ra)), cy + int(100*math.sin(ra))), (cx + int(230*math.cos(ra)), cy + int(230*math.sin(ra)))], fill=st['secondary'], width=2)
    elif pat == 'topography':
        for r_step in range(40, 300, 26):
            pts = [(cx + int(r_step * (1.0 + 0.15*math.sin(math.radians(a)*3)) * math.cos(math.radians(a))), cy + int(r_step * (1.0 + 0.15*math.sin(math.radians(a)*3)) * math.sin(math.radians(a)))) for a in range(0, 360, 12)]
            draw.polygon(pts, outline=st['primary'], fill=None)
    elif pat == 'wave':
        for step in range(-6, 7):
            pts = [(x, cy + step * 28 + int(45 * math.sin((x / w * 4 * math.pi) + step * 0.4))) for x in range(0, w + 10, 10)]
            draw.line(pts, fill=st['primary'] if step % 2 == 0 else st['secondary'], width=2)
    else:
        for r in range(220, 20, -14):
            draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=st['primary'], width=2)

    clean_kw = keyword.strip().upper()
    draw.rectangle([0, h - 80, w, h], fill=(0, 0, 0, 160))
    draw.line([(0, h - 80), (w, h - 80)], fill=st['primary'], width=2)
    draw.text((cx, h - 55), f"[ {clean_kw} ]", fill=(255, 255, 255), anchor="mm")
    draw.text((cx, h - 30), f"BACKCOVERS.AI STUDIO | {st['name'].upper()}", fill=(*st['secondary'], 200), anchor="mm")
    draw.text((w - 35, 45), f"EDITION #{style_idx + 1:02d}", fill=(*st['primary'], 180), anchor="rm")
    draw.text((35, 45), "PRO SERIES", fill=(200, 200, 220), anchor="lm")

    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=90)
    return base64.b64encode(buf.getvalue()).decode('utf-8')

def generate_single_item(i, keyword, phone_model):
    variation = COVER_STYLES[i % len(COVER_STYLES)]['name']
    prompt = f"Design phone cover for {phone_model}. Theme: {keyword}. Style: {variation}."
    img_data = generate_procedural_cover(keyword, i, phone_model)
    img_id = str(uuid.uuid4())[:8]
    item_name = f"{keyword.title()} - {variation}"
    price = 299 + (i * 30)
    generated_images[img_id] = {
        'id': img_id, 'data': img_data, 'prompt': prompt, 'keyword': keyword,
        'phone_model': phone_model, 'variation': variation, 'name': item_name,
        'price': price, 'rating': round(4.5 + (i % 5) * 0.1, 1), 'reviews_count': 64 + (i * 27)
    }
    return {
        'id': img_id, 'image': f"data:image/jpeg;base64,{img_data}", 'name': item_name,
        'price': price, 'rating': generated_images[img_id]['rating'],
        'reviews_count': generated_images[img_id]['reviews_count'],
        'variation': variation, 'phone_model': phone_model
    }

# ── Endpoints ────────────────────────────────────────────────────────
@router.get("/backcovers", response_class=HTMLResponse)
@router.get("/backcovers.ai", response_class=HTMLResponse)
async def backcovers_page(request: Request) -> Response:
    if not BACKCOVERS_HTML_PATH.exists():
        raise HTTPException(404, "backcovers.html not found")
    try:
        request.session["selected_terminal"] = "backcovers"
    except Exception:
        pass
    return HTMLResponse(BACKCOVERS_HTML_PATH.read_text(encoding="utf-8"))

@router.get("/api/brands")
@router.get("/api/backcovers/brands")
async def get_brands():
    return JSONResponse(PHONE_BRANDS)

@router.post("/api/generate")
@router.post("/api/backcovers/generate")
async def generate_covers(request: Request):
    data = await request.json() if request.method == "POST" else {}
    keyword = data.get('keyword', 'abstract art')
    phone_model = data.get('phone_model', 'iPhone 18 Pro')
    count = min(data.get('count', 10), 10)
    results = []
    with ThreadPoolExecutor(max_workers=count) as executor:
        futures = {executor.submit(generate_single_item, i, keyword, phone_model): i for i in range(count)}
        for future in as_completed(futures):
            res = future.result()
            if res: results.append(res)
    results.sort(key=lambda x: x['price'])
    return JSONResponse({'results': results, 'keyword': keyword, 'total': len(results)})

@router.post("/api/edit-image")
@router.post("/api/backcovers/edit-image")
async def edit_image(request: Request):
    data = await request.json()
    img_id = data.get('image_id')
    edit_prompt = data.get('edit_prompt', '').lower()
    style_preset = data.get('style_preset', '')
    raw_image_data = data.get('current_image', '')

    base_b64 = None
    if raw_image_data and ',' in raw_image_data:
        base_b64 = raw_image_data.split(',')[1]
    elif img_id and img_id in generated_images:
        base_b64 = generated_images[img_id]['data']

    if not base_b64:
        raise HTTPException(404, "Image not found")

    img_bytes = base64.b64decode(base_b64)
    img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
    w, h = img.size

    if style_preset == 'cyberpunk' or any(k in edit_prompt for k in ['neon', 'cyber', 'glow']):
        img = ImageEnhance.Contrast(img).enhance(1.4)
        img = ImageEnhance.Color(img).enhance(1.6)
        overlay = Image.new('RGB', (w, h), (180, 0, 240))
        img = Image.blend(img, overlay, 0.12)
    elif style_preset == 'galaxy' or any(k in edit_prompt for k in ['galaxy', 'space', 'star']):
        img = ImageEnhance.Contrast(img).enhance(1.3)
        overlay = Image.new('RGB', (w, h), (20, 10, 60))
        img = Image.blend(img, overlay, 0.18)
    elif style_preset == 'gold' or any(k in edit_prompt for k in ['gold', 'luxury']):
        img = ImageEnhance.Contrast(img).enhance(1.3)
        overlay = Image.new('RGB', (w, h), (255, 200, 50))
        img = Image.blend(img, overlay, 0.15)
    elif style_preset == 'anime' or any(k in edit_prompt for k in ['anime', 'aura']):
        img = ImageEnhance.Color(img).enhance(1.5)
        img = ImageEnhance.Sharpness(img).enhance(1.7)
    elif style_preset == 'dark' or any(k in edit_prompt for k in ['dark', 'black', 'stealth']):
        img = ImageEnhance.Brightness(img).enhance(0.65)
        img = ImageEnhance.Contrast(img).enhance(1.5)
    else:
        if 'bright' in edit_prompt: img = ImageEnhance.Brightness(img).enhance(1.3)
        if 'dark' in edit_prompt: img = ImageEnhance.Brightness(img).enhance(0.7)

    brightness = float(data.get('brightness', 1.0))
    contrast = float(data.get('contrast', 1.0))
    saturation = float(data.get('saturation', 1.0))
    if brightness != 1.0: img = ImageEnhance.Brightness(img).enhance(brightness)
    if contrast != 1.0: img = ImageEnhance.Contrast(img).enhance(contrast)
    if saturation != 1.0: img = ImageEnhance.Color(img).enhance(saturation)

    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=90)
    new_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    new_id = str(uuid.uuid4())[:8]
    generated_images[new_id] = {
        'id': new_id, 'data': new_b64, 'prompt': edit_prompt,
        'keyword': data.get('keyword', 'Custom Edit'),
        'phone_model': data.get('phone_model', 'iPhone 18 Pro'),
        'name': f"Customized - {style_preset.title() if style_preset else 'Fine-tuned'}",
        'price': 349
    }
    return JSONResponse({'success': True, 'id': new_id, 'image': f"data:image/jpeg;base64,{new_b64}", 'name': generated_images[new_id]['name'], 'price': 349})

@router.get("/api/image/{img_id}")
@router.get("/api/backcovers/image/{img_id}")
async def get_image(img_id: str):
    if img_id in generated_images:
        img = generated_images[img_id]
        return JSONResponse({'id': img_id, 'image': f"data:image/jpeg;base64,{img['data']}", 'name': img['name'], 'price': img['price'], 'phone_model': img.get('phone_model', '')})
    raise HTTPException(404, "Image not found")

@router.get("/api/cart")
@router.get("/api/backcovers/cart")
async def get_cart():
    return JSONResponse({'items': cart_items, 'total': sum(i.get('price', 299) for i in cart_items)})

@router.post("/api/cart")
@router.post("/api/backcovers/cart")
async def add_to_cart(request: Request):
    data = await request.json()
    item = {
        'cart_id': str(uuid.uuid4())[:8], 'id': data.get('id', str(uuid.uuid4())[:8]),
        'name': data.get('name', 'Custom Cover'), 'price': data.get('price', 299),
        'image': data.get('image', ''), 'phone_model': data.get('phone_model', 'iPhone 18 Pro'),
        'custom_text': data.get('custom_text', ''), 'quantity': 1
    }
    cart_items.append(item)
    return JSONResponse({'success': True, 'cart_count': len(cart_items), 'item': item})

@router.delete("/api/cart")
@router.delete("/api/backcovers/cart")
async def remove_from_cart(request: Request):
    data = await request.json()
    cart_id = data.get('cart_id')
    for i, it in enumerate(cart_items):
        if it['cart_id'] == cart_id:
            cart_items.pop(i)
            break
    return JSONResponse({'success': True, 'cart_count': len(cart_items)})
