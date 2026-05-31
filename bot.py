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
    "prize_fund": 0,
    "sponsors": [],
    "test_dates": [],
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
# Google Sheets ulanish
# ═══════════════════════════════════════════════
def get_sheet():
    scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEETS_ID).sheet1

def get_orders_sheet():
    scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
    client = gspread.authorize(creds)
    sh = client.open_by_key(SHEETS_ID)
    try:
        return sh.worksheet("Buyurtmalar")
    except Exception:
        ws = sh.add_worksheet(title="Buyurtmalar", rows="1000", cols="10")
        ws.append_row(["Buyurtma_ID","Telegram_ID","Ism","Sinf","Summa","Status","Sana"])
        return ws

def get_inlim_sheet():
    scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
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
# 2. TEST SAVOLLARI
# ═══════════════════════════════════════════════
TESTS = {
    "1-sinf": [
        {"question": "Hisoblang  2 + 3 + 4 ",
         "options": {"A": "8", "B": "9", "C": "10", "D": "11"},
         "answer": "B", "difficulty": "easy"},
        {"question": "Hisoblang  10 - 4 - 3  ?",
         "options": {"A": "2", "B": "4", "C": "3", "D": "5"},
         "answer": "C", "difficulty": "easy"},
        {"question": "Hisoblang  7 + 8 = ?",
         "options": {"A": "14", "B": "16", "C": "13", "D": "15"},
         "answer": "D", "difficulty": "easy"},
        {"question": "Hisoblang  15 - 6 = ?",
         "options": {"A": "8", "B": "10", "C": "9", "D": "7"},
         "answer": "C", "difficulty": "easy"},
        {"question": "Hisoblang   9 + 9 = ?",
         "options": {"A": "17", "B": "18", "C": "19", "D": "20"},
         "answer": "B", "difficulty": "easy"},
        {"question": "Hisoblang  20 - 7 = ?",
         "options": {"A": "12", "B": "14", "C": "11", "D": "13"},
         "answer": "D", "difficulty": "easy"},
        {"question": "Hisoblang  5 + 6 + 7 = ?",
         "options": {"A": "17", "B": "19", "C": "18", "D": "16"},
         "answer": "C", "difficulty": "easy"},
        {"question": "4 + [] = 11. Qutichada qanday son bor?",
         "options": {"A": "6", "B": "7", "C": "8", "D": "9"},
         "answer": "B", "difficulty": "medium"},
        {"question": "[] - 5 = 8. Qutichada qanday son bor?",
         "options": {"A": "12", "B": "14", "C": "11", "D": "13"},
         "answer": "D", "difficulty": "medium"},
        {"question": "4 + [] + 3 = 12. Qutichada qanday son bor?",
         "options": {"A": "4", "B": "6", "C": "5", "D": "3"},
         "answer": "C", "difficulty": "medium"},
        {"question": "Daftarda 6 ta sahifa bor, yana 4 ta qo'shildi. Jami nechta bo'ldi?",
         "options": {"A": "9", "B": "10", "C": "11", "D": "12"},
         "answer": "B", "difficulty": "easy"},
        {"question": "Bog'da 9 ta olma, 5 ta nok bor. Olmalar nokdan nechta ko'p?",
         "options": {"A": "3", "B": "5", "C": "2", "D": "4"},
         "answer": "D", "difficulty": "easy"},
        {"question": "Avtobusda 12 ta yo'lovchi bor edi. 5 tasi tushdi. Qanchasi qoldi?",
         "options": {"A": "6", "B": "8", "C": "5", "D": "7"},
         "answer": "D", "difficulty": "easy"},
        {"question": "ILM NURI markazida 20 ta o'quvchi bor. 8 tasi qiz. Nechta o'g'il bola bor?",
         "options": {"A": "11", "B": "13", "C": "12", "D": "10"},
         "answer": "C", "difficulty": "easy"},
        {"question": "Savatchada 6 ta qizil va 7 ta yashil olma bor. Savatda jami nechta olma bor?",
         "options": {"A": "12", "B": "14", "C": "11", "D": "13"},
         "answer": "D", "difficulty": "easy"},
        {"question": "Anvar bir sonni o'yladi. Unga 7 qo'shganda 15 chiqdi. U qanday son o'ylagan?",
         "options": {"A": "7", "B": "9", "C": "8", "D": "6"},
         "answer": "C", "difficulty": "medium"},
        {"question": "3 do'st konfetni teng bo'lishdi, so'ngra 1 ta ortib qoldi. Eng kamida nechta konfet bor edi?",
         "options": {"A": "7", "B": "13", "C": "4", "D": "10"},
         "answer": "C", "difficulty": "hard"},
        {"question": "Dilnozaning oldida 4 ta, orqasida 5 ta o'quvchi bor. Jami nechta o'quvchi bor?",
         "options": {"A": "9", "B": "11", "C": "8", "D": "10"},
         "answer": "D", "difficulty": "medium"},
        {"question": "Fermada tovuq va sigrlar boshi 10 ta, oyoqlari 28 ta bo'lsa. Nechta sigir bor?",
         "options": {"A": "3", "B": "5", "C": "4", "D": "6"},
         "answer": "C", "difficulty": "hard"},
        {"question": "Odam har kuni ertalab 2 ta, kechqurun 3 ta dori ichadi. U 4 kunda jami nechta dori ichadi?",
         "options": {"A": "18", "B": "22", "C": "16", "D": "20"},
         "answer": "D", "difficulty": "medium"},
        {"question": "5, 8, 11, 14, [] ketma-ketlikni davom ettiring.",
         "options": {"A": "16", "B": "18", "C": "15", "D": "17"},
         "answer": "D", "difficulty": "medium"},
        {"question": "Qaysi son 14 dan katta va 16 dan kichik?",
         "options": {"A": "14", "B": "16", "C": "13", "D": "15"},
         "answer": "D", "difficulty": "easy"},
        {"question": "Uchburchakning nechta burchagi bor?",
         "options": {"A": "2", "B": "4", "C": "3", "D": "5"},
         "answer": "C", "difficulty": "easy"},
        {"question": "Kvadratning nechta tomoni bor?",
         "options": {"A": "3", "B": "5", "C": "6", "D": "4"},
         "answer": "D", "difficulty": "easy"},
        {"question": "Katta kvadrat tomonlaridan uchburchak uchlarini ayirsa qanday son hosil bo'ladi?",
         "options": {"A": "1", "B": "3", "C": "4", "D": "2"},
         "answer": "A", "difficulty": "medium"},
        {"question": "Bir uchburchak ichiga yana bir uchburchak chizildi. Hammasi nechta uchburchak?",
         "image": "https://i.ibb.co/B2KNwVkS/3.png",
         "options": {"A": "2", "B": "4", "C": "5", "D": "3"},
         "answer": "C", "difficulty": "hard"},
        {"question": "Bir son ikkinchisidan 4 ta katta. Yig'indisi 10. Katta son qaysi?",
         "options": {"A": "6", "B": "8", "C": "5", "D": "7"},
         "answer": "D", "difficulty": "hard"},
        {"question": "Dushanba 1-kun bo'lsa, shanba nechanchi kun?",
         "options": {"A": "5", "B": "7", "C": "4", "D": "6"},
         "answer": "D", "difficulty": "easy"},
        {"question": "100 gacha 5 raqami bilan tugaydigan sonlar nechtata?",
         "options": {"A": "10", "B": "25", "C": "15", "D": "20"},
         "answer": "A", "difficulty": "hard"},
        {"question": "1 dan 10 gacha bo'lgan barcha sonlar yig'indisi nechaga teng?",
         "options": {"A": "50", "B": "60", "C": "45", "D": "55"},
         "answer": "D", "difficulty": "hard"},
    ],
    "2-sinf": [
        {"question": "Qonuniyatni davom ettiring: 12, 16, 20, 24, []",
         "options": {"A": "26", "B": "28", "C": "30", "D": "32"},
         "answer": "B", "difficulty": "easy"},
        {"question": "47 sonidan keyin keluvchi birinchi toq sonni toping.",
         "options": {"A": "48", "B": "50", "C": "49", "D": "51"},
         "answer": "C", "difficulty": "easy"},
        {"question": "3 ta o'nlik va 8 ta birlikdan 15 ni ayiring.",
         "options": {"A": "23", "B": "25", "C": "21", "D": "18"},
         "answer": "A", "difficulty": "easy"},
        {"question": "Kvadratning barcha tomonlari yig'indisi 16 sm. Uning bir tomoni necha sm?",
         "options": {"A": "8", "B": "2", "C": "6", "D": "4"},
         "answer": "D", "difficulty": "easy"},
        {"question": "Eng kichik ikki xonali songa 45 ni qo'shing.",
         "options": {"A": "55", "B": "56", "C": "54", "D": "46"},
         "answer": "A", "difficulty": "easy"},
        {"question": "1 metrdan 40 santimetrni ayirganda qancha qoladi?",
         "options": {"A": "50 sm", "B": "60 sm", "C": "70 sm", "D": "40 sm"},
         "answer": "B", "difficulty": "easy"},
        {"question": "Agar soat 14:00 bo'lsa, 3 soatdan keyin soat necha bo'ladi?",
         "options": {"A": "16:00", "B": "18:00", "C": "17:00", "D": "15:00"},
         "answer": "C", "difficulty": "easy"},
        {"question": "45, 42, 39, 36, [] qatordagi keyingi sonni toping.",
         "options": {"A": "30", "B": "34", "C": "33", "D": "35"},
         "answer": "C", "difficulty": "medium"},
        {"question": "Kitobning 10-betidan 25-betigacha o'qildi. Jami necha bet o'qilgan?",
         "options": {"A": "15", "B": "16", "C": "14", "D": "17"},
         "answer": "B", "difficulty": "medium"},
        {"question": "Hovlidagi tovuqlar va quyonlarning jami oyoqlari 12 ta. Agar quyonlar 2 ta bo'lsa, tovuqlar nechta?",
         "options": {"A": "3 ta", "B": "4 ta", "C": "2 ta", "D": "5 ta"},
         "answer": "C", "difficulty": "medium"},
        {"question": "18 tasmali lentani 3 sm dan bo'laklarga bo'lish uchun necha marta kesish kerak?",
         "options": {"A": "6", "B": "4", "C": "5", "D": "3"},
         "answer": "C", "difficulty": "medium"},
        {"question": "Anvar 15 yoshda, u singlisidan 4 yosh katta. Singlisi necha yoshda?",
         "options": {"A": "11", "B": "19", "C": "12", "D": "10"},
         "answer": "A", "difficulty": "easy"},
        {"question": "Qaysi ikki xonali sonning raqamlari yig'indisi eng katta?",
         "options": {"A": "90", "B": "19", "C": "89", "D": "99"},
         "answer": "D", "difficulty": "medium"},
        {"question": "Dilshodda 12 ta qalam bor edi. U yarmini do'stiga berdi. O'zida nechta qoldi?",
         "options": {"A": "4", "B": "6", "C": "8", "D": "10"},
         "answer": "B", "difficulty": "easy"},
        {"question": "ILM NURI markazida dars soat 09:00 da boshlanadi va 45 daqiqa davom etadi. Dars soat nechada tugaydi?",
         "options": {"A": "09:40", "B": "10:00", "C": "09:45", "D": "09:50"},
         "answer": "C", "difficulty": "easy"},
        {"question": "Bir qatorda 20 ta daraxt bor. 1-va 3-daraxtlar orasida nechta daraxt bor?",
         "options": {"A": "1", "B": "2", "C": "3", "D": "0"},
         "answer": "A", "difficulty": "medium"},
        {"question": "8 va 3 raqamlaridan foydalanib yozish mumkin bo'lgan eng kichik ikki xonali sonni toping.",
         "options": {"A": "83", "B": "38", "C": "33", "D": "88"},
         "answer": "B", "difficulty": "easy"},
        {"question": "To'g'ri to'rtburchakning bo'yi 8 sm, eni esa 3 sm. Perimetrini toping.",
         "options": {"A": "11 sm", "B": "22 sm", "C": "14 sm", "D": "24 sm"},
         "answer": "B", "difficulty": "medium"},
        {"question": "Savatda 5 ta qizil, 4 ta ko'k va 3 ta yashil koptok bor. Qaramasdan eng kamida nechta olinsa, albatta 1 ta qizil koptok chiqadi?",
         "options": {"A": "5", "B": "8", "C": "12", "D": "10"},
         "answer": "B", "difficulty": "hard"},
        {"question": "Ali va Vali birgalikda 10 ta kitob o'qishdi. Ali Validan 2 ta ko'p o'qigan bo'lsa, Vali nechta o'qigan?",
         "options": {"A": "4", "B": "6", "C": "5", "D": "3"},
         "answer": "A", "difficulty": "hard"},
        {"question": "Ikki ota va ikki o'g'il jami 3 kishi bo'lishi mumkinmi?",
         "options": {"A": "Yo'q", "B": "Ha, bobo, ota va o'g'il", "C": "Faqat 4 kishi bo'ladi", "D": "Bilmayman"},
         "answer": "B", "difficulty": "hard"},
        {"question": "50 dan 60 gacha nechta 5 raqami qatnashgan?",
         "options": {"A": "10", "B": "11", "C": "9", "D": "12"},
         "answer": "B", "difficulty": "hard"},
        {"question": "Qaysi son 5 ga ham, 2 ga ham bo'linadi?",
         "options": {"A": "15", "B": "12", "C": "10", "D": "5"},
         "answer": "C", "difficulty": "medium"},
        {"question": "Qutida 12 ta shar bor edi. Ularning 1/3 qismi qizil. Nechta qizil shar bor?",
         "options": {"A": "4", "B": "3", "C": "6", "D": "2"},
         "answer": "A", "difficulty": "medium"},
        {"question": "Bugun payshanba bo'lsa, 10 kundan keyin haftaning qaysi kuni bo'ladi?",
         "options": {"A": "Shanba", "B": "Yakshanba", "C": "Dushanba", "D": "Yakka-shanba"},
         "answer": "B", "difficulty": "hard"},
        {"question": "Ikkita uchburchak va bitta kvadratning jami nechta burchagi bor?",
         "options": {"A": "8", "B": "12", "C": "10", "D": "14"},
         "answer": "C", "difficulty": "medium"},
        {"question": "Agar A + B = 15 va A - B = 5 bo'lsa, A soni nechaga teng?",
         "options": {"A": "5", "B": "15", "C": "10", "D": "20"},
         "answer": "C", "difficulty": "hard"},
        {"question": "7 ta konfet 1400 so'm turadi. 1 ta konfet necha so'm?",
         "options": {"A": "200", "B": "300", "C": "100", "D": "400"},
         "answer": "A", "difficulty": "medium"},
        {"question": "1 dan 20 gacha bo'lgan sonlar ichida nechta 1 raqami bor?",
         "options": {"A": "10", "B": "11", "C": "12", "D": "9"},
         "answer": "C", "difficulty": "hard"},
        {"question": "Qaysi amal xato bajarilgan?",
         "options": {"A": "20+30=50", "B": "45-15=30", "C": "12+8=20", "D": "35+5=30"},
         "answer": "D", "difficulty": "easy"},
    ],
    "3-sinf": [
        {"question": "5, 11, 17, 23, [] qonuniyatni davom ettiring.",
         "options": {"A": "27", "B": "29", "C": "30", "D": "28"},
         "answer": "B", "difficulty": "easy"},
        {"question": "To'rtta 8 ning yig'indisi nechaga teng?",
         "options": {"A": "24", "B": "36", "C": "32", "D": "40"},
         "answer": "C", "difficulty": "easy"},
        {"question": "63 : 9 + 15 ifodaning qiymatini toping.",
         "options": {"A": "21", "B": "22", "C": "24", "D": "20"},
         "answer": "B", "difficulty": "easy"},
        {"question": "Kvadratning perimetri 36 sm. Uning tomoni necha sm?",
         "options": {"A": "6", "B": "8", "C": "9", "D": "12"},
         "answer": "C", "difficulty": "easy"},
        {"question": "Eng kichik uch xonali sondan eng katta ikki xonali sonni ayiring.",
         "options": {"A": "1", "B": "10", "C": "0", "D": "11"},
         "answer": "A", "difficulty": "medium"},
        {"question": "3 ta daftar 6000 so'm turadi. 5 ta daftar necha so'm bo'ladi?",
         "options": {"A": "8000", "B": "10000", "C": "9000", "D": "12000"},
         "answer": "B", "difficulty": "medium"},
        {"question": "Sinfda 24 ta o'quvchi bor. Ularning choragi (1/4 qismi) a'lochi. Nechta a'lochi o'quvchi bor?",
         "options": {"A": "4", "B": "8", "C": "6", "D": "10"},
         "answer": "C", "difficulty": "medium"},
        {"question": "To'g'ri to'rtburchakning bo'yi 10 sm, eni esa bo'yidan 4 sm qisqa. Perimetrini toping.",
         "options": {"A": "28 sm", "B": "32 sm", "C": "14 sm", "D": "30 sm"},
         "answer": "B", "difficulty": "medium"},
        {"question": "Qatorda 25 ta bola turibdi. Anvar oldindan 10-o'rinda bo'lsa, orqadan nechanchi?",
         "options": {"A": "15", "B": "16", "C": "14", "D": "17"},
         "answer": "B", "difficulty": "hard"},
        {"question": "Qaysi sonni 4 ga ko'paytirib, 8 ni ayirsak 24 hosil bo'ladi?",
         "options": {"A": "6", "B": "7", "C": "8", "D": "9"},
         "answer": "C", "difficulty": "medium"},
        {"question": "Daraxtda 18 ta chumchuq o'tirgan edi. Yarmi uchib ketdi va yana 5 tasi qo'ndi. Nechta chumchuq bo'ldi?",
         "options": {"A": "12", "B": "14", "C": "9", "D": "15"},
         "answer": "B", "difficulty": "easy"},
        {"question": "3 kg olma 12000 so'm. 1 kg olma necha so'm?",
         "options": {"A": "3000", "B": "5000", "C": "4000", "D": "6000"},
         "answer": "C", "difficulty": "easy"},
        {"question": "Eng katta ikki xonali juft sonni toping.",
         "options": {"A": "99", "B": "98", "C": "100", "D": "90"},
         "answer": "B", "difficulty": "easy"},
        {"question": "Bir soatning 1/3 qismi necha daqiqaga teng?",
         "options": {"A": "15", "B": "30", "C": "20", "D": "40"},
         "answer": "C", "difficulty": "medium"},
        {"question": "Kitob 120 sahifa. Lola har kuni 10 sahifa o'qisa, kitobni necha kunda tugatadi?",
         "options": {"A": "10", "B": "14", "C": "12", "D": "11"},
         "answer": "C", "difficulty": "easy"},
        {"question": "Ikkita sonning yig'indisi 50, ayirmasi 10. Kichik sonni toping.",
         "options": {"A": "20", "B": "30", "C": "25", "D": "15"},
         "answer": "A", "difficulty": "hard"},
        {"question": "6 ta mushuk 6 ta sichqonni 6 daqiqada tutsa, 1 ta mushuk 1 ta sichqonni necha daqiqada tutadi?",
         "options": {"A": "1", "B": "6", "C": "3", "D": "12"},
         "answer": "B", "difficulty": "hard"},
        {"question": "7, 0, 4 raqamlaridan foydalanib yozish mumkin bo'lgan eng kichik uch xonali son qaysi?",
         "options": {"A": "047", "B": "470", "C": "407", "D": "704"},
         "answer": "C", "difficulty": "medium"},
        {"question": "Shokolad 4 bo'lakka bo'lindi. Har bir bo'lak yana 2 ga bo'lindi. Jami nechta bo'lak?",
         "options": {"A": "6", "B": "10", "C": "8", "D": "12"},
         "answer": "C", "difficulty": "easy"},
        {"question": "Savatda 20 ta koptok bor. Ularning 1/5 qismi ko'k, qolgani qizil. Qizil koptoklar nechta?",
         "options": {"A": "4", "B": "16", "C": "15", "D": "12"},
         "answer": "B", "difficulty": "medium"},
        {"question": "Oila 3 ta qiz va har bir qizning bittadan akasi bor. Oilada jami nechta farzand?",
         "options": {"A": "6", "B": "4", "C": "5", "D": "3"},
         "answer": "B", "difficulty": "hard"},
        {"question": "Ikki xonali sonning raqamlari ko'paytmasi 12, yig'indisi 7. Bu qaysi son?",
         "options": {"A": "62", "B": "43", "C": "84", "D": "35"},
         "answer": "B", "difficulty": "medium"},
        {"question": "Velosipedda 2 ta g'ildirak, mototsiklda esa 3 ta (aravali). 2 ta velosiped va 3 ta mototsiklning g'ildiraklari nechta?",
         "options": {"A": "10", "B": "12", "C": "13", "D": "11"},
         "answer": "C", "difficulty": "medium"},
        {"question": "Quyidagi amallardan qaysi biri eng katta qiymatga ega?",
         "options": {"A": "5 * 5", "B": "9 * 3", "C": "4 * 7", "D": "10 * 2"},
         "answer": "C", "difficulty": "easy"},
        {"question": "2 metr arqonni 20 sm dan qilib kessak, nechta bo'lak hosil bo'ladi?",
         "options": {"A": "10", "B": "11", "C": "9", "D": "8"},
         "answer": "A", "difficulty": "medium"},
        {"question": "Sutkaning 1/4 qismi necha soatga teng?",
         "options": {"A": "4", "B": "6", "C": "8", "D": "12"},
         "answer": "B", "difficulty": "easy"},
        {"question": "Uchburchakning hamma tomonlari 7 sm dan. Uning perimetri necha?",
         "options": {"A": "14", "B": "28", "C": "21", "D": "35"},
         "answer": "C", "difficulty": "easy"},
        {"question": "Bugun 20-aprel bo'lsa, bir haftadan keyin sana necha bo'ladi?",
         "options": {"A": "27-aprel", "B": "26-aprel", "C": "28-aprel", "D": "25-aprel"},
         "answer": "A", "difficulty": "easy"},
        {"question": "15 + 15 + 15 + 15 ifodani ko'paytirish shaklida yozing.",
         "options": {"A": "15 * 3", "B": "15 * 5", "C": "15 * 4", "D": "4 * 4"},
         "answer": "C", "difficulty": "easy"},
        {"question": "Agar x + 25 = 60 bo'lsa, x nechaga teng?",
         "options": {"A": "35", "B": "45", "C": "25", "D": "40"},
         "answer": "A", "difficulty": "easy"},
    ],
    "4-sinf": [
        {"question": "25 * 4 + 150 : 3 ifodaning qiymatini toping.",
         "options": {"A": "130", "B": "150", "C": "120", "D": "140"},
         "answer": "B", "difficulty": "easy"},
        {"question": "Eng kichik to'rt xonali sondan eng katta uch xonali sonni ayiring.",
         "options": {"A": "10", "B": "100", "C": "1", "D": "11"},
         "answer": "C", "difficulty": "easy"},
        {"question": "To'g'ri to'rtburchakning yuzi 48 kv.sm. Bo'yi 8 sm bo'lsa, uning perimetri necha sm?",
         "options": {"A": "14", "B": "28", "C": "24", "D": "32"},
         "answer": "B", "difficulty": "medium"},
        {"question": "Poyezd 3 soatda 240 km yo'l yurdi. U xuddi shu tezlikda 5 soatda necha km yuradi?",
         "options": {"A": "350", "B": "420", "C": "400", "D": "450"},
         "answer": "C", "difficulty": "medium"},
        {"question": "720 : (x - 5) = 80 tenglamadagi x ni toping.",
         "options": {"A": "14", "B": "12", "C": "13", "D": "15"},
         "answer": "A", "difficulty": "medium"},
        {"question": "Sutkaning 1/6 qismi necha soatga teng?",
         "options": {"A": "4", "B": "6", "C": "3", "D": "5"},
         "answer": "A", "difficulty": "easy"},
        {"question": "Kvadratning tomoni 2 marta orttirilsa, uning perimetri necha marta ortadi?",
         "options": {"A": "4", "B": "3", "C": "2", "D": "O'zgarmaydi"},
         "answer": "C", "difficulty": "medium"},
        {"question": "1, 4, 9, 16, 25, [] ketma-ketlikdagi keyingi sonni toping.",
         "options": {"A": "30", "B": "36", "C": "49", "D": "35"},
         "answer": "B", "difficulty": "medium"},
        {"question": "Kitobning betlarini raqamlash uchun 1 dan 15 gacha nechta raqam ishlatiladi?",
         "options": {"A": "15", "B": "21", "C": "18", "D": "20"},
         "answer": "B", "difficulty": "medium"},
        {"question": "Uchta sonning o'rta arifmetigi 20 ga teng. Ulardan ikkitasi 15 va 25 bo'lsa, uchinchi sonni toping.",
         "options": {"A": "20", "B": "10", "C": "30", "D": "25"},
         "answer": "A", "difficulty": "medium"},
        {"question": "Onasi 32 yoshda, qizi 8 yoshda. Necha yildan keyin ona qizidan 3 marta katta bo'ladi?",
         "options": {"A": "2", "B": "3", "C": "4", "D": "5"},
         "answer": "C", "difficulty": "hard"},
        {"question": "3 kg qand 24 000 so'm turadi. 500 gramm qand necha so'm?",
         "options": {"A": "4000", "B": "6000", "C": "8000", "D": "3000"},
         "answer": "A", "difficulty": "medium"},
        {"question": "Qaysi son 3 ga ham, 4 ga ham qoldiqsiz bo'linadi?",
         "options": {"A": "14", "B": "18", "C": "24", "D": "16"},
         "answer": "C", "difficulty": "easy"},
        {"question": "Agar x * 15 = 0 bo'lsa, x nechaga teng?",
         "options": {"A": "1", "B": "0", "C": "15", "D": "Mavjud emas"},
         "answer": "B", "difficulty": "easy"},
        {"question": "Kubning nechta qirrasi bor?",
         "options": {"A": "6", "B": "8", "C": "12", "D": "10"},
         "answer": "C", "difficulty": "medium"},
        {"question": "1 dan 80 gacha bo'lgan sonlar orasida nechta 7 raqami qatnashgan?",
         "options": {"A": "15", "B": "16", "C": "14", "D": "18"},
         "answer": "D", "difficulty": "medium"},
        {"question": "Teng yonli uchburchakning perimetri 20 sm. Asosi 6 sm bo'lsa, yon tomoni necha sm?",
         "options": {"A": "7", "B": "14", "C": "8", "D": "6"},
         "answer": "A", "difficulty": "medium"},
        {"question": "Mevalar savatida 48 ta meva bor. Ularning 1/4 qismi olma, 1/3 qismi nok, qolgani shaftoli. Shaftolilar nechta?",
         "options": {"A": "12", "B": "16", "C": "20", "D": "28"},
         "answer": "C", "difficulty": "hard"},
        {"question": "4 ta mushuk 4 ta sichqonni 4 minutda yeydi. 10 ta mushuk 10 ta sichqonni necha minutda yeydi?",
         "options": {"A": "10", "B": "1", "C": "4", "D": "40"},
         "answer": "C", "difficulty": "hard"},
        {"question": "x qanday son?\n 81-36=3\n 49-9=4\n  25-16=x",
         "options": {"A": "1", "B": "10", "C": "100", "D": "11"},
         "answer": "A", "difficulty": "easy"},
        {"question": "Sonni 5 ga bo'lganda qoldiq qaysi son bo'lishi mumkin emas?",
         "options": {"A": "1", "B": "3", "C": "5", "D": "4"},
         "answer": "C", "difficulty": "easy"},
        {"question": "Agar kvadratning yuzi 25 kv.sm bo'lsa, uning perimetri necha sm?",
         "options": {"A": "25", "B": "20", "C": "10", "D": "15"},
         "answer": "B", "difficulty": "medium"},
        {"question": "2, 0, 5, 8 raqamlaridan foydalanib tuzish mumkin bo'lgan eng katta to'rt xonali son qaysi?",
         "options": {"A": "8502", "B": "8520", "C": "8250", "D": "5820"},
         "answer": "B", "difficulty": "easy"},
        {"question": "Rasmga qarang. 1ta Ayiq + 1 ta ot + 1 ta o'rdak natijasini aniqlang?",
         "image": "https://i.ibb.co/ZzvTrsPM/2.jpg",
         "options": {"A": "26", "B": "25", "C": "20", "D": "18"},
         "answer": "A", "difficulty": "hard"},
        {"question": "Ikki sonning ko'paytmasi 120 ga teng. Agar ko'paytuvchilardan biri 3 marta orttirilsa, yangi ko'paytma necha bo'ladi?",
         "options": {"A": "40", "B": "360", "C": "123", "D": "240"},
         "answer": "B", "difficulty": "medium"},
        {"question": "Aylana radiusi 5 sm bo'lsa, uning eng uzun vatari (diametri) necha sm?",
         "options": {"A": "5", "B": "15", "C": "10", "D": "20"},
         "answer": "C", "difficulty": "easy"},
        {"question": "Jasurning uyidan ilm nurigacha 45 daqiqa. U 7:05 da bordi, 15 daqiqa kechikdi. U uydan qachon chiqdi?",
         "image": "https://i.ibb.co/pvdc2wPb/1.jpg",
         "options": {"A": "A", "B": "B", "C": "C", "D": "E"},
         "answer": "C", "difficulty": "easy"},
    ],
    "5-sinf": [
        {"question": "Bog'bon insektitsid sepganda hosil bo'lmasligi sababi nimada?",
         "options": {"A": "Meva zararkunandadan shikastlanadi",
                     "B": "Changlanish bo'lmaydi — changlatuvchi hasharotlar yo'q bo'lib ketadi",
                     "C": "O'simlik qurib qoladi", "D": "Chang donasi shikastlanadi"},
         "answer": "B", "difficulty": "medium"},
        {"question": "Ikki jinsli gul deb qaysi gullarga aytiladi?",
         "options": {"A": "Faqat changchili", "B": "Ham changchi, ham urug'chisi bor gullarga",
                     "C": "Gulkosabargsiz", "D": "Faqat urug'chili"},
         "answer": "B", "difficulty": "easy"},
        {"question": "Oq ayiqning tukining ostidagi terisi qora. Nima uchun?",
         "options": {"A": "Qora teri quyosh issiqligini yaxshi singdirib saqlaydi",
                     "B": "Kasallikdan himoya", "C": "Estetik sabab", "D": "Kamuflyaj uchun"},
         "answer": "A", "difficulty": "easy"},
        {"question": "Zaharli qurbaqalar yorqin rangli. Bu qanday moslanish?",
         "options": {"A": "Tana rangi bezagi", "B": "Suv saqlov mexanizmi", "C": "Kamuflyaj",
                     "D": "Aposematizm — yorqin rang yirtqichlarga ogohlantiruvchi signal"},
         "answer": "D", "difficulty": "medium"},
        {"question": "Spirt suvga qaraganda tezroq bug'lanishining sababi?",
         "options": {"A": "Spirt og'irroq",
                     "B": "Spirt zarrachalari o'rtasidagi tortishish suv zarrachalarnikidan kuchsizroq",
                     "C": "Spirt kattaroq", "D": "Spirt issiqroq"},
         "answer": "B", "difficulty": "medium"},
        {"question": "Muzlaganda suv kengayadi. Ko'priqlarda nima uchun bo'shliq qoldiriladi?",
         "options": {"A": "Suv oqishi uchun", "B": "Bezak uchun", "C": "Sovuqda metall qisqaradi",
                     "D": "Muzlagan suv kengayib konstruksiyani yorib yubormasligi uchun"},
         "answer": "D", "difficulty": "medium"},
        {"question": "100 g suvda 20 g tuz eriganda hosil bo'lgan eritma konsentratsiyasi qancha?",
         "options": {"A": "16.7% (20/120×100)", "B": "10%", "C": "25%", "D": "20%"},
         "answer": "A", "difficulty": "hard"},
        {"question": "Ko'cha yo'liga qish faslida tuz sepilishi sababi?",
         "options": {"A": "Bezak uchun", "B": "Tuz yo'lni isitadi",
                     "C": "Tuzli eritma muzlash harorati 0°C dan pastda",
                     "D": "Yo'l uchun ozuqa"},
         "answer": "C", "difficulty": "medium"},
        {"question": "Parashyutchi terminal tezlikda tushayotganda kuchlar qanday?",
         "options": {"A": "Faqat gravitatsiya", "B": "Faqat havo qarshiligi",
                     "C": "Gravitatsiya > qarshilik",
                     "D": "Gravitatsiya = havoning qarshilik kuchi — muvozanat"},
         "answer": "D", "difficulty": "hard"},
        {"question": "Samolyot qanotining yuqori qismi qavariq — nima uchun?",
         "options": {"A": "Ishqalanish uchun", "B": "Ko'rinish uchun",
                     "C": "Qavariq qism havo tezroq oqadi — past bosim — ko'tarish kuchi (Bernulli)",
                     "D": "Og'irlik uchun"},
         "answer": "C", "difficulty": "hard"},
        {"question": "Chaqmoq va momaqaldiroq o'rtasidagi vaqtdan nima hisoblanadi?",
         "options": {"A": "Momaqaldiroq kuchi",
                     "B": "Chaqmoqdan masofa — tovush 340 m/s, vaqt × 340 = masofa",
                     "C": "Havo namligi", "D": "Yog'ingarchilik"},
         "answer": "B", "difficulty": "medium"},
        {"question": "Ko'rshapalak 0.1 s da aks-sado oldi (340 m/s). Devor qancha uzoq?",
         "options": {"A": "34 m", "B": "340 m", "C": "17 m", "D": "68 m"},
         "answer": "C", "difficulty": "hard"},
        {"question": "Bank kartasini magnitga yaqinlashtirmaslik sababi?",
         "options": {"A": "Karta rangi o'zgaradi", "B": "Plastik eriydi",
                     "C": "Magnit chiziq ma'lumotlari o'chib ketishi mumkin",
                     "D": "Karta ko'rinishi o'zgaradi"},
         "answer": "C", "difficulty": "easy"},
        {"question": "Amazon o'rmonlari dunyo iqlimiga katta ta'siri sababi?",
         "options": {"A": "Transpiratsiya orqali ko'p suv bug'ini atmosferaga chiqaradi va CO2 yutadi",
                     "B": "Ular issiq", "C": "Ular baland", "D": "Ular katta"},
         "answer": "A", "difficulty": "medium"},
        {"question": "Eutrofikatsiya nima?",
         "options": {"A": "Suvning muzlashi", "B": "Suvning qaynashi",
                     "C": "Suvga ortiqcha ozuqa tushishi — suv o'tlar ko'payadi, kislorod kamayadi, baliqlar nobud bo'ladi",
                     "D": "Suvning bug'lanishi"},
         "answer": "C", "difficulty": "hard"},
        {"question": "Karbon izi nima?",
         "options": {"A": "Inson oyoq izi", "B": "Ko'mir rangi",
                     "C": "Inson yoki tashkilot faoliyati natijasida chiqariladigan CO2 umumiy miqdori",
                     "D": "Tuproqdagi karbon"},
         "answer": "C", "difficulty": "medium"},
        {"question": "Barqaror rivojlanish nima?",
         "options": {"A": "Hozirgi va kelajak avlod ehtiyojlarini muvozanatli qondirish",
                     "B": "Faqat iqtisodiy", "C": "Faqat texnologik", "D": "Faqat sanoat"},
         "answer": "A", "difficulty": "easy"},
        {"question": "Galiley Yupiter yo'ldoshlarini kashf etishning ahamiyati nimada?",
         "options": {"A": "Hech qanday ahamiyat", "B": "Faqat ilmiy qiziqarli",
                     "C": "Geliotsentrik modelni tasdiqlashga yordam berdi",
                     "D": "Faqat astronomiya uchun"},
         "answer": "C", "difficulty": "medium"},
    ],
    "6-sinf": [
        {"question": "Muvozanatlashgan ratsion nima?",
         "options": {"A": "Faqat go'sht va yog'li mahsulotlar",
                     "B": "Organizm uchun zarur oziq moddalarni saqlaydigan oziq-ovqat mahsulotlari va suv",
                     "C": "Faqat meva-sabzavotlar", "D": "Ko'p miqdorda shakar va shirinliklar"},
         "answer": "B", "difficulty": "easy"},
        {"question": "Qizilo'ngach qanday organ?",
         "options": {"A": "Ovqat hazm qiluvchi organ",
                     "B": "Og'iz bo'shlig'ini oshqozon bilan bog'lovchi naysimon organ",
                     "C": "Nafas organi", "D": "Qon aylanish organi"},
         "answer": "B", "difficulty": "easy"},
        {"question": "Ingichka ichakda qanday jarayon sodir bo'ladi?",
         "options": {"A": "Ovqat faqat mexanik maydalanadi",
                     "B": "Hazm qilish yakunlanadi va parchalangan oziq moddalar qonga so'riladi",
                     "C": "Suv va minerallar so'riladi", "D": "Najas hosil bo'ladi"},
         "answer": "B", "difficulty": "easy"},
        {"question": "Nafas sistemasida gazlar almashinuvi qayerda sodir bo'ladi?",
         "options": {"A": "Traxeyada", "B": "Bronxlarda", "C": "Alveolalarda", "D": "Burun bo'shlig'ida"},
         "answer": "C", "difficulty": "easy"},
        {"question": "Yurak qon aylanish sistemasida qanday vazifani bajaradi?",
         "options": {"A": "Qonni tozalaydi", "B": "Kislorod ishlab chiqaradi",
                     "C": "Nasos singari qonni tana bo'ylab haydaydi",
                     "D": "Karbonat angidrid ishlab chiqaradi"},
         "answer": "C", "difficulty": "easy"},
        {"question": "Arteriya qanday qontomir?",
         "options": {"A": "Qonni yurakka olib keluvchi", "B": "Qonni yurakdan olib ketuvchi",
                     "C": "Arteriya va venani bog'lovchi", "D": "Faqat o'pkalarda bo'luvchi"},
         "answer": "B", "difficulty": "easy"},
        {"question": "Nima uchun yog'li mahsulotlarni ko'p iste'mol qilish zararli?",
         "options": {"A": "Vitaminlar kamayadi", "B": "Yurak kasalliklari rivojlanadi",
                     "C": "Suyaklar zaiflashadi", "D": "Ko'rish pasayadi"},
         "answer": "B", "difficulty": "medium"},
        {"question": "Yo'g'on ichakda asosan nima so'riladi?",
         "options": {"A": "Oqsillar", "B": "Uglevrodlar", "C": "Suv va ba'zi minerallar", "D": "Yog'lar"},
         "answer": "C", "difficulty": "medium"},
        {"question": "Kapillyar nima va uning vazifasi nima?",
         "options": {"A": "Qonni yurakdan olib ketuvchi yirik tomir",
                     "B": "Arteriya va venalarni bog'lovchi ingichka tomir; modda almashinuvi bu yerda bo'ladi",
                     "C": "O'pkadagi havo yo'li", "D": "Yurak muskuli"},
         "answer": "B", "difficulty": "medium"},
        {"question": "Teri organizmni qanday himoya qiladi?",
         "options": {"A": "Ferment ishlab chiqaradi",
                     "B": "Fizik, kimyoviy va mexanik ta'sirlardan himoya qiluvchi to'siq vazifasini bajaradi",
                     "C": "Kislorod yutadi", "D": "Karbonat angidrid chiqaradi"},
         "answer": "B", "difficulty": "medium"},
        {"question": "Qaysi kasalliklar viruslar tomonidan qo'zg'atiladi?",
         "options": {"A": "Vabo, ichterlama", "B": "Zamburug' kasalliklari",
                     "C": "COVID-19, gripp, suvchechak", "D": "Bezgak"},
         "answer": "C", "difficulty": "medium"},
        {"question": "Epidemiya nima?",
         "options": {"A": "Bir kishining kasallanishi", "B": "Kasallik aholi orasida tez tarqalishi",
                     "C": "Yangi kasallik kashf etilishi", "D": "Dori topilishi"},
         "answer": "B", "difficulty": "medium"},
        {"question": "Quyosh oziq zanjirida qanday rol o'ynaydi?",
         "options": {"A": "Konsument", "B": "Asosiy energiya manbayi", "C": "Parazit", "D": "Tashuvchi"},
         "answer": "B", "difficulty": "medium"},
        {"question": "Oziq zanjiridagi strelkalar nima yo'nalishini ifodalaydi?",
         "options": {"A": "Organizmlarning harakatlanish yo'nalishini", "B": "Energiya oqimi yo'nalishini",
                     "C": "Suvning oqish yo'nalishini", "D": "Quyosh nurining yo'nalishini"},
         "answer": "B", "difficulty": "medium"},
        {"question": "Kumush necha darajada eriydi?",
         "options": {"A": "0 °C", "B": "100 °C", "C": "962 °C", "D": "1665 °C"},
         "answer": "C", "difficulty": "medium"},
        {"question": "Qon karbonat angidridni qaysi yo'nalishda tashiydi?",
         "options": {"A": "O'pkalardan tananing barcha organlariga",
                     "B": "Tananing barcha organlaridan o'pkalarga",
                     "C": "Yurakdan oshqozonga", "D": "Ingichka ichakdan o'pkalarga"},
         "answer": "B", "difficulty": "hard"},
        {"question": "Agar oziq zanjiridagi birlamchi konsumentlar qirilib ketsa, nima bo'ladi?",
         "options": {"A": "Produtsent ko'payadi, ikkilamchi konsumentlar ozayadi",
                     "B": "Hamma o'zgarishsiz qoladi",
                     "C": "Faqat produtsent ta'sirlanadi", "D": "Faqat yirtqichlar ta'sirlanadi"},
         "answer": "A", "difficulty": "hard"},
        {"question": "Massasi 2 kg jismning Yerdagi og'irligi (taxminan)?",
         "options": {"A": "2 N", "B": "19.6 N", "C": "20 kg", "D": "9.8 N"},
         "answer": "B", "difficulty": "hard"},
    ],
}

