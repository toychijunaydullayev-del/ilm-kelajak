import asyncio
import logging
import random
import os
import time
import json
import gspread
import aiohttp
from aiogram.filters import StateFilter
from google.oauth2.service_account import Credentials
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

# ═══════════════════════════════════════════════
# 1. SOZLAMALAR
# ═══════════════════════════════════════════════
BOT_TOKEN             = os.environ.get("BOT_TOKEN", "8678044800:AAF9GGeTK1qS1dJMQayrq-J3qtKMhf39wdA")
ADMIN_ID              = 506343083
TEST_DURATION_SECONDS = 45 * 60
CHANNEL_LINK          = "https://t.me/IlmNuri_Markazi"
CHANNEL_USERNAME      = "@IlmNuri_Markazi"
SHEETS_ID             = "1gvaXkcJStGAUi0DH8eIBaB7R8GVJfC0z2z38mHie6MY"

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

# ═══════════════════════════════════════════════
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
    """Render-da fayl yo'qolganda Google credentials environmentdan parslash uchun."""
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if creds_json:
        try:
            info = json.loads(creds_json)
            return Credentials.from_service_account_info(info, scopes=scopes)
        except Exception as e:
            print(f"⚠️ Environment GOOGLE_CREDENTIALS xato: {e}")
    
    # Local fallback
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
# [BU YERDAGI TESTS VA PAID_TESTS LUG'ATINI O'ZINGIZNING KODINGIZDAGI HOLATCHA TO'LIQ QOLDIRING]
TESTS = {
    "1-sinf": [
        {"question": "Hisoblang  2 + 3 + 4 ",
         "options": {"A": "8", "B": "9", "C": "10", "D": "11"},
         "answer": "B", "difficulty": "easy"},
        # ... qolgan barcha free test savollaringizni aynan shu yerga yozib qo'ying
    ]
}

