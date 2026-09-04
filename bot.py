import asyncio
import logging
import os
import json
import datetime
import hashlib
import base64

import gspread
from google.oauth2.service_account import Credentials
from google.auth.exceptions import DefaultCredentialsError

from datetime import datetime, timezone, timedelta

# O'zbekiston vaqti (UTC+5)
UZB_TIMEZONE = timezone(timedelta(hours=5))
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, StateFilter  # ← StateFilter qo'shildi
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardRemove,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ilm_nuri_bot")

# ═══════════════════════════════════════════════
# 1. SOZLAMALAR
# ═══════════════════════════════════════════════
BOT_TOKEN = "8678044800:AAF9GGeTK1qS1dJMQayrq-J3qtKMhf39wdA"
ADMIN_IDS = [506343083]

CHANNEL_LINK = "https://t.me/ilmnuri_markazi"
CHANNEL_USERNAME = "@ilmnuri_markazi"
SHEETS_ID = "13DjVH9V9E9FARG-FTe230Ft4g1oBcvDhWGu15vGC3p0"
PLATFORM_BASE_URL = "https://osontalim.uz/student/rash"

FAN_LIST = ["Matematika", "Ona tili", "Ingliz tili", "Fizika", "Kimyo", "Biologiya", "Tarix", "Tabiiy fan", "Geografiya", "Prezident maktabi", "Ibn Sino maktabi", "Mental arifmetika", "Boshqa"]
SINF_LIST = [f"{i}-sinf" for i in range(1, 12)]


# ═══════════════════════════════════════════════
# 2. TOKEN YARATISH
# ═══════════════════════════════════════════════
def generate_user_token(telegram_id: int, full_name: str) -> str:
    """Foydalanuvchi uchun unikal token yaratish"""
    data = f"{telegram_id}_{full_name}_{datetime.now().timestamp()}"
    token = base64.urlsafe_b64encode(
        hashlib.sha256(data.encode()).digest()
    ).decode()[:16]
    return token


# ═══════════════════════════════════════════════
# 3. BOT VA DISPATCHER
# ═══════════════════════════════════════════════
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def is_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status not in ("left", "kicked")
    except Exception as e:
        log.warning("Obuna tekshirishda xato: %s", e)
        return False


def subscribe_keyboard(action: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📣 Kanalga obuna bo'lish", url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="✅ Obuna bo'ldim, tekshirish", callback_data=f"check_sub:{action}")],
    ])


async def send_subscription_required(message: types.Message, action: str):
    await message.answer(
        "📢 Botdan foydalanish uchun avval bizning rasmiy kanalimizga obuna bo'ling:\n"
        f"{CHANNEL_LINK}\n\n"
        "Obuna bo'lgach, pastdagi tugmani bosing 👇",
        reply_markup=subscribe_keyboard(action),
    )


# ═══════════════════════════════════════════════
# 4. GOOGLE SHEETS BILAN ISHLASH (TUZATILGAN)
# ═══════════════════════════════════════════════
SHEET_HEADERS = [
    "ID", "Telegram_ID", "Ism_Familiya", "Maktab",
    "Sinf", "Fan", "Telefon", "Token", "Ro'yxatdan_o'tgan_sana"
]

TEST_RESULT_HEADERS = [
    "ID", "Telegram_ID", "Ism_Familiya", "Fan",
    "To'g'ri", "Noto'g'ri", "Jami", "Foiz", "Sana", "Token"
]

_gs_client = None


def get_credentials():
    """Google Sheets uchun credentials olish"""
    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/spreadsheets"
    ]
    
    # 1-usul: credentials.json fayldan
    try:
        if os.path.exists("credentials.json"):
            log.info("credentials.json fayli topildi")
            return Credentials.from_service_account_file("credentials.json", scopes=scopes)
    except Exception as e:
        log.warning(f"credentials.json dan yuklashda xato: {e}")
    
    # 2-usul: GOOGLE_CREDENTIALS muhit o'zgaruvchisidan
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if creds_json:
        try:
            log.info("GOOGLE_CREDENTIALS muhit o'zgaruvchisi topildi")
            info = json.loads(creds_json)
            return Credentials.from_service_account_info(info, scopes=scopes)
        except Exception as e:
            log.warning(f"GOOGLE_CREDENTIALS dan yuklashda xato: {e}")
    
    log.error("Google Sheets credentials topilmadi!")
    return None


