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
SHEETS_ID             = "1gvaXkcJStGAUi0DH8eIBaB7R8GVJfC0z2z38mHie6MY"

# Google Sheets ulanish
def get_sheet():
    scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEETS_ID).sheet1

DIFFICULTY_LABEL = {
    "easy":   "🟢 Oson",
    "medium": "🟡 O'rta",
    "hard":   "🔴 Qiyin",
}

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
         "answer": "D", "difficulty": "easy"}
    ],
    "3-sinf": [
        {"question": "5, 11, 17, 23, [] qonuniyatni davom ettiring.",
         "options": {"A": "27", "B": "29", "C": "30", "D": "28"},
         "answer": "B", "difficulty": "easy"},
        {"question": "To'rtta 8 ning yig'indisi nechaga teng?",
         "options": {"A": "24", "B": "36", "C": "32", "D": "40"},
         "answer": "C", "difficulty": "easy"},
        {"question": "630 : 90 + 15 ifodaning qiymatini toping.",
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
         "answer": "A", "difficulty": "easy"}
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
        {"question": "@IlmNuri_Markazi da 30 ta o'quvchidan 18 tasi ingliz tili, 15 tasi matematika to'garagiga boradi. Agar har bir o'quvchi kamida bitta to'garakka borsa, nechta o'quvchi ikkala to'garakka ham boradi?",
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
        {"question": "@IlmNuri_Markazi da dars 08:30 da boshlanib, har biri 45 daqiqadan bo'lgan 4 ta dars o'tildi. Tanaffuslar jami 30 daqiqa bo'lsa, darslar soat nechada tugagan?",
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
        {"question": "Rasmga qarang. 1ta Ayiq + 1 ta ot + 1 ta o'rdak natijasini aniqlang ?",
         "image": "https://i.ibb.co/ZzvTrsPM/2.jpg",
         "options": {"A": "26", "B": "25", "C": "20", "D": "18"},
         "answer": "A", "difficulty": "hard"},
        {"question": "Ikki sonning ko'paytmasi 120 ga teng. Agar ko'paytuvchilardan biri 3 marta orttirilsa, yangi ko'paytma necha bo'ladi?",
         "options": {"A": "40", "B": "360", "C": "123", "D": "240"},
         "answer": "B", "difficulty": "medium"},
        {"question": "Aylana radiusi 5 sm bo'lsa, uning eng uzun vatari (diametri) necha sm?",
         "options": {"A": "5", "B": "15", "C": "10", "D": "20"},
         "answer": "C", "difficulty": "easy"},
        {"question": "Jasurning uyidan ilm nurigacha bo'lgan yo'l 45 daqiqa davom etadi. U mavzu topshirishi kerak 7.05 da markazga bordi va u 15 daqiqaga kechikdi. U soat nechada uydan chiqdi? javob rasmda",
         "image": "https://i.ibb.co/pvdc2wPb/1.jpg",
         "options": {"A": "A", "B": "B", "C": "C", "D": "E"},
         "answer": "C", "difficulty": "easy"}
    ],
    "5-sinf": [
    {
      "question": "Bog'bon insektitsid sepganda hosil bo'lmasligi sababi nimada?",
      "options": {
        "A": "Meva zararkunandadan shikastlanadi",
        "B": "Changlanish bo'lmaydi — changlatuvchi hasharotlar yo'q bo'lib ketadi",
        "C": "O'simlik qurib qoladi",
        "D": "Chang donasi shikastlanadi"
      },
      "answer": "B",
      "chapter": "1-bob",
      "difficulty": "medium"
    },
    {
      "question": "Ikki jinsli gul deb qaysi gullarga aytiladi?",
      "options": {
        "A": "Faqat changchili",
        "B": "Ham changchi, ham urug'chisi bor gullarga",
        "C": "Gulkosabargsiz",
        "D": "Faqat urug'chili"
      },
      "answer": "B",
      "chapter": "1-bob",
      "difficulty": "easy"
    },
    {
      "question": "Shamol bilan changlanadigan o'simliklar gullarida qanday xususiyat bo'ladi?",
      "options": {
        "A": "Yorqin rangli va xushbo'y",
        "B": "Ko'p miqdorda yengil chang hosil qiladi, ko'pincha rangsiz va hidsiz",
        "C": "Yirik va ko'zga ko'rinarli",
        "D": "Ko'p nektar hosil qiladi"
      },
      "answer": "B",
      "chapter": "1-bob",
      "difficulty": "medium"
    },
    {
      "question": "Oq ayiqning tukining ostidagi terisi qora. Nima uchun?",
      "options": {
        "A": "Qora teri quyosh issiqligini yaxshi singdirib saqlaydi",
        "B": "Kasallikdan himoya",
        "C": "Estetik sabab",
        "D": "Kamuflyaj uchun"
      },
      "answer": "A",
      "chapter": "2-bob",
      "difficulty": "easy"
    },
    {
      "question": "Nima uchun cho'l hayvonlari ko'pincha tunda faol?",
      "options": {
        "A": "Ovqat faqat tunda bo'lgani",
        "B": "Kunduzgi issiqdan va suv yo'qotishdan qochish uchun",
        "C": "Qo'rqoq bo'lganlari uchun",
        "D": "Ko'rmaydigan bo'lganlari uchun"
      },
      "answer": "B",
      "chapter": "2-bob",
      "difficulty": "easy"
    },
    {
      "question": "Zaharli qurbaqalar yorqin rangli. Bu qanday moslanish?",
      "options": {
        "A": "Tana rangi bezagi",
        "B": "Suv saqlov mexanizmi",
        "C": "Kamuflyaj",
        "D": "Aposematizm"
      },
      "answer": "D",
      "chapter": "2-bob",
      "difficulty": "medium"
    },
    {
      "question": "Spirt suvga qaraganda tezroq bug'lanishining sababi?",
      "options": {
        "A": "Spirt og'irroq",
        "B": "Spirt zarrachalari o'rtasidagi tortishish suv zarrachalarnikidan kuchsizroq",
        "C": "Spirt kattaroq",
        "D": "Spirt issiqroq"
      },
      "answer": "B",
      "chapter": "3-bob",
      "difficulty": "medium"
    },
    {
      "question": "Muzlaganda suv kengayadi. Ko'priklarda nima uchun bo'shliq qoldiriladi?",
      "options": {
        "A": "Suv oqishi uchun",
        "B": "Bezak uchun",
        "C": "Sovuqda metall qisqaradi",
        "D": "Muzlagan suv kengayib konstruksiyani yorib yubormasligi uchun"
      },
      "answer": "D",
      "chapter": "3-bob",
      "difficulty": "medium"
    },
    {
      "question": "Qaynatilgan suv tagi nima uchun loyqa bo'ladi?",
      "options": {
        "A": "Mineral moddalar eruvchanligini yo'qotib cho'kma hosil qiladi",
        "B": "Idish eski",
        "C": "Havo bosimi yuqori",
        "D": "Suv o'zgaradi"
      },
      "answer": "A",
      "chapter": "3-bob",
      "difficulty": "medium"
    },
    {
      "question": "100 g suvda 25 g tuz eriganda hosil bo'lgan eritma konsentratsiyasi qancha?",
      "options": {
        "A": "16.7%",
        "B": "10%",
        "C": "25%",
        "D": "20%"
      },
      "answer": "D",
      "chapter": "4-bob",
      "difficulty": "hard"
    },
    {
      "question": "To'yingan eritma nima?",
      "options": {
        "A": "Eruvchi maksimal miqdori erib bo'lgan eritma",
        "B": "Toza eritma",
        "C": "Kuchsiz eritma",
        "D": "Suyultirilgan eritma"
      },
      "answer": "A",
      "chapter": "4-bob",
      "difficulty": "easy"
    },
    {
      "question": "Yo'liga qish faslida tuz sepilishi sababi?",
      "options": {
        "A": "Bezak uchun",
        "B": "Tuz yo'lni isitadi",
        "C": "Tuzli eritma muzlash harorati 0°C dan pastda",
        "D": "Yo'l uchun ozuqa"
      },
      "answer": "C",
      "chapter": "4-bob",
      "difficulty": "medium"
    },
    {
      "question": "Parashyutchi terminal (doimiy) tezlikda tushayotganda kuchlar qanday?",
      "options": {
        "A": "Faqat gravitatsiya",
        "B": "Faqat havo qarshiligi",
        "C": "Gravitatsiya > qarshilik",
        "D": "Gravitatsiya = havoning qarshilik kuchi — muvozanat"
      },
      "answer": "D",
      "chapter": "5-bob",
      "difficulty": "hard"
    },
    {
      "question": "Samolyot qanotining yuqori qismi qavariq — nima uchun?",
      "options": {
        "A": "Ishqalanish uchun",
        "B": "Ko'rinish uchun",
        "C": "Qavariq qism havo tezroq oqadi — past bosim — ko'tarish kuchi hosil bo'ladi (Bernulli)",
        "D": "Og'irlik uchun"
      },
      "answer": "C",
      "chapter": "5-bob",
      "difficulty": "hard"
    },
    {
      "question": "Maglev poyezdining asosiy afzalligi nimada?",
      "options": {
        "A": "Relsdan ko'tarilib uchgani uchun ishqalanish yo'q — 500+ km/soat",
        "B": "Arzonroq",
        "C": "Ko'proq yo'lovchi",
        "D": "Tezroq"
      },
      "answer": "A",
      "chapter": "5-bob",
      "difficulty": "medium"
    },
    {
      "question": "Chaqmoq va momaqaldiroq o'rtasidagi vaqtdan nima hisoblanadi?",
      "options": {
        "A": "Momaqaldiroq kuchi",
        "B": "Chaqmoqdan masofa — tovush 340 m/s, vaqt × 340 = masofa",
        "C": "Havo namligi",
        "D": "Yog'ingarchilik"
      },
      "answer": "B",
      "chapter": "6-bob",
      "difficulty": "medium"
    },
    {
      "question": "Ko'rshapalak 0.1 s da aks-sado oldi (340 m/s). Devor qancha uzoq?",
      "options": {
        "A": "34 m",
        "B": "340 m",
        "C": "17 m",
        "D": "68 m"
      },
      "answer": "C",
      "chapter": "6-bob",
      "difficulty": "hard"
    },
    {
      "question": "Bo'sh xonada ovoz yangrashi, mebelli xonada yangramaslik sababi?",
      "options": {
        "A": "Bo'sh xonada devordan aks-sado qaytadi; mebel tovushni yutadi",
        "B": "Mebel issiqlik beradi",
        "C": "Mebel kuchaytiradi",
        "D": "Bo'sh xonada havo ko'p"
      },
      "answer": "A",
      "chapter": "6-bob",
      "difficulty": "medium"
    },
    {
      "question": "Magnit va magnetik materialning farqi nimada?",
      "options": {
        "A": "Magnit uchadi",
        "B": "Magnetik material kuchliroq",
        "C": "Bir xil",
        "D": "Magnit magnetik materialni tortadi va magnitlar bilan itaradi/tortadi; magnetik material esa boshqa magnetik materialni tortmaydi"
      },
      "answer": "D",
      "chapter": "7-bob",
      "difficulty": "medium"
    },
    {
      "question": "Magnitni qizdirsak magnit xususiyati yo'qolishi sababi?",
      "options": {
        "A": "Harorat magnit kuchini oshiradi",
        "B": "Magnit kuyadi",
        "C": "Magnit eriydi",
        "D": "Yuqori harorat atomlarning tartibli yo'nalishini buzadi"
      },
      "answer": "D",
      "chapter": "7-bob",
      "difficulty": "hard"
    },
    {
      "question": "Bank kartasini magnitga yaqinlashtirmaslik sababi?",
      "options": {
        "A": "Karta rangi o'zgaradi",
        "B": "Plastik eriydi",
        "C": "Magnit chiziq ma'lumotlari o'chib ketishi mumkin",
        "D": "Karta ko'rinishi o'zgaradi"
      },
      "answer": "C",
      "chapter": "7-bob",
      "difficulty": "easy"
    },
    {
      "question": "Amazon o'rmonlari dunyo iqlimiga katta ta'siri sababi?",
      "options": {
        "A": "Transpiratsiya orqali ko'p suv bug'ini atmosferaga chiqaradi va CO2 yutadi",
        "B": "Ular issiq",
        "C": "Ular baland",
        "D": "Ular katta"
      },
      "answer": "A",
      "chapter": "8-bob",
      "difficulty": "medium"
    },
    {
      "question": "Sahrolarda iqlim quruq bo'lishining sababi?",
      "options": {
        "A": "Bug'lanish ko'p, yog'in kam — ekvatordan ko'tarilgan havo subtropikda tushganda qurib qoladi",
        "B": "Quyosh yo'q",
        "C": "Suv ko'p",
        "D": "Shamol yo'q"
      },
      "answer": "A",
      "chapter": "8-bob",
      "difficulty": "hard"
    },
    {
      "question": "Gruntoviy suv qayta tiklanish davri qancha?",
      "options": {
        "A": "Bir hafta",
        "B": "Bir oy",
        "C": "Yuzlab yoki minglab yillar",
        "D": "Bir yil"
      },
      "answer": "C",
      "chapter": "8-bob",
      "difficulty": "medium"
    },
    {
      "question": "Eutrofikatsiya nima?",
      "options": {
        "A": "Suvning muzlashi",
        "B": "Suvning qaynashi",
        "C": "Suvga ortiqcha ozuqa tushishi — suv o'tlar ko'payadi, kislorod kamayadi, baliqlar nobud bo'ladi",
        "D": "Suvning bug'lanishi"
      },
      "answer": "C",
      "chapter": "9-bob",
      "difficulty": "hard"
    },
    {
      "question": "Karbon izi nima?",
      "options": {
        "A": "Inson oyoq izi",
        "B": "Ko'mir rangi",
        "C": "Inson yoki tashkilot faoliyati natijasida chiqariladigan CO2 umumiy miqdori",
        "D": "Tuproqdagi karbon"
      },
      "answer": "C",
      "chapter": "9-bob",
      "difficulty": "medium"
    },
    {
      "question": "Barqaror rivojlanish nima?",
      "options": {
        "A": "Hozirgi va kelajak avlod ehtiyojlarini muvozanatli qondirish",
        "B": "Faqat iqtisodiy",
        "C": "Faqat texnologik",
        "D": "Faqat sanoat"
      },
      "answer": "A",
      "chapter": "9-bob",
      "difficulty": "easy"
    },
    {
      "question": "Yer o'q qiyaligi 23.5° bo'lmasa fasllar bo'ladimi?",
      "options": {
        "A": "Ha, kuchliroq",
        "B": "Ha, bir xil",
        "C": "Yo'q yoki deyarli farq qilmasdi",
        "D": "Ha, zaifroq"
      },
      "answer": "C",
      "chapter": "10-bob",
      "difficulty": "hard"
    },
    {
      "question": "Galiley Yupiter yo'ldoshlarini kashf etishning ahamiyati nimada?",
      "options": {
        "A": "Hech qanday ahamiyat",
        "B": "Faqat ilmiy qiziqarli",
        "C": "Geliotsentrik modelni tasdiqlashga yordam berdi",
        "D": "Faqat astronomiya uchun"
      },
      "answer": "C",
      "chapter": "10-bob",
      "difficulty": "medium"
    },
    {
      "question": "Oy yiliga ~3.8 sm uzoqlashishi nimani anglatadi?",
      "options": {
        "A": "O'n million yildan keyin Quyosh tutilishi imkonsiz bo'ladi",
        "B": "Yaqin kelajakda ta'sir qiladi",
        "C": "Hech narsa",
        "D": "Hozir sezilarli ta'sir qiladi"
      },
      "answer": "A",
      "chapter": "10-bob",
      "difficulty": "hard"
    }
  ],
    "6-sinf": [
    {
      "question": "Muvozanatlashgan ratsion nima?",
      "options": {
        "A": "Faqat go'sht va yog'li mahsulotlar",
        "B": "Organizm uchun zarur oziq moddalarni saqlaydigan oziq-ovqat mahsulotlari va suv",
        "C": "Faqat meva-sabzavotlar",
        "D": "Ko'p miqdorda shakar va shirinliklar"
      },
      "answer": "B",
      "difficulty": "easy"
    },
    {
      "question": "Qizilo'ngach qanday organ?",
      "options": {
        "A": "Ovqat hazm qiluvchi organ",
        "B": "Og'iz bo'shlig'ini oshqozon bilan bog'lovchi naysimon organ",
        "C": "Nafas organi",
        "D": "Qon aylanish organi"
      },
      "answer": "B",
      "difficulty": "easy"
    },
    {
      "question": "Ingichka ichakda qanday jarayon sodir bo'ladi?",
      "options": {
        "A": "Ovqat faqat mexanik maydalanadi",
        "B": "Hazm qilish yakunlanadi va parchalangan oziq moddalar qonga so'riladi",
        "C": "Suv va minerallar so'riladi",
        "D": "Najas hosil bo'ladi"
      },
      "answer": "B",
      "difficulty": "easy"
    },
    {
      "question": "Oqsillar organizmda qanday vazifani bajaradi?",
      "options": {
        "A": "Energiya manbai",
        "B": "O'sishimizga yordam beradi",
        "C": "Immunitetni kuchaytiradi",
        "D": "Suyaklarni mustahkamlaydi"
      },
      "answer": "B",
      "difficulty": "easy"
    },
    {
      "question": "Nafas sistemasida gazlar almashinuvi qayerda sodir bo'ladi?",
      "options": {
        "A": "Traxeyada",
        "B": "Bronxlarda",
        "C": "Alveolalarda",
        "D": "Burun bo'shlig'ida"
      },
      "answer": "C",
      "difficulty": "easy"
    },
    {
      "question": "Nafas chastotasi nima?",
      "options": {
        "A": "Bir nafas miqdori",
        "B": "Bir daqiqadagi nafas harakatlari soni",
        "C": "O'pkaning hajmi",
        "D": "Diafragmaning kengligi"
      },
      "answer": "B",
      "difficulty": "easy"
    },
    {
      "question": "Yurak qon aylanish sistemasida qanday vazifani bajaradi?",
      "options": {
        "A": "Qonni tozalaydi",
        "B": "Kislorod ishlab chiqaradi",
        "C": "Nasos singari qonni tana bo'ylab haydaydi",
        "D": "Karbonat angidrid ishlab chiqaradi"
      },
      "answer": "C",
      "difficulty": "easy"
    },
    {
      "question": "Arteriya qanday qontomir?",
      "options": {
        "A": "Qonni yurakka olib keluvchi",
        "B": "Qonni yurakdan olib ketuvchi",
        "C": "Arteriya va venani bog'lovchi",
        "D": "Faqat o'pkalarda bo'luvchi"
      },
      "answer": "B",
      "difficulty": "easy"
    },
    {
      "question": "Nima uchun yog'li mahsulotlarni ko'p iste'mol qilish zararli?",
      "options": {
        "A": "Vitaminlar kamayadi",
        "B": "Yurak kasalliklari rivojlanadi",
        "C": "Suyaklar zaiflashadi",
        "D": "Ko'rish pasayadi"
      },
      "answer": "B",
      "difficulty": "medium"
    },
    {
      "question": "Yo'g'on ichakda asosan nima so'riladi?",
      "options": {
        "A": "Oqsillar",
        "B": "Uglevrodlar",
        "C": "Suv va ba'zi minerallar",
        "D": "Yog'lar"
      },
      "answer": "C",
      "difficulty": "medium"
    },
    {
      "question": "Diafragma qisqarganda nima sodir bo'ladi?",
      "options": {
        "A": "Nafas chiqariladi",
        "B": "Nafas olinadi — ko'krak qafasi va o'pkalar hajmi ortadi",
        "C": "Yurak tezlashadi",
        "D": "Qon bosimi pasayadi"
      },
      "answer": "B",
      "difficulty": "medium"
    },
    {
      "question": "Kapillyar nima va uning vazifasi nima?",
      "options": {
        "A": "Qonni yurakdan olib ketuvchi yirik tomir",
        "B": "Arteriya va venalarni bog'lovchi ingichka tomir; modda almashinuvi bu yerda bo'ladi",
        "C": "O'pkadagi havo yo'li",
        "D": "Yurak muskuli"
      },
      "answer": "B",
      "difficulty": "medium"
    },
    {
      "question": "Jismoniy mashq bajarilganda nafas chastotasi nima uchun ortadi?",
      "options": {
        "A": "Havo yetarli emas",
        "B": "Organizmga ko'proq kislorod va energiya kerak bo'ladi",
        "C": "Yurak dam oladi",
        "D": "Qon bosimi pasayadi"
      },
      "answer": "B",
      "difficulty": "medium"
    },
    {
      "question": "Teri organizmni qanday himoya qiladi?",
      "options": {
        "A": "Ferment ishlab chiqaradi",
        "B": "Fizik, kimyoviy va mexanik ta'sirlardan himoya qiluvchi to'siq vazifasini bajaradi",
        "C": "Kislorod yutadi",
        "D": "Karbonat angidrid chiqaradi"
      },
      "answer": "B",
      "difficulty": "medium"
    },
    {
      "question": "Qaysi kasalliklar viruslar tomonidan qo'zg'atiladi?",
      "options": {
        "A": "Vabo, ichterlama",
        "B": "Zamburug' kasalliklari",
        "C": "COVID-19, gripp, suvchechak",
        "D": "Bezgaк"
      },
      "answer": "C",
      "difficulty": "medium"
    },
    {
      "question": "Epidemiya nima?",
      "options": {
        "A": "Bir kishining kasallanishi",
        "B": "Kasallik aholi orasida tez tarqalishi",
        "C": "Yangi kasallik kashf etilishi",
        "D": "Dori topilishi"
      },
      "answer": "B",
      "difficulty": "medium"
    },
    {
      "question": "Quyosh oziq zanjirida qanday rol o'ynaydi?",
      "options": {
        "A": "Konsument",
        "B": "Asosiy energiya manbayi",
        "C": "Parazit",
        "D": "Tashuvchi"
      },
      "answer": "B",
      "difficulty": "medium"
    },
    {
      "question": "Pestitsid nima va u oziq zanjiriga qanday ta'sir qiladi?",
      "options": {
        "A": "O'g'it; tuproqni boyitadi",
        "B": "Kimyoviy zararkunanda dori; oziq zanjiriga tushib, barcha tirik organizmlarni zararlashi mumkin",
        "C": "Foydali bakteriya; o'simliklarga yordam beradi",
        "D": "Suv tozalagich"
      },
      "answer": "B",
      "difficulty": "medium"
    },
    {
      "question": "Oziq zanjiridagi strelkalar nima yo'nalishini ifodalaydi?",
      "options": {
        "A": "Organizmlarning harakatlanish yo'nalishini",
        "B": "Energiya oqimi yo'nalishini",
        "C": "Suvning oqish yo'nalishini",
        "D": "Quyosh nurining yo'nalishini"
      },
      "answer": "B",
      "difficulty": "medium"
    },
    {
      "question": "Kumush necha darajada eriydi?",
      "options": {
        "A": "0 °C",
        "B": "100 °C",
        "C": "962 °C",
        "D": "1665 °C"
      },
      "answer": "C",
      "difficulty": "medium"
    },
    {
      "question": "Uglevod, oqsil, yog', vitamin, minerallar — bularning hammasi nima?",
      "options": {
        "A": "Hazm shiralari",
        "B": "Oziq moddalar",
        "C": "Fermentlar",
        "D": "Vitaminlar"
      },
      "answer": "B",
      "difficulty": "hard"
    },
    {
      "question": "Qon karbonat angidridni qaysi yo'nalishda tashiydi?",
      "options": {
        "A": "O'pkalardan tananing barcha organlariga",
        "B": "Tananing barcha organlaridan o'pkalarga",
        "C": "Yurakdan oshqozonga",
        "D": "Ingichka ichakdan o'pkalarga"
      },
      "answer": "B",
      "difficulty": "hard"
    },
    {
      "question": "Nafas olish va chiqarish jarayonida diafragma va qovurg'alarning harakati qanday?",
      "options": {
        "A": "Olishda: diafragma pastga, qovurg'alar yuqoriga; Chiqarishda: teskari",
        "B": "Olishda: diafragma yuqoriga, qovurg'alar pastga; Chiqarishda: teskari",
        "C": "Ikkalasida ham bir xil yo'nalishda",
        "D": "Diafragma ishtirok etmaydi"
      },
      "answer": "A",
      "difficulty": "hard"
    },
    {
      "question": "Oshqozon patogenlardan himoya qilishda qanday rol o'ynaydi?",
      "options": {
        "A": "Antikorlar ishlab chiqaradi",
        "B": "Patogenlarni nobud qiluvchi xlorid kislota ishlab chiqaradi",
        "C": "Patogenlarni o'ziga yutadi",
        "D": "Patogenlarni o'pkaga yuboradi"
      },
      "answer": "B",
      "difficulty": "hard"
    },
    {
      "question": "Tashuvchi organizmga misol keltiring:",
      "options": {
        "A": "Bemor odam",
        "B": "Bezgak chivini — patogenni bir xo'jayindan ikkinchisiga o'tkazadi",
        "C": "Foydali bakteriya",
        "D": "Virus"
      },
      "answer": "B",
      "difficulty": "hard"
    },
    {
      "question": "Agar oziq zanjiridagi birlamchi konsumentlar qirilib ketsa, nima bo'ladi?",
      "options": {
        "A": "Produtsent ko'payadi, ikkilamchi konsumentlar ozayadi",
        "B": "Hamma o'zgarishsiz qoladi",
        "C": "Faqat produtsent ta'sirlanadi",
        "D": "Faqat yirtqichlar ta'sirlanadi"
      },
      "answer": "A",
      "difficulty": "hard"
    },
    {
      "question": "Simob oziq zanjirining qaysi bo'g'inida ko'proq to'planadi?",
      "options": {
        "A": "Produtsentda",
        "B": "Birlamchi konsumentda",
        "C": "Oziq zanjirining oxirgi bo'g'inida (masalan, tunes baliqda)",
        "D": "Ikkinchi bo'g'inda"
      },
      "answer": "C",
      "difficulty": "hard"
    },
    {
      "question": "Modda erish haroratiga qarab nima aniqlash mumkin?",
      "options": {
        "A": "Faqat rangini",
        "B": "Moddaning turini (xususiyati)",
        "C": "Faqat og'irligini",
        "D": "Elektr o'tkazuvchanligini"
      },
      "answer": "B",
      "difficulty": "hard"
    },
    {
      "question": "Elektr dazmolda metall asos va plastik tutqich ishlatilishining sababi nima?",
      "options": {
        "A": "Ikkalasi ham izolyator",
        "B": "Metall — issiqlik va elektr o'tkazgich (qizdirish uchun); plastik — izolyator (xavfsiz ushlab turish uchun)",
        "C": "Ikkalasi ham o'tkazgich",
        "D": "Metall izolyator, plastik o'tkazgich"
      },
      "answer": "B",
      "difficulty": "hard"
    },
    {
      "question": "Massasi 2 kg jismning Yerdagi og'irligi (taxminan)?",
      "options": {
        "A": "2 N",
        "B": "19.6 N",
        "C": "20 kg",
        "D": "9.8 N"
      },
      "answer": "B",
      "difficulty": "hard"
    }
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

# ═══════════════════════════════════════════════
# 4. GOOGLE SHEETS FUNKSIYALARI
# ═══════════════════════════════════════════════

# Barcha o'quvchilarni xotirada tezkor saqlash uchun lug'at
USERS_CACHE = {}

def load_users_to_cache():
    global USERS_CACHE
    USERS_CACHE.clear()
    try:
        ws = get_sheet()
        rows = ws.get_all_values()
        for row in rows[1:]:  # 1-qator sarlavha
            if row[0]:
                user_id = int(row[0])
                USERS_CACHE[user_id] = {
                    "id": user_id,
                    "telegram_id": int(row[1]) if row[1] else None,
                    "full_name": row[2],
                    "school": row[3],
                    "grade": row[4],
                    "phone": row[5],
                    "score": int(row[6]) if row[6] else 0,
                    "test_started": int(row[7]) if row[7] else 0,
                }
        print(f"✅ Baza yuklandi: {len(USERS_CACHE)} ta o'quvchi tayyor.")
    except Exception as e:
        print(f"❌ Google Sheets yuklashda xato: {e}")

def add_user(telegram_id, full_name, school, grade, phone):
    # Avval keshdan tekshiramiz
    for user in USERS_CACHE.values():
        if user["telegram_id"] == telegram_id:
            return None
    try:
        ws = get_sheet()
        rows = ws.get_all_values()
        new_id = len(rows)  # sarlavha + mavjud qatorlar
        ws.append_row([new_id, telegram_id, full_name, school, grade, phone, 0, 0])
        USERS_CACHE[new_id] = {
            "id": new_id, "telegram_id": telegram_id,
            "full_name": full_name, "school": school,
            "grade": grade, "phone": phone,
            "score": 0, "test_started": 0
        }
        return new_id
    except Exception as e:
        print(f"Foydalanuvchi qo'shishda xato: {e}")
        return None

def get_user_by_id(user_id):
    return USERS_CACHE.get(user_id)

def get_user_by_telegram_id(telegram_id):
    for user in USERS_CACHE.values():
        if user["telegram_id"] == telegram_id:
            return user
    return None

def update_user(user_id, score=None, test_started=None):
    if user_id in USERS_CACHE:
        if score is not None:
            USERS_CACHE[user_id]["score"] = score
        if test_started is not None:
            USERS_CACHE[user_id]["test_started"] = test_started
    try:
        ws = get_sheet()
        rows = ws.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if row[0] and int(row[0]) == user_id:
                if score is not None:
                    ws.update_cell(i, 7, score)
                if test_started is not None:
                    ws.update_cell(i, 8, test_started)
                break
    except Exception as e:
        print(f"Yangilashda xato: {e}")

def get_all_telegram_ids():
    return [user["telegram_id"] for user in USERS_CACHE.values() if user["telegram_id"]]

def get_users_count():
    return len(USERS_CACHE)

load_users_to_cache()

bot = Bot(token='8678044800:AAF9GGeTK1qS1dJMQayrq-J3qtKMhf39wdA')

dp = Dispatcher()

# ═══════════════════════════════════════════════
# 5. YORDAMCHI FUNKSIYALAR
# ═══════════════════════════════════════════════
def make_progress_bar(current: int, total: int, length: int = 10) -> str:
    filled = round(current / total * length) if total else 0
    return "█" * filled + "░" * (length - filled) + f"  {current}/{total}"

def make_timer_str(elapsed: int, total: int = TEST_DURATION_SECONDS) -> str:
    remaining = max(0, total - elapsed)
    return f"⏱ {remaining // 60:02d}:{remaining % 60:02d} qoldi"

def build_info_message(grade, q_index, total, difficulty, elapsed):
    diff  = DIFFICULTY_LABEL.get(difficulty, "")
    prog  = make_progress_bar(q_index, total)
    timer = make_timer_str(elapsed)
    return (
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📚 {grade}   |   {q_index}-savol\n"
        f"📊 {prog}\n"
        f"{timer}   {diff}\n"
        f"━━━━━━━━━━━━━━━━━━"
    )

def build_answer_keyboard(options: dict) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            text=f"{key}",
            callback_data=f"ans_{key}"
        )]
        for key in options.keys()
    ]
    # 2 ta tugmani bir qatorda joylashtirish: A B | C D
    paired = []
    keys = list(options.keys())
    for i in range(0, len(keys), 2):
        row = [InlineKeyboardButton(text=keys[i], callback_data=f"ans_{keys[i]}")]
        if i + 1 < len(keys):
            row.append(InlineKeyboardButton(text=keys[i+1], callback_data=f"ans_{keys[i+1]}"))
        paired.append(row)
    return InlineKeyboardMarkup(inline_keyboard=paired)

