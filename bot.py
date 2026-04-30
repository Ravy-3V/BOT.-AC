# ==========================================
# TELEGRAM ADVANCE HISAAB BOT
# By ChatGPT
# pip install python-telegram-bot==21.6
# ==========================================

import sqlite3
from datetime import datetime

from telegram import (
    Update,
    ReplyKeyboardMarkup
)

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

TOKEN = "8779700912:AAGJqIRuoLlxXGqSZVFum9PE9fSm4_nbYjk"

# ------------------------------------------
# DATABASE
# ------------------------------------------
conn = sqlite3.connect("hisab.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS deals (
id INTEGER PRIMARY KEY AUTOINCREMENT,
provider TEXT,
holder TEXT,
brand TEXT,
sell INTEGER,
cost INTEGER,
profit INTEGER,
paid INTEGER,
pending INTEGER,
date TEXT
)
""")
conn.commit()

# ------------------------------------------
# STATES
# ------------------------------------------
PROVIDER, HOLDER, BRAND, SELL = range(4)
PAY_ID, PAY_AMOUNT = range(2)

# ------------------------------------------
# MENU
# ------------------------------------------
def menu():
    keyboard = [
        ["➕ Add Deal", "💸 Pay Provider"],
        ["📋 Pending List", "📊 Profit Report"],
        ["👤 Provider Report", "🔍 Search Holder"],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True
    )

# ------------------------------------------
# START
# ------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 Advance Hisaab Bot Ready",
        reply_markup=menu()
    )

# ------------------------------------------
# COST LOGIC
# ------------------------------------------
def get_cost(provider, sell):
    provider = provider.upper()

    if provider == "KT":
        return 12000

    elif provider == "LT":
        return 17000

    elif provider == "AK":
        return sell // 2

    return 0

# ------------------------------------------
# ADD DEAL FLOW
# ------------------------------------------
async def add_start(update, context):
    await update.message.reply_text(
        "Provider Name?\n( KT / AK / LT )"
    )
    return PROVIDER

async def add_provider(update, context):
    context.user_data["provider"] = update.message.text.upper()
    await update.message.reply_text("Holder Name?")
    return HOLDER

async def add_holder(update, context):
    context.user_data["holder"] = update.message.text.upper()
    await update.message.reply_text("Brand Name?")
    return BRAND

async def add_brand(update, context):
    context.user_data["brand"] = update.message.text.upper()
    await update.message.reply_text("Sell Amount?")
    return SELL

async def add_sell(update, context):
    sell = int(update.message.text)

    provider = context.user_data["provider"]
    holder = context.user_data["holder"]
    brand = context.user_data["brand"]

    cost = get_cost(provider, sell)
    profit = sell - cost

    date = datetime.now().strftime("%d/%m/%Y")

    cur.execute("""
    INSERT INTO deals
    (provider, holder, brand, sell, cost, profit, paid, pending, date)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        provider, holder, brand,
        sell, cost, profit,
        0, cost, date
    ))

    conn.commit()

    await update.message.reply_text(
        f"✅ Deal Added\n\n"
        f"Provider: {provider}\n"
        f"Holder: {holder}\n"
        f"Brand: {brand}\n"
        f"Sell: ₹{sell}\n"
        f"Payable: ₹{cost}\n"
        f"Profit: ₹{profit}",
        reply_markup=menu()
    )

    return ConversationHandler.END

# ------------------------------------------
# PAY FLOW
# ------------------------------------------
async def pay_start(update, context):
    await update.message.reply_text("Entry ID?")
    return PAY_ID

async def pay_id(update, context):
    context.user_data["pay_id"] = int(update.message.text)
    await update.message.reply_text("Amount Paid?")
    return PAY_AMOUNT

async def pay_amount(update, context):
    entry_id = context.user_data["pay_id"]
    amount = int(update.message.text)

    cur.execute("""
    SELECT paid, pending
    FROM deals
    WHERE id=?
    """, (entry_id,))

    row = cur.fetchone()

    if not row:
        await update.message.reply_text(
            "Invalid ID",
            reply_markup=menu()
        )
        return ConversationHandler.END

    old_paid = row[0]
    old_pending = row[1]

    new_paid = old_paid + amount
    new_pending = old_pending - amount

    if new_pending < 0:
        new_pending = 0

    cur.execute("""
    UPDATE deals
    SET paid=?, pending=?
    WHERE id=?
    """, (
        new_paid,
        new_pending,
        entry_id
    ))

    conn.commit()

    await update.message.reply_text(
        f"✅ Payment Updated\n"
        f"Paid: ₹{new_paid}\n"
        f"Pending: ₹{new_pending}",
        reply_markup=menu()
    )

    return ConversationHandler.END

