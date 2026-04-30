# bot.py
# Premium Stable Tally Telegram Bot
# python-telegram-bot==21.6

import sqlite3
from datetime import datetime
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

TOKEN = "8779700912:AAGJqIRuoLlxXGqSZVFum9PE9fSm4_nbYjk"
ADMIN_ID = 8748005457

# ==================================================
# DATABASE
# ==================================================
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

cur.execute("""
CREATE TABLE IF NOT EXISTS ledger(
id INTEGER PRIMARY KEY AUTOINCREMENT,
party TEXT,
type TEXT,
amount INTEGER,
date TEXT,
note TEXT
)
""")

conn.commit()

# ==================================================
# CONFIG
# ==================================================
COSTS = {
    "KT": 12000,
    "LT": 17000,
    "AK": 0
}

BRANDS = ["BOM", "RBL", "CBI", "BB"]

# ==================================================
def allowed(update):
    return update.effective_user.id == ADMIN_ID


def menu():
    keyboard = [
        ["📦 Add Kit", "💰 Sell to KK"],
        ["📥 KK Payment", "💸 Pay Provider"],
        ["📋 Stock", "🧾 KK Pending"],
        ["👤 Providers", "📊 Reports"],
        ["📜 Ledger"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def today():
    return datetime.now().strftime("%d/%m/%Y")


def add_ledger(party, typ, amount, note):
    cur.execute("""
    INSERT INTO ledger(party,type,amount,date,note)
    VALUES(?,?,?,?,?)
    """, (party, typ, amount, today(), note))
    conn.commit()

# ==================================================
# START
# ==================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        await update.message.reply_text("⛔ Access Denied")
        return

    await update.message.reply_text(
        "🔥 Premium Tally Bot Ready",
        reply_markup=menu()
    )

# ==================================================
# ADD KIT
# ==================================================
async def add_kit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        [InlineKeyboardButton("KT", callback_data="provider_KT")],
        [InlineKeyboardButton("LT", callback_data="provider_LT")],
        [InlineKeyboardButton("AK", callback_data="provider_AK")]
    ]

    await update.message.reply_text(
        "📦 Select Provider:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ==================================================
# CALLBACKS (FIXED BUTTON SYSTEM)
# ==================================================
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return

    query = update.callback_query
    await query.answer()

    data = query.data

    # ---------------- Provider ----------------
    if data.startswith("provider_"):
        provider = data.replace("provider_", "")
        context.user_data["provider"] = provider

        buttons = [
            [InlineKeyboardButton(b, callback_data=f"brand_{b}")]
            for b in BRANDS
        ]

        await query.edit_message_text(
            "🏷 Select Brand:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # ---------------- Brand ----------------
    if data.startswith("brand_"):
        brand = data.replace("brand_", "")
        context.user_data["brand"] = brand
        context.user_data["mode"] = "holder"

        await query.edit_message_text("👤 Enter Holder Name:")
        return

    # ---------------- Sell ----------------
    if data.startswith("sell_"):
        kit_id = int(data.replace("sell_", ""))
        context.user_data["sell_kit"] = kit_id

        buttons = [
            [InlineKeyboardButton("₹25,000", callback_data="price_25000")]
        ]

        await query.edit_message_text(
            "💰 Sell Price:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # ---------------- Price ----------------
    if data.startswith("price_"):
        price = int(data.replace("price_", ""))
        context.user_data["sell_price"] = price

        buttons = [
            [InlineKeyboardButton("₹0", callback_data="recv_0")],
            [InlineKeyboardButton("₹5,000", callback_data="recv_5000")],
            [InlineKeyboardButton("Full", callback_data=f"recv_{price}")]
        ]

        await query.edit_message_text(
            "💵 Received Now?",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # ---------------- Received ----------------
    if data.startswith("recv_"):
        recv = int(data.replace("recv_", ""))

        kit_id = context.user_data["sell_kit"]
        price = context.user_data["sell_price"]

        pending = price - recv

        cur.execute("""
        INSERT INTO sales(kit_id,sell_price,received,pending,date)
        VALUES(?,?,?,?,?)
        """, (kit_id, price, recv, pending, today()))

        cur.execute("UPDATE kits SET status='SOLD' WHERE id=?", (kit_id,))
        conn.commit()

        if recv > 0:
            add_ledger("KK", "RECEIVED", recv, "Sale Payment")

        await query.edit_message_text(
            f"✅ Sold to KK\n\n"
            f"Sell ₹{price}\n"
            f"Received ₹{recv}\n"
            f"Pending ₹{pending}",
            reply_markup=menu()
        )
        return

# ==================================================
# TEXT HANDLER
# ==================================================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return

    txt = update.message.text.strip()

    # HOLDER ENTRY
    if context.user_data.get("mode") == "holder":
        provider = context.user_data["provider"]
        brand = context.user_data["brand"]
        holder = txt.upper()

        cost = COSTS[provider]

        cur.execute("""
        INSERT INTO kits(provider,brand,holder,cost,status,date)
        VALUES(?,?,?,?,?,?)
        """, (provider, brand, holder, cost, "STOCK", today()))

        conn.commit()
        context.user_data["mode"] = ""

        await update.message.reply_text(
            f"✅ Kit Added\n\nProvider: {provider}\nBrand: {brand}\nHolder: {holder}\nCost: ₹{cost}",
            reply_markup=menu()
        )
        return

# ==================================================
# APP
# ==================================================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(callbacks))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

print("Bot Running...")
app.run_polling()