def get_motivation():
    return random.choice(MOTIVATIONAL_MESSAGES)

# ═══════════════════════════════════════════════
# 6. SAVOL YUBORISH
# ═══════════════════════════════════════════════
async def send_question(chat_id: int, state: FSMContext):
    data     = await state.get_data()
    grade    = data["grade"]
    q_list   = data["questions"]
    index    = data["current"]
    start_ts = data["start_ts"]

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

    # 1) INFO PANEL — alohida xabar
    info_text = build_info_message(grade, index + 1, total, q.get("difficulty", "easy"), elapsed)
    info_msg  = await bot.send_message(chat_id=chat_id, text=info_text)

    # 2) SAVOL + VARIANTLAR MATNDA
    options_text = "\n".join([f"{key}) {val}" for key, val in q["options"].items()])
    full_question = f"{q['question']}\n\n{options_text}"

    kb        = build_answer_keyboard(q["options"])
    image_url = q.get("image")

    if image_url:
        q_msg = await bot.send_photo(
            chat_id      = chat_id,
            photo        = image_url,
            caption      = full_question,
            reply_markup = kb,
        )
    else:
        q_msg = await bot.send_message(
            chat_id      = chat_id,
            text         = full_question,
            reply_markup = kb,
        )

    await state.update_data(
        last_info_msg_id = info_msg.message_id,
        last_q_msg_id    = q_msg.message_id,
    )