def get_client():
    """Google Sheets client olish"""
    global _gs_client
    if _gs_client is None:
        creds = get_credentials()
        if not creds:
            log.error("Credentials mavjud emas!")
            return None
        try:
            _gs_client = gspread.authorize(creds)
            log.info("Google Sheets ga ulanish muvaffaqiyatli!")
        except Exception as e:
            log.error(f"Google Sheets ulanishda xato: {e}")
            return None
    return _gs_client


def get_registration_sheet():
    """Ro'yxatdan o'tganlar jadvalini olish"""
    try:
        client = get_client()
        if not client:
            log.error("Google Sheets client topilmadi!")
            return None
        
        sh = client.open_by_key(SHEETS_ID)
        log.info(f"Sheets ochildi: {SHEETS_ID}")
        
        try:
            ws = sh.worksheet("Royxatdan_otganlar")
            log.info("Royxatdan_otganlar jadvali topildi")
        except gspread.WorksheetNotFound:
            log.info("Royxatdan_otganlar jadvali topilmadi, yangi yaratilmoqda...")
            ws = sh.add_worksheet(title="Royxatdan_otganlar", rows="2000", cols="10")
            ws.append_row(SHEET_HEADERS)
            log.info("Yangi jadval yaratildi")
        
        return ws
    except Exception as e:
        log.error(f"Google Sheets ulanish xatosi: {e}")
        return None


def get_test_results_sheet():
    """Test natijalari jadvalini olish"""
    try:
        client = get_client()
        if not client:
            return None
        
        sh = client.open_by_key(SHEETS_ID)
        try:
            ws = sh.worksheet("Test_natijalari")
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title="Test_natijalari", rows="2000", cols="10")
            ws.append_row(TEST_RESULT_HEADERS)
        return ws
    except Exception as e:
        log.error(f"Test natijalari jadvalini olishda xato: {e}")
        return None


REGISTERED_USERS = {}
ROW_COUNTER = [0]
TEST_RESULT_COUNTER = [0]


def load_registrations_to_cache():
    """Google Sheets dan ro'yxatni yuklash"""
    REGISTERED_USERS.clear()
    ws = get_registration_sheet()
    if not ws:
        log.warning("Ro'yxat jadvali topilmadi, kesh bo'sh")
        return
    
    try:
        rows = ws.get_all_values()
        log.info(f"Jadvaldan {len(rows)} ta qator olindi")
        
        max_id = 0
        for row in rows[1:]:  # Headerdan keyin
            if not row or not row[0]:
                continue
            try:
                reg_id = int(row[0])
            except ValueError:
                continue
            
            max_id = max(max_id, reg_id)
            
            # Telegram ID ni int ga o'tkazish
            try:
                telegram_id = int(row[1])
            except (ValueError, IndexError):
                continue
            
            REGISTERED_USERS[telegram_id] = {
                "id": reg_id,
                "telegram_id": telegram_id,
                "full_name": row[2] if len(row) > 2 else "",
                "school": row[3] if len(row) > 3 else "",
                "grade": row[4] if len(row) > 4 else "",
                "subject": row[5] if len(row) > 5 else "",
                "phone": row[6] if len(row) > 6 else "",
                "token": row[7] if len(row) > 7 else "",
                "created_at": row[8] if len(row) > 8 else "",
            }
        
        ROW_COUNTER[0] = max_id
        log.info(f"Ro'yxat yuklandi: {len(REGISTERED_USERS)} ta foydalanuvchi")
        
    except Exception as e:
        log.error(f"Ro'yxatni yuklashda xato: {e}")


def is_registered(telegram_id: int) -> bool:
    return telegram_id in REGISTERED_USERS


