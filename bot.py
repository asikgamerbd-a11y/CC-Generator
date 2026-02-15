import random
import logging
import asyncio
import os
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from faker import Faker
from aiohttp import web

# --- কনফিগারেশন ---
API_TOKEN = '8527092463:AAF0Kj3grq53tUJn10YmjyDIo3Z7iOexkYg'
ADMIN_ID = 8197284774
PHOTO_URL = 'https://res.cloudinary.com/dv6ugwzk8/image/upload/v1758564178/jnzm7tnz7qyab3jionie.jpg'

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- ডাটাবেস সেটআপ ---
conn = sqlite3.connect('database.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
conn.commit()

cursor.execute('INSERT OR IGNORE INTO settings VALUES (?, ?)', ('bin', '415464'))
cursor.execute('INSERT OR IGNORE INTO settings VALUES (?, ?)', ('country', 'USA'))
conn.commit()

class AdminStates(StatesGroup):
    waiting_for_bin = State()
    waiting_for_country = State()
    waiting_for_broadcast = State()
    waiting_for_info_country = State()

# --- হেল্পার ফাংশন ---
def get_db(key):
    cursor.execute('SELECT value FROM settings WHERE key=?', (key,))
    res = cursor.fetchone()
    return res[0] if res else ""

def set_db(key, val):
    cursor.execute('UPDATE settings SET value=? WHERE key=?', (val, key))
    conn.commit()

def generate_card(bin_num):
    card = str(bin_num)
    while len(card) < 15: card += str(random.randint(0, 9))
    sum_val = 0
    for i, digit in enumerate(reversed(card)):
        n = int(digit)
        if i % 2 == 0:
            n *= 2
            if n > 9: n -= 9
        sum_val += n
    card += str((10 - (sum_val % 10)) % 10)
    return card

def get_fake_info(country_code="US"):
    try: f = Faker(country_code)
    except: f = Faker()
    return {
        "name": f.name(),
        "address": f.street_address(),
        "city": f.city(),
        "postcode": f.postcode(),
        "state": f.state()
    }

# --- স্টার্ট মেনু ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    cursor.execute('INSERT OR IGNORE INTO users VALUES (?)', (message.from_user.id,))
    conn.commit()
    kb = [[types.InlineKeyboardButton(text="🌍 Card Country Info", callback_data="get_info")]]
    await message.answer("বটটি সক্রিয় হয়েছে!\n\nবিন জেনারেট করতে /gen ব্যবহার করুন।", 
                         reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))

# --- অ্যাডমিন প্যানেল ---
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    kb = [
        [types.InlineKeyboardButton(text="📥 সেভ বিন", callback_data="set_bin"),
         types.InlineKeyboardButton(text="🌍 সেভ দেশ", callback_data="set_country")],
        [types.InlineKeyboardButton(text="📢 ব্রডকাস্ট", callback_data="bc")]
    ]
    await message.answer(f"🛠 **Admin Panel**\n\nBIN: `{get_db('bin')}`\nCountry: {get_db('country')}", 
                         reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "set_bin")
