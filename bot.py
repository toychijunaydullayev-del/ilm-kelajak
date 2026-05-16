import asyncio
import logging
import random
import os
import time
import json
import gspread
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
BOT_TOKEN             = "8678044800:AAF9GGeTK1qS1dJMQayrq-J3qtKMhf39wdA"
ADMIN_ID              = 506343083
TEST_DURATION_SECONDS = 45 * 60
CHANNEL_LINK          = "https://t.me/IlmNuri_Markazi"
CHANNEL_USERNAME      = "@IlmNuri_Markazi"
SHEETS_ID             = "1gvaXkcJStGAUi0DH8eIBaB7R8GVJfC0z2z38mHie6MY"

# VAB narxlari
VAB_PER_CORRECT_ANSWER = 2       # Har to'g'ri javob uchun
VAB_FOR_TEST_PURCHASE  = 500     # Bir test sotib olish narxi
VAB_FOR_REFERRAL       = 50      # Har 3 ta do'st uchun (taklif)

# To'lov rekvizitlari (admin ko'rsatadi)
PAYMENT_CARD          = "8600 **** **** 1234"   # O'zingizni kartangizni yozing
PAYMENT_AMOUNT        = 10000                    # So'm
PAYMENT_OWNER         = "Ilm Nuri Markazi"

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
    """Buyurtmalar uchun ikkinchi varaq (Sheet2)"""
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

DIFFICULTY_LABEL = {
    "easy":   "🟢 Oson",
    "medium": "🟡 O'rta",
    "hard":   "🔴 Qiyin",
}

TEST_SCHEDULE = {
    "1-sinf": (17, 0, 18, 0),
    "2-sinf": (17, 0, 18, 0),
    "3-sinf": (18, 0, 19, 0),
    "4-sinf": (18, 0, 19, 0),
    "5-sinf": (19, 0, 20, 0),
    "6-sinf": (19, 0, 20, 0),
}