# ═══════════════════════════════════════════════
# 7. TEST TUGASH
# ═══════════════════════════════════════════════
async def finish_test(chat_id: int, state: FSMContext):
    data    = await state.get_data()
    score   = data.get("score", 0)
    total   = len(data["questions"])
    user_id = data["db_user_id"]
    name    = data.get("user_name", "O'quvchi")

    update_user(user_id, score=score)

    percent = round(score / total * 100) if total else 0
    if percent == 100:
        medal = "🥇 Mukammal!"
    elif percent >= 80:
        medal = "🥈 A'lo!"
    elif percent >= 60:
        medal = "🥉 Yaxshi!"
    elif percent >= 40:
        medal = "📖 Qoniqarli"
    else:
        medal = "💡 Ko'proq mashq qiling!"

    motivation = get_motivation()

    result_text = (
        f"🏁 Test yakunlandi!\n\n"
        f"👤 {name}\n"
        f"✅ To'g'ri javoblar: {score}/{total}  ({percent}%)\n"
        f"🏅 Natija: {medal}\n\n"
        f"{motivation}\n\n"
        f"📢 Yaxshi natija uchun ILM NURI o'quv markazida "
        f"jonkuyar ustozlar orqali ilm oling!\n\n"
        f"\bYakuniy natijalarni bilish uchun rasmiy kanalimizga qo'shiling\\b 👇"
    )

    await bot.send_message(
        chat_id,
        result_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📣 Kanalga o'tish", url=CHANNEL_LINK)]
        ]),
    )
    await state.clear()

