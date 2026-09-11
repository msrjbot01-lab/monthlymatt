import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)

# --- KONFIGURASI ---
BOT_TOKEN = "8997458072:AAHEi_St3plnzLKQ98tN5rO2eSnGA0PDJhc"

# Logging untuk memantau aktivitas & error di terminal
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# State untuk alur percakapan (Input Transaksi)
KETERANGAN, KATEGORI, BANK_ASAL, BANK_TUJUAN, NOMINAL, BIAYA_ADM = range(6)

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

# --- HANDLERS UTAMA ---
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
        await update.message.reply_text("📊 *Rekapitualsi Total:* Fitur siap diintegrasikan.", parse_mode="Markdown")
    elif "Stop Bot" in text:
        await update.message.reply_text("🛑 Bot dinonaktifkan. Ketik /start untuk mengaktifkan kembali.", reply_markup=ReplyKeyboardRemove())
    else:
        await update.message.reply_text("⚠️ Perintah tidak dikenali. Silakan gunakan tombol menu yang tersedia.")

# --- MAIN RUNNER ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot Python sedang berjalan...")
    app.run_polling()