PAID_TESTS = {
    "1-sinf": [
        {"question": "💎 Sehrli kvadrat: markaziy qator bo'sh katagi?",
         "options": {"A": "4", "B": "2", "C": "8", "D": "1"},
         "answer": "A", "difficulty": "hard"},
        # ... qolgan barcha pullik test variantlarining to'liq ro'yxati joylashsin
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
    waiting_check  = State()
    waiting_grade  = State()

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
    """Server o'chib yonganda Renderda orders va inlim cache yo'qolishini oldini oladi (Sheets dan tiklaydi)."""
    global ORDER_CACHE, INLIM_REGISTRATIONS
    ORDER_CACHE.clear()
    INLIM_REGISTRATIONS.clear()
    
    # INLIM yuklash
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

    # Buyurtmalar yuklash
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

def spend_vab(user_id, amount):
    user = USERS_CACHE.get(user_id)
    if user and user["vab"] >= amount:
        new_vab = user["vab"] - amount
        update_user_field(user_id, vab=new_vab)
        return True
    return False

def _paid_key(grade, variant_index):
    return f"{grade}:{variant_index}"

def has_paid_test(user_id, grade, variant_index=None):
    user = USERS_CACHE.get(user_id)
    if not user:
        return False
    paid = user.get("paid_tests", "")
    keys = set(paid.split(",")) if paid else set()
    if variant_index is None:
        return any(k.startswith(f"{grade}:") for k in keys)
    return _paid_key(grade, variant_index) in keys

def grant_paid_test(user_id, grade, variant_index=0):
    user = USERS_CACHE.get(user_id)
    if not user:
        return
    paid = user.get("paid_tests", "")
    keys = set(paid.split(",")) if paid else set()
    keys.discard("")
    keys.add(_paid_key(grade, variant_index))
    update_user_field(user_id, paid_tests=",".join(keys))

def add_result(user_id, grade, score, total, test_type="free"):
    import datetime
    now = datetime.datetime.now().strftime("%d.%m %H:%M")
    tag = "💎" if test_type == "paid" else "🆓"
    entry = f"{tag}{grade}:{score}/{total}@{now}"
    user = USERS_CACHE.get(user_id)
    if not user:
        return
    results = user.get("results", "")
    all_results = results.split("|") if results else []
    all_results.append(entry)
    if len(all_results) > 10:
        all_results = all_results[-10:]
    update_user_field(user_id, results="|".join(all_results))

def get_all_telegram_ids():
    return [u["telegram_id"] for u in USERS_CACHE.values() if u["telegram_id"]]

def get_users_count():
    return len(USERS_CACHE)

def save_order(telegram_id, full_name, grade, photo_file_id, variant_index=0):
    import datetime
    ORDER_COUNTER[0] += 1
    order_id = ORDER_COUNTER[0]
    ORDER_CACHE[order_id] = {
        "order_id":      order_id,
        "telegram_id":   telegram_id,
        "full_name":     full_name,
        "grade":         grade,
        "variant_index": variant_index,
        "photo_file_id": photo_file_id,
        "status":        "pending",
    }
    try:
        ws = get_orders_sheet()
        if ws:
            ws.append_row([order_id, telegram_id, full_name,
                           f"{grade} Variant {variant_index+1}",
                           PAYMENT_AMOUNT, "pending",
                           datetime.datetime.now().strftime("%d.%m.%Y %H:%M")])
    except Exception as e:
        print(f"save_order xato: {e}")
    return order_id

def confirm_order(order_id):
    order = ORDER_CACHE.get(order_id)
    if not order:
        return None
    order["status"] = "confirmed"
    try:
        ws = get_orders_sheet()
        if ws:
            rows = ws.get_all_values()
            for i, row in enumerate(rows[1:], start=2):
                if row[0] and int(row[0]) == order_id:
                    ws.update_cell(i, 6, "confirmed")
                    break
    except Exception as e:
        print(f"confirm_order xato: {e}")
    return order

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
        add_result(user_id, grade, score, total, test_type)

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
# 9. TIMEOUT Watcher
# ═══════════════════════════════════════════════
async def timeout_watcher(chat_id, state):
    await asyncio.sleep(TEST_DURATION_SECONDS)
    current_state = await state.get_state()
    if current_state == TestProcess.answering.state:
        await bot.send_message(chat_id, "⏰ Vaqt tugadi! Test yakunlanmoqda...")
        await finish_test(chat_id, state)

# ═══════════════════════════════════════════════
# 10. /START
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

# ═══════════════════════════════════════════════
# 11. RO'YXATDAN O'TISH
# ═══════════════════════════════════════════════
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
# 12. INLIM BO'LIMI
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
        "🏆 INLIM — Ilm Nuri Olimpiadasi\n\n"
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

# ═══════════════════════════════════════════════
# 13. INLIM RO'YXATDAN O'TISH (DUBLIKATSIZ EXTRA-INTEGRATION)
# ═══════════════════════════════════════════════
@dp.callback_query(F.data == "inlim_register")
async def inlim_register_start(callback: types.CallbackQuery, state: FSMContext):
    # Do'stlarga tarqatish haolasi (Telegram Share URL)
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
        "Tarqatganingiz uchun rahmat. Ro'yxatni davom ettiramiz 👇",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Davom etish", callback_data="inlim_check_share")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="inlim_register")],
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "inlim_check_share")
async def inlim_check_share(callback: types.CallbackQuery, state: FSMContext):
    # FOYDALANUVCHINI IKKI MARTA RO'YXATDAN O'TKAZMASLIK LOGIKASI
    user = get_user_by_telegram_id(callback.from_user.id)
    if user:
        # Bazadagi ma'lumotlarni avtomatik state xotirasiga yuklaymiz
        await state.update_data(
            inlim_full_name=user["full_name"],
            inlim_school=user["school"],
            inlim_phone=user["phone"]
        )
        await callback.message.answer(
            f"✅ Profilingiz aniqlandi (ma'lumotlarni qayta kiritish shart emas):\n\n"
            f"👤 Ism: {user['full_name']}\n"
            f"🏫 Maktab: {user['school']}\n"
            f"📞 Telefon: {user['phone']}\n\n"
            f"📚 Repititsion sinf guruhingizni belgilang:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔢 1-2 sinf — Matematika", callback_data="inlim_grade_12")],
                [InlineKeyboardButton(text="🔢 3-4 sinf — Aniq fan (Matematika)", callback_data="inlim_grade_34")],
                [InlineKeyboardButton(text="🌿 5-6 sinf — Tabiiy fan", callback_data="inlim_grade_56")],
            ])
        )
        await state.set_state(InlimRegistration.grade_group)
    else:
        # Tizimda yo'q foydalanuvchiga noldan so'rash
        await callback.message.answer(
            "✅ Ro'yxatdan o'tishni boshlaymiz.\n\n"
            "👤 Ism va Familiyangizni kiriting:\nMasalan: Alisherov Vali"
        )
        await state.set_state(InlimRegistration.full_name)
    await callback.answer()

@dp.message(InlimRegistration.full_name)
async def inlim_process_name(message: types.Message, state: FSMContext):
    await state.update_data(inlim_full_name=message.text)
    await message.answer("🏫 Maktab raqamingizni yozing:\nMasalan: 45")
    await state.set_state(InlimRegistration.school)

@dp.message(InlimRegistration.school)
async def inlim_process_school(message: types.Message, state: FSMContext):
    await state.update_data(inlim_school=message.text)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📲 Kontakt yuborish", request_contact=True)]],
        resize_keyboard=True,
    )
    await message.answer("📞 Telefon raqamingizni yuboring:", reply_markup=keyboard)
    await state.set_state(InlimRegistration.phone)