def save_registration(telegram_id, full_name, school, grade, subject, phone):
    """Foydalanuvchini Google Sheets ga saqlash"""
    ROW_COUNTER[0] += 1
    reg_id = ROW_COUNTER[0]
    created_at = datetime.now(UZB_TIMEZONE).strftime("%d.%m.%Y %H:%M")
    
    # Unikal token yaratish
    token = generate_user_token(telegram_id, full_name)

    # Keshlash
    REGISTERED_USERS[telegram_id] = {
        "id": reg_id,
        "telegram_id": telegram_id,
        "full_name": full_name,
        "school": school,
        "grade": grade,
        "subject": subject,
        "phone": phone,
        "token": token,
        "created_at": created_at,
    }

    # Google Sheets ga yozish
    ws = get_registration_sheet()
    if ws:
        try:
            row_data = [reg_id, telegram_id, full_name, school, grade, subject, phone, token, created_at]
            ws.append_row(row_data)
            log.info(f"Foydalanuvchi saqlandi: {full_name} (ID: {reg_id})")
            return reg_id
        except Exception as e:
            log.error(f"Google Sheets'ga yozishda xato: {e}")
            # Xatolik haqida adminlarga xabar yuborish
            asyncio.create_task(notify_admin_error(f"Google Sheets ga yozish xatosi: {e}"))
    else:
        log.error("Google Sheets jadvali topilmadi!")
    
    return reg_id


def save_test_result(telegram_id, full_name, subject, correct, wrong, total, percentage, token):
    """Test natijasini Google Sheets ga saqlash"""
    TEST_RESULT_COUNTER[0] += 1
    result_id = TEST_RESULT_COUNTER[0]
    created_at = datetime.now(UZB_TIMEZONE).strftime("%d.%m.%Y %H:%M")

    ws = get_test_results_sheet()
    if ws:
        try:
            ws.append_row([result_id, telegram_id, full_name, subject, correct, wrong, total, percentage, created_at, token])
            log.info(f"Test natijasi saqlandi: {full_name} - {correct}/{total}")
        except Exception as e:
            log.error(f"Test natijasini yozishda xato: {e}")
    else:
        log.error("Test natijalari jadvali topilmadi!")


async def notify_admin_error(error_msg: str):
    """Adminlarga xatolik haqida xabar yuborish"""
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"⚠️ Google Sheets xatosi:\n\n{error_msg}\n\n"
                f"📌 credentials.json fayli borligini tekshiring.\n"
                f"📌 Sheets ID to'g'riligini tekshiring."
            )
        except Exception:
            pass


def get_all_registered_telegram_ids():
    return list(REGISTERED_USERS.keys())


def get_registered_count():
    return len(REGISTERED_USERS)


# ═══════════════════════════════════════════════
# 5. HOLATLAR (FSM STATES)
# ═══════════════════════════════════════════════
class Registration(StatesGroup):
    full_name = State()
    school = State()
    grade = State()
    subject = State()
    phone = State()


class AdminBroadcast(StatesGroup):
    waiting_text = State()
    confirm = State()


# ═══════════════════════════════════════════════
# 6. KLAVIATURALAR
# ═══════════════════════════════════════════════
def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Ro'yxatdan o'tish")],
            [KeyboardButton(text="🧪 Test topshirish")],
            [KeyboardButton(text="👤 Profilim")],
        ],
        resize_keyboard=True,
    )


def registered_main_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🧪 Test topshirish")],
            [KeyboardButton(text="📊 Natijalarim")],
            [KeyboardButton(text="👤 Profilim")],
            [KeyboardButton(text="🔄 Fan o'zgartirish")],
        ],
        resize_keyboard=True,
    )


def phone_request_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📲 Telefon raqamni yuborish", request_contact=True)],
            [KeyboardButton(text="⬅️ Orqaga")],
        ],
        resize_keyboard=True,
    )


def grade_inline_keyboard():
    rows, current = [], []
    for i, g in enumerate(SINF_LIST, 1):
        current.append(InlineKeyboardButton(text=g, callback_data=f"grade_{g}"))
        if i % 3 == 0:
            rows.append(current)
            current = []
    if current:
        rows.append(current)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def subject_inline_keyboard():
    rows, current = [], []
    for i, s in enumerate(FAN_LIST, 1):
        current.append(InlineKeyboardButton(text=s, callback_data=f"subject_{s}"))
        if i % 2 == 0:
            rows.append(current)
            current = []
    if current:
        rows.append(current)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_panel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Barchaga xabar yuborish", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📈 Test natijalari", callback_data="admin_test_results")],
    ])


def confirm_keyboard(yes_cb: str, no_cb: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha, yuborish", callback_data=yes_cb)],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=no_cb)],
    ])