PAID_TESTS = {
    "1-sinf": [
        {"question": "💎 Sehrli kvadrat: markaziy qator bo'sh katagi?\n2 | ? | 6\n7 | 5 | 3\n6 | 9 | ?",
         "options": {"A": "4", "B": "2", "C": "8", "D": "1"},
         "answer": "A", "difficulty": "hard"},
        {"question": "💎 1 dan 20 gacha juft sonlarning yig'indisi?",
         "options": {"A": "100", "B": "110", "C": "90", "D": "120"},
         "answer": "B", "difficulty": "hard"},
        {"question": "💎 1, 2, 3 raqamlaridan nechta xar xil uch xonali son tuzish mumkin?",
         "options": {"A": "3", "B": "9", "C": "6", "D": "12"},
         "answer": "C", "difficulty": "hard"},
    ],
    "2-sinf": [
        {"question": "💎 99 × 99 = ?",
         "options": {"A": "9801", "B": "9900", "C": "9999", "D": "9800"},
         "answer": "A", "difficulty": "hard"},
        {"question": "💎 1+2+3+...+100 = ?",
         "options": {"A": "4950", "B": "5000", "C": "5050", "D": "5100"},
         "answer": "C", "difficulty": "hard"},
        {"question": "💎 Qaysi son o'zidan kichik barcha bo'luvchilar yig'indisiga teng?",
         "options": {"A": "6", "B": "8", "C": "4", "D": "9"},
         "answer": "A", "difficulty": "hard"},
    ],
    "3-sinf": [
        {"question": "💎 15 ta ot va g'oz, hammasi 44 ta oyoq. G'oz nechta?",
         "options": {"A": "5", "B": "7", "C": "10", "D": "8"},
         "answer": "B", "difficulty": "hard"},
        {"question": "💎 Har kuni 2 barobar ko'paysa, 1-kuni 1 ta bo'lsa, 10-kuni nechta bo'ladi?",
         "options": {"A": "512", "B": "256", "C": "1024", "D": "128"},
         "answer": "A", "difficulty": "hard"},
        {"question": "💎 6 ga ham, 8 ga ham bo'linadigan eng kichik 3 xonali son?",
         "options": {"A": "112", "B": "120", "C": "108", "D": "144"},
         "answer": "B", "difficulty": "hard"},
    ],
    "4-sinf": [
        {"question": "💎 8×8 to'rdagi barcha kvadratlar soni (faqat 1×1 emas)?",
         "options": {"A": "64", "B": "200", "C": "204", "D": "168"},
         "answer": "C", "difficulty": "hard"},
        {"question": "💎 5! = ?",
         "options": {"A": "100", "B": "120", "C": "60", "D": "24"},
         "answer": "B", "difficulty": "hard"},
        {"question": "💎 Fibonacci: 1,1,2,3,5,8,13... 10-son nechta?",
         "options": {"A": "55", "B": "34", "C": "21", "D": "89"},
         "answer": "A", "difficulty": "hard"},
    ],
    "5-sinf": [
        {"question": "💎 Ishqalanish kuchi F=μN. μ=0.3, N=50N bo'lsa F=?",
         "options": {"A": "15 N", "B": "50 N", "C": "30 N", "D": "0.3 N"},
         "answer": "A", "difficulty": "hard"},
        {"question": "💎 Atom yadrosida nima bor?",
         "options": {"A": "Elektronlar", "B": "Proton va neytronlar", "C": "Faqat protonlar", "D": "Kvarklar"},
         "answer": "B", "difficulty": "hard"},
        {"question": "💎 pH=7 — bu qanday muhit?",
         "options": {"A": "Kislotali", "B": "Ishqoriy", "C": "Neytral", "D": "Zaharli"},
         "answer": "C", "difficulty": "hard"},
    ],
    "6-sinf": [
        {"question": "💎 DNK replikatsiyasi qayerda sodir bo'ladi?",
         "options": {"A": "Sitoplazma", "B": "Yadro", "C": "Ribosoma", "D": "Mitoxondriya"},
         "answer": "B", "difficulty": "hard"},
        {"question": "💎 Mendel qonuniga ko'ra Aa × Aa da nechta dominant fenotip?",
         "options": {"A": "25%", "B": "50%", "C": "75%", "D": "100%"},
         "answer": "C", "difficulty": "hard"},
        {"question": "💎 Oziq zanjirida energiyaning necha foizi keyingi sathga o'tadi?",
         "options": {"A": "50%", "B": "90%", "C": "10%", "D": "1%"},
         "answer": "C", "difficulty": "hard"},
    ],
}