# ═══════════════════════════════════════════════
# 8. TIMEOUT KUZATUVCHI
# ═══════════════════════════════════════════════
async def timeout_watcher(chat_id: int, state: FSMContext):
    await asyncio.sleep(TEST_DURATION_SECONDS)
    current_state = await state.get_state()
    if current_state == TestProcess.answering.state:
        await bot.send_message(chat_id, "⏰ Vaqt tugadi! Test yakunlanmoqda...")
        await finish_test(chat_id, state)

# ═══════════════════════════════════════════════
# 9. TEST BOSHLASH CALLBACK
# ═══════════════════════════════════════════════
@dp.callback_query(F.data.startswith("start_"))
async def start_test(callback: types.CallbackQuery, state: FSMContext):
    p_id = int(callback.data.split("_")[1])

    user = get_user_by_id(p_id)

    if not user:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return

    # Test faqat bir marta
    if user["test_started"]:
        await callback.answer(
            "Siz testni allaqachon ishlagansiz! Qayta ishlash mumkin emas.",
            show_alert=True
        )
        return

    grade  = user["grade"]
    q_list = TESTS.get(grade, [])

    if not q_list:
        await callback.message.answer(
            f"{grade} uchun savollar hali qo'shilmagan.")
        await callback.answer()
        return

    # Test boshlanganini Excel ga yozish
    update_user(p_id, test_started=1)

    await state.set_state(TestProcess.answering)
    await state.update_data(
        grade            = grade,
        questions        = q_list,
        current          = 0,
        score            = 0,
        streak           = 0,
        start_ts         = time.time(),
        db_user_id       = p_id,
        user_name        = user["full_name"],
        last_info_msg_id = None,
        last_q_msg_id    = None,
    )

    await callback.message.answer(
        f"🚀 {grade} testi boshlanmoqda!\n"
        f"📝 Savollar soni: {len(q_list)}\n"
        f"⏱ Vaqt: 45 daqiqa\n\n"
        f"Omad! 🍀   @IlmNuri_Markazi"
    )
    await callback.answer()

    asyncio.create_task(timeout_watcher(callback.from_user.id, state))
    await send_question(callback.from_user.id, state)