def get_test_platform_link(user):
    """Foydalanuvchi uchun platforma linkini yaratish"""
    token = user.get("token", "")
    telegram_id = user.get("telegram_id", "")
    subject = user.get("subject", "")
    grade = user.get("grade", "")
    
    link = (
        f"{PLATFORM_BASE_URL}"
        f"?token={token}"
        f"&user_id={telegram_id}"
        f"&subject={subject}"
        f"&grade={grade}"
    )
    return link


# ═══════════════════════════════════════════════
# 7. /START VA ADMIN
# ═══════════════════════════════════════════════
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user = REGISTERED_USERS.get(message.from_user.id)

    if user:
        await message.answer(
            f"👋 Salom, {user['full_name']}!\n\n"
            f"✅ Siz allaqachon ro'yxatdan o'tgansiz.\n"
            f"📚 Sinf: {user['grade']}\n"
            f"📘 Fan: {user['subject']}\n\n"
            f"🧪 Test topshirish uchun pastdagi tugmani bosing!",
            reply_markup=registered_main_menu_keyboard(),
        )
        return

    await message.answer(
        "🌟 Assalomu alaykum!\n\n"
        "🏆 Ilm Nuri: Kelajak Olimpiadasi botiga xush kelibsiz!\n\n"
        "📝 Testda qatnashish uchun avval ro'yxatdan o'ting.\n"
        "Ro'yxatdan o'tish 1 daqiqa davom etadi!\n\n"
        "Quyidagi tugmani bosing 👇",
        reply_markup=main_menu_keyboard(),
    )