# ═══════════════════════════════════════════════
# 3. HOLATLAR
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
# 4. GOOGLE SHEETS (CACHE)
# ═══════════════════════════════════════════════
USERS_CACHE = {}

def load_users_to_cache():
    global USERS_CACHE
    USERS_CACHE.clear()
    try:
        ws = get_sheet()
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

def add_user(telegram_id, full_name, school, grade, phone, referred_by=0):
    for user in USERS_CACHE.values():
        if user["telegram_id"] == telegram_id:
            return None
    try:
        ws = get_sheet()
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

# Buyurtmalar
ORDER_CACHE = {}
ORDER_COUNTER = [1000]

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
        rows = ws.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if row[0] and int(row[0]) == order_id:
                ws.update_cell(i, 6, "confirmed")
                break
    except Exception as e:
        print(f"confirm_order xato: {e}")
    return order

# INLIM ro'yxat cache
INLIM_REGISTRATIONS = {}
INLIM_REG_COUNTER   = [2000]

def save_inlim_registration(telegram_id, full_name, school, phone,
                             grade_group, test_date, test_format, payment_type):
    import datetime
    INLIM_REG_COUNTER[0] += 1
    reg_id = INLIM_REG_COUNTER[0]
    rec = {
        "reg_id":       reg_id,
        "telegram_id":  telegram_id,
        "full_name":    full_name,
        "school":       school,
        "phone":        phone,
        "grade_group":  grade_group,
        "test_date":    test_date,
        "test_format":  test_format,
        "payment_type": payment_type,
        "status":       "pending",
        "created_at":   datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
    }
    INLIM_REGISTRATIONS[reg_id] = rec
    try:
        ws = get_inlim_sheet()
        ws.append_row([
            reg_id, telegram_id, full_name, school, phone,
            grade_group, test_date, test_format, payment_type,
            "pending", rec["created_at"]
        ])
    except Exception as e:
        print(f"save_inlim_registration xato: {e}")
    return reg_id

