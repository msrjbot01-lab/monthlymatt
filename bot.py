import os
import json
import logging
import asyncio
from datetime import datetime
from aiohttp import web
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)

# --- KONFIGURASI BOT ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8997458072:AAHEi_St3plnzLKQ98tN5rO2eSnGA0PDJhc")
SPREADSHEET_NAME = "50/30/20 monthly spending"
SHEET_MAIN_NAME = "MATT88"
SHEET_PEMBAGIAN_NAME = "PEMBAGIAN 50% 30% 20 %"

# State ConversationHandler
KETERANGAN, KATEGORI, BANK_ASAL, BANK_TUJUAN, NOMINAL, BIAYA_ADM = range(6)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)

# --- KONEKSI GOOGLE SHEETS ---
def get_spreadsheet():
    try:
        creds_json = os.environ.get("GOOGLE_CREDENTIALS")
        if creds_json:
            creds_dict = json.loads(creds_json)
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            return client.open(SPREADSHEET_NAME)
    except Exception as e:
        logging.error(f"Error Google Sheets: {e}")
    return None

# --- WEB SERVER UNTUK RENDER (HEALTH CHECK) ---
async def handle_health_check(request):
    return web.Response(text="Bot Telegram Keuangan Aktif 24/7!")

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

def get_bank_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["BCA MATTHEW", "MANDIRI MATTHEW"],
            ["BLU MATTHEW"]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
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