@dp.message(InlimRegistration.phone)
async def inlim_process_phone(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    await state.update_data(inlim_phone=phone)

    await message.answer(
        "📚 Sinf guruhingizni tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔢 1-2 sinf — Matematika", callback_data="inlim_grade_12")],
            [InlineKeyboardButton(text="🔢 3-4 sinf — Aniq fan (Matematika)", callback_data="inlim_grade_34")],
            [InlineKeyboardButton(text="🌿 5-6 sinf — Tabiiy fan", callback_data="inlim_grade_56")],
        ])
    )
    await state.set_state(InlimRegistration.grade_group)

@dp.callback_query(F.data.startswith("inlim_grade_"), StateFilter(InlimRegistration.grade_group))
async def inlim_process_grade(callback: types.CallbackQuery, state: FSMContext):
    grade_map = {
        "inlim_grade_12": "1-2 sinf (Matematika)",
        "inlim_grade_34": "3-4 sinf (Aniq fan)",
        "inlim_grade_56": "5-6 sinf (Tabiiy fan)",
    }
    grade_group = grade_map.get(callback.data, "")
    await state.update_data(inlim_grade_group=grade_group)

    dates = INLIM_SETTINGS.get("test_dates", [])
    if not dates:
        await callback.message.answer(
            "⚠️ Hozircha test sanalari belgilanmagan.\n"
            "Admindan so'rang yoki keyinroq urinib ko'ring.",
            reply_markup=main_menu_keyboard()
        )
        await state.clear()
        await callback.answer()
        return

    buttons = []
    for i, d in enumerate(dates):
        label = f"📅 {d['date']} — {d.get('grade', '')} {d.get('subject', '')}"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"inlim_date_{i}")])

    await callback.message.answer(
        f"✅ Tanlandi: {grade_group}\n\n📅 Test sanasini tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await state.set_state(InlimRegistration.test_date)
    await callback.answer()

@dp.callback_query(F.data.startswith("inlim_date_"), StateFilter(InlimRegistration.test_date))
async def inlim_process_date(callback: types.CallbackQuery, state: FSMContext):
    idx   = int(callback.data.split("_")[2])
    dates = INLIM_SETTINGS.get("test_dates", [])
    if idx >= len(dates):
        await callback.answer("Sana topilmadi!", show_alert=True)
        return

    chosen_date = dates[idx]
    date_str    = f"{chosen_date['date']} — {chosen_date.get('subject', '')}"
    await state.update_data(inlim_test_date=date_str)

    await callback.message.answer(
        f"✅ Tanlangan sana: {date_str}\n\n🖥 Test formatini tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💻 Onlayn", callback_data="inlim_format_online")],
            [InlineKeyboardButton(text="🏢 Oflayn (ILM NURI markazida)",
                                  callback_data="inlim_format_offline")],
        ])
    )
    await state.set_state(InlimRegistration.test_format)
    await callback.answer()

@dp.callback_query(F.data.startswith("inlim_format_"), StateFilter(InlimRegistration.test_format))
async def inlim_process_format(callback: types.CallbackQuery, state: FSMContext):
    fmt_map = {
        "inlim_format_online":  "💻 Onlayn",
        "inlim_format_offline": "🏢 Oflayn",
    }
    fmt = fmt_map.get(callback.data, "")
    await state.update_data(inlim_test_format=fmt)

    notice = "⚠️ Diqqat! Sovrin faqat oflayn qatnashganlar uchun!\n\n" if "online" in callback.data else ""

    await callback.message.answer(
        f"✅ Format: {fmt}\n\n{notice}💳 To'lov usulini tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"💳 Hozir karta orqali to'lash ({PAYMENT_AMOUNT:,} so'm)",
                callback_data="inlim_pay_now"
            )],
            [InlineKeyboardButton(
                text="📅 Test kuni to'layman",
                callback_data="inlim_pay_later"
            )],
        ])
    )
    await state.set_state(InlimRegistration.payment)
    await callback.answer()

