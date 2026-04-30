# bot.py
# Advanced Tally Style Telegram Bot
# pip install python-telegram-bot==21.6

import sqlite3
from datetime import datetime
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

TOKEN = "8779700912:AAGJqIRuoLlxXGqSZVFum9PE9fSm4_nbYjk"

# ---------------- DATABASE ----------------
conn = sqlite3.connect("tally.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS kits(
id INTEGER PRIMARY KEY AUTOINCREMENT,
provider TEXT,
brand TEXT,
holder TEXT,
cost INTEGER,
status TEXT,
date TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS sales(
id INTEGER PRIMARY KEY AUTOINCREMENT,
kit_id INTEGER,
sell_price INTEGER,
received INTEGER,
pending INTEGER,
date TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS provider_payments(
id INTEGER PRIMARY KEY AUTOINCREMENT,
provider TEXT,
amount INTEGER,
date TEXT
)
""")

conn.commit()

# ---------------- CONFIG ----------------
COSTS = {
    "KT": 12000,
    "LT": 17000,
    "AK": 0
}

BRANDS = ["BOM", "RBL", "CBI", "BB"]

# ---------------- MENU ----------------
def menu():
    keyboard = [
        ["📦 Add Kit", "💰 Sell to KK"],
        ["📥 KK Payment", "📋 Unsold Stock"],
        ["👤 Providers", "🧾 KK Pending"],
        ["📊 Reports", "💸 Pay Provider"],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 Advanced Tally Bot Ready",
        reply_markup=menu()
    )

# ---------------- ADD KIT ----------------
async def add_kit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        [InlineKeyboardButton("KT", callback_data="provider_KT")],
        [InlineKeyboardButton("LT", callback_data="provider_LT")],
        [InlineKeyboardButton("AK", callback_data="provider_AK")],
    ]

    await update.message.reply_text(
        "Select Provider:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ---------------- CALLBACKS ----------------
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    # Provider selected
    if data.startswith("provider_"):
        provider = data.replace("provider_", "")
        context.user_data["provider"] = provider

        buttons = []
        for b in BRANDS:
            buttons.append(
                [InlineKeyboardButton(b, callback_data=f"brand_{b}")]
            )

        await query.message.reply_text(
            "Select Brand:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # Brand selected
    elif data.startswith("brand_"):
        brand = data.replace("brand_", "")
        context.user_data["brand"] = brand
        context.user_data["mode"] = "holder"

        await query.message.reply_text("Enter Holder Name:")

    # Sell kit select
    elif data.startswith("sell_"):
        kit_id = int(data.replace("sell_", ""))
        context.user_data["sell_kit"] = kit_id

        buttons = [
            [InlineKeyboardButton("₹25000", callback_data="price_25000")]
        ]

        await query.message.reply_text(
            "Sell Price:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # Price select
    elif data.startswith("price_"):
        price = int(data.replace("price_", ""))
        context.user_data["sell_price"] = price

        buttons = [
            [InlineKeyboardButton("₹0", callback_data="recv_0")],
            [InlineKeyboardButton("₹5000", callback_data="recv_5000")],
            [InlineKeyboardButton("Full", callback_data=f"recv_{price}")]
        ]

        await query.message.reply_text(
            "Received Now?",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # Received select
    elif data.startswith("recv_"):
        recv = int(data.replace("recv_", ""))

        kit_id = context.user_data["sell_kit"]
        sell_price = context.user_data["sell_price"]

        pending = sell_price - recv
        date = datetime.now().strftime("%d/%m/%Y")

        cur.execute("""
        INSERT INTO sales
        (kit_id, sell_price, received, pending, date)
        VALUES (?, ?, ?, ?, ?)
        """, (
            kit_id,
            sell_price,
            recv,
            pending,
            date
        ))

        cur.execute("""
        UPDATE kits
        SET status='SOLD'
        WHERE id=?
        """, (kit_id,))

        conn.commit()

        await query.message.reply_text(
            f"✅ Sold to KK\n"
            f"Sell: ₹{sell_price}\n"
            f"Received: ₹{recv}\n"
            f"Pending: ₹{pending}",
            reply_markup=menu()
        )

# ---------------- TEXT INPUT ----------------
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text

    # Add Kit
    if txt == "📦 Add Kit":
        await add_kit(update, context)
        return

    # Holder input
    if context.user_data.get("mode") == "holder":
        holder = txt.upper()

        provider = context.user_data["provider"]
        brand = context.user_data["brand"]

        cost = COSTS[provider]
        date = datetime.now().strftime("%d/%m/%Y")

        cur.execute("""
        INSERT INTO kits
        (provider, brand, holder, cost, status, date)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            provider,
            brand,
            holder,
            cost,
            "STOCK",
            date
        ))

        conn.commit()

        context.user_data["mode"] = ""

        await update.message.reply_text(
            f"✅ Kit Added\n"
            f"Provider: {provider}\n"
            f"Brand: {brand}\n"
            f"Holder: {holder}\n"
            f"Cost: ₹{cost}",
            reply_markup=menu()
        )
        return

    # Sell to KK
    if txt == "💰 Sell to KK":
        cur.execute("""
        SELECT id, provider, brand, holder
        FROM kits
        WHERE status='STOCK'
        """)

        rows = cur.fetchall()

        if not rows:
            await update.message.reply_text("No Stock")
            return

        buttons = []

        for r in rows:
            text = f"{r[0]} {r[1]} {r[2]} {r[3]}"
            buttons.append(
                [InlineKeyboardButton(text, callback_data=f"sell_{r[0]}")]
            )

        await update.message.reply_text(
            "Select Kit:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # KK Pending
    if txt == "🧾 KK Pending":
        cur.execute("""
        SELECT id, pending, date
        FROM sales
        WHERE pending > 0
        """)

        rows = cur.fetchall()

        if not rows:
            await update.message.reply_text("No Pending")
            return

        msg = "🧾 KK Pending\n\n"

        for r in rows:
            msg += f"ID {r[0]} | ₹{r[1]} | {r[2]}\n"

        await update.message.reply_text(msg)
        return

    # Unsold Stock
    if txt == "📋 Unsold Stock":
        cur.execute("""
        SELECT id, provider, brand, holder
        FROM kits
        WHERE status='STOCK'
        """)

        rows = cur.fetchall()

        if not rows:
            await update.message.reply_text("No Stock")
            return

        msg = "📋 Stock\n\n"

        for r in rows:
            msg += f"{r[0]} | {r[1]} | {r[2]} | {r[3]}\n"

        await update.message.reply_text(msg)
        return

    # Providers
    if txt == "👤 Providers":
        for p in ["KT", "LT", "AK"]:
            cur.execute("""
            SELECT COUNT(*), SUM(cost)
            FROM kits
            WHERE provider=?
            """, (p,))
            row = cur.fetchone()

            total = row[0]
            amount = row[1] if row[1] else 0

            cur.execute("""
            SELECT SUM(amount)
            FROM provider_payments
            WHERE provider=?
            """, (p,))
            paid = cur.fetchone()[0]
            paid = paid if paid else 0

            pending = amount - paid

            await update.message.reply_text(
                f"{p}\nDeals: {total}\nPayable: ₹{amount}\nPaid: ₹{paid}\nPending: ₹{pending}"
            )
        return

    # Reports
    if txt == "📊 Reports":
        cur.execute("SELECT COUNT(*) FROM sales")
        deals = cur.fetchone()[0]

        cur.execute("SELECT SUM(sell_price) FROM sales")
        sale = cur.fetchone()[0]
        sale = sale if sale else 0

        cur.execute("SELECT SUM(cost) FROM kits WHERE status='SOLD'")
        cost = cur.fetchone()[0]
        cost = cost if cost else 0

        profit = sale - cost

        await update.message.reply_text(
            f"📊 Reports\n\n"
            f"Sold Deals: {deals}\n"
            f"Sales: ₹{sale}\n"
            f"Cost: ₹{cost}\n"
            f"Profit: ₹{profit}"
        )
        return

# ---------------- APP ----------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(callbacks))
app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler)
)

print("Bot Running...")
app.run_polling()