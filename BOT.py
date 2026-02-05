from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
import sqlite3
from datetime import datetime, timedelta

# ================= CONFIG =================
TOKEN = "8515514254:AAEp9mkYEOuZt13Fj1BHbGCTeAjLHBPXS2o"
ADMIN_ID = 6462125044
# =========================================

# ---------- DATABASE ----------
conn = sqlite3.connect("events.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    date TEXT,
    time TEXT
)
""")
conn.commit()

# ---------- BASIC COMMANDS ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Lachoo Events Notification Bot*\n\n"
        "Commands:\n"
        "/event - Upcoming events\n"
        "/help - Help",
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 *Commands*\n\n"
        "User:\n"
        "/event\n\n"
        "Admin:\n"
        "/add_event Event | YYYY-MM-DD | HH:MM\n"
        "/edit_event ID | Event | YYYY-MM-DD | HH:MM\n"
        "/delete_event ID",
        parse_mode="Markdown"
    )

# ---------- SHOW EVENTS ----------
async def event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT id, name, date, time FROM events ORDER BY date, time")
    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("📭 No upcoming events")
        return

    msg = "📅 *Upcoming Events*\n\n"
    for r in rows:
        msg += (
            f"🆔 ID: {r[0]}\n"
            f"🎉 {r[1]}\n"
            f"📆 {r[2]} ⏰ {r[3]}\n\n"
        )

    await update.message.reply_text(msg, parse_mode="Markdown")

# ---------- ADD EVENT ----------
async def add_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Only admin can add events")
        return

    text = " ".join(context.args)
    if "|" not in text:
        await update.message.reply_text(
            "❗ Format:\n/add_event Event | YYYY-MM-DD | HH:MM"
        )
        return

    try:
        name, date, time = [x.strip() for x in text.split("|")]
        event_time = datetime.strptime(
            date + " " + time, "%Y-%m-%d %H:%M"
        )
    except:
        await update.message.reply_text("❌ Date/Time format wrong")
        return

    cursor.execute(
        "INSERT INTO events (name, date, time) VALUES (?, ?, ?)",
        (name, date, time)
    )
    conn.commit()
    event_id = cursor.lastrowid

    await update.message.reply_text("✅ Event added successfully")

    # reminder (10 min before)
    reminder_time = event_time - timedelta(minutes=10)
    delay = (reminder_time - datetime.now()).total_seconds()

    if delay > 0:
        context.job_queue.run_once(
            send_reminder,
            when=delay,
            chat_id=update.effective_chat.id,
            data=name
        )

    # auto delete after 7 days
    delete_time = event_time + timedelta(days=7)
    delete_delay = (delete_time - datetime.now()).total_seconds()

    if delete_delay > 0:
        context.job_queue.run_once(
            auto_delete_event,
            when=delete_delay,
            data=event_id
        )

# ---------- EDIT EVENT ----------
async def edit_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Only admin can edit events")
        return

    text = " ".join(context.args)
    if text.count("|") != 3:
        await update.message.reply_text(
            "❗ Format:\n/edit_event ID | Event | YYYY-MM-DD | HH:MM"
        )
        return

    try:
        event_id, name, date, time = [x.strip() for x in text.split("|")]
        datetime.strptime(date + " " + time, "%Y-%m-%d %H:%M")
    except:
        await update.message.reply_text("❌ Invalid data")
        return

    cursor.execute(
        "UPDATE events SET name=?, date=?, time=? WHERE id=?",
        (name, date, time, event_id)
    )
    conn.commit()

    if cursor.rowcount == 0:
        await update.message.reply_text("❌ Event ID not found")
    else:
        await update.message.reply_text("✏️ Event updated successfully")

# ---------- DELETE EVENT ----------
async def delete_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Only admin can delete events")
        return

    if not context.args:
        await update.message.reply_text(
            "❗ Format:\n/delete_event ID"
        )
        return

    event_id = context.args[0]
    cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
    conn.commit()

    if cursor.rowcount == 0:
        await update.message.reply_text("❌ Event ID not found")
    else:
        await update.message.reply_text("🗑️ Event deleted successfully")

# ---------- REMINDER ----------
async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    event_name = context.job.data
    await context.bot.send_message(
        chat_id=context.job.chat_id,
        text=(
            "⏰ *Reminder!*\n\n"
            f"🎉 {event_name}\n"
            "Starts in 10 minutes!"
        ),
        parse_mode="Markdown"
    )

# ---------- AUTO DELETE ----------
async def auto_delete_event(context: ContextTypes.DEFAULT_TYPE):
    event_id = context.job.data
    cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
    conn.commit()
    print(f"🗑️ Event ID {event_id} auto-deleted after 7 days")

# ---------- BOT START ----------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("event", event))
app.add_handler(CommandHandler("add_event", add_event))
app.add_handler(CommandHandler("edit_event", edit_event))
app.add_handler(CommandHandler("delete_event", delete_event))

print("🤖 Lachoo Events Notification Bot is running...")
app.run_polling()
