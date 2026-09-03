import asyncio
import logging
import os
import json
import datetime

import gspread

from aiogram.client.session.aiohttp import AiohttpSession
from google.oauth2.service_account import Credentials

from datetime import datetime, timezone, timedelta

# O'zbekiston vaqti (UTC+5)
UZB_TIMEZONE = timezone(timedelta(hours=5))
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, StateFilter
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
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8678044800:AAF9GGeTK1qS1dJMQayrq-J3qtKMhf39wdA")

ADMIN_IDS = [
    int(x) for x in os.environ.get("ADMIN_IDS", "506343083").split(",") if x.strip()
]

CHANNEL_LINK = "https://t.me/ilmnuri_markazi"
CHANNEL_USERNAME = "@ilmnuri_markazi"
SHEETS_ID = os.environ.get("SHEETS_ID", "13DjVH9V9E9FARG-FTe230Ft4g1oBcvDhWGu15vGC3p0")

TEST_PLATFORM_URL = os.environ.get("TEST_PLATFORM_URL", "https://osontalim.uz/student/rash")

FAN_LIST = ["Matematika", "Ona tili", "Ingliz tili", "Fizika", "Kimyo", "Biologiya", "Tarix", "Boshqa"]
SINF_LIST = [f"{i}-sinf" for i in range(1, 12)]

# Bot va Dispatcher obyektlari
# PythonAnywhere bepul tarifi uchun Proxy sozlamasi
session = AiohttpSession(proxy="http://proxy.server:3128")

bot = Bot(token=BOT_TOKEN, session=session)
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
# 2. GOOGLE SHEETS BILAN ISHLASH
# ═══════════════════════════════════════════════
SHEET_HEADERS = [
    "ID", "Telegram_ID", "Ism_Familiya", "Maktab",
    "Sinf", "Fan", "Telefon", "Ro'yxatdan_o'tgan_sana",
]

_gs_client = None


def get_credentials():
    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if creds_json:
        try:
            info = json.loads(creds_json)
            return Credentials.from_service_account_info(info, scopes=scopes)
        except Exception as e:
            log.warning("GOOGLE_CREDENTIALS muhit o'zgaruvchisini o'qishda xato: %s", e)
    try:
        return Credentials.from_service_account_file("credentials.json", scopes=scopes)
    except Exception as e:
        log.warning("credentials.json topilmadi: %s", e)
        return None


def get_client():
    global _gs_client
    if _gs_client is None:
        creds = get_credentials()
        if not creds:
            return None
        _gs_client = gspread.authorize(creds)
    return _gs_client


def get_registration_sheet():
    try:
        client = get_client()
        if not client:
            return None
        sh = client.open_by_key(SHEETS_ID)
        try:
            ws = sh.worksheet("Royxatdan_otganlar")
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title="Royxatdan_otganlar", rows="2000", cols="10")
            ws.append_row(SHEET_HEADERS)
        return ws
    except Exception as e:
        log.error("Google Sheets ulanish xatosi: %s", e)
        return None


REGISTERED_USERS = {}
ROW_COUNTER = [0]


def load_registrations_to_cache():
    REGISTERED_USERS.clear()
    ws = get_registration_sheet()
    if not ws:
        return
    try:
        rows = ws.get_all_values()
        max_id = 0
        for row in rows[1:]:
            if not row or not row[0]:
                continue
            try:
                reg_id = int(row[0])
            except ValueError:
                continue
            max_id = max(max_id, reg_id)
            REGISTERED_USERS[int(row[1])] = {
                "id": reg_id,
                "telegram_id": int(row[1]),
                "full_name": row[2] if len(row) > 2 else "",
                "school": row[3] if len(row) > 3 else "",
                "grade": row[4] if len(row) > 4 else "",
                "subject": row[5] if len(row) > 5 else "",
                "phone": row[6] if len(row) > 6 else "",
                "created_at": row[7] if len(row) > 7 else "",
            }
        ROW_COUNTER[0] = max_id
        log.info("Ro'yxat yuklandi: %d foydalanuvchi", len(REGISTERED_USERS))
    except Exception as e:
        log.error("Ro'yxatni yuklashda xato: %s", e)