async def ask_bin(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.answer("নতুন বিনটি পাঠান:")
    await state.set_state(AdminStates.waiting_for_bin)

@dp.message(AdminStates.waiting_for_bin)
async def save_bin(message: types.Message, state: FSMContext):
    set_db('bin', "".join(filter(str.isdigit, message.text))[:6])
    await message.answer("✅ বিন সেভ হয়েছে।")
    await state.clear()

@dp.callback_query(F.data == "set_country")
async def ask_country(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.answer("দেশের নাম লিখুন (যেমন: USA):")
    await state.set_state(AdminStates.waiting_for_country)

@dp.message(AdminStates.waiting_for_country)
async def save_country(message: types.Message, state: FSMContext):
    set_db('country', message.text)
    await message.answer("✅ দেশ সেভ হয়েছে।")
    await state.clear()

# --- Country Info জেনারেটর ---
@dp.callback_query(F.data == "get_info")
async def ask_info_country(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.answer("কোন দেশের তথ্য চান? নাম লিখুন (যেমন: UK, USA, BD):")
    await state.set_state(AdminStates.waiting_for_info_country)

@dp.message(AdminStates.waiting_for_info_country)
async def send_country_info(message: types.Message, state: FSMContext):
    info = get_fake_info()
    text = (f"🌍 **𝗖𝗢𝗨𝗡𝗧𝗥𝗬 :** {message.text}\n\n"
            f"👨‍💻 **NAME :** {info['name']}\n\n"
            f"🏠 **𝗔𝗗𝗗𝗥𝗘𝗦𝗦 𝗟𝗜𝗡𝗘 𝟭 :** {info['address']}\n\n"
            f"🏙️ **𝗧𝗢𝗪𝗡 / 𝗖𝗜𝗧𝗬 :** {info['city']}\n\n"
            f"📮 **𝗣𝗢𝗦𝗧𝗖𝗢𝗗𝗘 :** {info['postcode']}\n\n"
            f"📍 **𝗦𝗧𝗔𝗧𝗘 :** {info['state']}")
    await message.answer(text)
    await state.clear()

# --- জেনারেটর লজিক ---
@dp.message(Command("gen"))
async def gen_handler(message: types.Message):
    args = message.text.split()
    bin_num, month, year = get_db('bin'), str(random.randint(1,12)).zfill(2), str(random.randint(2026, 2031))
    
    # ইউজার যদি নিজে বিন দেয়
    custom = False
    if len(args) > 1:
        custom = True
        parts = args[1].split('|')
        bin_num = "".join(filter(str.isdigit, parts[0]))[:12]
        if len(parts) > 1: month = parts[1].zfill(2)
        if len(parts) > 2: year = parts[2]

    is_group = message.chat.type in ["group", "supergroup"]
    
    if is_group or custom:
        text = "✨ 〘 𝗖𝗛𝗘𝗖𝗞 𝗔𝗡𝗗 𝗦𝗔𝗩𝗘 𝗬𝗢𝗨𝗥 𝗣𝗥𝗘𝗠𝗜𝗨𝗠 〙 ✨\n\n`"
        for _ in range(10):
            text += f"{generate_card(bin_num)}|{month}|{year}|{random.randint(100,999)}\n"
        text += "`"
    else:
        info = get_fake_info()
        text = "✨ 𝗖𝗛𝗘𝗖𝗞 𝗔𝗡𝗗 𝗦𝗔𝗩𝗘 𝗬𝗢𝗨𝗥 𝗣𝗥𝗘𝗠𝗜𝗨𝗠 𝗠𝗔𝗦𝗧𝗘𝗥𝗖𝗔𝗥𝗗 ✨\n\n"
        text += (f"💳 **𝗖𝗔𝗥𝗗 𝗡𝗨𝗠𝗕𝗘𝗥 :** `{generate_card(bin_num)}`\n\n"
                 f"📅 **𝗠𝗠/𝗬𝗬 :** `{month}/{year}`\n\n"
                 f"🔒 **𝗦𝗘𝗖𝗨𝗥𝗜𝗧𝗬 𝗖𝗢𝗗𝗘 / 𝗖𝗩𝗩 :** `{random.randint(100,999)}`\n\n"
                 f"🌍 **𝗖𝗢𝗨𝗡𝗧𝗥𝗬 :** {get_db('country')}\n\n"
                 f"👨‍💻 **NAME :** {info['name']}\n\n"
                 f"🏠 **𝗔𝗗𝗗𝗥𝗘𝗦𝗦 𝗟𝗜𝗡𝗘 𝟭 :** {info['address']}\n\n"
                 f"🏙️ **𝗧𝗢𝗪𝗡 / 𝗖𝗜𝗧𝗬 :** {info['city']}\n\n"
                 f"📮 **𝗣𝗢𝗦𝗧𝗖𝗢𝗗𝗘 :** {info['postcode']}\n\n"
                 f"📍 **𝗦𝗧𝗔𝗧𝗘 :** {info['state']}")
    
    try:
        await message.answer_photo(photo=PHOTO_URL, caption=text, parse_mode="Markdown")
    except:
        await message.answer(text, parse_mode="Markdown")

# --- Web Server (Keep Alive) ---
async def handle(request): return web.Response(text="Bot Alive")
async def main():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.getenv("PORT", 10000))).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