# ═══════════════════════════════════════════════
# 10. JAVOB TEKSHIRISH
# ═══════════════════════════════════════════════
@dp.callback_query(F.data.startswith("ans_"), TestProcess.answering)
async def check_answer(callback: types.CallbackQuery, state: FSMContext):
    chosen = callback.data.split("_")[1]
    data   = await state.get_data()
    index  = data["current"]
    q      = data["questions"][index]

    score  = data.get("score",  0)
    streak = data.get("streak", 0)

    if chosen == q["answer"]:
        streak += 1
        score  += 1
        toast = "✅ To'g'ri!" + (" 🔥" if streak >= 2 else "")
    else:
        streak = 0
        cl     = q["answer"]
        toast  = f"Noto'g'ri! To'g'ri: {cl}) {q['options'][cl]}"

    await state.update_data(score=score, streak=streak, current=index + 1)

    try:
        await callback.answer(toast, show_alert=False)
    except Exception:
        pass

    await send_question(callback.from_user.id, state)

# ═══════════════════════════════════════════════
# 11. RO'YXATDAN O'TISH
# ═══════════════════════════════════════════════
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    existing = get_user_by_telegram_id(message.from_user.id)

    if existing:
        await message.answer(
            f"Siz allaqachon ro'yxatdan o'tgansiz, {existing['full_name']}!")
        return

    await message.answer(
        "Assalomu alaykum! 🌟\n\n"
        "🏆 Ilm Nuri: Kelajak Olimpiadasi rasmiy botiga xush kelibsiz!\n\n"
        "Prezident, Al-Xorazmiy va Ibn Sino maktablarida o'qishni orzu qilasizmi? "
        "O'z bilimingizni sinab ko'ring va super sovrinlarni yutib oling!\n\n"
        "👇 Ism va Familiyangizni kiriting:\n"
        "Masalan: Alisherov Vali"
    )
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
            [KeyboardButton(text="1-sinf"), KeyboardButton(text="2-sinf"),
             KeyboardButton(text="3-sinf")],
            [KeyboardButton(text="4-sinf"), KeyboardButton(text="5-sinf"),
             KeyboardButton(text="6-sinf")],
        ],
        resize_keyboard=True,
    )
    await message.answer("📚 Sinfingizni tanlang:\nPastdagi tugmalar orqali 👇👇👇",
                         reply_markup=keyboard)
    await state.set_state(Registration.grade)

