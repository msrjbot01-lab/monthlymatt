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

# State ConversationHandler untuk Input Transaksi & Pilih Bulan Rekap
KETERANGAN, KATEGORI, BANK_ASAL, BANK_TUJUAN, NOMINAL, BIAYA_ADM = range(6)
PILIH_BULAN = 10  # State khusus untuk rekap bulanan

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

def get_month_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["SEP", "OCT"],
            ["NOV", "DEC"],
            ["🔙 Kembali ke Menu Utama"]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

# --- HANDLERS TELEGRAM ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name or "mattsraj"
    msg = (
        f"🚀 *Halo {user_name}! Selamat Datang di Bot Monthly Savings MATT* 🚀\n\n"
        "✨ *Sistem Pintar Pencatat Keuangan & Anggaran Pribadi* ✨\n\n"
        "📌 *INFORMASI REKENING & PERUNTUKAN:*\n"
        "🏦 *BCA*\nMATTHEW - KEBUTUHAN\n\n"
        "🏦 *BLU BCA*\nMATTHEW - KEINGINAN\n\n"
        "🏦 *MANDIRI*\nMATTHEW - TABUNGAN\n\n"
        "Silakan pilih menu di bawah ini untuk mulai mengelola keuanganmu:"
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
        await update.message.reply_text(
            "📅 Silakan pilih **Bulan Rekap** yang ingin kamu lihat rinciannya:",
            parse_mode="Markdown",
            reply_markup=get_month_keyboard()
        )
        return PILIH_BULAN
    elif "Stop Bot" in text:
        await update.message.reply_text("🛑 Bot dinonaktifkan. Ketik /start untuk mengaktifkan kembali.", reply_markup=ReplyKeyboardRemove())

# --- HANDLER PILIH BULAN REKAP ---
async def handle_pilih_bulan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()
    
    if "KEMBALI" in text:
        await update.message.reply_text("Kembali ke menu utama:", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    month_rows = {
        "SEP": 3,
        "OCT": 5,
        "NOV": 7,
        "DEC": 9
    }

    if text not in month_rows:
        await update.message.reply_text("⚠️ Bulan tidak valid. Silakan pilih tombol bulan yang tersedia di bawah:", reply_markup=get_month_keyboard())
        return PILIH_BULAN

    doc = get_spreadsheet()
    if not doc:
        await update.message.reply_text("⚠️ Gagal terhubung ke Google Sheets.", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    try:
        sheet_pembagian = doc.worksheet(SHEET_PEMBAGIAN_NAME)
        target_row = month_rows[text]
        r_data = sheet_pembagian.row_values(target_row)

        # Ambil data dari kolom A sampai H berdasarkan gambar sheet pembagian
        kebutuhan_50 = r_data[0] if len(r_data) > 0 and r_data[0] != '' else '0'
        keinginan_30 = r_data[1] if len(r_data) > 1 and r_data[1] != '' else '0'
        tabungan_20  = r_data[2] if len(r_data) > 2 and r_data[2] != '' else '0'
        total_adm    = r_data[3] if len(r_data) > 3 and r_data[3] != '' else '0'
        total_masuk  = r_data[4] if len(r_data) > 4 and r_data[4] != '' else '0'
        biaya_adm    = r_data[5] if len(r_data) > 5 and r_data[5] != '' else '0'
        selisih      = r_data[6] if len(r_data) > 6 and r_data[6] != '' else '0'
        total_terpakai = r_data[7] if len(r_data) > 7 and r_data[7] != '' else '0'

        # Hitung sisa saldo/budget yang masih bisa digunakan (Total Masuk - Total Terpakai)
        try:
            clean_masuk = float(str(total_masuk).replace(',', ''))
            clean_pakai = float(str(total_terpakai).replace(',', ''))
            sisa_budget = clean_masuk - clean_pakai
            sisa_str = f"Rp {sisa_budget:,.0f}"
        except:
            sisa_str = "Rp 0"

        msg = (
            f"📊 *REKAPITULASI KEUANGAN BULAN {text}*\n\n"
            f"• *50% (Kebutuhan):* Rp {kebutuhan_50}\n"
            f"• *30% (Keinginan):* Rp {keinginan_30}\n"
            f"• *20% (Tabungan):* Rp {tabungan_20}\n"
            f"• *TOTAL + ADM:* Rp {total_adm}\n"
            f"• *TOTAL MASUK:* Rp {total_masuk}\n"
            f"• *BIAYA ADM:* Rp {biaya_adm}\n"
            f"• *SELISIH:* Rp {selisih}\n"
            f"• *TOTAL TERPAKAI:* Rp {total_terpakai}\n"
            f"• *SISA SALDO/BUDGET:* {sisa_str}"
        )
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_main_keyboard())
    except Exception as e:
        await update.message.reply_text(f"⚠️ Gagal membaca data bulan {text}: {e}", reply_markup=get_main_keyboard())

    return ConversationHandler.END

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
        text = update.message.text.strip()
        digits = ''.join(filter(str.isdigit, text))
        if not digits or text == "0" or text.startswith("0 ("):
            adm = 0.0
        else:
            adm = float(digits)

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
    await update.message.reply_text("🛑 Proses dibatalkan.", reply_markup=get_main_keyboard())
    return ConversationHandler.END

# --- MAIN ASYNC ENGINE ---
async def main():
    server = web.Application()
    server.router.add_get('/', handle_health_check)
    runner = web.AppRunner(server)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"Web server berjalan di port {port}")

    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()

    # Conversation handler untuk Input Transaksi
    conv_input = ConversationHandler(
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

    # Conversation handler untuk Pilih Bulan Rekap
    conv_rekap = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📊 Total Rekap$"), handle_saldo)],
        states={
            PILIH_BULAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_pilih_bulan)],
        },
        fallbacks=[CommandHandler("cancel", cancel_input)],
    )

    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(conv_input)
    app_bot.add_handler(conv_rekap)
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_saldo))

    await app_bot.initialize()
    await app_bot.start()
    await app_bot.updater.start_polling(drop_pending_updates=True)
    logging.info("Bot Telegram berhasil polling!")

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