@dp.callback_query(F.data == "inlim_pay_now", StateFilter(InlimRegistration.payment))
async def inlim_pay_now(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await callback.message.answer(
        f"💳 To'lov ma'lumotlari:\n\n"
        f"🏦 Karta: {PAYMENT_CARD}\n"
        f"👤 Egasi: {PAYMENT_OWNER}\n"
        f"💰 Summa: {PAYMENT_AMOUNT:,} so'm\n\n"
        f"⚠️ Izohga yozing: {data.get('inlim_full_name', '')} — INLIM\n\n"
        f"To'lov chekini (screenshot) shu yerga yuboring 👇\n/cancel — bekor"
    )
    await state.update_data(inlim_payment_type="Hozir to'lagan")
    await callback.answer()

@dp.callback_query(F.data == "inlim_pay_later", StateFilter(InlimRegistration.payment))
async def inlim_pay_later(callback: types.CallbackQuery, state: FSMContext):
    await _finalize_inlim_registration(callback.from_user.id, state, "Test kuni to'laydi")
    await callback.answer()

@dp.message(StateFilter(InlimRegistration.payment))
async def inlim_receive_check(message: types.Message, state: FSMContext):
    if message.text and message.text.strip() == "/cancel":
        await message.answer("Bekor qilindi.", reply_markup=main_menu_keyboard())
        await state.clear()
        return

    if not message.photo:
        await message.answer("⚠️ Iltimos, to'lov cheki rasmini yuboring yoki /cancel bosing!")
        return

    photo_id = message.photo[-1].file_id
    data     = await state.get_data()

    try:
        await bot.send_photo(
            ADMIN_ID,
            photo=photo_id,
            caption=(
                f"💳 INLIM TO'LOV CHEKI!\n\n"
                f"👤 {data.get('inlim_full_name', '')}\n"
                f"📚 {data.get('inlim_grade_group', '')}\n"
                f"📅 {data.get('inlim_test_date', '')}\n"
                f"📞 {data.get('inlim_phone', '')}\n"
                f"💰 {PAYMENT_AMOUNT:,} so'm"
            )
        )
    except Exception as e:
        print(f"Admin INLIM chek xato: {e}")

    await _finalize_inlim_registration(message.from_user.id, state, "Chek yuborildi")

async def _finalize_inlim_registration(telegram_id, state, payment_type):
    data = await state.get_data()
    full_name   = data.get("inlim_full_name", "")
    school      = data.get("inlim_school", "")
    phone       = data.get("inlim_phone", "")
    grade_group = data.get("inlim_grade_group", "")
    test_date   = data.get("inlim_test_date", "")
    test_format = data.get("inlim_test_format", "")

    reg_id = save_inlim_registration(
        telegram_id, full_name, school, phone,
        grade_group, test_date, test_format, payment_type
    )

    try:
        await bot.send_message(
            ADMIN_ID,
            f"📝 YANGI INLIM RO'YXAT!\n\n"
            f"🆔 #{reg_id}\n👤 {full_name}\n🏫 {school}\n"
            f"📞 {phone}\n📚 {grade_group}\n📅 {test_date}\n"
            f"🖥 {test_format}\n💳 {payment_type}"
        )
    except Exception:
        pass

    await bot.send_message(
        telegram_id,
        f"🎉 Ro'yxatdan muvaffaqiyatli o'tdingiz!\n\n"
        f"🆔 Raqamingiz: #{reg_id}\n"
        f"👤 {full_name}\n📚 {grade_group}\n"
        f"📅 {test_date}\n🖥 {test_format}\n💳 {payment_type}\n\n"
        f"📣 Yangiliklar: {CHANNEL_LINK}\n\nOmad! 🍀",
        reply_markup=main_menu_keyboard()
    )
    await state.clear()

# ═══════════════════════════════════════════════
# 14. ASOSIY MENYU TUGMALARI
# ═══════════════════════════════════════════════
@dp.message(F.text == "🆓 Bepul testlar")
async def free_tests_menu(message: types.Message):
    user = get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Avval /start bosing va ro'yxatdan o'ting!")
        return

    grade = user["grade"]

    if grade == "noma'lum" or grade not in TESTS:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="1-sinf"), KeyboardButton(text="2-sinf"), KeyboardButton(text="3-sinf")],
                [KeyboardButton(text="4-sinf"), KeyboardButton(text="5-sinf"), KeyboardButton(text="6-sinf")],
            ], resize_keyboard=True,
        )
        await message.answer("📚 Avval sinfingizni tanlang:", reply_markup=keyboard)
        return

    q_count = len(TESTS.get(grade, []))
    await message.answer(
        f"🆓 Bepul test: {grade}\n"
        f"📝 Savollar: {q_count} ta\n"
        f"⏱ Vaqt: 45 daqiqa\n\n"
        f"Boshlashga tayyormisiz?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Boshlash", callback_data="start_free")]
        ])
    )

@dp.message(F.text.in_({"1-sinf", "2-sinf", "3-sinf", "4-sinf", "5-sinf", "6-sinf"}))
async def set_grade_from_menu(message: types.Message):
    user = get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Avval /start bosing!")
        return
    update_user_field(user["id"], grade=message.text)
    user["grade"] = message.text
    grade   = message.text
    q_count = len(TESTS.get(grade, []))
    await message.answer(
        f"✅ Sinf: {grade}\n\n"
        f"📝 Savollar: {q_count} ta\n\n"
        f"Boshlashga tayyormisiz?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Boshlash", callback_data="start_free")]
        ])
    )

