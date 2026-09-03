import asyncio
import logging
import random
import os
import time
import json
import datetime
import gspread
import aiohttp

from google.oauth2.service_account import Credentials
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

# ═══════════════════════════════════════════════
# 1. SOZLAMALAR VA BOT OB YEKTI (DP SOTILISHI)
# ═══════════════════════════════════════════════
BOT_TOKEN             = os.environ.get("BOT_TOKEN", "8678044800:AAF9GGeTK1qS1dJMQayrq-J3qtKMhf39wdA")
ADMIN_ID              = 506343083
TEST_DURATION_SECONDS = 45 * 60
CHANNEL_LINK          = "https://t.me/IlmNuri_Markazi"
CHANNEL_USERNAME      = "@IlmNuri_Markazi"
SHEETS_ID             = "1gvaXkcJStGAUi0DH8eIBaB7R8GVJfC0z2z38mHie6MY"

# Bot va Dispatcher obyektlarini barcha funksiya hamda handlerlardan O'Z VAQTIDA yaratamiz
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# VAB narxlari
VAB_PER_CORRECT_ANSWER = 2
VAB_FOR_TEST_PURCHASE  = 500
VAB_FOR_REFERRAL       = 50

# To'lov rekvizitlari
PAYMENT_CARD          = "8600 **** **** 1234"
PAYMENT_AMOUNT        = 10000
PAYMENT_OWNER         = "Ilm Nuri Markazi"

# INLIM sozlamalari
INLIM_SETTINGS = {
    "prize_fund": 10000000,
    "sponsors": [],
    "test_dates": [
        {"date": "2025-06-15", "grade": "1-6 sinf", "subject": "Matematika"},
        {"date": "2025-06-22", "grade": "1-6 sinf", "subject": "Matematika"},
        {"date": "2025-06-29", "grade": "1-6 sinf", "subject": "Matematika"},
    ],
    "registration_open": True,
    "admin_username": "@admin",
}

# ─── Admin ID tekshirish yordamchi funksiya ───────────────────
def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

async def is_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status not in ("left", "kicked")
    except Exception:
        return False

# ═══════════════════════════════════════════════
# 2. GOOGLE CREDENTIALS ENHANCED FOR RENDER
# ═══════════════════════════════════════════════
def get_credentials(scopes):
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if creds_json:
        try:
            info = json.loads(creds_json)
            return Credentials.from_service_account_info(info, scopes=scopes)
        except Exception as e:
            print(f"⚠️ Environment GOOGLE_CREDENTIALS xato: {e}")
    
    try:
        return Credentials.from_service_account_file("credentials.json", scopes=scopes)
    except Exception as e:
        print(f"⚠️ credentials.json topilmadi: {e}")
        return None

def get_sheet():
    try:
        scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = get_credentials(scopes)
        if not creds: return None
        client = gspread.authorize(creds)
        return client.open_by_key(SHEETS_ID).sheet1
    except Exception as e:
        print(f"⚠️ Google Sheets ulanish xatosi (sheet1): {e}")
        return None

def get_orders_sheet():
    try:
        scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = get_credentials(scopes)
        if not creds: return None
        client = gspread.authorize(creds)
        sh = client.open_by_key(SHEETS_ID)
        try:
            return sh.worksheet("Buyurtmalar")
        except Exception:
            ws = sh.add_worksheet(title="Buyurtmalar", rows="1000", cols="10")
            ws.append_row(["Buyurtma_ID","Telegram_ID","Ism","Sinf","Summa","Status","Sana"])
            return ws
    except Exception as e:
        print(f"⚠️ Google Sheets ulanish xatosi (Buyurtmalar): {e}")
        return None