load_users_to_cache()

bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher()

# ═══════════════════════════════════════════════
# 5. YORDAMCHI FUNKSIYALAR
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
# 6. SAVOL YUBORISH
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
# 7. TEST TUGASH
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
# 8. TIMEOUT
# ═══════════════════════════════════════════════
async def timeout_watcher(chat_id, state):
    await asyncio.sleep(TEST_DURATION_SECONDS)
    current_state = await state.get_state()
    if current_state == TestProcess.answering.state:
        await bot.send_message(chat_id, "⏰ Vaqt tugadi! Test yakunlanmoqda...")
        await finish_test(chat_id, state)

# ═══════════════════════════════════════════════
# 9. /START
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
# 10. RO'YXATDAN O'TISH
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
# 11. INLIM BO'LIMI
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
# 12. INLIM RO'YXATDAN O'TISH
# ═══════════════════════════════════════════════

@dp.callback_query(F.data == "inlim_register")
async def inlim_register_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📝 Repititsion testga ro'yxatdan o'tish\n\n"
        "1️⃣ @IlmNuri_Markazi kanaliga a'zo bo'ling\n"
        "2️⃣ Bu xabarni 3 ta guruhga yuboring\n\n"
        "Tayyor bo'lgach, '✅ A'zo bo'ldim' tugmasini bosing 👇",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📣 Kanalga o'tish", url=CHANNEL_LINK)],
            [InlineKeyboardButton(text="✅ A'zo bo'ldim", callback_data="inlim_check_sub")],
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
        "✅ Kanalga a'zo bo'ldingiz!\n\n"
        "2️⃣ Bu xabarni 3 ta guruhga yuboring:\n\n"
        "📢 «ILM NURI Repititsion test boshlanmoqda! @IlmNuri_Markazi»\n\n"
        "Yuborgach, '✅ Yubordim' tugmasini bosing 👇",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Yubordim, davom etish",
                                  callback_data="inlim_check_share")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="inlim_register")],
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "inlim_check_share")
async def inlim_check_share(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "✅ Rahmat! Ro'yxatdan o'tishni davom ettiramiz.\n\n"
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
            [InlineKeyboardButton(
                text="🔢 1-2 sinf — Matematika",
                callback_data="inlim_grade_12"
            )],
            [InlineKeyboardButton(
                text="🔢 3-4 sinf — Aniq fan (Matematika)",
                callback_data="inlim_grade_34"
            )],
            [InlineKeyboardButton(
                text="🌿 5-6 sinf — Tabiiy fan",
                callback_data="inlim_grade_56"
            )],
        ])
    )
    await state.set_state(InlimRegistration.grade_group)