def is_test_time(grade: str) -> bool:
    # Bepul testlar uchun cheklov yo'q — istalgan vaqtda ishlash mumkin
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
        {"question": " Hisoblang   9 + 9 = ?",
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
        {"question": "Qaysi son 5 ga ham, 2 ga ham bo'linadi (ya'ni ham 5 lik, ham juft)?",
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
        {"question": "@IlmNuri_Markazi da 30 ta o'quvchidan 18 tasi ingliz tili, 15 tasi matematika to'garagiga boradi.",
         "options": {"A": "3", "B": "5", "C": "2", "D": "4"},
         "answer": "A", "difficulty": "hard"},
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
        {"question": "@IlmNuri_Markazi da dars 08:30 da boshlanib, 4 ta dars 45 daqiqadan + 30 daqiqa tanaffus. Qachon tugaydi?",
         "options": {"A": "11:30", "B": "12:00", "C": "11:45", "D": "12:15"},
         "answer": "B", "difficulty": "hard"},
        {"question": "Kitobning betlarini raqamlash uchun 1 dan 15 gacha nechta raqam ishlatiladi?",
         "options": {"A": "15", "B": "21", "C": "18", "D": "20"},
         "answer": "B", "difficulty": "medium"},
        {"question": "Uchta sonning o'rta arifmetigi 20 ga teng. Ulardan ikkitasi 15 va 25 bo'lsa, uchinchi sonni toping.",
         "options": {"A": "20", "B": "10", "C": "30", "D": "25"},
         "answer": "A", "difficulty": "medium"},
        {"question": "G'ildirak 1 minutda 60 marta aylanadi. U 30 sekuntda 2,5 minutdagidan necha marta kam aylanadi?",
         "options": {"A": "1", "B": "5", "C": "12", "D": "2"},
         "answer": "B", "difficulty": "easy"},
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
        {"question": "Shamol bilan changlanadigan o'simliklar gullarida qanday xususiyat bo'ladi?",
         "options": {"A": "Yorqin rangli va xushbo'y",
                     "B": "Ko'p miqdorda yengil chang hosil qiladi, ko'pincha rangsiz va hidsiz",
                     "C": "Yirik va ko'zga ko'rinarli", "D": "Ko'p nektar hosil qiladi"},
         "answer": "B", "difficulty": "medium"},
        {"question": "Oq ayiqning tukining ostidagi terisi qora. Nima uchun?",
         "options": {"A": "Qora teri quyosh issiqligini yaxshi singdirib saqlaydi",
                     "B": "Kasallikdan himoya", "C": "Estetik sabab", "D": "Kamuflyaj uchun"},
         "answer": "A", "difficulty": "easy"},
        {"question": "Nima uchun cho'l hayvonlari ko'pincha tunda faol?",
         "options": {"A": "Ovqat faqat tunda bo'lgani",
                     "B": "Kunduzgi issiqdan va suv yo'qotishdan qochish uchun",
                     "C": "Qo'rqoq bo'lganlari uchun", "D": "Ko'rmaydigan bo'lganlari uchun"},
         "answer": "B", "difficulty": "easy"},
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
        {"question": "Qaynatilgan suv tagi nima uchun loyqa bo'ladi?",
         "options": {"A": "Mineral moddalar eruvchanligini yo'qotib cho'kma hosil qiladi",
                     "B": "Idish eski", "C": "Havo bosimi yuqori", "D": "Suv o'zgaradi"},
         "answer": "A", "difficulty": "medium"},
        {"question": "100 g suvda 20 g tuz eriganda hosil bo'lgan eritma konsentratsiyasi qancha?",
         "options": {"A": "16.7% (20/120×100)", "B": "10%", "C": "25%", "D": "20%"},
         "answer": "A", "difficulty": "hard"},
        {"question": "To'yingan eritma nima?",
         "options": {"A": "Eruvchi maksimal miqdori erib bo'lgan eritma", "B": "Toza eritma",
                     "C": "Kuchsiz eritma", "D": "Suyultirilgan eritma"},
         "answer": "A", "difficulty": "easy"},
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
        {"question": "Maglev poyezdining asosiy afzalligi nimada?",
         "options": {"A": "Relsdan ko'tarilib uchgani uchun ishqalanish yo'q — 500+ km/soat",
                     "B": "Arzonroq", "C": "Ko'proq yo'lovchi", "D": "Tezroq"},
         "answer": "A", "difficulty": "medium"},
        {"question": "Chaqmoq va momaqaldiroq o'rtasidagi vaqtdan nima hisoblanadi?",
         "options": {"A": "Momaqaldiroq kuchi",
                     "B": "Chaqmoqdan masofa — tovush 340 m/s, vaqt × 340 = masofa",
                     "C": "Havo namligi", "D": "Yog'ingarchilik"},
         "answer": "B", "difficulty": "medium"},
        {"question": "Ko'rshapalak 0.1 s da aks-sado oldi (340 m/s). Devor qancha uzoq?",
         "options": {"A": "34 m", "B": "340 m", "C": "17 m", "D": "68 m"},
         "answer": "C", "difficulty": "hard"},
        {"question": "Bo'sh xonada ovoz yangrashi, mebelli xonada yangramaslik sababi?",
         "options": {"A": "Bo'sh xonada devordan aks-sado qaytadi; mebel tovushni yutadi",
                     "B": "Mebel issiqlik beradi", "C": "Mebel kuchaytiradi", "D": "Bo'sh xonada havo ko'p"},
         "answer": "A", "difficulty": "medium"},
        {"question": "Magnit va magnetik materialning farqi nimada?",
         "options": {"A": "Magnit uchadi", "B": "Magnetik material kuchliroq", "C": "Bir xil",
                     "D": "Magnit magnetik materialni tortadi; magnetik material boshqa magnetik materialni tortmaydi"},
         "answer": "D", "difficulty": "medium"},
        {"question": "Magnitni qizdirsak magnit xususiyati yo'qolishi sababi?",
         "options": {"A": "Harorat magnit kuchini oshiradi", "B": "Magnit kuyadi", "C": "Magnit eriydi",
                     "D": "Yuqori harorat atomlarning tartibli yo'nalishini buzadi"},
         "answer": "D", "difficulty": "hard"},
        {"question": "Bank kartasini magnitga yaqinlashtirmaslik sababi?",
         "options": {"A": "Karta rangi o'zgaradi", "B": "Plastik eriydi",
                     "C": "Magnit chiziq ma'lumotlari o'chib ketishi mumkin",
                     "D": "Karta ko'rinishi o'zgaradi"},
         "answer": "C", "difficulty": "easy"},
        {"question": "Amazon o'rmonlari dunyo iqlimiga katta ta'siri sababi?",
         "options": {"A": "Transpiratsiya orqali ko'p suv bug'ini atmosferaga chiqaradi va CO2 yutadi",
                     "B": "Ular issiq", "C": "Ular baland", "D": "Ular katta"},
         "answer": "A", "difficulty": "medium"},
        {"question": "Sahrolarda iqlim quruq bo'lishining sababi?",
         "options": {"A": "Bug'lanish ko'p, yog'in kam — ekvatordan ko'tarilgan havo subtropikda tushganda qurib qoladi",
                     "B": "Quyosh yo'q", "C": "Suv ko'p", "D": "Shamol yo'q"},
         "answer": "A", "difficulty": "hard"},
        {"question": "Gruntoviy suv qayta tiklanish davri qancha?",
         "options": {"A": "Bir hafta", "B": "Bir oy", "C": "Yuzlab yoki minglab yillar", "D": "Bir yil"},
         "answer": "C", "difficulty": "medium"},
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
        {"question": "Yer o'q qiyaligi 23.5° bo'lmasa fasllar bo'ladimi?",
         "options": {"A": "Ha, kuchliroq", "B": "Ha, bir xil", "C": "Yo'q yoki deyarli farq qilmasdi", "D": "Ha, zaifroq"},
         "answer": "C", "difficulty": "hard"},
        {"question": "Galiley Yupiter yo'ldoshlarini kashf etishning ahamiyati nimada?",
         "options": {"A": "Hech qanday ahamiyat", "B": "Faqat ilmiy qiziqarli",
                     "C": "Geliotsentrik modelni tasdiqlashga yordam berdi",
                     "D": "Faqat astronomiya uchun"},
         "answer": "C", "difficulty": "medium"},
        {"question": "Oy yiliga ~3.8 sm uzoqlashishi nimani anglatadi?",
         "options": {"A": "O'n million yildan keyin Quyosh tutilishi imkonsiz bo'ladi",
                     "B": "Yaqin kelajakda ta'sir qiladi", "C": "Hech narsa", "D": "Hozir sezilarli ta'sir qiladi"},
         "answer": "A", "difficulty": "hard"},
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
        {"question": "Oqsillar organizmda qanday vazifani bajaradi?",
         "options": {"A": "Energiya manbai", "B": "O'sishimizga yordam beradi",
                     "C": "Immunitetni kuchaytiradi", "D": "Suyaklarni mustahkamlaydi"},
         "answer": "B", "difficulty": "easy"},
        {"question": "Nafas sistemasida gazlar almashinuvi qayerda sodir bo'ladi?",
         "options": {"A": "Traxeyada", "B": "Bronxlarda", "C": "Alveolalarda", "D": "Burun bo'shlig'ida"},
         "answer": "C", "difficulty": "easy"},
        {"question": "Nafas chastotasi nima?",
         "options": {"A": "Bir nafas miqdori", "B": "Bir daqiqadagi nafas harakatlari soni",
                     "C": "O'pkaning hajmi", "D": "Diafragmaning kengligi"},
         "answer": "B", "difficulty": "easy"},
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
        {"question": "Diafragma qisqarganda nima sodir bo'ladi?",
         "options": {"A": "Nafas chiqariladi",
                     "B": "Nafas olinadi — ko'krak qafasi va o'pkalar hajmi ortadi",
                     "C": "Yurak tezlashadi", "D": "Qon bosimi pasayadi"},
         "answer": "B", "difficulty": "medium"},
        {"question": "Kapillyar nima va uning vazifasi nima?",
         "options": {"A": "Qonni yurakdan olib ketuvchi yirik tomir",
                     "B": "Arteriya va venalarni bog'lovchi ingichka tomir; modda almashinuvi bu yerda bo'ladi",
                     "C": "O'pkadagi havo yo'li", "D": "Yurak muskuli"},
         "answer": "B", "difficulty": "medium"},
        {"question": "Jismoniy mashq bajarilganda nafas chastotasi nima uchun ortadi?",
         "options": {"A": "Havo yetarli emas",
                     "B": "Organizmga ko'proq kislorod va energiya kerak bo'ladi",
                     "C": "Yurak dam oladi", "D": "Qon bosimi pasayadi"},
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
        {"question": "Pestitsid nima va u oziq zanjiriga qanday ta'sir qiladi?",
         "options": {"A": "O'g'it; tuproqni boyitadi",
                     "B": "Kimyoviy zararkunanda dori; oziq zanjiriga tushib, barcha tirik organizmlarni zararlashi mumkin",
                     "C": "Foydali bakteriya; o'simliklarga yordam beradi", "D": "Suv tozalagich"},
         "answer": "B", "difficulty": "medium"},
        {"question": "Oziq zanjiridagi strelkalar nima yo'nalishini ifodalaydi?",
         "options": {"A": "Organizmlarning harakatlanish yo'nalishini", "B": "Energiya oqimi yo'nalishini",
                     "C": "Suvning oqish yo'nalishini", "D": "Quyosh nurining yo'nalishini"},
         "answer": "B", "difficulty": "medium"},
        {"question": "Kumush necha darajada eriydi?",
         "options": {"A": "0 °C", "B": "100 °C", "C": "962 °C", "D": "1665 °C"},
         "answer": "C", "difficulty": "medium"},
        {"question": "Uglevod, oqsil, yog', vitamin, minerallar — bularning hammasi nima?",
         "options": {"A": "Hazm shiralari", "B": "Oziq moddalar", "C": "Fermentlar", "D": "Vitaminlar"},
         "answer": "B", "difficulty": "hard"},
        {"question": "Qon karbonat angidridni qaysi yo'nalishda tashiydi?",
         "options": {"A": "O'pkalardan tananing barcha organlariga",
                     "B": "Tananing barcha organlaridan o'pkalarga",
                     "C": "Yurakdan oshqozonga", "D": "Ingichka ichakdan o'pkalarga"},
         "answer": "B", "difficulty": "hard"},
        {"question": "Nafas olish va chiqarish jarayonida diafragma va qovurg'alarning harakati qanday?",
         "options": {"A": "Olishda: diafragma pastga, qovurg'alar yuqoriga; Chiqarishda: teskari",
                     "B": "Olishda: diafragma yuqoriga, qovurg'alar pastga; Chiqarishda: teskari",
                     "C": "Ikkalasida ham bir xil yo'nalishda", "D": "Diafragma ishtirok etmaydi"},
         "answer": "A", "difficulty": "hard"},
        {"question": "Oshqozon patogenlardan himoya qilishda qanday rol o'ynaydi?",
         "options": {"A": "Antikorlar ishlab chiqaradi",
                     "B": "Patogenlarni nobud qiluvchi xlorid kislota ishlab chiqaradi",
                     "C": "Patogenlarni o'ziga yutadi", "D": "Patogenlarni o'pkaga yuboradi"},
         "answer": "B", "difficulty": "hard"},
        {"question": "Tashuvchi organizmga misol keltiring:",
         "options": {"A": "Bemor odam",
                     "B": "Bezgak chivini — patogenni bir xo'jayindan ikkinchisiga o'tkazadi",
                     "C": "Foydali bakteriya", "D": "Virus"},
         "answer": "B", "difficulty": "hard"},
        {"question": "Agar oziq zanjiridagi birlamchi konsumentlar qirilib ketsa, nima bo'ladi?",
         "options": {"A": "Produtsent ko'payadi, ikkilamchi konsumentlar ozayadi",
                     "B": "Hamma o'zgarishsiz qoladi",
                     "C": "Faqat produtsent ta'sirlanadi", "D": "Faqat yirtqichlar ta'sirlanadi"},
         "answer": "A", "difficulty": "hard"},
        {"question": "Simob oziq zanjirining qaysi bo'g'inida ko'proq to'planadi?",
         "options": {"A": "Produtsentda", "B": "Birlamchi konsumentda",
                     "C": "Oziq zanjirining oxirgi bo'g'inida (masalan, tunes baliqda)",
                     "D": "Ikkinchi bo'g'inda"},
         "answer": "C", "difficulty": "hard"},
        {"question": "Modda erish haroratiga qarab nima aniqlash mumkin?",
         "options": {"A": "Faqat rangini", "B": "Moddaning turini (xususiyati)",
                     "C": "Faqat og'irligini", "D": "Elektr o'tkazuvchanligini"},
         "answer": "B", "difficulty": "hard"},
        {"question": "Elektr dazmolda metall asos va plastik tutqich ishlatilishining sababi nima?",
         "options": {"A": "Ikkalasi ham izolyator",
                     "B": "Metall — issiqlik va elektr o'tkazgich (qizdirish uchun); plastik — izolyator (xavfsiz ushlab turish uchun)",
                     "C": "Ikkalasi ham o'tkazgich", "D": "Metall izolyator, plastik o'tkazgich"},
         "answer": "B", "difficulty": "hard"},
        {"question": "Massasi 2 kg jismning Yerdagi og'irligi (taxminan)?",
         "options": {"A": "2 N", "B": "19.6 N", "C": "20 kg", "D": "9.8 N"},
         "answer": "B", "difficulty": "hard"},
    ],
}

# Pullik testlar (bepul testlardan ALOHIDA savollar seti)
PAID_TESTS = {
    "1-sinf": [
        {"question": "💎 [PULLIK] Sehrli kvadrat: har qator, ustun va diagonal yig'indisi teng. Bo'sh katakni toping.\n2 | ? | 6\n7 | 5 | 3\n6 | 9 | ?\nMarkaziy qator bo'sh katagi?",
         "options": {"A": "4", "B": "2", "C": "8", "D": "1"},
         "answer": "A", "difficulty": "hard"},
        {"question": "💎 [PULLIK] 1 dan 20 gacha juft sonlarning yig'indisi?",
         "options": {"A": "100", "B": "110", "C": "90", "D": "120"},
         "answer": "B", "difficulty": "hard"},
        {"question": "💎 [PULLIK] Uch xona: 1, 2, 3 raqamlaridan nechta xar xil uch xonali son tuzish mumkin?",
         "options": {"A": "3", "B": "9", "C": "6", "D": "12"},
         "answer": "C", "difficulty": "hard"},
    ],
    "2-sinf": [
        {"question": "💎 [PULLIK] 99 × 99 = ? (hisoblang)",
         "options": {"A": "9801", "B": "9900", "C": "9999", "D": "9800"},
         "answer": "A", "difficulty": "hard"},
        {"question": "💎 [PULLIK] 1+2+3+...+100 = ?",
         "options": {"A": "4950", "B": "5000", "C": "5050", "D": "5100"},
         "answer": "C", "difficulty": "hard"},
        {"question": "💎 [PULLIK] Qaysi son o'zi kamroq yoki teng barcha bo'luvchilari yig'indisiga teng?",
         "options": {"A": "6", "B": "8", "C": "4", "D": "9"},
         "answer": "A", "difficulty": "hard"},
    ],
    "3-sinf": [
        {"question": "💎 [PULLIK] 15 ta ot va g'oz, hammasi 44 ta oyoq. G'oz nechta?",
         "options": {"A": "5", "B": "7", "C": "10", "D": "8"},
         "answer": "B", "difficulty": "hard"},
        {"question": "💎 [PULLIK] Agar har kuni 2 barobar ko'paysa, 1-kuni 1 ta bo'lsa, 10-kuni nechta bo'ladi?",
         "options": {"A": "512", "B": "256", "C": "1024", "D": "128"},
         "answer": "A", "difficulty": "hard"},
        {"question": "💎 [PULLIK] 3 xonali minimal karrali: 6 ga ham, 8 ga ham bo'linadigan eng kichik 3 xonali son?",
         "options": {"A": "112", "B": "120", "C": "108", "D": "144"},
         "answer": "B", "difficulty": "hard"},
    ],
    "4-sinf": [
        {"question": "💎 [PULLIK] Chessboard muammosi: 8×8 to'rdagi kvadratlar soni (faqat 1×1 emas)?",
         "options": {"A": "64", "B": "200", "C": "204", "D": "168"},
         "answer": "C", "difficulty": "hard"},
        {"question": "💎 [PULLIK] n! = 1×2×3×...×n. 5! = ?",
         "options": {"A": "100", "B": "120", "C": "60", "D": "24"},
         "answer": "B", "difficulty": "hard"},
        {"question": "💎 [PULLIK] Fibonacci: 1,1,2,3,5,8,13... 10-son nechta?",
         "options": {"A": "55", "B": "34", "C": "21", "D": "89"},
         "answer": "A", "difficulty": "hard"},
    ],
    "5-sinf": [
        {"question": "💎 [PULLIK] Ishqalanish kuchi formulasi F=μN. μ=0.3, N=50N bo'lsa F=?",
         "options": {"A": "15 N", "B": "50 N", "C": "30 N", "D": "0.3 N"},
         "answer": "A", "difficulty": "hard"},
        {"question": "💎 [PULLIK] Atom yadrosida nima bor?",
         "options": {"A": "Elektronlar", "B": "Proton va neytronlar", "C": "Faqat protonlar", "D": "Kvarklar"},
         "answer": "B", "difficulty": "hard"},
        {"question": "💎 [PULLIK] pH=7 — bu qanday muhit?",
         "options": {"A": "Kislotali", "B": "Ishqoriy", "C": "Neytral", "D": "Zaharli"},
         "answer": "C", "difficulty": "hard"},
    ],
    "6-sinf": [
        {"question": "💎 [PULLIK] DNK replikatsiyasi qayerda sodir bo'ladi?",
         "options": {"A": "Sitoplazma", "B": "Yadro", "C": "Ribosoma", "D": "Mitoxondriya"},
         "answer": "B", "difficulty": "hard"},
        {"question": "💎 [PULLIK] Mendel qonuniga ko'ra Aa × Aa da nechta AA fenotip?",
         "options": {"A": "25%", "B": "50%", "C": "75%", "D": "100%"},
         "answer": "C", "difficulty": "hard"},
        {"question": "💎 [PULLIK] Oziq zanjirida energiyaning necha foizi keyingi sathga o'tadi?",
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
    grade     = State()
    phone     = State()

class TestProcess(StatesGroup):
    answering = State()

class AdminState(StatesGroup):
    waiting_for_ad_content = State()

class PaymentState(StatesGroup):
    waiting_check  = State()   # Foydalanuvchi chek kutilmoqda
    waiting_grade  = State()   # Sinf tanlash

class AdminConfirmState(StatesGroup):
    waiting_order_id = State()

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
                    "id":          user_id,
                    "telegram_id": int(row[1]) if row[1] else None,
                    "full_name":   row[2],
                    "school":      row[3],
                    "grade":       row[4],
                    "phone":       row[5],
                    "score":       int(row[6]) if row[6] else 0,
                    "test_started":int(row[7]) if row[7] else 0,
                    # yangi ustunlar
                    "vab":         int(row[8]) if len(row) > 8 and row[8] else 0,
                    "referral_count": int(row[9]) if len(row) > 9 and row[9] else 0,
                    "referred_by": int(row[10]) if len(row) > 10 and row[10] else 0,
                    "paid_tests":  row[11] if len(row) > 11 else "",
                    "results":     row[12] if len(row) > 12 else "",
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
    """Bir yoki bir nechta maydonni yangilaydi"""
    if user_id not in USERS_CACHE:
        return
    USERS_CACHE[user_id].update(kwargs)
    try:
        ws = get_sheet()
        rows = ws.get_all_values()
        col_map = {
            "score": 7, "test_started": 8, "vab": 9,
            "referral_count": 10, "paid_tests": 12, "results": 13,
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

def has_paid_test(user_id, grade):
    user = USERS_CACHE.get(user_id)
    if not user:
        return False
    paid = user.get("paid_tests", "")
    return grade in paid.split(",") if paid else False

def grant_paid_test(user_id, grade):
    user = USERS_CACHE.get(user_id)
    if not user:
        return
    paid = user.get("paid_tests", "")
    grades = set(paid.split(",")) if paid else set()
    grades.discard("")
    grades.add(grade)
    update_user_field(user_id, paid_tests=",".join(grades))

def add_result(user_id, grade, score, total, test_type="free"):
    user = USERS_CACHE.get(user_id)
    if not user:
        return
    import datetime
    now = datetime.datetime.now().strftime("%d.%m %H:%M")
    tag = "💎" if test_type == "paid" else "🆓"
    entry = f"{tag}{grade}:{score}/{total}@{now}"
    results = user.get("results", "")
    all_results = results.split("|") if results else []
    all_results.append(entry)
    # Oxirgi 10 ta natijani saqlash
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

def save_order(telegram_id, full_name, grade, photo_file_id):
    ORDER_COUNTER[0] += 1
    order_id = ORDER_COUNTER[0]
    ORDER_CACHE[order_id] = {
        "order_id": order_id,
        "telegram_id": telegram_id,
        "full_name": full_name,
        "grade": grade,
        "photo_file_id": photo_file_id,
        "status": "pending",
    }
    try:
        ws = get_orders_sheet()
        import datetime
        ws.append_row([order_id, telegram_id, full_name, grade,
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
            [KeyboardButton(text="👤 Profilim"),       KeyboardButton(text="🔗 Do'stlarni taklif et")],
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
        # Bepul test: faqat natija, VAB yo'q, Google Sheets ga saqlanmaydi
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
        # Pullik test: ballni saqlash, VAB qo'shish, natijani yozish
        update_user_field(user_id, score=score)
        earned_vab = score * VAB_PER_CORRECT_ANSWER
        new_vab    = add_vab(user_id, earned_vab)
        add_result(user_id, grade, score, total, test_type)

        tag = "💎 Pullik test"
        result_text = (
            f"🏁 Test yakunlandi! {tag}\n\n"
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
# 9. /START — RO'YXAT + REFERAL
# ═══════════════════════════════════════════════
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    # Referal tekshirish: /start ref_<telegram_id>
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
            [KeyboardButton(text="1-sinf"), KeyboardButton(text="2-sinf"), KeyboardButton(text="3-sinf")],
            [KeyboardButton(text="4-sinf"), KeyboardButton(text="5-sinf"), KeyboardButton(text="6-sinf")],
        ], resize_keyboard=True,
    )
    await message.answer("📚 Sinfingizni tanlang:", reply_markup=keyboard)
    await state.set_state(Registration.grade)

@dp.message(Registration.grade)
async def process_grade(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Orqaga":
        await message.answer("🏫 Maktab raqamini qaytadan yozing:",
                             reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Registration.school)
        return
    if message.text not in TESTS:
        await message.answer("❌ Noto'g'ri! Tugmalardan birini tanlang:")
        return
    await state.update_data(grade=message.text)
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
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="1-sinf"), KeyboardButton(text="2-sinf"), KeyboardButton(text="3-sinf")],
                [KeyboardButton(text="4-sinf"), KeyboardButton(text="5-sinf"), KeyboardButton(text="6-sinf")],
            ], resize_keyboard=True,
        )
        await message.answer("📚 Sinfingizni qaytadan tanlang:", reply_markup=keyboard)
        await state.set_state(Registration.grade)
        return

    phone = message.contact.phone_number if message.contact else message.text
    data  = await state.get_data()
    referred_by = data.get("referred_by", 0)

    p_id = add_user(message.from_user.id, data["full_name"], data["school"],
                    data["grade"], phone, referred_by)

    if p_id is None:
        await message.answer("Siz allaqachon ro'yxatdan o'tgansiz!",
                             reply_markup=types.ReplyKeyboardRemove())
        await state.clear()
        return

    # Referal mukofot: 1 ta taklif = 1/3 ulush (3 ta to'lganda 50 VAB)
    if referred_by:
        ref_user = get_user_by_telegram_id(referred_by)
        if ref_user:
            ref_user_id = ref_user["id"]
            new_count = ref_user["referral_count"] + 1
            update_user_field(ref_user_id, referral_count=new_count)
            # Har 3 da 50 VAB
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
# 11. ASOSIY MENYU TUGMALARI
# ═══════════════════════════════════════════════

# ── BEPUL TESTLAR ──────────────────────────────
@dp.message(F.text == "🆓 Bepul testlar")
async def free_tests_menu(message: types.Message):
    user = get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Avval /start bosing va ro'yxatdan o'ting!")
        return

    grade = user["grade"]
    q_count = len(TESTS.get(grade, []))

    await message.answer(
        f"🆓 Bepul test: {grade}\n"
        f"📝 Savollar: {q_count} ta\n"
        f"⏱ Vaqt: 45 daqiqa\n\n"
        f"✅ Bepul testlar istalgan vaqtda ishlash mumkin!\n"
        f"ℹ️ Natija faqat ekranda ko'rsatiladi.\n\n"
        f"Boshlashga tayyormisiz?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Boshlash", callback_data=f"start_{user['id']}")]
        ])
    )