def is_registered(telegram_id: int) -> bool:
    return telegram_id in REGISTERED_USERS


def save_registration(telegram_id, full_name, school, grade, subject, phone):
    ROW_COUNTER[0] += 1
    reg_id = ROW_COUNTER[0]
    created_at = datetime.now(UZB_TIMEZONE).strftime("%d.%m.%Y %H:%M")

    REGISTERED_USERS[telegram_id] = {
        "id": reg_id,
        "telegram_id": telegram_id,
        "full_name": full_name,
        "school": school,
        "grade": grade,
        "subject": subject,
        "phone": phone,
        "created_at": created_at,
    }

    ws = get_registration_sheet()
    if ws:
        try:
            ws.append_row([reg_id, telegram_id, full_name, school, grade, subject, phone, created_at])
        except Exception as e:
            log.error("Google Sheets'ga yozishda xato: %s", e)
    return reg_id


def get_all_registered_telegram_ids():
    return list(REGISTERED_USERS.keys())


def get_registered_count():
    return len(REGISTERED_USERS)


# ═══════════════════════════════════════════════
# 3. HOLATLAR (FSM STATES)
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


class AdminTestStart(StatesGroup):
    waiting_datetime = State()
    waiting_link = State()
    confirm = State()


# ═══════════════════════════════════════════════
# 4. KLAVIATURALAR
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
            [KeyboardButton(text="👤 Profilim")],
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
        [InlineKeyboardButton(text="🕐 Testni boshlash e'lonini yuborish", callback_data="admin_start_test")],
        [InlineKeyboardButton(text="📢 Barchaga xabar yuborish", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")],
    ])


def confirm_keyboard(yes_cb: str, no_cb: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha, yuborish", callback_data=yes_cb)],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=no_cb)],
    ])


# ═══════════════════════════════════════════════
# 5. /START VA ADMIN
# ═══════════════════════════════════════════════
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user = REGISTERED_USERS.get(message.from_user.id)

    if user:
        await message.answer(
            f"Salom, {user['full_name']}! ✋\n"
            f"Siz allaqachon ro'yxatdan o'tgansiz.\n\n"
            f"🏫 Maktab: {user['school']}\n"
            f"🎒 Sinf: {user['grade']}\n"
            f"📘 Fan: {user['subject']}",
            reply_markup=registered_main_menu_keyboard(),
        )
        return

    await message.answer(
        "Assalomu alaykum! 🌟\n\n"
        "🏆 Ilm Nuri: Kelajak Olimpiadasi botiga xush kelibsiz!\n\n"
        "Testda qatnashish uchun avval ro'yxatdan o'tishingiz kerak.\n"
        "Quyidagi tugma orqali boshlang 👇",
        reply_markup=main_menu_keyboard(),
    )