@dp.callback_query(F.data.startswith("inlim_grade_"), StateFilter(InlimRegistration.grade_group))
async def inlim_process_grade(callback: types.CallbackQuery, state: FSMContext):
    grade_map = {           # ← 4 ta bo'sh joy (to'g'ri)
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
# 13. ASOSIY MENYU TUGMALARI
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
            [InlineKeyboardButton(text="🚀 Boshlash", callback_data=f"start_{user['id']}")]
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
            [InlineKeyboardButton(text="🚀 Boshlash", callback_data=f"start_{user['id']}")]
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
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"paidgrade_{g}_{user['id']}")])

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
    p_id  = int(parts[2])
    user  = get_user_by_id(p_id)
    if not user:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return

    variants = PAID_TESTS.get(grade, [])
    VARIANT_SIZE = 3
    variant_count = (len(variants) + VARIANT_SIZE - 1) // VARIANT_SIZE

    buttons = []
    for i in range(variant_count):
        bought = has_paid_test(p_id, grade, i)
        if bought:
            buttons.append([InlineKeyboardButton(
                text=f"▶️ Variant {i+1} — Boshlash",
                callback_data=f"start_paid_{p_id}_{grade}_{i}"
            )])
        else:
            buttons.append([InlineKeyboardButton(
                text=f"🔒 Variant {i+1} — {PAYMENT_AMOUNT:,} so'm / {VAB_FOR_TEST_PURCHASE} VAB",
                callback_data=f"buy_variant_{p_id}_{grade}_{i}"
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
    p_id          = int(parts[2])
    grade         = parts[3]
    variant_index = int(parts[4])
    user = get_user_by_id(p_id)
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
                callback_data=f"pay_money_{p_id}_{grade}_{variant_index}"
            )],
            [InlineKeyboardButton(
                text=f"💰 VAB sarflash ({VAB_FOR_TEST_PURCHASE} VAB)",
                callback_data=f"pay_vab_{p_id}_{grade}_{variant_index}"
            )],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"paidgrade_{grade}_{p_id}")],
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
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"paidgrade_{g}_{user['id']}")])
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
# 14. TO'LOV CALLBACK-LAR
# ═══════════════════════════════════════════════