@dp.message(Command("admin"))
async def cmd_admin(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Sizda admin huquqlari mavjud emas!")
        return
    await state.clear()
    await message.answer(
        "🛠 Admin panel\n\n"
        f"👥 Ro'yxatdan o'tganlar soni: {get_registered_count()}",
        reply_markup=admin_panel_keyboard(),
    )


# ═══════════════════════════════════════════════
# 8. RO'YXATDAN O'TISH
# ═══════════════════════════════════════════════
@dp.message(F.text == "📝 Ro'yxatdan o'tish")
async def start_registration(message: types.Message, state: FSMContext):
    if is_registered(message.from_user.id):
        await message.answer(
            "✅ Siz allaqachon ro'yxatdan o'tgansiz!\n\n"
            "🧪 Test topshirish tugmasini bosing.",
            reply_markup=registered_main_menu_keyboard(),
        )
        return
    
    if not await is_subscribed(message.from_user.id):
        await send_subscription_required(message, "register")
        return
    
    await ask_full_name(message, state)


async def ask_full_name(message: types.Message, state: FSMContext):
    await message.answer(
        "👇 Ism va familiyangizni to'liq kiriting:\n"
        "Masalan: Alisherov Vali",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(Registration.full_name)


@dp.message(Registration.full_name)
async def reg_full_name(message: types.Message, state: FSMContext):
    text = (message.text or "").strip()
    if len(text) < 3:
        await message.answer("❌ Iltimos, ism va familiyangizni to'liq kiriting.")
        return
    await state.update_data(full_name=text)
    await message.answer(
        "🏫 Maktabingiz nomi yoki raqamini kiriting:\n"
        "Masalan: 5 yoki IDUM"
    )
    await state.set_state(Registration.school)


@dp.message(Registration.school)
async def reg_school(message: types.Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text:
        await message.answer("❌ Iltimos, maktab nomini kiriting.")
        return
    await state.update_data(school=text)
    await message.answer(
        "🎒 Sinfingizni tanlang:",
        reply_markup=grade_inline_keyboard()
    )
    await state.set_state(Registration.grade)


@dp.callback_query(Registration.grade, F.data.startswith("grade_"))
async def reg_grade(callback: types.CallbackQuery, state: FSMContext):
    grade = callback.data.split("_", 1)[1]
    await state.update_data(grade=grade)
    await callback.message.edit_text(f"✅ Sinf: {grade}")
    await callback.message.answer(
        "📘 Fanni tanlang (qaysi fandan test topshirmoqchisiz?):",
        reply_markup=subject_inline_keyboard()
    )
    await state.set_state(Registration.subject)
    await callback.answer()


@dp.callback_query(Registration.subject, F.data.startswith("subject_"))
async def reg_subject(callback: types.CallbackQuery, state: FSMContext):
    subject = callback.data.split("_", 1)[1]
    await state.update_data(subject=subject)
    await callback.message.edit_text(f"✅ Fan: {subject}")
    await callback.message.answer(
        "📞 Telefon raqamingizni yuboring:\n"
        "(tugma orqali yoki qo'lda yozing)",
        reply_markup=phone_request_keyboard(),
    )
    await state.set_state(Registration.phone)
    await callback.answer()


@dp.message(Registration.phone)
async def reg_phone(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Orqaga":
        await message.answer(
            "📘 Fanni qaytadan tanlang:",
            reply_markup=ReplyKeyboardRemove()
        )
        await message.answer(
            "📘 Fanni tanlang:",
            reply_markup=subject_inline_keyboard()
        )
        await state.set_state(Registration.subject)
        return

    phone = message.contact.phone_number if message.contact else (message.text or "").strip()
    if not phone or len(phone) < 7:
        await message.answer("❌ Iltimos, to'g'ri telefon raqam kiriting yoki tugmadan foydalaning.")
        return

    data = await state.get_data()
    
    # Google Sheets ga saqlash
    try:
        save_registration(
            telegram_id=message.from_user.id,
            full_name=data["full_name"],
            school=data["school"],
            grade=data["grade"],
            subject=data["subject"],
            phone=phone,
        )
        
        user = REGISTERED_USERS.get(message.from_user.id)
        token = user["token"] if user else ""

        await message.answer(
            "🎉 Tabriklaymiz!\n\n"
            "✅ Siz muvaffaqiyatli ro'yxatdan o'tdingiz!\n\n"
            f"👤 {data['full_name']}\n"
            f"🏫 {data['school']}\n"
            f"🎒 {data['grade']}\n"
            f"📘 {data['subject']}\n"
            f"📞 {phone}\n"
            f"🔑 Token: `{token}`\n\n"
            "🧪 Endi test topshirishingiz mumkin!\n"
            "Pastdagi tugmani bosing 👇",
            reply_markup=registered_main_menu_keyboard(),
        )
        
    except Exception as e:
        log.error(f"Ro'yxatdan o'tishda xato: {e}")
        await message.answer(
            "❌ Xatolik yuz berdi! Iltimos, qayta urinib ko'ring.\n"
            f"Xato: {str(e)}"
        )
    
    await state.clear()

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"🆕 Yangi ro'yxatdan o'tish!\n"
                f"👤 {data['full_name']}\n"
                f"🏫 {data['school']}\n"
                f"🎒 {data['grade']}\n"
                f"📘 {data['subject']}\n"
                f"📞 {phone}",
            )
        except Exception:
            pass


# ═══════════════════════════════════════════════
# 9. FAN O'ZGARTIRISH
# ═══════════════════════════════════════════════
@dp.message(F.text == "🔄 Fan o'zgartirish")
async def change_subject(message: types.Message, state: FSMContext):
    if not is_registered(message.from_user.id):
        await message.answer(
            "❌ Siz hali ro'yxatdan o'tmagansiz.",
            reply_markup=main_menu_keyboard()
        )
        return
    
    await message.answer(
        "📘 Qaysi fanga o'zgartirmoqchisiz?",
        reply_markup=subject_inline_keyboard()
    )
    await state.set_state("changing_subject")


@dp.callback_query(F.data.startswith("subject_"))
async def change_subject_callback(callback: types.CallbackQuery, state: FSMContext):
    # State ni tekshirish
    current_state = await state.get_state()
    if current_state != "changing_subject":
        await callback.answer("❌ Bu holatda emassiz!")
        return
    
    subject = callback.data.split("_", 1)[1]
    
    # Foydalanuvchini yangilash
    user = REGISTERED_USERS.get(callback.from_user.id)
    if user:
        # Google Sheets da yangilash
        ws = get_registration_sheet()
        if ws:
            try:
                # Foydalanuvchini topish va yangilash
                cell = ws.find(str(callback.from_user.id), in_column=2)
                if cell:
                    ws.update_cell(cell.row, 6, subject)  # 6-column = Fan
                    user["subject"] = subject
                    log.info(f"Fan o'zgartirildi: {user['full_name']} -> {subject}")
            except Exception as e:
                log.error(f"Fanni yangilashda xato: {e}")
    
    await callback.message.edit_text(f"✅ Fan muvaffaqiyatli o'zgartirildi: {subject}")
    await callback.message.answer(
        f"📘 Endi sizning faningiz: {subject}\n\n"
        "🧪 Test topshirish tugmasini bosing!",
        reply_markup=registered_main_menu_keyboard()
    )
    await state.clear()
    await callback.answer()


# ═══════════════════════════════════════════════
# 10. TEST TOPSHIRISH
# ═══════════════════════════════════════════════
@dp.message(F.text == "🧪 Test topshirish")
async def open_test_platform(message: types.Message):
    if not is_registered(message.from_user.id):
        await message.answer(
            "❌ Testda qatnashish uchun avval ro'yxatdan o'tishingiz kerak.\n\n"
            "📝 Ro'yxatdan o'tish tugmasini bosing.",
            reply_markup=main_menu_keyboard(),
        )
        return
    
    if not await is_subscribed(message.from_user.id):
        await send_subscription_required(message, "test")
        return
    
    user = REGISTERED_USERS.get(message.from_user.id)
    
    # Platformaga link
    platform_url = get_test_platform_link(user)
    
    await message.answer(
        f"🧪 Test topshirish\n\n"
        f"👤 {user['full_name']}\n"
        f"📚 Sinf: {user['grade']}\n"
        f"📘 Fan: {user['subject']}\n\n"
        f"⚠️ Diqqat! Siz {user['subject']} fanidan test topshirasiz.\n"
        f"✅ Boshqa fan bo'yicha test uchun 'Fan o'zgartirish' tugmasini bosing.\n\n"
        f"🔽 Testni boshlash uchun tugmani bosing:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Testni boshlash", url=platform_url)],
        ]),
    )