def get_inlim_sheet():
    try:
        scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = get_credentials(scopes)
        if not creds: return None
        client = gspread.authorize(creds)
        sh = client.open_by_key(SHEETS_ID)
        try:
            return sh.worksheet("INLIM_Royxat")
        except Exception:
            ws = sh.add_worksheet(title="INLIM_Royxat", rows="1000", cols="12")
            ws.append_row([
                "ID", "Telegram_ID", "Ism", "Maktab", "Telefon",
                "Sinf_Guruh", "Test_Sanasi", "Format",
                "Tolov_Turi", "Status", "Sana_Vaqt"
            ])
            return ws
    except Exception as e:
        print(f"⚠️ Google Sheets ulanish xatosi (INLIM_Royxat): {e}")
        return None

DIFFICULTY_LABEL = {
    "easy":   "🟢 Oson",
    "medium": "🟡 O'rta",
    "hard":   "🔴 Qiyin",
}

def is_test_time(grade: str) -> bool:
    return True

def get_test_time_str(grade: str) -> str:
    return "istalgan vaqt"

MOTIVATIONAL_MESSAGES = [
    "💪 Zo'r ketayapsiz! Davom eting!",
    "🔥 Ajoyib! Har bir savol sizni aqlliroq qiladi!",
    "⚡ Harakatda davom eting, maqsadingizga yetasiz!",
    "🌟 Bilimingiz — kelajagingiz!",
    "🚀 Siz qila olasiz! Olimlar ham shunday boshlagan!",
    "🏆 Har bir to'g'ri javob g'alabaga bir qadam!",
    "🎯 Diqqatingizni jamlang — oldinga faqat oldinga!",
    "🌈 Qiyinchilik — bu o'sishning belgisi!",
]

# ═══════════════════════════════════════════════
# 3. TEST SAVOLLARI
# ═══════════════════════════════════════════════
TESTS = {
    "1-sinf": [
        {"question": "Hisoblang  2 + 3 + 4 ",
         "options": {"A": "8", "B": "9", "C": "10", "D": "11"},
         "answer": "B", "difficulty": "easy"},
    ]
}

PAID_TESTS = {
    "1-sinf": [
        {"question": "💎 Sehrli kvadrat: markaziy qator bo'sh katagi?",
         "options": {"A": "4", "B": "2", "C": "8", "D": "1"},
         "answer": "A", "difficulty": "hard"},
    ]
}

# ═══════════════════════════════════════════════
# 4. HOLATLAR
# ═══════════════════════════════════════════════
class Registration(StatesGroup):
    full_name = State()
    school    = State()
    phone     = State()

class TestProcess(StatesGroup):
    answering = State()

class AdminState(StatesGroup):
    waiting_for_ad_content = State()

class PaymentState(StatesGroup):
    waiting_check   = State()
    waiting_grade   = State()

class AdminConfirmState(StatesGroup):
    waiting_order_id = State()

class InlimRegistration(StatesGroup):
    checking_sub   = State()
    checking_share = State()
    full_name      = State()
    school         = State()
    phone          = State()
    grade_group    = State()
    test_date      = State()
    test_format    = State()
    payment        = State()

class AdminInlimState(StatesGroup):
    add_date        = State()
    set_prize       = State()
    add_sponsor     = State()
    set_admin_user  = State()

# ═══════════════════════════════════════════════
# 5. GOOGLE SHEETS (CACHE & DYNAMIC LOAD)
# ═══════════════════════════════════════════════
USERS_CACHE = {}
ORDER_CACHE = {}
INLIM_REGISTRATIONS = {}

ORDER_COUNTER = [1000]
INLIM_REG_COUNTER   = [2000]

def load_users_to_cache():
    global USERS_CACHE
    USERS_CACHE.clear()
    try:
        ws = get_sheet()
        if not ws: return
        rows = ws.get_all_values()
        for row in rows[1:]:
            if row[0]:
                user_id = int(row[0])
                USERS_CACHE[user_id] = {
                    "id":             user_id,
                    "telegram_id":    int(row[1]) if row[1] else None,
                    "full_name":      row[2],
                    "school":         row[3],
                    "grade":          row[4],
                    "phone":          row[5],
                    "score":          int(row[6]) if row[6] else 0,
                    "test_started":   int(row[7]) if row[7] else 0,
                    "vab":            int(row[8]) if len(row) > 8 and row[8] else 0,
                    "referral_count": int(row[9]) if len(row) > 9 and row[9] else 0,
                    "referred_by":    int(row[10]) if len(row) > 10 and row[10] else 0,
                    "paid_tests":     row[11] if len(row) > 11 else "",
                    "results":        row[12] if len(row) > 12 else "",
                }
        print(f"✅ Baza yuklandi: {len(USERS_CACHE)} ta o'quvchi.")
    except Exception as e:
        print(f"❌ Yuklashda xato: {e}")