# ── PULLIK TESTLAR ─────────────────────────────
@dp.message(F.text == "💎 Pullik testlar")
async def paid_tests_menu(message: types.Message):
    user = get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Avval /start bosing!")
        return

    # Barcha sinflarni ko'rsatish
    grades = list(PAID_TESTS.keys())
    buttons = []
    for g in grades:
        variant_count = len(PAID_TESTS.get(g, []))
        has = has_paid_test(user["id"], g)
        label = f"{'✅' if has else '🔒'} {g} — {variant_count} ta variant"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"paidgrade_{g}_{user['id']}")])

    await message.answer(
        f"💎 Pullik testlar — Sinf tanlang:\n\n"
        f"✅ — aktiv (sotib olingan)\n"
        f"🔒 — sotib olinmagan\n\n"
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
    variant_count = len(variants)
    has = has_paid_test(p_id, grade)

    if has:
        # Aktivlashtirilgan — variantlarni ko'rsatish
        buttons = []
        for i in range(variant_count):
            buttons.append([InlineKeyboardButton(
                text=f"📝 Variant {i+1}",
                callback_data=f"start_paid_{p_id}_{grade}_{i}"
            )])
        buttons.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_paid_menu")])
        await callback.message.edit_text(
            f"💎 {grade} — Variant tanlang:\n"
            f"📝 Jami {variant_count} ta variant mavjud\n\n"
            f"Qaysi variantni ishlashni xohlaysiz?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    else:
        # Sotib olinmagan — variant sonini ko'rsatib to'lov so'rash
        await callback.message.edit_text(
            f"💎 {grade} — Pullik test\n\n"
            f"📝 Variantlar soni: {variant_count} ta\n"
            f"✅ Bir nechta marta ishlash mumkin\n"
            f"✅ Har to'g'ri javob: +{VAB_PER_CORRECT_ANSWER} VAB\n\n"
            f"💰 Narxi: {PAYMENT_AMOUNT:,} so'm yoki {VAB_FOR_TEST_PURCHASE} VAB\n"
            f"💼 Sizda: {user['vab']} VAB\n\n"
            f"To'lov usulini tanlang:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"💳 Pul to'lash ({PAYMENT_AMOUNT:,} so'm)",
                                      callback_data=f"pay_money_{p_id}_{grade}")],
                [InlineKeyboardButton(text=f"💰 VAB sarflash ({VAB_FOR_TEST_PURCHASE} VAB)",
                                      callback_data=f"pay_vab_{p_id}_{grade}")],
                [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_paid_menu")],
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
        variant_count = len(PAID_TESTS.get(g, []))
        has = has_paid_test(user["id"], g)
        label = f"{'✅' if has else '🔒'} {g} — {variant_count} ta variant"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"paidgrade_{g}_{user['id']}")])
    await callback.message.edit_text(
        f"💎 Pullik testlar — Sinf tanlang:\n\n"
        f"✅ — aktiv (sotib olingan)\n"
        f"🔒 — sotib olinmagan\n\n"
        f"💼 Sizda: {user['vab']} VAB",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()

# ── PROFIL ─────────────────────────────────────
@dp.message(F.text == "👤 Profilim")
async def profile_menu(message: types.Message):
    user = get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Avval /start bosing!")
        return

    # Natijalarni parse qilish
    results_raw = user.get("results", "")
    results_list = [r for r in results_raw.split("|") if r] if results_raw else []

    results_text = ""
    if results_list:
        results_text = "\n📋 Oxirgi natijalar:\n"
        for r in results_list[-5:]:  # Oxirgi 5 ta
            # Format: tag+grade:score/total@date
            try:
                tag_grade, rest = r.split(":", 1)
                score_total, date = rest.split("@", 1)
                results_text += f"  {tag_grade}: {score_total} — {date}\n"
            except Exception:
                results_text += f"  {r}\n"
    else:
        results_text = "\n📋 Hali natija yo'q.\n"

    paid_tests = user.get("paid_tests", "")
    paid_text  = paid_tests if paid_tests else "Yo'q"
    ref_count  = user.get("referral_count", 0)
    next_bonus = 3 - (ref_count % 3)

    profile_text = (
        f"👤 Profil\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📛 Ism: {user['full_name']}\n"
        f"🏫 Maktab: {user['school']}\n"
        f"📚 Sinf: {user['grade']}\n"
        f"📞 Tel: {user['phone']}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 VAB balansi: {user['vab']} VAB\n"
        f"💎 Pullik testlar: {paid_text}\n"
        f"👫 Taklif qilinganlar: {ref_count} ta\n"
        f"🎁 Keyingi bonus uchun: {next_bonus} ta do'st kerak\n"
        f"━━━━━━━━━━━━━━━━━━"
        f"{results_text}"
        f"━━━━━━━━━━━━━━━━━━"
    )

    await message.answer(profile_text, reply_markup=main_menu_keyboard())

# ── DO'STLARNI TAKLIF ET ───────────────────────
@dp.message(F.text == "🔗 Do'stlarni taklif et")
async def invite_menu(message: types.Message):
    user = get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Avval /start bosing!")
        return

    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{message.from_user.id}"
    ref_count = user.get("referral_count", 0)
    next_bonus = 3 - (ref_count % 3)

    await message.answer(
        f"🔗 Taklif havolangiz:\n"
        f"{ref_link}\n\n"
        f"📊 Siz taklif qilganlar: {ref_count} ta\n"
        f"🎁 Keyingi bonus: {next_bonus} ta do'st kerak\n\n"
        f"💰 Har 3 ta do'st = {VAB_FOR_REFERRAL} VAB!\n"
        f"💎 {VAB_FOR_TEST_PURCHASE} VAB to'plang → pullik test bepul!\n\n"
        f"Havolani do'stlaringizga yuboring 👆",
        reply_markup=main_menu_keyboard()
    )

# ═══════════════════════════════════════════════
# 12. TO'LOV CALLBACK-LAR
# ═══════════════════════════════════════════════

# ── PULLA TO'LASH ──────────────────────────────
@dp.callback_query(F.data.startswith("pay_money_"))
async def pay_with_money(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    # format: pay_money_{p_id}_{grade}
    p_id  = int(parts[2])
    grade = parts[3] if len(parts) > 3 else None
    user  = get_user_by_id(p_id)
    if not user:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return
    if not grade:
        grade = user["grade"]

    await callback.message.answer(
        f"💳 To'lov ma'lumotlari:\n\n"
        f"🏦 Karta: {PAYMENT_CARD}\n"
        f"👤 Egasi: {PAYMENT_OWNER}\n"
        f"💰 Summa: {PAYMENT_AMOUNT:,} so'm\n\n"
        f"⚠️ To'lov izohiga: {user['full_name']} — {grade}\n\n"
        f"To'lov chekini (screenshot) yuborish uchun quyidagi tugmani bosing 👇",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Chek yuborish", callback_data=f"send_check_{p_id}_{grade}")]
        ])
    )
    await callback.answer()