@dp.message(F.text == "💎 Pullik testlar")
async def paid_tests_menu(message: types.Message):
    user = get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Avval /start bosing!")
        return

    grades = list(PAID_TESTS.keys())
    buttons = []
    for g in grades:
        has = has_paid_test(user["id"], g)
        label = f"{'✅' if has else '🔒'} {g}"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"paidgrade_{g}")])

    await message.answer(
        f"💎 Pullik testlar — Sinf tanlang:\n\n"
        f"✅ — sotib olingan   🔒 — sotib olinmagan\n\n"
        f"💼 Sizda: {user['vab']} VAB",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@dp.callback_query(F.data.startswith("paidgrade_"))
async def paid_grade_selected(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    grade = parts[1]
    
    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        # Cache sinxronizatsiya yuz bermagan bo'lsa qayta yuklaydi
        load_users_to_cache()
        user = get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("Foydalanuvchi topilmadi! Qayta urinib ko'ring.", show_alert=True)
            return

    variants = PAID_TESTS.get(grade, [])
    VARIANT_SIZE = 3
    variant_count = (len(variants) + VARIANT_SIZE - 1) // VARIANT_SIZE

    buttons = []
    for i in range(variant_count):
        bought = has_paid_test(user["id"], grade, i)
        if bought:
            buttons.append([InlineKeyboardButton(
                text=f"▶️ Variant {i+1} — Boshlash",
                callback_data=f"start_paid_{grade}_{i}"
            )])
        else:
            buttons.append([InlineKeyboardButton(
                text=f"🔒 Variant {i+1} — {PAYMENT_AMOUNT:,} so'm / {VAB_FOR_TEST_PURCHASE} VAB",
                callback_data=f"buy_variant_{grade}_{i}"
            )])
    buttons.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_paid_menu")])

    await callback.message.edit_text(
        f"💎 {grade} — Variantlar:\n💼 Sizda: {user['vab']} VAB",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_variant_"))
async def buy_variant_selected(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    grade         = parts[2]
    variant_index = int(parts[3])
    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return

    await callback.message.edit_text(
        f"💎 {grade} — Variant {variant_index + 1}\n\n"
        f"✅ Har to'g'ri javob: +{VAB_PER_CORRECT_ANSWER} VAB\n"
        f"💰 Narxi: {PAYMENT_AMOUNT:,} so'm yoki {VAB_FOR_TEST_PURCHASE} VAB\n"
        f"💼 Sizda: {user['vab']} VAB\n\n"
        f"To'lov usulini tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"💳 Pul to'lash ({PAYMENT_AMOUNT:,} so'm)",
                callback_data=f"pay_money_{grade}_{variant_index}"
            )],
            [InlineKeyboardButton(
                text=f"💰 VAB sarflash ({VAB_FOR_TEST_PURCHASE} VAB)",
                callback_data=f"pay_vab_{grade}_{variant_index}"
            )],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"paidgrade_{grade}")],
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_paid_menu")
async def back_to_paid_menu(callback: types.CallbackQuery):
    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return
    grades = list(PAID_TESTS.keys())
    buttons = []
    for g in grades:
        has = has_paid_test(user["id"], g)
        label = f"{'✅' if has else '🔒'} {g}"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"paidgrade_{g}")])
    await callback.message.edit_text(
        f"💎 Pullik testlar\n💼 Sizda: {user['vab']} VAB",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()

@dp.message(F.text == "👤 Profilim")
async def profile_menu(message: types.Message):
    user = get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Avval /start bosing!")
        return

    results_raw  = user.get("results", "")
    results_list = [r for r in results_raw.split("|") if r] if results_raw else []

    results_text = "\n📋 Oxirgi natijalar:\n"
    if results_list:
        for r in results_list[-5:]:
            try:
                tag_grade, rest = r.split(":", 1)
                score_total, date = rest.split("@", 1)
                results_text += f"  {tag_grade}: {score_total} — {date}\n"
            except Exception:
                results_text += f"  {r}\n"
    else:
        results_text = "\n📋 Hali natija yo'q.\n"

    ref_count  = user.get("referral_count", 0)
    next_bonus = 3 - (ref_count % 3)

    await message.answer(
        f"👤 Profil\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📛 Ism: {user['full_name']}\n"
        f"🏫 Maktab: {user['school']}\n"
        f"📚 Sinf: {user['grade']}\n"
        f"📞 Tel: {user['phone']}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 VAB balansi: {user['vab']} VAB\n"
        f"👫 Taklif qilinganlar: {ref_count} ta\n"
        f"🎁 Keyingi bonus uchun: {next_bonus} ta do'st\n"
        f"━━━━━━━━━━━━━━━━━━"
        f"{results_text}"
        f"━━━━━━━━━━━━━━━━━━",
        reply_markup=main_menu_keyboard()
    )

@dp.message(F.text == "🔗 Do'stlarni taklif et")
async def invite_menu(message: types.Message):
    user = get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Avval /start bosing!")
        return

    bot_info   = await bot.get_me()
    ref_link   = f"https://t.me/{bot_info.username}?start=ref_{message.from_user.id}"
    ref_count  = user.get("referral_count", 0)
    next_bonus = 3 - (ref_count % 3)

    await message.answer(
        f"🔗 Taklif havolangiz:\n{ref_link}\n\n"
        f"📊 Siz taklif qilganlar: {ref_count} ta\n"
        f"🎁 Keyingi bonus: {next_bonus} ta do'st kerak\n\n"
        f"💰 Har 3 ta do'st = {VAB_FOR_REFERRAL} VAB!\n"
        f"💎 {VAB_FOR_TEST_PURCHASE} VAB to'plang → pullik test bepul!",
        reply_markup=main_menu_keyboard()
    )

# ═══════════════════════════════════════════════
# 15. TO'LOV CALLBACK-LAR
# ═══════════════════════════════════════════════
@dp.callback_query(F.data.startswith("pay_money_"))
async def pay_with_money(callback: types.CallbackQuery, state: FSMContext):
    parts         = callback.data.split("_")
    grade         = parts[2]
    variant_index = int(parts[3])
    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return

    await callback.message.answer(
        f"💳 To'lov ma'lumotlari:\n\n"
        f"🏦 Karta: {PAYMENT_CARD}\n"
        f"👤 Egasi: {PAYMENT_OWNER}\n"
        f"💰 Summa: {PAYMENT_AMOUNT:,} so'm\n\n"
        f"⚠️ Izohga yozing: {user['full_name']} — {grade} Variant {variant_index+1}\n\n"
        f"Chekni yuborish uchun tugmani bosing 👇",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Chek yuborish",
                                  callback_data=f"send_check_{grade}_{variant_index}")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("send_check_"))
