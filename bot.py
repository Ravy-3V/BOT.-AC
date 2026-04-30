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
# MENU
# ==================================================
def menu():
    keyboard = [
        ["📦 Add Kit", "💰 Sell to KK"],
        ["📥 KK Payment", "💸 Pay Provider"],
        ["📋 Stock", "🧾 KK Pending"],
        ["👤 Providers", "📊 Reports"],
        ["📜 Ledger"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ==================================================
# HELPERS
# ==================================================
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
    await update.message.reply_text(
        "🔥 Premium Tally Bot Ready",
        reply_markup=menu()
    )

# ==================================================
# ADD KIT
# ==================================================
async def add_kit(update, context):
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
# CALLBACKS
# ==================================================
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    # Provider Select
    if data.startswith("provider_"):
        provider = data.replace("provider_", "")
        context.user_data["provider"] = provider

        buttons = []
        for b in BRANDS:
            buttons.append(
                [InlineKeyboardButton(b, callback_data=f"brand_{b}")]
            )

        await query.message.reply_text(
            "🏷 Select Brand:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # Brand Select
    if data.startswith("brand_"):
        brand = data.replace("brand_", "")
        context.user_data["brand"] = brand
        context.user_data["mode"] = "holder"

        await query.message.reply_text(
            "👤 Enter Holder Name:"
        )
        return

    # Sell Select
    if data.startswith("sell_"):
        kit_id = int(data.replace("sell_", ""))
        context.user_data["sell_kit"] = kit_id

        buttons = [
            [InlineKeyboardButton("₹25,000", callback_data="price_25000")]
        ]

        await query.message.reply_text(
            "💰 Sell Price:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # Price Select
    if data.startswith("price_"):
        price = int(data.replace("price_", ""))
        context.user_data["sell_price"] = price

        buttons = [
            [InlineKeyboardButton("₹0", callback_data="recv_0")],
            [InlineKeyboardButton("₹5,000", callback_data="recv_5000")],
            [InlineKeyboardButton("Full", callback_data=f"recv_{price}")]
        ]

        await query.message.reply_text(
            "💵 Received Now?",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # Received Select
    if data.startswith("recv_"):
        recv = int(data.replace("recv_", ""))

        kit_id = context.user_data["sell_kit"]
        price = context.user_data["sell_price"]

        pending = price - recv

        cur.execute("""
        INSERT INTO sales(kit_id,sell_price,received,pending,date)
        VALUES(?,?,?,?,?)
        """, (kit_id, price, recv, pending, today()))

        cur.execute("""
        UPDATE kits SET status='SOLD' WHERE id=?
        """, (kit_id,))

        conn.commit()

        if recv > 0:
            add_ledger("KK", "RECEIVED", recv, "Sale Payment")

        await query.message.reply_text(
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
    txt = update.message.text.strip()

    # --------------------------------------
    # HOLDER ENTRY
    # --------------------------------------
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
            f"✅ Kit Added\n\n"
            f"Provider: {provider}\n"
            f"Brand: {brand}\n"
            f"Holder: {holder}\n"
            f"Cost: ₹{cost}",
            reply_markup=menu()
        )
        return

    # --------------------------------------
    # KK PAYMENT PROCESS
    # --------------------------------------
    if context.user_data.get("mode") == "kkpay":
        try:
            sale_id, amount = txt.split()
            sale_id = int(sale_id)
            amount = int(amount)

            cur.execute("""
            SELECT received,pending FROM sales WHERE id=?
            """, (sale_id,))
            row = cur.fetchone()

            if not row:
                await update.message.reply_text("❌ Wrong ID")
                return

            new_received = row[0] + amount
            new_pending = row[1] - amount

            if new_pending < 0:
                new_pending = 0

            cur.execute("""
            UPDATE sales
            SET received=?, pending=?
            WHERE id=?
            """, (new_received, new_pending, sale_id))

            conn.commit()

            add_ledger("KK", "RECEIVED", amount, f"Payment Sale ID {sale_id}")

            context.user_data["mode"] = ""

            await update.message.reply_text(
                "✅ KK Payment Updated",
                reply_markup=menu()
            )
            return

        except:
            await update.message.reply_text("Use:\nID Amount")
            return

    # --------------------------------------
    # PROVIDER PAYMENT PROCESS
    # --------------------------------------
    if context.user_data.get("mode") == "providerpay":
        try:
            provider, amount = txt.split()
            provider = provider.upper()
            amount = int(amount)

            cur.execute("""
            INSERT INTO provider_payments(provider,amount,date)
            VALUES(?,?,?)
            """, (provider, amount, today()))

            conn.commit()

            add_ledger(provider, "PAID", amount, "Provider Payment")

            context.user_data["mode"] = ""

            await update.message.reply_text(
                f"✅ {provider} Payment Saved",
                reply_markup=menu()
            )
            return

        except:
            await update.message.reply_text("Use:\nKT 5000")
            return

    # ==================================================
    # BUTTONS
    # ==================================================

    if txt == "📦 Add Kit":
        await add_kit(update, context)
        return

    if txt == "💰 Sell to KK":
        cur.execute("""
        SELECT id,provider,brand,holder
        FROM kits
        WHERE status='STOCK'
        """)
        rows = cur.fetchall()

        if not rows:
            await update.message.reply_text("📭 No Stock")
            return

        buttons = []

        for r in rows:
            buttons.append([
                InlineKeyboardButton(
                    f"{r[0]} | {r[1]} | {r[2]} | {r[3]}",
                    callback_data=f"sell_{r[0]}"
                )
            ])

        await update.message.reply_text(
            "📦 Select Kit:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    if txt == "📥 KK Payment":
        cur.execute("""
        SELECT id,pending,date FROM sales
        WHERE pending>0
        """)
        rows = cur.fetchall()

        if not rows:
            await update.message.reply_text("✅ No KK Pending")
            return

        msg = "💵 Send:\nID Amount\n\n"

        for r in rows:
            msg += f"ID {r[0]} | ₹{r[1]} | {r[2]}\n"

        context.user_data["mode"] = "kkpay"

        await update.message.reply_text(msg)
        return

    if txt == "💸 Pay Provider":
        context.user_data["mode"] = "providerpay"

        await update.message.reply_text(
            "💸 Send:\nKT 5000\nLT 7000"
        )
        return

    if txt == "📋 Stock":
        cur.execute("""
        SELECT id,provider,brand,holder
        FROM kits
        WHERE status='STOCK'
        """)
        rows = cur.fetchall()

        if not rows:
            await update.message.reply_text("📭 No Stock")
            return

        msg = "📋 Unsold Stock\n\n"

        for r in rows:
            msg += f"{r[0]} | {r[1]} | {r[2]} | {r[3]}\n"

        await update.message.reply_text(msg)
        return

    if txt == "🧾 KK Pending":
        cur.execute("""
        SELECT id,pending,date
        FROM sales
        WHERE pending>0
        """)
        rows = cur.fetchall()

        if not rows:
            await update.message.reply_text("✅ No Pending")
            return

        msg = "🧾 KK Pending\n\n"

        for r in rows:
            msg += f"ID {r[0]} | ₹{r[1]} | {r[2]}\n"

        await update.message.reply_text(msg)
        return

    if txt == "👤 Providers":
        for p in ["KT", "LT", "AK"]:
            cur.execute("""
            SELECT SUM(cost)
            FROM kits
            WHERE provider=?
            """, (p,))
            payable = cur.fetchone()[0] or 0

            cur.execute("""
            SELECT SUM(amount)
            FROM provider_payments
            WHERE provider=?
            """, (p,))
            paid = cur.fetchone()[0] or 0

            pending = payable - paid

            await update.message.reply_text(
                f"👤 {p}\n"
                f"Payable ₹{payable}\n"
                f"Paid ₹{paid}\n"
                f"Pending ₹{pending}"
            )
        return

    if txt == "📊 Reports":
        cur.execute("SELECT SUM(sell_price) FROM sales")
        sales_total = cur.fetchone()[0] or 0

        cur.execute("""
        SELECT SUM(cost)
        FROM kits
        WHERE status='SOLD'
        """)
        cost_total = cur.fetchone()[0] or 0

        cur.execute("""
        SELECT SUM(received)
        FROM sales
        """)
        received_total = cur.fetchone()[0] or 0

        profit = sales_total - cost_total

        await update.message.reply_text(
            f"📊 Reports\n\n"
            f"Sales ₹{sales_total}\n"
            f"Received ₹{received_total}\n"
            f"Cost ₹{cost_total}\n"
            f"Profit ₹{profit}"
        )
        return

    if txt == "📜 Ledger":
        cur.execute("""
        SELECT party,type,amount,date,note
        FROM ledger
        ORDER BY id DESC
        LIMIT 30
        """)
        rows = cur.fetchall()

        if not rows:
            await update.message.reply_text("📭 No Ledger Data")
            return

        msg = "📜 Latest Ledger\n\n"

        for r in rows:
            icon = "⬅️" if r[1] == "RECEIVED" else "➡️"
            msg += f"{r[3]} {icon} {r[0]} ₹{r[2]}\n"

        await update.message.reply_text(msg)
        return

# ==================================================
# APP
# ==================================================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(callbacks))
app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler)
)

print("Bot Running...")
app.run_polling()