# ── VAB BILAN TO'LASH ──────────────────────────
@dp.callback_query(F.data.startswith("send_check_"))
async def send_check_prompt(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    p_id  = int(parts[2])
    grade = parts[3] if len(parts) > 3 else None
    user  = get_user_by_id(p_id)
    if not user:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return
    if not grade:
        grade = user["grade"]

    await callback.message.answer(
        f"📤 To'lov cheki rasmini shu yerga yuboring:\n\n"
        f"📚 Sinf: {grade}\n"
        f"💰 Summa: {PAYMENT_AMOUNT:,} so'm\n\n"
        f"Rasm yuboring 👇\n"
        f"Bekor qilish: /cancel"
    )
    await state.update_data(paying_user_id=p_id, paying_grade=grade)
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

    data     = await state.get_data()
    p_id     = data["paying_user_id"]
    grade    = data["paying_grade"]
    user     = get_user_by_id(p_id)
    photo_id = message.photo[-1].file_id

    order_id = save_order(message.from_user.id, user["full_name"], grade, photo_id)

    # Adminga inline tasdiqlash/rad tugmalari bilan yuborish
    try:
        await bot.send_photo(
            ADMIN_ID,
            photo=photo_id,
            caption=(
                f"💳 YANGI TO'LOV CHEKI!\n\n"
                f"📋 Buyurtma ID: #{order_id}\n"
                f"👤 Ism: {user['full_name']}\n"
                f"📚 Sinf: {grade}\n"
                f"📞 Tel: {user['phone']}\n"
                f"💰 Summa: {PAYMENT_AMOUNT:,} so'm"
            ),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"admin_confirm_{order_id}"),
                    InlineKeyboardButton(text="❌ Rad etish",  callback_data=f"admin_reject_{order_id}"),
                ]
            ])
        )
    except Exception as e:
        print(f"Admin yuborishda xato: {e}")

    await message.answer(
        f"✅ Chek qabul qilindi!\n"
        f"📋 Buyurtma ID: #{order_id}\n\n"
        f"Admin tekshiradi va tez orada aktivlanadi.\n"
        f"Odatda 5-30 daqiqa davom etadi.",
        reply_markup=main_menu_keyboard()
    )
    await state.clear()

