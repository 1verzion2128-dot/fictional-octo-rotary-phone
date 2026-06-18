import os
import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime

app = FastAPI()

# Дозволяємо запити з GitHub Pages (і будь-якого іншого сайту)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")


def format_order_message(data: dict) -> str:
    user = data.get("user", {})
    items = data.get("items", [])
    total = data.get("total", 0)
    timestamp = data.get("timestamp", "")

    # Форматуємо час
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        time_str = dt.strftime("%d.%m.%Y о %H:%M")
    except Exception:
        time_str = timestamp

    # Блок з інфо про покупця
    name = user.get("name") or "—"
    username = user.get("username") or "—"
    phone = user.get("phone")
    tg_id = user.get("id")

    buyer_lines = [f"👤 <b>{name}</b>"]
    if username != "—":
        buyer_lines.append(f"🔗 @{username}")
    if phone:
        buyer_lines.append(f"📞 {phone}")
    if tg_id:
        buyer_lines.append(f"🆔 <code>{tg_id}</code>")

    # Список товарів
    items_lines = []
    for item in items:
        item_name = item.get("name", "?")
        qty = item.get("qty", 1)
        price = item.get("price", 0)
        line_total = price * qty
        items_lines.append(
            f"  • {item_name} × {qty} = <b>{line_total:,} ₴</b>".replace(",", " ")
        )

    msg = (
        "🛒 <b>НОВЕ ЗАМОВЛЕННЯ!</b>\n"
        f"🕐 {time_str}\n"
        "\n"
        "━━━━ Покупець ━━━━\n"
        + "\n".join(buyer_lines) +
        "\n\n"
        "━━━━ Товари ━━━━\n"
        + "\n".join(items_lines) +
        f"\n\n💰 <b>Сума: {total:,} ₴</b>".replace(",", " ")
    )
    return msg


async def send_telegram_message(text: str):
    if not BOT_TOKEN or not ADMIN_CHAT_ID:
        print("⚠️  BOT_TOKEN або ADMIN_CHAT_ID не задані!")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": ADMIN_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, timeout=10)
        return resp.status_code == 200


@app.post("/order")
async def receive_order(request: Request):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    print(f"📦 Нове замовлення: {data}")

    message = format_order_message(data)
    success = await send_telegram_message(message)

    if success:
        return JSONResponse({"status": "ok", "message": "Замовлення прийнято"})
    else:
        # Повертаємо 200 щоб фронтенд показав success навіть якщо щось з ботом
        return JSONResponse({"status": "warn", "message": "Замовлення збережено, але сповіщення не надіслано"})


@app.get("/")
async def root():
    return {"status": "GearZone backend is running 🎮"}


@app.get("/health")
async def health():
    return {"status": "ok"}