@dp.callback_query(F.data.startswith("check_sub:"))
async def check_subscription_callback(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data.split(":", 1)[1]

    if not await is_subscribed(callback.from_user.id):
        await callback.answer(
            "❌ Siz hali kanalga obuna bo'lmadingiz!",
            show_alert=True,
        )
        return

    await callback.answer("✅ Obuna tasdiqlandi!")
    try:
        await callback.message.delete()
    except Exception:
        pass

    if action == "register":
        if is_registered(callback.from_user.id):
            await callback.message.answer(
                "✅ Siz allaqachon ro'yxatdan o'tgansiz!",
                reply_markup=registered_main_menu_keyboard(),
            )
        else:
            await ask_full_name(callback.message, state)
    elif action == "test":
        await open_test_platform(callback.message)


# ═══════════════════════════════════════════════
# 11. NATIJALARIM
# ═══════════════════════════════════════════════
@dp.message(F.text == "📊 Natijalarim")
async def show_results(message: types.Message):
    user = REGISTERED_USERS.get(message.from_user.id)
    
    if not user:
        await message.answer(
            "❌ Siz hali ro'yxatdan o'tmagansiz.",
            reply_markup=main_menu_keyboard()
        )
        return
    
    ws = get_test_results_sheet()
    if not ws:
        await message.answer("❌ Natijalar hali mavjud emas.")
        return
    
    try:
        rows = ws.get_all_values()
        user_results = []
        for row in rows[1:]:
            if len(row) > 1 and int(row[1]) == message.from_user.id:
                user_results.append(row)
        
        if not user_results:
            await message.answer(
                "📊 Siz hali test topshirmagansiz.\n\n"
                "🧪 Test topshirish tugmasini bosing!",
                reply_markup=registered_main_menu_keyboard()
            )
            return
        
        result_text = "📊 Sizning natijalaringiz:\n\n"
        for row in user_results[-5:]:
            result_text += (
                f"📘 {row[3]}\n"
                f"✅ To'g'ri: {row[4]} | ❌ Noto'g'ri: {row[5]}\n"
                f"📈 {row[7]}% | 📅 {row[8]}\n\n"
        )
        
        # O'rtacha foiz
        if len(user_results) > 0:
            percentages = [float(row[7]) for row in user_results if len(row) > 7]
            avg = sum(percentages) / len(percentages) if percentages else 0
            result_text += f"📊 O'rtacha natija: {round(avg, 1)}%"
        
        await message.answer(
            result_text,
            reply_markup=registered_main_menu_keyboard()
        )
        
    except Exception as e:
        log.error(f"Natijalarni o'qishda xato: {e}")
        await message.answer("❌ Natijalarni o'qishda xatolik yuz berdi.")


# ═══════════════════════════════════════════════
# 12. PROFIL
# ═══════════════════════════════════════════════
@dp.message(F.text == "👤 Profilim")
async def show_profile(message: types.Message):
    user = REGISTERED_USERS.get(message.from_user.id)
    if not user:
        await message.answer(
            "❌ Siz hali ro'yxatdan o'tmagansiz.",
            reply_markup=main_menu_keyboard(),
        )
        return
    
    await message.answer(
        f"👤 Profil\n\n"
        f"👤 {user['full_name']}\n"
        f"🏫 Maktab: {user['school']}\n"
        f"🎒 Sinf: {user['grade']}\n"
        f"📘 Fan: {user['subject']}\n"
        f"📞 Telefon: {user['phone']}\n"
        f"🔑 Token: `{user['token']}`\n"
        f"🗓 Ro'yxatdan o'tgan: {user['created_at']}",
        reply_markup=registered_main_menu_keyboard()
    )


# ═══════════════════════════════════════════════
# 13. ADMIN PANEL
# ═══════════════════════════════════════════════
@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return
    
    ws = get_test_results_sheet()
    total_tests = 0
    if ws:
        try:
            rows = ws.get_all_values()
            total_tests = len(rows) - 1
        except:
            pass
    
    await callback.answer(
        f"📊 Statistika:\n\n"
        f"👥 Ro'yxatdan o'tganlar: {get_registered_count()}\n"
        f"📝 Jami testlar: {total_tests}",
        show_alert=True
    )


@dp.callback_query(F.data == "admin_test_results")
async def admin_test_results(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return
    
    ws = get_test_results_sheet()
    if not ws:
        await callback.answer("❌ Test natijalari topilmadi.")
        return
    
    try:
        rows = ws.get_all_values()
        total_tests = len(rows) - 1
        
        if total_tests == 0:
            await callback.answer("📊 Hali hech kim test topshirmagan.", show_alert=True)
            return
        
        # Oxirgi 10 ta natija
        result_text = "📈 So'nggi test natijalari:\n\n"
        count = 0
        for row in reversed(rows[1:]):  # Eng oxirgidan boshlab
            if len(row) > 8:
                result_text += f"👤 {row[2]}\n"
                result_text += f"📘 {row[3]} | ✅ {row[4]} | ❌ {row[5]}\n"
                result_text += f"📈 {row[7]}% | 📅 {row[8]}\n\n"
                count += 1
                if count >= 10:
                    break
        
        if len(result_text) > 4000:
            result_text = result_text[:4000] + "..."
        
        await callback.message.answer(result_text)
        await callback.answer()
        
    except Exception as e:
        log.error(f"Admin test natijalarida xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi.")


@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.set_state(AdminBroadcast.waiting_text)
    await callback.message.answer("📢 Yubormoqchi bo'lgan xabar matnini kiriting:")
    await callback.answer()


@dp.message(AdminBroadcast.waiting_text)
async def admin_broadcast_text(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(text=message.text)
    await message.answer(
        f"Quyidagi xabar {get_registered_count()} ta foydalanuvchiga yuboriladi:\n\n{message.text}",
        reply_markup=confirm_keyboard("confirm_broadcast", "cancel_broadcast"),
    )
    await state.set_state(AdminBroadcast.confirm)


@dp.callback_query(AdminBroadcast.confirm, F.data == "confirm_broadcast")
async def admin_broadcast_confirm(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return
    data = await state.get_data()
    text = data["text"]
    await state.clear()
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)

    sent, failed = 0, 0
    for telegram_id in get_all_registered_telegram_ids():
        try:
            await bot.send_message(telegram_id, text)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)
    
    await callback.message.answer(f"✅ Xabar yuborildi.\nMuvaffaqiyatli: {sent}\nXato: {failed}")


@dp.callback_query(AdminBroadcast.confirm, F.data == "cancel_broadcast")
async def admin_broadcast_cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Bekor qilindi")
    await callback.message.edit_reply_markup(reply_markup=None)


# ═══════════════════════════════════════════════
# 14. ISHGA TUSHIRISH
# ═══════════════════════════════════════════════
async def main():
    load_registrations_to_cache()
    log.info("Bot ishga tushmoqda...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