# Admin inline tasdiqlash/rad
@dp.callback_query(F.data.startswith("admin_confirm_"), F.from_user.id == ADMIN_ID)
async def admin_confirm_inline(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[2])
    order = confirm_order(order_id)
    if not order:
        await callback.answer(f"#{order_id} topilmadi!", show_alert=True)
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
                f"💰 Bonus: +50 VAB\n\n"
                f"Boshlash uchun '💎 Pullik testlar' tugmasini bosing!",
                reply_markup=main_menu_keyboard()
            )
        except Exception:
            pass

    await callback.message.edit_caption(
        caption=callback.message.caption + f"\n\n✅ TASDIQLANDI (admin: {callback.from_user.full_name})"
    )
    await callback.answer(f"✅ #{order_id} tasdiqlandi!")

@dp.callback_query(F.data.startswith("admin_reject_"), F.from_user.id == ADMIN_ID)
async def admin_reject_inline(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[2])
    order = ORDER_CACHE.get(order_id)
    if not order:
        await callback.answer(f"#{order_id} topilmadi!", show_alert=True)
        return

    order["status"] = "rejected"
    try:
        await bot.send_message(
            order["telegram_id"],
            f"❌ #{order_id} to'lovingiz rad etildi.\n\n"
            f"Sababi: Chek aniq ko'rinmagan yoki noto'g'ri summa.\n"
            f"Qayta to'lov uchun admin bilan bog'laning."
        )
    except Exception:
        pass

    await callback.message.edit_caption(
        caption=callback.message.caption + f"\n\n❌ RAD ETILDI (admin: {callback.from_user.full_name})"
    )
    await callback.answer(f"❌ #{order_id} rad etildi!")