@dp.message(Command("admin"))
async def cmd_admin(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(
        "🛠 Admin panel\n\n"
        f"👥 Ro'yxatdan o'tganlar soni: {get_registered_count()}",
        reply_markup=admin_panel_keyboard(),
    )


# ═══════════════════════════════════════════════
# 6. RO'YXATDAN O'TISH
# ═══════════════════════════════════════════════
@dp.message(F.text == "📝 Ro'yxatdan o'tish")
async def start_registration(message: types.Message, state: FSMContext):
    if is_registered(message.from_user.id):
        await message.answer(
            "Siz allaqachon ro'yxatdan o'tgansiz ✅",
            reply_markup=registered_main_menu_keyboard(),
        )
        return
    if not await is_subscribed(message.from_user.id):
        await send_subscription_required(message, "register")
        return
    await ask_full_name(message, state)


async def ask_full_name(message: types.Message, state: FSMContext):
    await message.answer(
        "👇 Ism va familiyangizni to'liq kiriting:\nMasalan: Alisherov Vali",
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
    await message.answer("🏫 Maktabingiz nomi yoki raqamini kiriting:\nMasalan: 5-maktab")
    await state.set_state(Registration.school)


@dp.message(Registration.school)
async def reg_school(message: types.Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text:
        await message.answer("❌ Iltimos, maktab nomini kiriting.")
        return
    await state.update_data(school=text)
    await message.answer("🎒 Sinfingizni tanlang:", reply_markup=grade_inline_keyboard())
    await state.set_state(Registration.grade)


@dp.callback_query(Registration.grade, F.data.startswith("grade_"))
async def reg_grade(callback: types.CallbackQuery, state: FSMContext):
    grade = callback.data.split("_", 1)[1]
    await state.update_data(grade=grade)
    await callback.message.edit_text(f"🎒 Sinf: {grade} ✅")
    await callback.message.answer("📘 Fanni tanlang:", reply_markup=subject_inline_keyboard())
    await state.set_state(Registration.subject)
    await callback.answer()


@dp.callback_query(Registration.subject, F.data.startswith("subject_"))
async def reg_subject(callback: types.CallbackQuery, state: FSMContext):
    subject = callback.data.split("_", 1)[1]
    await state.update_data(subject=subject)
    await callback.message.edit_text(f"📘 Fan: {subject} ✅")
    await callback.message.answer(
        "📞 Telefon raqamingizni yuboring (tugma orqali yoki qo'lda yozing):",
        reply_markup=phone_request_keyboard(),
    )
    await state.set_state(Registration.phone)
    await callback.answer()


@dp.message(Registration.phone)
async def reg_phone(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Orqaga":
        await message.answer("📘 Fanni qaytadan tanlang:", reply_markup=ReplyKeyboardRemove())
        await message.answer("📘 Fanni tanlang:", reply_markup=subject_inline_keyboard())
        await state.set_state(Registration.subject)
        return

    phone = message.contact.phone_number if message.contact else (message.text or "").strip()
    if not phone or len(phone) < 7:
        await message.answer("❌ Iltimos, to'g'ri telefon raqam kiriting yoki tugmadan foydalaning.")
        return

    data = await state.get_data()
    save_registration(
        telegram_id=message.from_user.id,
        full_name=data["full_name"],
        school=data["school"],
        grade=data["grade"],
        subject=data["subject"],
        phone=phone,
    )

    await message.answer(
        "✅ Tabriklaymiz! Siz muvaffaqiyatli ro'yxatdan o'tdingiz.\n\n"
        f"👤 Ism familiya: {data['full_name']}\n"
        f"🏫 Maktab: {data['school']}\n"
        f"🎒 Sinf: {data['grade']}\n"
        f"📘 Fan: {data['subject']}\n"
        f"📞 Telefon: {phone}\n\n"
        "Test boshlanishi haqida shu yerda xabardor qilinasiz. 🔔",
        reply_markup=registered_main_menu_keyboard(),
    )
    await state.clear()

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"🆕 Yangi ro'yxatdan o'tish!\n"
                f"👤 {data['full_name']}\n🏫 {data['school']}  |  🎒 {data['grade']}  |  📘 {data['subject']}\n"
                f"📞 {phone}",
            )
        except Exception:
            pass


# ═══════════════════════════════════════════════
# 7. TEST TOPSHIRISH VA PROFIL
# ═══════════════════════════════════════════════
@dp.message(F.text == "🧪 Test topshirish")
async def open_test_platform(message: types.Message):
    if not is_registered(message.from_user.id):
        await message.answer(
            "❌ Testda qatnashish uchun avval ro'yxatdan o'tishingiz kerak.",
            reply_markup=main_menu_keyboard(),
        )
        return
    if not await is_subscribed(message.from_user.id):
        await send_subscription_required(message, "test")
        return
    await show_test_platform(message)


async def show_test_platform(message: types.Message):
    await message.answer(
        "🧪 Test platformasi\n\n"
        "Testni boshlash uchun quyidagi havolaga o'ting. "
        "Test faqat admin e'lon qilgan vaqtda faol bo'ladi.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Testni ochish", url=TEST_PLATFORM_URL)],
        ]),
    )


