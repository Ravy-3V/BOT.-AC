import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = "8779700912:AAGJqIRuoLlxXGqSZVFum9PE9fSm4_nbYjk"

conn = sqlite3.connect("hisab.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS entries (
id INTEGER PRIMARY KEY AUTOINCREMENT,
provider TEXT,
holder TEXT,
brand TEXT,
rate INTEGER,
deposit INTEGER,
balance INTEGER,
date TEXT,
payment_date TEXT
)
""")
conn.commit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hisaab Kitab Bot Ready")

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    provider, holder, brand = context.args[0], context.args[1], context.args[2]
    rate, deposit = int(context.args[3]), int(context.args[4])
    balance = rate - deposit
    date = datetime.now().strftime("%d/%m/%Y")
    cur.execute("INSERT INTO entries (provider,holder,brand,rate,deposit,balance,date,payment_date) VALUES (?,?,?,?,?,?,?,?)",
                (provider,holder,brand,rate,deposit,balance,date,"Pending"))
    conn.commit()
    await update.message.reply_text(f"Added. Balance ₹{balance}")

async def pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cur.execute("SELECT id,provider,holder,balance FROM entries WHERE balance>0")
    rows = cur.fetchall()
    if not rows:
        await update.message.reply_text("No pending")
        return
    msg="Pending:\\n"
    for r in rows:
        msg += f"ID:{r[0]} {r[1]} {r[2]} ₹{r[3]}\\n"
    await update.message.reply_text(msg)

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("add", add))
app.add_handler(CommandHandler("pending", pending))
app.run_polling()