def load_inlim_and_orders_to_cache():
    global ORDER_CACHE, INLIM_REGISTRATIONS
    ORDER_CACHE.clear()
    INLIM_REGISTRATIONS.clear()
    
    try:
        ws = get_inlim_sheet()
        if ws:
            rows = ws.get_all_values()
            max_id = 2000
            for row in rows[1:]:
                if row[0]:
                    reg_id = int(row[0])
                    max_id = max(max_id, reg_id)
                    INLIM_REGISTRATIONS[reg_id] = {
                        "reg_id":       reg_id,
                        "telegram_id":  int(row[1]) if row[1] else None,
                        "full_name":    row[2],
                        "school":       row[3],
                        "phone":        row[4],
                        "grade_group":  row[5],
                        "test_date":    row[6],
                        "test_format":  row[7],
                        "payment_type": row[8],
                        "status":       row[9],
                        "created_at":   row[10] if len(row) > 10 else "",
                    }
            INLIM_REG_COUNTER[0] = max_id
            print(f"✅ INLIM yuklandi: {len(INLIM_REGISTRATIONS)} ta.")
    except Exception as e:
        print(f"❌ INLIM yuklash xatosi: {e}")

    try:
        ws = get_orders_sheet()
        if ws:
            rows = ws.get_all_values()
            max_id = 1000
            for row in rows[1:]:
                if row[0]:
                    order_id = int(row[0])
                    max_id = max(max_id, order_id)
                    ORDER_CACHE[order_id] = {
                        "order_id":      order_id,
                        "telegram_id":   int(row[1]) if row[1] else None,
                        "full_name":     row[2],
                        "grade":         row[3],
                        "variant_index": 0,
                        "photo_file_id": "",
                        "status":        row[5],
                    }
            ORDER_COUNTER[0] = max_id
            print(f"✅ Buyurtmalar yuklandi: {len(ORDER_CACHE)} ta.")
    except Exception as e:
        print(f"❌ Buyurtma yuklash xatosi: {e}")

def add_user(telegram_id, full_name, school, grade, phone, referred_by=0):
    for user in USERS_CACHE.values():
        if user["telegram_id"] == telegram_id:
            return None
    try:
        ws = get_sheet()
        if not ws: return None
        rows = ws.get_all_values()
        new_id = len(rows)
        ws.append_row([new_id, telegram_id, full_name, school, grade, phone,
                       0, 0, 0, 0, referred_by, "", ""])
        USERS_CACHE[new_id] = {
            "id": new_id, "telegram_id": telegram_id,
            "full_name": full_name, "school": school,
            "grade": grade, "phone": phone,
            "score": 0, "test_started": 0,
            "vab": 0, "referral_count": 0,
            "referred_by": referred_by, "paid_tests": "", "results": "",
        }
        return new_id
    except Exception as e:
        print(f"add_user xato: {e}")
        return None

def get_user_by_id(user_id):
    return USERS_CACHE.get(user_id)

def get_user_by_telegram_id(telegram_id):
    for user in USERS_CACHE.values():
        if user["telegram_id"] == telegram_id:
            return user
    return None