async def send_check_prompt(callback: types.CallbackQuery, state: FSMContext):
    parts         = callback.data.split("_")
    grade         = parts[2]
    variant_index = int(parts[3])
    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return

    await callback.message.answer(
        f"📤 To'lov cheki rasmini shu yerga yuboring:\n"
        f"📚 {grade} — Variant {variant_index+1}\n"
        f"💰 {PAYMENT_AMOUNT:,} so'm\n\nBekor qilish: /cancel"
    )
    await state.update_data(paying_user_id=user["id"], paying_grade=grade, paying_variant=variant_index)
    await state.set_state(PaymentState.waiting_check)
    await callback.answer()

@dp.message(PaymentState.waiting_check)
async def receive_payment_check(message: types.Message, state: FSMContext):
    if message.text and message.text.strip() == "/cancel":
        await message.answer("Bekor qilindi.", reply_markup=main_menu_keyboard())
        await state.clear()
        return

    if not message.photo:
        await message.answer("⚠️ Iltimos, to'lov cheki rasm formatida bo'lishi shart!")
        return

    data          = await state.get_data()
    p_id          = data["paying_user_id"]
    grade         = data["paying_grade"]
    variant_index = data.get("paying_variant", 0)
    user     = get_user_by_id(p_id)
    photo_id = message.photo[-1].file_id

    order_id = save_order(message.from_user.id, user["full_name"], grade, photo_id,
                          variant_index=variant_index)

    try:
        await bot.send_photo(
            ADMIN_ID,
            photo=photo_id,
            caption=(
                f"💳 YANGI TO'LOV!\n\n"
                f"📋 Buyurtma: #{order_id}\n"
                f"👤 {user['full_name']}\n"
                f"📚 {grade} — Variant {variant_index+1}\n"
                f"📞 {user['phone']}\n"
                f"💰 {PAYMENT_AMOUNT:,} so'm"
            ),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Tasdiqlash",
                                         callback_data=f"admin_confirm_{order_id}"),
                    InlineKeyboardButton(text="❌ Rad etish",
                                         callback_data=f"admin_reject_{order_id}"),
                ]
            ])
        )
    except Exception as e:
        print(f"Admin yuborishda xato: {e}")

    await message.answer(
        f"✅ Chek qabul qilindi!\n"
        f"📋 Buyurtma: #{order_id}\n"
        f"Admin tekshiruvidan so'ng faollashtiriladi.",
        reply_markup=main_menu_keyboard()
    )
    await state.clear()

