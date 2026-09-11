import os
import logging
from threading import Thread
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# --- KONFIGURASI BOT ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# --- WEB SERVER UNTUK RENDER (DUMMY PORT) ---
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot Telegram Aktif 24/7!"

def run_flask():
    # Render otomatis menyediakan environment variable PORT
    port = int(os.environ.get("PORT", 8080))
    app_flask.run(host="0.0.0.0", port=port)

# --- KEYBOARD MENUS ---
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["💰 BCA", "💳 BLU BCA", "🏦 Mandiri"],
            ["📊 Total Rekap", "📝 Input Transaksi"],
            ["🛑 Stop Bot"]
        ],
        resize_keyboard=True
    )

# --- HANDLERS TELEGRAM ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🔥 *Halo Matthew! Selamat Datang di Bot Keuangan!* 🔥\n\n"
        "Saya siap membantu mencatat transaksi keuanganmu secara otomatis.\n\n"
        "📌 *INFORMASI REKENING & PERUNTUKAN:*\n"
        "🏦 *BCA*\nMATTHEW - KEBUTUHAN\n\n"
        "🏦 *BLU BCA*\nMATTHEW - KEINGINAN\n\n"
        "🏦 *MANDIRI*\nMATTHEW - TABUNGAN\n\n"
        "Silakan pilih menu di bawah ini:"
    )
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_main_keyboard())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if "BCA" in text and "BLU" not in text:
        await update.message.reply_text("💳 *Saldo BCA Matthew (KEBUTUHAN):*\nFitur baca Google Sheets siap diintegrasikan.", parse_mode="Markdown")
    elif "BLU" in text:
        await update.message.reply_text("💳 *Saldo BLU BCA Matthew (KEINGINAN):*\nFitur baca Google Sheets siap diintegrasikan.", parse_mode="Markdown")
    elif "Mandiri" in text:
        await update.message.reply_text("💳 *Saldo Mandiri Matthew (TABUNGAN):*\nFitur baca Google Sheets siap diintegrasikan.", parse_mode="Markdown")
    elif "Total Rekap" in text:
        await update.message.reply_text("📊 *Rekapitulasi Total:* Fitur siap diintegrasikan.", parse_mode="Markdown")
    elif "Stop Bot" in text:
        await update.message.reply_text("🛑 Bot dinonaktifkan. Ketik /start untuk mengaktifkan kembali.", reply_markup=ReplyKeyboardRemove())
    else:
        await update.message.reply_text("⚠️ Perintah tidak dikenali. Silakan gunakan tombol menu yang tersedia.")

# --- MAIN RUNNER ---
if __name__ == "__main__":
    # 1. Jalankan Flask Server di Background Thread
    server_thread = Thread(target=run_flask)
    server_thread.daemon = True
    server_thread.start()

    # 2. Jalankan Telegram Bot Polling
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot Python & Flask Web Server berjalan...")
    app_bot.run_polling()
