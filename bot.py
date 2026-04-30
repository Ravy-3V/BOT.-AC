# Advanced Button UI Telegram Bot (bot.py)
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
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

TOKEN = "8779700912:AAGJqIRuoLlxXGqSZVFum9PE9fSm4_nbYjk"

# ---------------- DATABASE ----------------
conn = sqlite3.connect("hisab.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS deals (
id INTEGER PRIMARY KEY AUTOINCREMENT,
provider TEXT,
brand TEXT,
holder TEXT,
sell INTEGER,
cost INTEGER,
profit INTEGER,
date TEXT
)
""")
conn.commit()

# ---------------- STATES ----------------
HOLDER, SELL = range(2)

# ---------------- DATA ----------------
PROVIDERS = {
    "KT": 12000,
    "LT": 17000,
    "AK": "half"
}

BRANDS = ["BOM", "RBL", "CBI", "BB"]

# ---------------- MENU ----------------
def main_menu():
    keyboard = [
        ["➕ Add Kit", "📊 Reports"],
        ["💸 Pay Provider", "💰 KK Payment"],
        ["⚙️ Manage"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 Business Hisaab Bot Ready",
        reply_markup=main_menu()
    )

# ---------------- ADD KIT ----------------
async def add_kit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        [InlineKeyboardButton(x, callback_data=f"provider_{x}")]
        for x in PROVIDERS.keys()
    ]
    await update.message.reply_text(
        "Select Provider:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def provider_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    provider = query.data.replace("provider_", "")
    context.user_data["provider"] = provider

    buttons = [
        [InlineKeyboardButton(x, callback_data=f"brand_{x}")]
        for x in BRANDS
    ]

    await query.message.reply_text(
        "Select Brand:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def brand_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    brand = query.data.replace("brand_", "")
    context.user_data["brand"] = brand

    await query.message.reply_text("Enter Holder Name:")
    return HOLDER

async def holder_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["holder"] = update.message.text.upper()

    buttons = [
        [InlineKeyboardButton("₹25000", callback_data="sell_25000")],
        [InlineKeyboardButton("Custom Amount", callback_data="sell_custom")]
    ]

    await update.message.reply_text(
        "Select Sell Amount:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def sell_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "sell_custom":
        await query.message.reply_text("Enter Custom Sell Amount:")
        return SELL

    sell = 25000
    await save_deal(query.message, context, sell)
    return ConversationHandler.END

async def custom_sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sell = int(update.message.text)
    await save_deal(update.message, context, sell)
    return ConversationHandler.END

async def save_deal(message, context, sell):
    provider = context.user_data["provider"]
    brand = context.user_data["brand"]
    holder = context.user_data["holder"]

    rule = PROVIDERS[provider]

    if rule == "half":
        cost = sell // 2
    else:
        cost = rule

    profit = sell - cost
    date = datetime.now().strftime("%d/%m/%Y")

    cur.execute("""
    INSERT INTO deals
    (provider, brand, holder, sell, cost, profit, date)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        provider, brand, holder,
        sell, cost, profit, date
    ))
    conn.commit()

    await message.reply_text(
        f"✅ Deal Saved\n\n"
        f"Provider: {provider}\n"
        f"Brand: {brand}\n"
        f"Holder: {holder}\n"
        f"Sell: ₹{sell}\n"
        f"Cost: ₹{cost}\n"
        f"Profit: ₹{profit}",
        reply_markup=main_menu()
    )

# ---------------- REPORT ----------------
async def reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cur.execute("SELECT COUNT(*), SUM(profit) FROM deals")
    row = cur.fetchone()

    total = row[0]
    profit = row[1] if row[1] else 0

    await update.message.reply_text(
        f"📊 Reports\n\n"
        f"Total Deals: {total}\n"
        f"Total Profit: ₹{profit}",
        reply_markup=main_menu()
    )

# ---------------- BUTTON ROUTER ----------------
async def menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text

    if txt == "➕ Add Kit":
        await add_kit(update, context)

    elif txt == "📊 Reports":
        await reports(update, context)

    elif txt == "💸 Pay Provider":
        await update.message.reply_text("Coming Soon")

    elif txt == "💰 KK Payment":
        await update.message.reply_text("Coming Soon")

    elif txt == "⚙️ Manage":
        await update.message.reply_text("Coming Soon")

# ---------------- APP ----------------
app = ApplicationBuilder().token(TOKEN).build()

conv = ConversationHandler(
    entry_points=[],
    states={
        HOLDER: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, holder_name)
        ],
        SELL: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, custom_sell)
        ],
    },
    fallbacks=[],
)

app.add_handler(CommandHandler("start", start))
app.add_handler(conv)

app.add_handler(CallbackQueryHandler(provider_select, pattern="^provider_"))
app.add_handler(CallbackQueryHandler(brand_select, pattern="^brand_"))
app.add_handler(CallbackQueryHandler(sell_select, pattern="^sell_"))

app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, menu_buttons)
)

print("Bot Running...")
app.run_polling()