# ── VAB BILAN TO'LASH ──────────────────────────
@dp.callback_query(F.data.startswith("pay_vab_"))
async def pay_with_vab(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    p_id  = int(parts[2])
    grade = parts[3] if len(parts) > 3 else None
    user  = get_user_by_id(p_id)
    if not user:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return
    if not grade:
        grade = user["grade"]

    if user["vab"] < VAB_FOR_TEST_PURCHASE:
        await callback.answer(
            f"❌ VAB yetarli emas!\n"
            f"Kerak: {VAB_FOR_TEST_PURCHASE} VAB\n"
            f"Sizda: {user['vab']} VAB",
            show_alert=True
        )
        return

    if has_paid_test(p_id, grade):
        await callback.answer("Bu test allaqachon aktiv!", show_alert=True)
        return

    success = spend_vab(p_id, VAB_FOR_TEST_PURCHASE)
    if success:
        grant_paid_test(p_id, grade)
        await callback.message.answer(
            f"✅ {grade} pullik test aktivlashtirildi!\n"
            f"💰 -{VAB_FOR_TEST_PURCHASE} VAB sarflandi\n\n"
            f"💎 Testni hozir ishlashingiz mumkin!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💎 Boshlash",
                                      callback_data=f"paidgrade_{grade}_{p_id}")]
            ])
        )
    else:
        await callback.answer("Xato yuz berdi!", show_alert=True)
    await callback.answer()