@dp.callback_query(F.data.startswith("pay_money_"))
async def pay_with_money(callback: types.CallbackQuery, state: FSMContext):
    parts         = callback.data.split("_")
    p_id          = int(parts[2])
    grade         = parts[3]
    variant_index = int(parts[4])
    user = get_user_by_id(p_id)
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
                                  callback_data=f"send_check_{p_id}_{grade}_{variant_index}")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("send_check_"))
async def send_check_prompt(callback: types.CallbackQuery, state: FSMContext):
    parts         = callback.data.split("_")
    p_id          = int(parts[2])
    grade         = parts[3]
    variant_index = int(parts[4])
    user = get_user_by_id(p_id)
    if not user:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return

    await callback.message.answer(
        f"📤 To'lov cheki rasmini shu yerga yuboring:\n"
        f"📚 {grade} — Variant {variant_index+1}\n"
        f"💰 {PAYMENT_AMOUNT:,} so'm\n\nBekor: /cancel"
    )
    await state.update_data(paying_user_id=p_id, paying_grade=grade, paying_variant=variant_index)
    await state.set_state(PaymentState.waiting_check)
    await callback.answer()

@dp.message(PaymentState.waiting_check)
async def receive_payment_check(message: types.Message, state: FSMContext):
    if message.text and message.text.strip() == "/cancel":
        await message.answer("Bekor qilindi.", reply_markup=main_menu_keyboard())
        await state.clear()
        return

    if not message.photo:
        await message.answer("⚠️ Iltimos, to'lov cheki rasmini yuboring!")
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
        f"Admin tekshiradi va tez orada aktivlanadi.",
        reply_markup=main_menu_keyboard()
    )
    await state.clear()

# ─── ADMIN TO'LOV TASDIQLASH (callback ichida admin tekshirish) ───
@dp.callback_query(F.data.startswith("admin_confirm_"))
async def admin_confirm_inline(callback: types.CallbackQuery):
    # Admin tekshirish
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
            f"Chek aniq ko'rinmagan yoki noto'g'ri summa.\n"
            f"Qayta to'lov uchun admin bilan bog'laning."
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
    p_id          = int(parts[2])
    grade         = parts[3]
    variant_index = int(parts[4])
    user = get_user_by_id(p_id)
    if not user:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return

    if user["vab"] < VAB_FOR_TEST_PURCHASE:
        await callback.answer(
            f"❌ VAB yetarli emas!\nKerak: {VAB_FOR_TEST_PURCHASE} VAB\nSizda: {user['vab']} VAB",
            show_alert=True
        )
        return

    if has_paid_test(p_id, grade, variant_index):
        await callback.answer("Bu variant allaqachon aktiv!", show_alert=True)
        return

    success = spend_vab(p_id, VAB_FOR_TEST_PURCHASE)
    if success:
        grant_paid_test(p_id, grade, variant_index)
        await callback.message.answer(
            f"✅ {grade} — Variant {variant_index+1} aktivlashtirildi!\n"
            f"💰 -{VAB_FOR_TEST_PURCHASE} VAB sarflandi\n\n"
            f"💎 Testni hozir ishlashingiz mumkin!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💎 Boshlash",
                                      callback_data=f"start_paid_{p_id}_{grade}_{variant_index}")]
            ])
        )
    else:
        await callback.answer("Xato yuz berdi!", show_alert=True)
    await callback.answer()