def update_user_field(user_id, **kwargs):
    if user_id not in USERS_CACHE:
        return
    USERS_CACHE[user_id].update(kwargs)
    try:
        ws = get_sheet()
        if not ws: return
        rows = ws.get_all_values()
        col_map = {
            "score": 7, "test_started": 8, "vab": 9,
            "referral_count": 10, "paid_tests": 12, "results": 13,
            "grade": 5,
        }
        for i, row in enumerate(rows[1:], start=2):
            if row[0] and int(row[0]) == user_id:
                for field, val in kwargs.items():
                    col = col_map.get(field)
                    if col:
                        ws.update_cell(i, col, val)
                break
    except Exception as e:
        print(f"update_user_field xato: {e}")

def add_vab(user_id, amount):
    user = USERS_CACHE.get(user_id)
    if user:
        new_vab = user["vab"] + amount
        update_user_field(user_id, vab=new_vab)
        return new_vab
    return 0

# ═══════════════════════════════════════════════
# 6. YORDAMCHI FUNKSIYALAR
# ═══════════════════════════════════════════════
def make_progress_bar(current, total, length=10):
    filled = round(current / total * length) if total else 0
    return "█" * filled + "░" * (length - filled) + f"  {current}/{total}"

def make_timer_str(elapsed, total=TEST_DURATION_SECONDS):
    remaining = max(0, total - elapsed)
    return f"⏱ {remaining // 60:02d}:{remaining % 60:02d} qoldi"

def build_info_message(grade, q_index, total, difficulty, elapsed, test_type="free"):
    diff  = DIFFICULTY_LABEL.get(difficulty, "")
    prog  = make_progress_bar(q_index, total)
    timer = make_timer_str(elapsed)
    tag   = "💎 Pullik" if test_type == "paid" else "🆓 Bepul"
    return (
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📚 {grade}  {tag}  |  {q_index}-savol\n"
        f"📊 {prog}\n"
        f"{timer}   {diff}\n"
        f"━━━━━━━━━━━━━━━━━━"
    )

def build_answer_keyboard(options):
    keys = list(options.keys())
    paired = []
    for i in range(0, len(keys), 2):
        row = [InlineKeyboardButton(text=keys[i], callback_data=f"ans_{keys[i]}")]
        if i + 1 < len(keys):
            row.append(InlineKeyboardButton(text=keys[i+1], callback_data=f"ans_{keys[i+1]}"))
        paired.append(row)
    return InlineKeyboardMarkup(inline_keyboard=paired)

def get_motivation():
    return random.choice(MOTIVATIONAL_MESSAGES)

def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🆓 Bepul testlar"), KeyboardButton(text="💎 Pullik testlar")],
            [KeyboardButton(text="🏆 INLIM"),          KeyboardButton(text="👤 Profilim")],
            [KeyboardButton(text="🔗 Do'stlarni taklif et")],
        ],
        resize_keyboard=True,
    )

# ═══════════════════════════════════════════════
# 7. SAVOL YUBORISH
# ═══════════════════════════════════════════════
async def send_question(chat_id, state):
    data      = await state.get_data()
    grade     = data["grade"]
    q_list    = data["questions"]
    index     = data["current"]
    start_ts  = data["start_ts"]
    test_type = data.get("test_type", "free")

    if index >= len(q_list):
        await finish_test(chat_id, state)
        return

    q       = q_list[index]
    elapsed = int(time.time() - start_ts)
    total   = len(q_list)

    for key in ("last_info_msg_id", "last_q_msg_id"):
        old_id = data.get(key)
        if old_id:
            try:
                await bot.delete_message(chat_id, old_id)
            except Exception:
                pass

    info_text = build_info_message(grade, index + 1, total,
                                    q.get("difficulty", "easy"), elapsed, test_type)
    info_msg  = await bot.send_message(chat_id=chat_id, text=info_text)

    options_text = "\n".join([f"{k}) {v}" for k, v in q["options"].items()])
    full_question = f"{q['question']}\n\n{options_text}"
    kb = build_answer_keyboard(q["options"])
    image_url = q.get("image")

    if image_url:
        q_msg = await bot.send_photo(chat_id=chat_id, photo=image_url,
                                     caption=full_question, reply_markup=kb)
    else:
        q_msg = await bot.send_message(chat_id=chat_id, text=full_question, reply_markup=kb)

    await state.update_data(
        last_info_msg_id=info_msg.message_id,
        last_q_msg_id=q_msg.message_id,
    )