# ── BEPUL TEST BOSHLASH ────────────────────────
@dp.callback_query(F.data.startswith("start_") & ~F.data.startswith("start_paid_"))
async def start_free_test(callback: types.CallbackQuery, state: FSMContext):
    p_id = int(callback.data.split("_")[1])
    user = get_user_by_id(p_id)
    if not user:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return

    grade  = user["grade"]
    q_list = TESTS.get(grade, [])
    if not q_list:
        await callback.message.answer(f"{grade} uchun savollar yo'q.")
        await callback.answer()
        return

    await _start_test_session(callback, state, user, q_list, "free")

# ── PULLIK TEST BOSHLASH ───────────────────────
@dp.callback_query(F.data.startswith("start_paid_"))
async def start_paid_test(callback: types.CallbackQuery, state: FSMContext):
    # format: start_paid_{p_id}_{grade}_{variant_index}
    parts = callback.data.split("_")
    p_id  = int(parts[2])
    grade = parts[3] if len(parts) > 3 else None
    variant_index = int(parts[4]) if len(parts) > 4 else 0

    user = get_user_by_id(p_id)
    if not user:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return
    if not grade:
        grade = user["grade"]

    if not has_paid_test(p_id, grade):
        await callback.answer("Pullik test sotib olinmagan!", show_alert=True)
        return

    all_variants = PAID_TESTS.get(grade, [])
    if not all_variants:
        await callback.message.answer(f"{grade} pullik savollar yo'q.")
        await callback.answer()
        return

    # Har bir variant — 3 ta savol (yoki mavjud savollar bo'linadi)
    VARIANT_SIZE = 3
    start = variant_index * VARIANT_SIZE
    end   = start + VARIANT_SIZE
    q_list = all_variants[start:end] if start < len(all_variants) else all_variants

    if not q_list:
        q_list = all_variants

    await _start_test_session(callback, state, user, q_list, "paid", grade=grade)