# ═══════════════════════════════════════════════
# 15. TEST BOSHLASH CALLBACK-LAR
# ═══════════════════════════════════════════════

@dp.callback_query(F.data.startswith("start_") & ~F.data.startswith("start_paid_"))
async def start_free_test(callback: types.CallbackQuery, state: FSMContext):
    p_id = int(callback.data.split("_")[1])
    user = get_user_by_id(p_id)
    if not user:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return

    if not await is_subscribed(callback.from_user.id):
        await callback.message.answer(
            "📢 Testni boshlash uchun avval kanalimizga obuna bo'ling!\n\n",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📣 Kanalga o'tish", url=CHANNEL_LINK)],
                [InlineKeyboardButton(text="✅ Obuna bo'ldim", callback_data=f"start_{p_id}")]
            ])
        )
        await callback.answer()
        return

    grade  = user["grade"]
    q_list = TESTS.get(grade, [])
    if not q_list:
        await callback.message.answer(f"{grade} uchun savollar yo'q.")
        await callback.answer()
        return

    await _start_test_session(callback, state, user, q_list, "free")

@dp.callback_query(F.data.startswith("start_paid_"))
async def start_paid_test(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    p_id          = int(parts[2])
    grade         = parts[3]
    variant_index = int(parts[4])

    user = get_user_by_id(p_id)
    if not user:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return

    if not has_paid_test(p_id, grade, variant_index):
        await callback.answer("Pullik test sotib olinmagan!", show_alert=True)
        return

    all_variants = PAID_TESTS.get(grade, [])
    if not all_variants:
        await callback.message.answer(f"{grade} pullik savollar yo'q.")
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
        f"🚀 {grade} — {tag} test boshlanmoqda!\n"
        f"📝 Savollar soni: {len(q_list)}\n"
        f"⏱ Vaqt: 45 daqiqa\n\nOmad! 🍀   @IlmNuri_Markazi"
    )
    await callback.answer()
    asyncio.create_task(timeout_watcher(callback.from_user.id, state))
    await send_question(callback.from_user.id, state)

@dp.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: types.CallbackQuery):
    await callback.message.answer("Asosiy menyu:", reply_markup=main_menu_keyboard())
    await callback.answer()

# ═══════════════════════════════════════════════
# 16. JAVOB TEKSHIRISH
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
# 17. ADMIN BUYRUQLARI
# ═══════════════════════════════════════════════

@dp.message(Command("refresh"))
async def refresh_cache(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    old = get_users_count()
    load_users_to_cache()
    new = get_users_count()
    await message.answer(f"✅ Baza yangilandi!\nOldin: {old} → Hozir: {new} ta")

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "🛠 Admin panel:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Xabar yuborish",       callback_data="send_ad")],
            [InlineKeyboardButton(text="📊 Statistika",            callback_data="admin_stats")],
            [InlineKeyboardButton(text="💳 Kutilayotgan to'lovlar", callback_data="pending_orders")],
            [InlineKeyboardButton(text="🏆 INLIM sozlamalari",    callback_data="inlim_admin")],
        ])
    )

# ── INLIM ADMIN PANEL ─────────────────────────
@dp.callback_query(F.data == "inlim_admin")
async def inlim_admin_panel(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Faqat admin!", show_alert=True)
        return

    prize    = INLIM_SETTINGS.get("prize_fund", 0)
    dates    = INLIM_SETTINGS.get("test_dates", [])
    sponsors = INLIM_SETTINGS.get("sponsors", [])
    admin_u  = INLIM_SETTINGS.get("admin_username", "@admin")

    await callback.message.edit_text(
        f"🏆 INLIM Admin Panel\n\n"
        f"💰 Sovrin: {prize:,} so'm\n"
        f"📅 Test sanalari: {len(dates)} ta\n"
        f"🤝 Homiylar: {len(sponsors)} ta\n"
        f"👤 Admin: {admin_u}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💰 Sovrin miqdorini o'rnatish",
                                  callback_data="inlim_set_prize")],
            [InlineKeyboardButton(text="📅 Test sanasi qo'shish",
                                  callback_data="inlim_add_date")],
            [InlineKeyboardButton(text="📅 Test sanalarini ko'rish",
                                  callback_data="inlim_view_dates")],
            [InlineKeyboardButton(text="🤝 Homiy qo'shish",
                                  callback_data="inlim_add_sponsor")],
            [InlineKeyboardButton(text="🤝 Homiylarni ko'rish",
                                  callback_data="inlim_view_sponsors")],
            [InlineKeyboardButton(text="👤 Admin username o'rnatish",
                                  callback_data="inlim_set_admin_user")],
            [InlineKeyboardButton(text="📋 INLIM ro'yxatlar",
                                  callback_data="inlim_view_regs")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_back")],
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_back")
async def admin_back(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Faqat admin!", show_alert=True)
        return
    await callback.message.edit_text(
        "🛠 Admin panel:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Xabar yuborish",       callback_data="send_ad")],
            [InlineKeyboardButton(text="📊 Statistika",            callback_data="admin_stats")],
            [InlineKeyboardButton(text="💳 Kutilayotgan to'lovlar", callback_data="pending_orders")],
            [InlineKeyboardButton(text="🏆 INLIM sozlamalari",    callback_data="inlim_admin")],
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "inlim_set_prize")
async def inlim_set_prize_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Faqat admin!", show_alert=True)
        return
    await callback.message.answer(
        f"💰 Joriy sovrin: {INLIM_SETTINGS['prize_fund']:,} so'm\n\n"
        f"Yangi miqdorni kiriting (faqat raqam):\nMasalan: 500000\n\n/cancel — bekor"
    )
    await state.set_state(AdminInlimState.set_prize)
    await callback.answer()