@dp.callback_query(F.data.startswith("check_sub:"))
async def check_subscription_callback(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data.split(":", 1)[1]

    if not await is_subscribed(callback.from_user.id):
        await callback.answer(
            "❌ Siz hali kanalga obuna bo'lmadingiz! Iltimos, avval obuna bo'ling.",
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
                "Siz allaqachon ro'yxatdan o'tgansiz ✅",
                reply_markup=registered_main_menu_keyboard(),
            )
        else:
            await ask_full_name(callback.message, state)
    elif action == "test":
        await show_test_platform(callback.message)


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
        f"👤 {user['full_name']}\n"
        f"🏫 Maktab: {user['school']}\n"
        f"🎒 Sinf: {user['grade']}\n"
        f"📘 Fan: {user['subject']}\n"
        f"📞 Telefon: {user['phone']}\n"
        f"🗓 Ro'yxatdan o'tgan: {user['created_at']}"
    )


# ═══════════════════════════════════════════════
# 8. ADMIN PANEL FUNKSIYALARI
# ═══════════════════════════════════════════════
@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return
    await callback.answer(f"👥 Jami ro'yxatdan o'tganlar: {get_registered_count()}", show_alert=True)


@dp.callback_query(F.data == "admin_start_test")
async def admin_start_test(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.set_state(AdminTestStart.waiting_datetime)
    await callback.message.answer(
        "🕐 Test qachon boshlanadi? Sanani va vaqtni yozing.\n"
        "Masalan: 15.06.2026 10:00\n\n"
        "Agar test HOZIR boshlansa, \"hozir\" deb yozing."
    )
    await callback.answer()


@dp.message(AdminTestStart.waiting_datetime)
async def admin_test_datetime(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(test_time=message.text.strip())
    await message.answer(
        "🔗 Test havolasini yuboring (agar standart havoladan foydalanilsa \"-\" deb yozing):"
    )
    await state.set_state(AdminTestStart.waiting_link)


@dp.message(AdminTestStart.waiting_link)
async def admin_test_link(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    link = message.text.strip()
    if link != "-":
        await state.update_data(test_link=link)
    else:
        await state.update_data(test_link=TEST_PLATFORM_URL)

    data = await state.get_data()
    preview = (
        f"🔔 E'TIBOR BERING!\n\n"
        f"🏆 Test boshlanish vaqti: {data['test_time']}\n"
        f"🔗 Havola: {data['test_link']}\n\n"
        f"Omad tilaymiz! 🍀"
    )
    await message.answer(
        f"Quyidagi e'lon {get_registered_count()} ta foydalanuvchiga yuboriladi:\n\n{preview}",
        reply_markup=confirm_keyboard("confirm_test_start", "cancel_test_start"),
    )
    await state.update_data(preview=preview)
    await state.set_state(AdminTestStart.confirm)


@dp.callback_query(AdminTestStart.confirm, F.data == "confirm_test_start")
async def admin_test_start_confirm(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return
    data = await state.get_data()
    preview = data["preview"]
    await state.clear()
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)

    sent, failed = await broadcast_message(preview, with_platform_button=True, link=data.get("test_link"))
    await callback.message.answer(f"✅ E'lon yuborildi.\nMuvaffaqiyatli: {sent}\nXato: {failed}")


@dp.callback_query(AdminTestStart.confirm, F.data == "cancel_test_start")
async def admin_test_start_cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Bekor qilindi")
    await callback.message.edit_reply_markup(reply_markup=None)


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

    sent, failed = await broadcast_message(text)
    await callback.message.answer(f"✅ Xabar yuborildi.\nMuvaffaqiyatli: {sent}\nXato: {failed}")


@dp.callback_query(AdminBroadcast.confirm, F.data == "cancel_broadcast")
async def admin_broadcast_cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Bekor qilindi")
    await callback.message.edit_reply_markup(reply_markup=None)


async def broadcast_message(text: str, with_platform_button: bool = False, link: str | None = None):
    kb = None
    if with_platform_button:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Testni ochish", url=link or TEST_PLATFORM_URL)]
        ])

    sent, failed = 0, 0
    for telegram_id in get_all_registered_telegram_ids():
        try:
            await bot.send_message(telegram_id, text, reply_markup=kb)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)
    return sent, failed


# ═══════════════════════════════════════════════
# 9. ISHGA TUSHIRISH
# ═══════════════════════════════════════════════
async def main():
    load_registrations_to_cache()
    log.info("Bot ishga tushmoqda...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