# ------------------------------------------
# PENDING LIST
# ------------------------------------------
async def pending(update, context):
    cur.execute("""
    SELECT id, provider, holder, pending
    FROM deals
    WHERE pending > 0
    """)

    rows = cur.fetchall()

    if not rows:
        await update.message.reply_text(
            "✅ No Pending",
            reply_markup=menu()
        )
        return

    msg = "📋 Pending List\n\n"

    for r in rows:
        msg += (
            f"ID:{r[0]} | {r[1]} | "
            f"{r[2]} | ₹{r[3]}\n"
        )

    await update.message.reply_text(
        msg,
        reply_markup=menu()
    )

# ------------------------------------------
# PROFIT REPORT
# ------------------------------------------
async def profit(update, context):
    cur.execute("""
    SELECT SUM(profit)
    FROM deals
    """)

    total = cur.fetchone()[0]

    if total is None:
        total = 0

    await update.message.reply_text(
        f"📊 Total Profit: ₹{total}",
        reply_markup=menu()
    )

# ------------------------------------------
# PROVIDER REPORT
# ------------------------------------------
async def provider_report(update, context):
    await update.message.reply_text(
        "Use command:\n/provider KT"
    )

async def provider_cmd(update, context):
    provider = context.args[0].upper()

    cur.execute("""
    SELECT id, holder, pending
    FROM deals
    WHERE provider=?
    """, (provider,))

    rows = cur.fetchall()

    if not rows:
        await update.message.reply_text("No Data")
        return

    msg = f"👤 {provider} Report\n\n"

    for r in rows:
        msg += (
            f"ID:{r[0]} | "
            f"{r[1]} | ₹{r[2]}\n"
        )

    await update.message.reply_text(msg)

# ------------------------------------------
# SEARCH HOLDER
# ------------------------------------------
async def search(update, context):
    await update.message.reply_text(
        "Use command:\n/search ABHISHEK"
    )

async def search_cmd(update, context):
    name = context.args[0].upper()

    cur.execute("""
    SELECT id, provider, brand, pending
    FROM deals
    WHERE holder=?
    """, (name,))

    rows = cur.fetchall()

    if not rows:
        await update.message.reply_text("No Record")
        return

    msg = f"🔍 {name}\n\n"

    for r in rows:
        msg += (
            f"ID:{r[0]} | {r[1]} | "
            f"{r[2]} | ₹{r[3]}\n"
        )

    await update.message.reply_text(msg)

# ------------------------------------------
# BUTTON ROUTER
# ------------------------------------------
async def buttons(update, context):
    txt = update.message.text

    if txt == "📋 Pending List":
        await pending(update, context)

    elif txt == "📊 Profit Report":
        await profit(update, context)

    elif txt == "👤 Provider Report":
        await provider_report(update, context)

    elif txt == "🔍 Search Holder":
        await search(update, context)

# ------------------------------------------
# APP
# ------------------------------------------
app = ApplicationBuilder().token(TOKEN).build()

# Add Deal Flow
add_conv = ConversationHandler(
    entry_points=[
        MessageHandler(
            filters.Regex("^➕ Add Deal$"),
            add_start
        )
    ],
    states={
        PROVIDER: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                add_provider
            )
        ],
        HOLDER: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                add_holder
            )
        ],
        BRAND: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                add_brand
            )
        ],
        SELL: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                add_sell
            )
        ],
    },
    fallbacks=[]
)

# Pay Flow
pay_conv = ConversationHandler(
    entry_points=[
        MessageHandler(
            filters.Regex("^💸 Pay Provider$"),
            pay_start
        )
    ],
    states={
        PAY_ID: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                pay_id
            )
        ],
        PAY_AMOUNT: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                pay_amount
            )
        ],
    },
    fallbacks=[]
)

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("provider", provider_cmd))
app.add_handler(CommandHandler("search", search_cmd))

app.add_handler(add_conv)
app.add_handler(pay_conv)

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        buttons
    )
)

print("Bot Running...")
app.run_polling()