# ═══════════════════════════════════════════════
# 8. TEST TUGASH
# ═══════════════════════════════════════════════
async def finish_test(chat_id, state):
    data      = await state.get_data()
    score     = data.get("score", 0)
    total     = len(data["questions"])
    user_id   = data["db_user_id"]
    name      = data.get("user_name", "O'quvchi")
    grade     = data.get("grade", "")
    test_type = data.get("test_type", "free")

    percent = round(score / total * 100) if total else 0
    if percent == 100:  medal = "🥇 Mukammal!"
    elif percent >= 80: medal = "🥈 A'lo!"
    elif percent >= 60: medal = "🥉 Yaxshi!"
    elif percent >= 40: medal = "📖 Qoniqarli"
    else:               medal = "💡 Ko'proq mashq qiling!"

    if test_type == "free":
        result_text = (
            f"🏁 Bepul test yakunlandi!\n\n"
            f"👤 {name}\n"
            f"✅ To'g'ri javoblar: {score}/{total}  ({percent}%)\n"
            f"🏅 Natija: {medal}\n\n"
            f"{get_motivation()}\n\n"
            f"📢 Yaxshi natija uchun ILM NURI o'quv markazida o'qing!\n"
            f"📣 Yakuniy natijalar uchun kanalga qo'shiling 👇"
        )
    else:
        update_user_field(user_id, score=score)
        earned_vab = score * VAB_PER_CORRECT_ANSWER
        new_vab    = add_vab(user_id, earned_vab)

        result_text = (
            f"🏁 Test yakunlandi! 💎 Pullik test\n\n"
            f"👤 {name}\n"
            f"✅ To'g'ri javoblar: {score}/{total}  ({percent}%)\n"
            f"🏅 Natija: {medal}\n\n"
            f"💰 Bu testdan: +{earned_vab} VAB\n"
            f"💼 Jami VAB: {new_vab} VAB\n\n"
            f"{get_motivation()}\n\n"
            f"📢 Yaxshi natija uchun ILM NURI o'quv markazida o'qing!\n"
            f"📣 Yakuniy natijalar uchun kanalga qo'shiling 👇"
        )

    await bot.send_message(
        chat_id, result_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📣 Kanalga o'tish", url=CHANNEL_LINK)],
            [InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="main_menu")],
        ]),
    )
    await state.clear()

# ═══════════════════════════════════════════════
# 9. /START VA RO'YXATDAN O'TISH
# ═══════════════════════════════════════════════
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    args = message.text.split()
    referred_by = 0
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referred_by = int(args[1][4:])
        except ValueError:
            pass

    existing = get_user_by_telegram_id(message.from_user.id)
    if existing:
        await message.answer(
            f"Salom, {existing['full_name']}! ✋\n"
            f"💼 VAB balansingiz: {existing['vab']} VAB",
            reply_markup=main_menu_keyboard()
        )
        return

    await message.answer(
        "Assalomu alaykum! 🌟\n\n"
        "🏆 Ilm Nuri: Kelajak Olimpiadasi botiga xush kelibsiz!\n\n"
        "Prezident, Al-Xorazmiy va Ibn Sino maktablarida o'qishni orzu qilasizmi? "
        "O'z bilimingizni sinab ko'ring!\n\n"
        "👇 Ism va Familiyangizni kiriting:\nMasalan: Alisherov Vali"
    )
    await state.update_data(referred_by=referred_by)
    await state.set_state(Registration.full_name)

@dp.message(Registration.full_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer("🏫 Maktab raqamini yozing:\nFaqat raqam. Masalan: 5")
    await state.set_state(Registration.school)

@dp.message(Registration.school)
async def process_school(message: types.Message, state: FSMContext):
    await state.update_data(school=message.text)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📲 Kontakt yuborish", request_contact=True)],
            [KeyboardButton(text="⬅️ Orqaga")],
        ], resize_keyboard=True,
    )
    await message.answer("📞 Telefon raqamingizni yuboring:", reply_markup=keyboard)
    await state.set_state(Registration.phone)