async def _start_test_session(callback, state, user, q_list, test_type, grade=None):
    if not grade:
        grade = user["grade"]
    tag   = "💎 Pullik" if test_type == "paid" else "🆓 Bepul"

    await state.set_state(TestProcess.answering)
    await state.update_data(
        grade=grade, questions=q_list, current=0, score=0, streak=0,
        start_ts=time.time(), db_user_id=user["id"], user_name=user["full_name"],
        last_info_msg_id=None, last_q_msg_id=None, test_type=test_type,
    )
    await callback.message.answer(
        f"🚀 {grade} — {tag} test boshlanmoqda!\n"
        f"📝 Savollar soni: {len(q_list)}\n"
        f"⏱ Vaqt: 45 daqiqa\n\n"
        f"Omad! 🍀   @IlmNuri_Markazi"
    )
    await callback.answer()
    asyncio.create_task(timeout_watcher(callback.from_user.id, state))
    await send_question(callback.from_user.id, state)

# ── ASOSIY MENYU CALLBACK ──────────────────────
@dp.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: types.CallbackQuery):
    await callback.message.answer("Asosiy menyu:", reply_markup=main_menu_keyboard())
    await callback.answer()

# ═══════════════════════════════════════════════
# 13. JAVOB TEKSHIRISH
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
        toast = "✅ To'g'ri! +2 VAB" + (" 🔥" if streak >= 2 else "")
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
# 14. ADMIN BUYRUQLARI
# ═══════════════════════════════════════════════
@dp.message(Command("refresh"), F.from_user.id == ADMIN_ID)
async def refresh_cache(message: types.Message):
    old = get_users_count()
    load_users_to_cache()
    new = get_users_count()
    await message.answer(f"✅ Baza yangilandi!\nOldin: {old} → Hozir: {new} ta")

@dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def admin_panel(message: types.Message):
    await message.answer(
        "🛠 Admin panel:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Xabar yuborish", callback_data="send_ad")],
            [InlineKeyboardButton(text="📊 Statistika",     callback_data="admin_stats")],
            [InlineKeyboardButton(text="💳 Kutilayotgan to'lovlar", callback_data="pending_orders")],
        ])
    )

@dp.callback_query(F.data == "admin_stats", F.from_user.id == ADMIN_ID)
async def admin_stats(callback: types.CallbackQuery):
    total  = get_users_count()
    orders = len([o for o in ORDER_CACHE.values() if o["status"] == "pending"])
    await callback.answer(
        f"Jami: {total} ta\nKutilayotgan to'lovlar: {orders} ta",
        show_alert=True
    )

@dp.callback_query(F.data == "pending_orders", F.from_user.id == ADMIN_ID)
async def pending_orders(callback: types.CallbackQuery):
    orders = [o for o in ORDER_CACHE.values() if o["status"] == "pending"]
    if not orders:
        await callback.answer("Kutilayotgan to'lov yo'q!", show_alert=True)
        return
    for o in orders:
        await callback.message.answer(
            f"📋 Buyurtma #{o['order_id']}\n"
            f"👤 {o['full_name']}\n"
            f"📚 Sinf: {o['grade']}\n\n"
            f"✅ Tasdiqlash: /confirm {o['order_id']}\n"
            f"❌ Rad etish: /reject {o['order_id']}"
        )
    await callback.answer()

# /confirm <order_id>
@dp.message(Command("confirm"), F.from_user.id == ADMIN_ID)
async def confirm_payment(message: types.Message):
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

    # Foydalanuvchiga pullik test berish
    user = get_user_by_telegram_id(order["telegram_id"])
    if user:
        grant_paid_test(user["id"], order["grade"])
        # VAB ham berish (bonus)
        add_vab(user["id"], 50)
        try:
            await bot.send_message(
                order["telegram_id"],
                f"🎉 To'lovingiz tasdiqlandi!\n\n"
                f"💎 {order['grade']} pullik test aktivlashtirildi!\n"
                f"💰 Bonus: +50 VAB\n\n"
                f"Boshlash uchun '💎 Pullik testlar' tugmasini bosing!",
                reply_markup=main_menu_keyboard()
            )
        except Exception:
            pass

    await message.answer(f"✅ #{order_id} tasdiqlandi! Foydalanuvchiga xabar yuborildi.")

# /reject <order_id>
@dp.message(Command("reject"), F.from_user.id == ADMIN_ID)
async def reject_payment(message: types.Message):
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
            f"❌ #{order_id} to'lovingiz rad etildi.\n\n"
            f"Sababi: Chek aniq ko'rinmagan yoki noto'g'ri summa.\n"
            f"Qayta to'lov uchun admin bilan bog'laning."
        )
    except Exception:
        pass
    await message.answer(f"❌ #{order_id} rad etildi.")

# Admin: foydalanuvchiga qo'lda VAB qo'shish
@dp.message(Command("addvab"), F.from_user.id == ADMIN_ID)
async def add_vab_cmd(message: types.Message):
    # /addvab <telegram_id> <amount>
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
    await message.answer(f"✅ {user['full_name']}ga +{amount} VAB qo'shildi. Jami: {new_vab} VAB")
    try:
        await bot.send_message(tg_id, f"🎁 Admindan: +{amount} VAB qo'shildi!\n💼 Jami: {new_vab} VAB")
    except Exception:
        pass

# ── REKLAMA YUBORISH ───────────────────────────
@dp.callback_query(F.data == "send_ad", F.from_user.id == ADMIN_ID)
async def start_ad(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("📝 Xabar matnini yoki rasm/video yuboring.\n/cancel — bekor qilish")
    await state.set_state(AdminState.waiting_for_ad_content)
    await callback.answer()

@dp.message(AdminState.waiting_for_ad_content, F.from_user.id == ADMIN_ID)
async def process_ad_content(message: types.Message, state: FSMContext):
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

# ═══════════════════════════════════════════════
# 15. MAIN
# ═══════════════════════════════════════════════
async def main():
    logging.basicConfig(level=logging.INFO)
    load_users_to_cache()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
