# FIX ISSUE: Holder Name ke baad freeze ho raha tha
# Reason:
# CallbackQuery se brand select ke baad Conversation start nahi ho rahi thi.
# Isliye full fixed bot.py below.

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
CHOOSING_PROVIDER = 1
CHOOSING_BRAND = 2
ASK_HOLDER = 3
ASK_SELL = 4

# ---------------- DATA ----------------
PROVIDERS = {
    "KT": 12000,
    "LT": 17000,
    "AK": "half"
}

BRANDS = ["BOM", "RBL", "CBI", "BB"]

# ---------------- MENU ----------------
def menu():
    keyboard = [
        ["➕ Add Kit", "📊 Reports"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 Bot Ready",
        reply_markup=menu()
    )

# ---------------- ADD KIT FLOW ----------------
async def add_kit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        [InlineKeyboardButton(x, callback_data=x)]
        for x in PROVIDERS.keys()
    ]

    await update.message.reply_text(
        "Select Provider:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return CHOOSING_PROVIDER

# ---------------- PROVIDER ----------------
async def provider_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["provider"] = query.data

    buttons = [
        [InlineKeyboardButton(x, callback_data=x)]
        for x in BRANDS
    ]

    await query.message.reply_text(
        "Select Brand:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return CHOOSING_BRAND

# ---------------- BRAND ----------------
async def brand_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["brand"] = query.data

    await query.message.reply_text(
        "Enter Holder Name:"
    )

    return ASK_HOLDER

# ---------------- HOLDER ----------------
async def holder_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["holder"] = update.message.text.upper()

    buttons = [
        [InlineKeyboardButton("₹25000", callback_data="25000")],
        [InlineKeyboardButton("Custom Amount", callback_data="custom")]
    ]

    await update.message.reply_text(
        "Select Sell Amount:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

    return ASK_SELL

# ---------------- SELL BUTTON ----------------
async def sell_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "custom":
        await query.message.reply_text(
            "Enter Sell Amount:"
        )
        return ASK_SELL

    sell = int(query.data)
    await save_deal(query.message, context, sell)

    return ConversationHandler.END

# ---------------- CUSTOM SELL ----------------
async def custom_sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.isdigit():
        sell = int(update.message.text)
        await save_deal(update.message, context, sell)
        return ConversationHandler.END

    return ASK_SELL

# ---------------- SAVE ----------------
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
        provider,
        brand,
        holder,
        sell,
        cost,
        profit,
        date
    ))
    conn.commit()

    await message.reply_text(
        f"✅ Saved Successfully\n\n"
        f"Provider: {provider}\n"
        f"Brand: {brand}\n"
        f"Holder: {holder}\n"
        f"Sell: ₹{sell}\n"
        f"Profit: ₹{profit}",
        reply_markup=menu()
    )

# ---------------- REPORT ----------------
async def reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cur.execute("SELECT COUNT(*), SUM(profit) FROM deals")
    row = cur.fetchone()

    total = row[0]
    profit = row[1] if row[1] else 0

    await update.message.reply_text(
        f"📊 Total Deals: {total}\n"
        f"💰 Profit: ₹{profit}"
    )

# ---------------- BUTTONS ----------------
async def main_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text

    if txt == "📊 Reports":
        await reports(update, context)

# ---------------- APP ----------------
app = ApplicationBuilder().token(TOKEN).build()

conv = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex("^➕ Add Kit$"), add_kit)
    ],
    states={
        CHOOSING_PROVIDER: [
            CallbackQueryHandler(provider_selected)
        ],
        CHOOSING_BRAND: [
            CallbackQueryHandler(brand_selected)
        ],
        ASK_HOLDER: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, holder_received)
        ],
        ASK_SELL: [
            CallbackQueryHandler(sell_selected),
            MessageHandler(filters.TEXT & ~filters.COMMAND, custom_sell)
        ],
    },
    fallbacks=[],
)

app.add_handler(CommandHandler("start", start))
app.add_handler(conv)
app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, main_buttons)
)

print("Running...")
app.run_polling()