@dp.message(Registration.phone)
async def process_phone(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Orqaga":
        await message.answer("🏫 Maktab raqamini qaytadan yozing:",
                             reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Registration.school)
        return

    phone = message.contact.phone_number if message.contact else message.text
    data  = await state.get_data()
    referred_by = data.get("referred_by", 0)

    p_id = add_user(message.from_user.id, data["full_name"], data["school"],
                    "noma'lum", phone, referred_by)

    if p_id is None:
        await message.answer("Siz allaqachon ro'yxatdan o'tgansiz!",
                             reply_markup=types.ReplyKeyboardRemove())
        await state.clear()
        return

    if referred_by:
        ref_user = get_user_by_telegram_id(referred_by)
        if ref_user:
            ref_user_id = ref_user["id"]
            new_count = ref_user["referral_count"] + 1
            update_user_field(ref_user_id, referral_count=new_count)
            if new_count % 3 == 0:
                earned = add_vab(ref_user_id, VAB_FOR_REFERRAL)
                try:
                    await bot.send_message(
                        referred_by,
                        f"🎉 3 ta do'stingiz botga qo'shildi!\n"
                        f"💰 +{VAB_FOR_REFERRAL} VAB qo'shildi!\n"
                        f"💼 Jami: {earned} VAB"
                    )
                except Exception:
                    pass

    await message.answer("✅ Ro'yxatdan o'tdingiz!", reply_markup=types.ReplyKeyboardRemove())
    await message.answer(
        f"🎉 Xush kelibsiz, {data['full_name']}!\n\n"
        f"💼 Boshlang'ich VAB: 0 VAB\n\n"
        f"Asosiy menyudan boshlang 👇",
        reply_markup=main_menu_keyboard()
    )
    await state.clear()

# ═══════════════════════════════════════════════
# 10. INLIM BO'LIMI VA REGISTRATION
# ═══════════════════════════════════════════════
def inlim_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Repititsion testga ro'yxatdan o'tish",
                              callback_data="inlim_register")],
        [InlineKeyboardButton(text="🤝 Homiylarimiz",
                              callback_data="inlim_sponsors")],
        [InlineKeyboardButton(text="🏆 Sovrin jamg'armasi hozirda",
                              callback_data="inlim_prize")],
        [InlineKeyboardButton(text="💼 Homiylik qilish",
                              callback_data="inlim_sponsor_apply")],
    ])

@dp.message(F.text == "🏆 INLIM")
async def inlim_menu(message: types.Message):
    prize = INLIM_SETTINGS.get("prize_fund", 0)
    await message.answer(
        "🏆 Ilm Nuri Olimpiadasi\n\n"
        f"🎯 Repititsion test orqali bilimingizni sinab ko'ring!\n"
        f"💰 Joriy sovrin jamg'armasi: {prize:,} so'm\n\n"
        "Quyidagi bo'limlardan birini tanlang 👇",
        reply_markup=inlim_main_keyboard()
    )