# ─── ADMIN TO'LOV TASDIQLASH (callback ichida admin tekshirish) ───
@dp.callback_query(F.data.startswith("admin_confirm_"))
async def admin_confirm_inline(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Faqat admin!", show_alert=True)
        return

    order_id = int(callback.data.split("_")[2])
    order    = confirm_order(order_id)
    if not order:
        await callback.answer(f"#{order_id} topilmadi!", show_alert=True)
        return

    user = get_user_by_telegram_id(order["telegram_id"])
    if user:
        vi = order.get("variant_index", 0)
        grant_paid_test(user["id"], order["grade"], vi)
        add_vab(user["id"], 50)
        try:
            await bot.send_message(
                order["telegram_id"],
                f"🎉 To'lovingiz tasdiqlandi!\n\n"
                f"💎 {order['grade']} — Variant {vi+1} aktivlashtirildi!\n"
                f"💰 Bonus: +50 VAB\n\n"
                f"Boshlash uchun '💎 Pullik testlar' tugmasini bosing!",
                reply_markup=main_menu_keyboard()
            )
        except Exception:
            pass

    try:
        await callback.message.edit_caption(
            caption=(callback.message.caption or "") + f"\n\n✅ TASDIQLANDI"
        )
    except Exception:
        pass
    await callback.answer(f"✅ #{order_id} tasdiqlandi!")

@dp.callback_query(F.data.startswith("admin_reject_"))
async def admin_reject_inline(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Faqat admin!", show_alert=True)
        return

    order_id = int(callback.data.split("_")[2])
    order    = ORDER_CACHE.get(order_id)
    if not order:
        await callback.answer(f"#{order_id} topilmadi!", show_alert=True)
        return

    order["status"] = "rejected"
    try:
        await bot.send_message(
            order["telegram_id"],
            f"❌ #{order_id} to'lovingiz rad etildi.\n"
            f"Chek to'liq emas yoki rasm tushunarsiz.\n"
            f"Qayta to'lov qilishingizni so'raymiz."
        )
    except Exception:
        pass

    try:
        await callback.message.edit_caption(
            caption=(callback.message.caption or "") + f"\n\n❌ RAD ETILDI"
        )
    except Exception:
        pass
    await callback.answer(f"❌ #{order_id} rad etildi!")

@dp.callback_query(F.data.startswith("pay_vab_"))
async def pay_with_vab(callback: types.CallbackQuery):
    parts         = callback.data.split("_")
    grade         = parts[2]
    variant_index = int(parts[3])
    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return

    if user["vab"] < VAB_FOR_TEST_PURCHASE:
        await callback.answer(
            f"❌ VAB yetarli emas!\nKerak: {VAB_FOR_TEST_PURCHASE} VAB\nSizda: {user['vab']} VAB",
            show_alert=True
        )
        return

    if has_paid_test(user["id"], grade, variant_index):
        await callback.answer("Bu variant allaqachon faol!", show_alert=True)
        return

    success = spend_vab(user["id"], VAB_FOR_TEST_PURCHASE)
    if success:
        grant_paid_test(user["id"], grade, variant_index)
        await callback.message.answer(
            f"✅ {grade} — Variant {variant_index+1} aktivlashtirildi!\n"
            f"💰 -{VAB_FOR_TEST_PURCHASE} VAB sarflandi\n\n"
            f"💎 Testni hozir yuklashingiz mumkin!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💎 Boshlash",
                                      callback_data=f"start_paid_{grade}_{variant_index}")]
            ])
        )
    else:
        await callback.answer("Amalda xatolik!", show_alert=True)
    await callback.answer()

# ═══════════════════════════════════════════════
# 16. TEST BOSHLASH CALLBACK-LAR
# ═══════════════════════════════════════════════
@dp.callback_query(F.data == "start_free")
async def start_free_test(callback: types.CallbackQuery, state: FSMContext):
    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return

    if not await is_subscribed(callback.from_user.id):
        await callback.message.answer(
            "📢 Testni boshlash uchun kanalga a'zo bo'lishingiz kerak!\n\n",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📣 Kanalga a'zo bo'lish", url=CHANNEL_LINK)],
                [InlineKeyboardButton(text="✅ Obuna bo'ldim", callback_data="start_free")]
            ])
        )
        await callback.answer()
        return

    grade  = user["grade"]
    q_list = TESTS.get(grade, [])
    if not q_list:
        await callback.message.answer(f"{grade} uchun bepul ulamolar yo'q.")
        await callback.answer()
        return

    await _start_test_session(callback, state, user, q_list, "free")