@dp.message(Registration.grade)
async def process_grade(message: types.Message, state: FSMContext):
    # Orqaga qaytish tugmasi bosilsa
    if message.text == "⬅️ Orqaga":
        await message.answer(
            "🏫 Maktab raqamini qaytadan yozing:\nFaqat raqam. Masalan: 5",
            reply_markup=types.ReplyKeyboardRemove()
        )
        await state.set_state(Registration.school)
        return

    if message.text not in TESTS:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="1-sinf"), KeyboardButton(text="2-sinf"),
                 KeyboardButton(text="3-sinf")],
                [KeyboardButton(text="4-sinf"), KeyboardButton(text="5-sinf"),
                 KeyboardButton(text="6-sinf")],
                [KeyboardButton(text="⬅️ Orqaga")],
            ],
            resize_keyboard=True,
        )
        await message.answer(
            "❌ Noto'g'ri! Iltimos, quyidagi tugmalardan birini tanlang:",
            reply_markup=keyboard
        )
        return

    await state.update_data(grade=message.text)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📲 Kontakt yuborish", request_contact=True)],
            [KeyboardButton(text="⬅️ Orqaga")],
        ],
        resize_keyboard=True,
    )
    await message.answer(
        "📞 Telefon raqamingizni yuboring:\nSiz g'olib bo'lganda bog'lanish uchun",
        reply_markup=keyboard)
    await state.set_state(Registration.phone)