async def handle_saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    doc = get_spreadsheet()
    
    if not doc:
        await update.message.reply_text("⚠️ Gagal terhubung ke Google Sheets.")
        return

    sheet = doc.worksheet(SHEET_MAIN_NAME)

    if "BCA" in text and "BLU" not in text:
        val = sheet.acell("H4").value
        await update.message.reply_text(f"💳 *Saldo BCA Matthew (KEBUTUHAN):*\nRp {val}", parse_mode="Markdown")
    elif "BLU" in text:
        val = sheet.acell("G4").value
        await update.message.reply_text(f"💳 *Saldo BLU BCA Matthew (KEINGINAN):*\nRp {val}", parse_mode="Markdown")
    elif "Mandiri" in text:
        val = sheet.acell("F4").value
        await update.message.reply_text(f"💳 *Saldo Mandiri Matthew (TABUNGAN):*\nRp {val}", parse_mode="Markdown")
    elif "Total Rekap" in text:
        try:
            sheet_pembagian = doc.worksheet(SHEET_PEMBAGIAN_NAME)
            r4 = sheet_pembagian.row_values(4)
            msg = (
                "📊 *REKAPITULASI TOTAL & PEMBAGIAN (50/30/20)*\n\n"
                f"• *50% (Kebutuhan):* Rp {r4[0] if len(r4) > 0 else '0'}\n"
                f"• *30% (Keinginan):* Rp {r4[1] if len(r4) > 1 else '0'}\n"
                f"• *20% (Tabungan):* Rp {r4[2] if len(r4) > 2 else '0'}\n"
                f"• *TOTAL + ADM:* Rp {r4[3] if len(r4) > 3 else '0'}\n"
                f"• *TOTAL MASUK:* Rp {r4[4] if len(r4) > 4 else '0'}\n"
                f"• *BIAYA ADM:* Rp {r4[5] if len(r4) > 5 else '0'}\n"
                f"• *SELISIH:* Rp {r4[6] if len(r4) > 6 else '0'}"
            )
            await update.message.reply_text(msg, parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Gagal membaca Sheet Pembagian: {e}")
    elif "Stop Bot" in text:
        await update.message.reply_text("🛑 Bot dinonaktifkan. Ketik /start untuk mengaktifkan kembali.", reply_markup=ReplyKeyboardRemove())

# --- ALUR INPUT TRANSAKSI ---
async def start_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    formatted_date = datetime.now().strftime("%d %b %Y")
    context.user_data["tgl"] = formatted_date

    await update.message.reply_text(
        f"📅 Tanggal otomatis diset: *{formatted_date}*\n\nSilakan masukkan *KETERANGAN* transaksi:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return KETERANGAN

async def input_keterangan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["keterangan"] = update.message.text
    keyboard = ReplyKeyboardMarkup(
        [["GAJI", "PINDAH DANA"], ["KEBUTUHAN", "KEINGINAN"]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await update.message.reply_text("Pilih *KATEGORI* transaksi:", reply_markup=keyboard, parse_mode="Markdown")
    return KATEGORI

async def input_kategori(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kategori = update.message.text.upper()
    context.user_data["kategori"] = kategori

    if "PINDAH" in kategori:
        await update.message.reply_text("Pilih *BANK ASAL* (Pengirim):", reply_markup=get_bank_keyboard(), parse_mode="Markdown")
        return BANK_ASAL
    else:
        await update.message.reply_text("Pilih *BANK REKENING*:", reply_markup=get_bank_keyboard(), parse_mode="Markdown")
        return BANK_TUJUAN

async def input_bank_asal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["bank_asal"] = update.message.text.upper()
    await update.message.reply_text("Pilih *BANK TUJUAN* (Penerima):", reply_markup=get_bank_keyboard(), parse_mode="Markdown")
    return BANK_TUJUAN

async def input_bank_tujuan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["bank_tujuan"] = update.message.text.upper()
    if "PINDAH" in context.user_data["kategori"]:
        context.user_data["keterangan"] = f"{context.user_data['bank_asal']} >> {context.user_data['bank_tujuan']}"

    await update.message.reply_text("Masukkan *NOMINAL* angka (contoh: 42901):", reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")
    return NOMINAL

async def input_nominal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        nom = float(''.join(filter(str.isdigit, update.message.text)))
        context.user_data["nominal"] = nom
        keyboard = ReplyKeyboardMarkup([["0 (Lewati)"]], resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("Masukkan *BIAYA ADMIN* jika ada (atau pilih 0):", reply_markup=keyboard, parse_mode="Markdown")
        return BIAYA_ADM
    except ValueError:
        await update.message.reply_text("Nominal harus berupa angka! Silakan masukkan ulang:")
        return NOMINAL

async def input_biaya_adm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text
        adm = 0.0 if "0" in text else float(''.join(filter(str.isdigit, text)))
        context.user_data["biaya_adm"] = adm

        doc = get_spreadsheet()
        if doc:
            sheet = doc.worksheet(SHEET_MAIN_NAME)
            mandiri, blu, bca = "", "", ""
            adm_val = -adm if adm > 0 else ""
            nom = context.user_data["nominal"]
            kat = context.user_data["kategori"]

            if "PINDAH" in kat:
                asal = context.user_data["bank_asal"]
                tujuan = context.user_data["bank_tujuan"]
                
                if "MANDIRI" in asal: mandiri = -(nom + adm)
                elif "MANDIRI" in tujuan: mandiri = nom

                if "BLU" in asal: blu = -(nom + adm)
                elif "BLU" in tujuan: blu = nom

                if "BCA" in asal and "BLU" not in asal: bca = -(nom + adm)
                elif "BCA" in tujuan and "BLU" not in tujuan: bca = nom
            else:
                val = nom if "GAJI" in kat else -nom
                tujuan = context.user_data["bank_tujuan"]
                if "MANDIRI" in tujuan: mandiri = val
                if "BLU" in tujuan: blu = val
                if "BCA" in tujuan and "BLU" not in tujuan: bca = val

            # --- CARI BARIS KOSONG PERTAMA BERDASARKAN KOLOM A ---
            col_a_values = sheet.col_values(1)
            next_row = len(col_a_values) + 1
            if next_row < 6:
                next_row = 6

            row_data = [
                context.user_data["tgl"],
                context.user_data["keterangan"],
                kat,
                "",
                "",
                mandiri,
                blu,
                bca,
                adm_val
            ]

            sheet.update(f"A{next_row}:I{next_row}", [row_data])

            await update.message.reply_text(
                f"✅ *BERHASIL DI-INPUT KE BARIS {next_row}!*\n\n"
                f"📅 Tanggal: {context.user_data['tgl']}\n"
                f"📝 Keterangan: {context.user_data['keterangan']}\n"
                f"🏷 Kategori: {context.user_data['kategori']}\n"
                f"💵 Nominal: Rp {nom:,.0f}\n"
                f"💸 Biaya Adm: Rp {adm:,.0f}",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
        else:
            await update.message.reply_text("⚠️ Gagal menyimpan data ke Google Sheets.", reply_markup=get_main_keyboard())

    except Exception as e:
        logging.error(f"Error Save: {e}")
        await update.message.reply_text(f"⚠️ Terjadi kesalahan saat menyimpan data: {e}", reply_markup=get_main_keyboard())

    return ConversationHandler.END

async def cancel_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛑 Proses input dibatalkan.", reply_markup=get_main_keyboard())
    return ConversationHandler.END

# --- MAIN ASYNC ENGINE ---
async def main():
    # 1. Inisialisasi Web Server (aiohttp)
    server = web.Application()
    server.router.add_get('/', handle_health_check)
    runner = web.AppRunner(server)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"Web server berjalan di port {port}")

    # 2. Inisialisasi Telegram Bot Application
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📝 Input Transaksi$"), start_input)],
        states={
            KETERANGAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_keterangan)],
            KATEGORI: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_kategori)],
            BANK_ASAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_bank_asal)],
            BANK_TUJUAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_bank_tujuan)],
            NOMINAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_nominal)],
            BIAYA_ADM: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_biaya_adm)],
        },
        fallbacks=[CommandHandler("cancel", cancel_input)],
    )

    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(conv_handler)
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_saldo))

    # 3. Jalankan Polling secara Asynchronous murni
    await app_bot.initialize()
    await app_bot.start()
    await app_bot.updater.start_polling(drop_pending_updates=True)
    logging.info("Bot Telegram berhasil polling!")

    # Tetap jalankan proses selamanya
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