@dp.message(AdminInlimState.set_prize)
async def inlim_set_prize_process(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.text and message.text.strip() == "/cancel":
        await message.answer("Bekor qilindi.")
        await state.clear()
        return
    try:
        amount = int(message.text.strip().replace(" ", "").replace(",", ""))
        INLIM_SETTINGS["prize_fund"] = amount
        await message.answer(f"✅ Sovrin jamg'armasi: {amount:,} so'm!")
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting.")
    await state.clear()

@dp.callback_query(F.data == "inlim_add_date")
async def inlim_add_date_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Faqat admin!", show_alert=True)
        return
    await callback.message.answer(
        "📅 Test sanasini qo'shish\n\n"
        "Format: Sana | Sinf | Fan\n\n"
        "Misol:\n2025-06-15 | 3-4 sinf | Matematika\n\n/cancel — bekor"
    )
    await state.set_state(AdminInlimState.add_date)
    await callback.answer()

@dp.message(AdminInlimState.add_date)
async def inlim_add_date_process(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.text and message.text.strip() == "/cancel":
        await message.answer("Bekor qilindi.")
        await state.clear()
        return
    try:
        parts = [p.strip() for p in message.text.split("|")]
        if len(parts) < 3:
            await message.answer("❌ Format: 2025-06-15 | 3-4 sinf | Matematika")
            return
        entry = {"date": parts[0], "grade": parts[1], "subject": parts[2]}
        INLIM_SETTINGS["test_dates"].append(entry)
        await message.answer(
            f"✅ Qo'shildi!\n📅 {entry['date']} | {entry['grade']} | {entry['subject']}"
        )
    except Exception as e:
        await message.answer(f"❌ Xato: {e}")
    await state.clear()

@dp.callback_query(F.data == "inlim_view_dates")
async def inlim_view_dates(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Faqat admin!", show_alert=True)
        return
    dates = INLIM_SETTINGS.get("test_dates", [])
    if not dates:
        await callback.answer("Hozircha test sanalari yo'q!", show_alert=True)
        return
    text = "📅 Test sanalari:\n\n"
    buttons = []
    for i, d in enumerate(dates):
        text += f"{i+1}. {d['date']} | {d.get('grade','')} | {d.get('subject','')}\n"
        buttons.append([InlineKeyboardButton(
            text=f"🗑 {i+1}-ni o'chirish",
            callback_data=f"inlim_del_date_{i}"
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="inlim_admin")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("inlim_del_date_"))
async def inlim_delete_date(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Faqat admin!", show_alert=True)
        return
    idx = int(callback.data.split("_")[3])
    dates = INLIM_SETTINGS.get("test_dates", [])
    if idx < len(dates):
        removed = dates.pop(idx)
        await callback.answer(f"✅ {removed['date']} o'chirildi!", show_alert=True)
    else:
        await callback.answer("Topilmadi!", show_alert=True)

@dp.callback_query(F.data == "inlim_add_sponsor")
async def inlim_add_sponsor_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Faqat admin!", show_alert=True)
        return
    await callback.message.answer(
        "🤝 Homiy qo'shish\n\n"
        "Format: Ism | Telegram | Instagram\n\n"
        "Misol: ABC Kompaniya | @abc_company | @abc_instagram\n"
        "Instagram yo'q: ABC | @abc | -\n\n/cancel — bekor"
    )
    await state.set_state(AdminInlimState.add_sponsor)
    await callback.answer()

@dp.message(AdminInlimState.add_sponsor)
async def inlim_add_sponsor_process(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.text and message.text.strip() == "/cancel":
        await message.answer("Bekor qilindi.")
        await state.clear()
        return
    try:
        parts = [p.strip() for p in message.text.split("|")]
        if len(parts) < 2:
            await message.answer("❌ Format: Ism | @telegram | @instagram")
            return
        entry = {
            "name":      parts[0],
            "telegram":  parts[1] if len(parts) > 1 else "",
            "instagram": parts[2] if len(parts) > 2 and parts[2] != "-" else "",
        }
        INLIM_SETTINGS["sponsors"].append(entry)
        await message.answer(f"✅ Homiy qo'shildi: {entry['name']}")
    except Exception as e:
        await message.answer(f"❌ Xato: {e}")
    await state.clear()

@dp.callback_query(F.data == "inlim_view_sponsors")
async def inlim_view_sponsors(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Faqat admin!", show_alert=True)
        return
    sponsors = INLIM_SETTINGS.get("sponsors", [])
    if not sponsors:
        await callback.answer("Hozircha homiylar yo'q!", show_alert=True)
        return
    text = "🤝 Homiylar:\n\n"
    buttons = []
    for i, s in enumerate(sponsors):
        text += f"{i+1}. {s.get('name','')} | {s.get('telegram','')} | {s.get('instagram','')}\n"
        buttons.append([InlineKeyboardButton(
            text=f"🗑 {i+1}-ni o'chirish",
            callback_data=f"inlim_del_sponsor_{i}"
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="inlim_admin")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("inlim_del_sponsor_"))
async def inlim_delete_sponsor(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Faqat admin!", show_alert=True)
        return
    idx = int(callback.data.split("_")[3])
    sponsors = INLIM_SETTINGS.get("sponsors", [])
    if idx < len(sponsors):
        removed = sponsors.pop(idx)
        await callback.answer(f"✅ {removed['name']} o'chirildi!", show_alert=True)
    else:
        await callback.answer("Topilmadi!", show_alert=True)

@dp.callback_query(F.data == "inlim_set_admin_user")
async def inlim_set_admin_user_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Faqat admin!", show_alert=True)
        return
    await callback.message.answer(
        f"👤 Joriy admin: {INLIM_SETTINGS.get('admin_username', '@admin')}\n\n"
        f"Yangi admin usernameni kiriting:\nMasalan: @admin_ilmnuri\n\n/cancel — bekor"
    )
    await state.set_state(AdminInlimState.set_admin_user)
    await callback.answer()

@dp.message(AdminInlimState.set_admin_user)
async def inlim_set_admin_user_process(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.text and message.text.strip() == "/cancel":
        await message.answer("Bekor qilindi.")
        await state.clear()
        return
    username = message.text.strip()
    if not username.startswith("@"):
        username = "@" + username
    INLIM_SETTINGS["admin_username"] = username
    await message.answer(f"✅ Admin username: {username}")
    await state.clear()

@dp.callback_query(F.data == "inlim_view_regs")
async def inlim_view_regs(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Faqat admin!", show_alert=True)
        return
    regs = list(INLIM_REGISTRATIONS.values())
    if not regs:
        await callback.answer("Hozircha ro'yxat yo'q!", show_alert=True)
        return
    text = f"📋 INLIM Ro'yxatlar: {len(regs)} ta\n\n"
    for r in regs[-10:]:
        text += (f"#{r['reg_id']} {r['full_name']} | {r['grade_group']} | "
                 f"{r['test_format']} | {r['payment_type']}\n")
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="inlim_admin")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Faqat admin!", show_alert=True)
        return
    total  = get_users_count()
    orders = len([o for o in ORDER_CACHE.values() if o["status"] == "pending"])
    regs   = len(INLIM_REGISTRATIONS)
    await callback.answer(
        f"👥 Foydalanuvchilar: {total} ta\n"
        f"💳 Kutilayotgan to'lovlar: {orders} ta\n"
        f"📝 INLIM ro'yxatlar: {regs} ta",
        show_alert=True
    )

@dp.callback_query(F.data == "pending_orders")
async def pending_orders(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Faqat admin!", show_alert=True)
        return
    orders = [o for o in ORDER_CACHE.values() if o["status"] == "pending"]
    if not orders:
        await callback.answer("Kutilayotgan to'lov yo'q!", show_alert=True)
        return
    for o in orders:
        await callback.message.answer(
            f"📋 #{o['order_id']}\n"
            f"👤 {o['full_name']}\n"
            f"📚 {o['grade']}\n\n"
            f"Tasdiqlash tugmasini to'lov xabarida bosing!"
        )
    await callback.answer()

@dp.callback_query(F.data == "send_ad")
async def start_ad(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Faqat admin!", show_alert=True)
        return
    await callback.message.answer("📝 Xabar matnini yoki rasm/video yuboring.\n/cancel — bekor")
    await state.set_state(AdminState.waiting_for_ad_content)
    await callback.answer()

@dp.message(AdminState.waiting_for_ad_content)
async def process_ad_content(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.text and message.text.strip() == "/cancel":
        await message.answer("Bekor qilindi.")
        await state.clear()
        return
    users = get_all_telegram_ids()
    count = 0
    await message.answer(f"🚀 {len(users)} ta foydalanuvchiga yuborilmoqda...")
    for uid in users:
        try:
            await message.copy_to(chat_id=uid)
            count += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    await message.answer(f"✅ {count} ta foydalanuvchiga yetkazildi!")
    await state.clear()

@dp.message(Command("confirm"))
async def confirm_payment(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Foydalanish: /confirm <order_id>")
        return
    try:
        order_id = int(args[1])
    except ValueError:
        await message.answer("Noto'g'ri ID!")
        return

    order = confirm_order(order_id)
    if not order:
        await message.answer(f"#{order_id} buyurtma topilmadi!")
        return

    user = get_user_by_telegram_id(order["telegram_id"])
    if user:
        grant_paid_test(user["id"], order["grade"])
        add_vab(user["id"], 50)
        try:
            await bot.send_message(
                order["telegram_id"],
                f"🎉 To'lovingiz tasdiqlandi!\n\n"
                f"💎 {order['grade']} pullik test aktivlashtirildi!\n"
                f"💰 Bonus: +50 VAB",
                reply_markup=main_menu_keyboard()
            )
        except Exception:
            pass
    await message.answer(f"✅ #{order_id} tasdiqlandi!")

@dp.message(Command("reject"))
async def reject_payment(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Foydalanish: /reject <order_id>")
        return
    try:
        order_id = int(args[1])
    except ValueError:
        await message.answer("Noto'g'ri ID!")
        return

    order = ORDER_CACHE.get(order_id)
    if not order:
        await message.answer(f"#{order_id} topilmadi!")
        return

    order["status"] = "rejected"
    try:
        await bot.send_message(
            order["telegram_id"],
            f"❌ #{order_id} to'lovingiz rad etildi.\n"
            f"Qayta to'lov uchun admin bilan bog'laning."
        )
    except Exception:
        pass
    await message.answer(f"❌ #{order_id} rad etildi.")

@dp.message(Command("addvab"))
async def add_vab_cmd(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 3:
        await message.answer("Foydalanish: /addvab <telegram_id> <amount>")
        return
    try:
        tg_id  = int(args[1])
        amount = int(args[2])
    except ValueError:
        await message.answer("Noto'g'ri format!")
        return
    user = get_user_by_telegram_id(tg_id)
    if not user:
        await message.answer("Foydalanuvchi topilmadi!")
        return
    new_vab = add_vab(user["id"], amount)
    await message.answer(f"✅ {user['full_name']}ga +{amount} VAB. Jami: {new_vab} VAB")
    try:
        await bot.send_message(tg_id, f"🎁 Admindan: +{amount} VAB!\n💼 Jami: {new_vab} VAB")
    except Exception:
        pass

# ═══════════════════════════════════════════════
# 18. MAIN — WEBHOOK (Render uchun)
# ═══════════════════════════════════════════════
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# Render ilovangizning URL manzili — environment variable orqali o'rnating
WEBHOOK_HOST = os.environ.get("RENDER_EXTERNAL_URL", "https://your-app-name.onrender.com")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL  = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
PORT         = int(os.environ.get("PORT", 8080))

async def keep_alive_ping():
    """Render'da bot o'chmasligini ta'minlaydi — har 14 daqiqada o'z-o'ziga ping"""
    await asyncio.sleep(60)  # bot to'liq ishga tushguncha kut
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                url = os.environ.get("RENDER_EXTERNAL_URL", "https://your-app.onrender.com")
                async with session.get(f"{url}/health", timeout=aiohttp.ClientTimeout(total=10)):
                    pass
        except Exception:
            pass
        await asyncio.sleep(14 * 60)  # 14 daqiqa
async def on_startup(app: web.Application) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    await bot.set_webhook(url=WEBHOOK_URL, drop_pending_updates=True)
    logging.info("✅ Webhook o'rnatildi!")
    asyncio.create_task(keep_alive_ping())


async def on_shutdown(app: web.Application) -> None:
    pass  # hech narsa qilmasin


async def health_check(request):
    """Render health check uchun"""
    return web.Response(text="OK", status=200)


def create_app():
    app = web.Application()
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    # Health check endpoint
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)

    # Webhook handler
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=PORT)