@dp.message(Registration.phone)
async def process_phone(message: types.Message, state: FSMContext):
    # Orqaga qaytish
    if message.text == "⬅️ Orqaga":
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="1-sinf"), KeyboardButton(text="2-sinf"),
                 KeyboardButton(text="3-sinf")],
                [KeyboardButton(text="4-sinf"), KeyboardButton(text="5-sinf"),
                 KeyboardButton(text="6-sinf")],
                [KeyboardButton(text="⬅️ Orqaga")],
            ],
            resize_keyboard=True,
        )
        await message.answer("📚 Sinfingizni qaytadan tanlang:",
                             reply_markup=keyboard)
        await state.set_state(Registration.grade)
        return

    phone = message.contact.phone_number if message.contact else message.text
    data  = await state.get_data()

    p_id = add_user(
        message.from_user.id,
        data["full_name"],
        data["school"],
        data["grade"],
        phone
    )

    if p_id is None:
        await message.answer("Siz allaqachon ro'yxatdan o'tgansiz!",
                             reply_markup=types.ReplyKeyboardRemove())
        await state.clear()
        return

    await message.answer("✅ Ro'yxatdan o'tdingiz!",
                         reply_markup=types.ReplyKeyboardRemove())
    await message.answer(
        "Testni boshlash uchun quyidagi tugmani bosing:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Testni boshlash",
                                  callback_data=f"start_{p_id}")]
        ]),
    )
    await state.clear()

# ═══════════════════════════════════════════════
# 12. ADMIN BO'LIMI
# ═══════════════════════════════════════════════
@dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def admin_panel(message: types.Message):
    await message.answer(
        "🛠 Admin panelga xush kelibsiz!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Xabar yuborish", callback_data="send_ad")],
            [InlineKeyboardButton(text="📊 Statistika",     callback_data="admin_stats")],
        ]),
    )

@dp.callback_query(F.data == "admin_stats", F.from_user.id == ADMIN_ID)
async def admin_stats(callback: types.CallbackQuery):
    count = get_users_count()
    await callback.answer(f"Jami ishtirokchilar: {count} ta", show_alert=True)

@dp.callback_query(F.data == "send_ad", F.from_user.id == ADMIN_ID)
async def start_ad(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "📝 Xabar matnini yoki rasm/video yuboring.\n"
        "Bekor qilish: /cancel"
    )
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
    await message.answer("🚀 Yuborilmoqda...")
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
# 13. MAIN
# ═══════════════════════════════════════════════
async def main():
    logging.basicConfig(level=logging.INFO)

    # MUHIM: Bot ishlashidan oldin bazani xotiraga yuklash!
    load_users_to_cache()

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