@dp.callback_query(F.data.startswith("start_paid_"))
async def start_paid_test(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    grade         = parts[2]
    variant_index = int(parts[3])

    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return

    if not has_paid_test(user["id"], grade, variant_index):
        await callback.answer("Ushbu pullik test aktiv qilinmagan!", show_alert=True)
        return

    all_variants = PAID_TESTS.get(grade, [])
    if not all_variants:
        await callback.message.answer(f"{grade} savollari topilmadi.")
        await callback.answer()
        return

    VARIANT_SIZE = 3
    start  = variant_index * VARIANT_SIZE
    end    = start + VARIANT_SIZE
    q_list = all_variants[start:end] if start < len(all_variants) else all_variants

    await _start_test_session(callback, state, user, q_list, "paid", grade=grade)

async def _start_test_session(callback, state, user, q_list, test_type, grade=None):
    if not grade:
        grade = user["grade"]
    tag = "💎 Pullik" if test_type == "paid" else "🆓 Bepul"

    await state.set_state(TestProcess.answering)
    await state.update_data(
        grade=grade, questions=q_list, current=0, score=0, streak=0,
        start_ts=time.time(), db_user_id=user["id"], user_name=user["full_name"],
        last_info_msg_id=None, last_q_msg_id=None, test_type=test_type,
    )
    await callback.message.answer(
        f"🚀 {grade} — {tag} sinov boshlandi!\n"
        f"📝 Savollar: {len(q_list)}\n"
        f"⏱ Vaqt: 45 daqiqa\n\nOmad! 🍀 @IlmNuri_Markazi"
    )
    await callback.answer()
    asyncio.create_task(timeout_watcher(callback.from_user.id, state))
    await send_question(callback.from_user.id, state)

@dp.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: types.CallbackQuery):
    await callback.message.answer("Asosiy menyu:", reply_markup=main_menu_keyboard())
    await callback.answer()

# ═══════════════════════════════════════════════
# 17. JAVOB TEKSHIRISH
# ═══════════════════════════════════════════════
@dp.callback_query(F.data.startswith("ans_"), TestProcess.answering)
async def check_answer(callback: types.CallbackQuery, state: FSMContext):
    chosen = callback.data.split("_")[1]
    data   = await state.get_data()
    index  = data["current"]
    q      = data["questions"][index]
    score  = data.get("score", 0)
    streak = data.get("streak", 0)

    if chosen == q["answer"]:
        streak += 1
        score  += 1
        toast   = "✅ To'g'ri!" + (" 🔥" if streak >= 2 else "")
    else:
        streak = 0
        cl     = q["answer"]
        toast  = f"❌ Noto'g'ri! To'g'ri: {cl}) {q['options'][cl]}"

    await state.update_data(score=score, streak=streak, current=index + 1)
    try:
        await callback.answer(toast, show_alert=False)
    except Exception:
        pass
    await send_question(callback.from_user.id, state)

# ═══════════════════════════════════════════════
# 18. ADMIN PANEL & STATISTIKA (O'zgarmagan qismlar)
# ═══════════════════════════════════════════════
@dp.message(Command("refresh"))
async def refresh_cache(message: types.Message):
    if not is_admin(message.from_user.id): return
    old = get_users_count()
    load_users_to_cache()
    load_inlim_and_orders_to_cache()
    new = get_users_count()
    await message.answer(f"✅ Baza yangilandi!\nEski cache: {old} → Yangi cache: {new} ta")

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id): return
    await message.answer(
        "🛠 Admin panel:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Xabar yuborish",       callback_data="send_ad")],
            [InlineKeyboardButton(text="📊 Statistika",            callback_data="admin_stats")],
            [InlineKeyboardButton(text="💳 Kutilayotgan to'lovlar", callback_data="pending_orders")],
            [InlineKeyboardButton(text="🏆 INLIM sozlamalari",    callback_data="inlim_admin")],
        ])
    )

# ... [Kodingizdagi boshqa barcha admin komandalar: inlim_admin, send_ad, confirm, reject va h.k. aynan o'zgarishsiz qolsin]

# ═══════════════════════════════════════════════
# 19. MAIN — WEBHOOK (Render ulanishi)
# ═══════════════════════════════════════════════
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler

RENDER_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "ilm-kelajak-bot.onrender.com")
if not RENDER_HOSTNAME.startswith("https://"):
    RENDER_HOSTNAME = f"https://{RENDER_HOSTNAME}"
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{RENDER_HOSTNAME}{WEBHOOK_PATH}"
PORT = int(os.environ.get("PORT", 10000))

async def keep_alive_ping():
    """Render bepul instansi o'chib qolishi oldini oladi (Health Pinger)"""
    await asyncio.sleep(60)
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{RENDER_HOSTNAME}/health", timeout=aiohttp.ClientTimeout(total=10)):
                    pass
        except Exception:
            pass
        await asyncio.sleep(14 * 60)

async def on_startup(app: web.Application) -> None:
    logging.info(f"Webhook o'rnatilmoqda: {WEBHOOK_URL}")
    await bot.delete_webhook()
    result = await bot.set_webhook(url=WEBHOOK_URL)
    if result:
        logging.info("✅ Webhook muvaffaqiyatli o'rnatildi!")
    else:
        logging.error("❌ Webhook ulanmadi!")
    asyncio.create_task(keep_alive_ping())

async def on_shutdown(app: web.Application) -> None:
    logging.info("Bot o'chmoqda...")
    await bot.delete_webhook()
    await bot.session.close()

async def health_check(request):
    return web.Response(text="OK", status=200)

def create_app():
    app = web.Application()
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    return app

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=PORT)