@dp.callback_query(F.data == "inlim_sponsors")
async def inlim_sponsors(callback: types.CallbackQuery):
    sponsors = INLIM_SETTINGS.get("sponsors", [])
    if not sponsors:
        text = "🤝 Homiylarimiz\n\nHozircha homiylar yo'q."
    else:
        text = "🤝 Homiylarimiz\n\n"
        for i, s in enumerate(sponsors, 1):
            text += f"{i}. {s.get('name', 'Noaniq')}\n"
            if s.get("telegram"): text += f"   📱 {s['telegram']}\n"
            if s.get("instagram"): text += f"   📸 {s['instagram']}\n"
            text += "\n"

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="inlim_back")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "inlim_prize")
async def inlim_prize(callback: types.CallbackQuery):
    prize = INLIM_SETTINGS.get("prize_fund", 0)
    await callback.message.edit_text(
        f"🏆 Sovrin jamg'armasi\n\n"
        f"💰 Hozirgi jamg'arma: {prize:,} so'm\n\n"
        f"🥇 1-o'rin: Prezident maktabiga yo'llanma\n"
        f"🥈 2-o'rin: Al-Xorazmiy maktabiga yo'llanma\n"
        f"🥉 3-o'rin: Ibn Sino maktabiga yo'llanma",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💼 Homiylik qilish", callback_data="inlim_sponsor_apply")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="inlim_back")],
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "inlim_sponsor_apply")
async def inlim_sponsor_apply(callback: types.CallbackQuery):
    admin_username = INLIM_SETTINGS.get("admin_username", "@admin")
    await callback.message.edit_text(
        "💼 Homiylik qilish\n\n"
        "Homiylik turlari:\n"
        "• Pul mablag'i\n"
        "• Sovg'a va hadyalar\n"
        "• Reklama va targ'ibot\n\n"
        "Admin bilan bog'lanish 👇",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="✉️ Adminga yozish",
                url=f"https://t.me/{admin_username.lstrip('@')}"
            )],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="inlim_back")],
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "inlim_back")
async def inlim_back(callback: types.CallbackQuery):
    prize = INLIM_SETTINGS.get("prize_fund", 0)
    await callback.message.edit_text(
        "🏆 INLIM — Ilm Nuri Olimpiadasi\n\n"
        f"💰 Joriy sovrin jamg'armasi: {prize:,} so'm\n\n"
        "Quyidagi bo'limlardan birini tanlang 👇",
        reply_markup=inlim_main_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "inlim_register")
async def inlim_register_start(callback: types.CallbackQuery, state: FSMContext):
    share_url = f"https://t.me/share/url?url=https://t.me/{CHANNEL_USERNAME.lstrip('@')}&text=Prezident%20va%20Al-Xorazmiy%20maktablari%20repititsion%20test%20olimpiadasi%20boshlanmoqda!%21"
    await callback.message.edit_text(
        "📝 Repititsion testga ro'yxatdan o'tish\n\n"
        "1️⃣ @IlmNuri_Markazi kanaliga a'zo bo'ling\n"
        "2️⃣ Sinfdoshlar va do'stlarga quyidagi Havola orqali ulashing\n\n"
        "Tayyor bo'lgach keyingi bosqichga o'ting👇",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📣 Kanalga o'tish", url=CHANNEL_LINK)],
            [InlineKeyboardButton(text="🚀 Guruhga ulashish", url=share_url)],
            [InlineKeyboardButton(text="✅ Obuna bo'ldim, ulashtim", callback_data="inlim_check_sub")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="inlim_back")],
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "inlim_check_sub")
async def inlim_check_sub(callback: types.CallbackQuery, state: FSMContext):
    if not await is_subscribed(callback.from_user.id):
        await callback.answer(
            "❌ Siz hali @IlmNuri_Markazi kanaliga a'zo bo'lmadingiz!",
            show_alert=True
        )
        return

    await callback.message.edit_text(
        "✅ Obuna aniqlandi!\n\n"
        "Tarqatganingiz uchun rahmat. Ro'yxatdan o'tish muvaffaqiyatli davom etmoqda!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="main_menu")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: types.CallbackQuery):
    await callback.message.answer("🏠 Asosiy menyu:", reply_markup=main_menu_keyboard())
    await callback.answer()

# ═══════════════════════════════════════════════
# 11. MAIN ISHGA TUSHIRISH
# ═══════════════════════════════════════════════
async def main():
    logging.basicConfig(level=logging.INFO)
    print("🚀 Bot ishga tushmoqda...")
    load_users_to_cache()
    load_inlim_and_orders_to_cache()
    
    # Eskidan qolib ketgan yangilanishlarni o'chirish
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Pollingni boshlash
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
