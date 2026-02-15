import random
import logging
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from faker import Faker

# --- কনফিগারেশন ---
API_TOKEN = '8527092463:AAF0Kj3grq53tUJn10YmjyDIo3Z7iOexkYg'
ADMIN_ID = 8197284774
PHOTO_URL = 'https://res.cloudinary.com/dv6ugwzk8/image/upload/v1758564178/jnzm7tnz7qyab3jionie.jpg'

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
fake = Faker()

# --- ডাটাবেস সেটআপ ---
conn = sqlite3.connect('database.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
conn.commit()

# ডিফল্ট ডাটা সেভ করা (যদি আগে থেকে না থাকে)
cursor.execute('INSERT OR IGNORE INTO settings VALUES (?, ?)', ('bin', '415464'))
cursor.execute('INSERT OR IGNORE INTO settings VALUES (?, ?)', ('country', 'USA'))
conn.commit()

class AdminStates(StatesGroup):
    waiting_for_bin = State()
    waiting_for_country = State()
    waiting_for_broadcast = State()

# --- ফাংশনস ---
def get_db_val(key):
    cursor.execute('SELECT value FROM settings WHERE key=?', (key,))
    return cursor.fetchone()[0]

def set_db_val(key, val):
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

# --- হ্যান্ডলারস ---

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    cursor.execute('INSERT OR IGNORE INTO users VALUES (?)', (message.from_user.id,))
    conn.commit()
    await message.answer("বট সক্রিয়! ব্যবহার শুরু করতে /gen টাইপ করুন।")

@dp.callback_query(F.data == "admin_home")
@dp.message(Command("admin"))
async def admin_panel(message: types.Message | types.CallbackQuery, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await state.clear()
    cursor.execute('SELECT COUNT(*) FROM users')
    total = cursor.fetchone()[0]
    
    text = (f"🛠 **ADMIN PANEL**\n\n📍 বিন: `{get_db_val('bin')}`\n📍 দেশ: {get_db_val('country')}\n👥 ইউজার: {total}")
    kb = [[types.InlineKeyboardButton(text="📥 সেভ বিন", callback_data="set_bin"),
           types.InlineKeyboardButton(text="🌍 সেভ দেশ", callback_data="set_country")],
          [types.InlineKeyboardButton(text="📢 ব্রডকাস্ট", callback_data="broadcast_msg")]]
    
    if isinstance(message, types.Message):
        await message.answer(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")
    else:
        await message.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

@dp.callback_query(F.data == "set_bin")
async def ask_bin(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("নতুন বিনটি পাঠান:", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ ফিরে যান", callback_data="admin_home")]]))
    await state.set_state(AdminStates.waiting_for_bin)

@dp.message(AdminStates.waiting_for_bin)
async def save_bin(message: types.Message, state: FSMContext):
    new_bin = "".join(filter(str.isdigit, message.text))[:6]
    set_db_val('bin', new_bin)
    await message.answer(f"✅ বিন `{new_bin}` সেভ হয়েছে।")
    await state.clear()

@dp.callback_query(F.data == "set_country")
async def ask_country(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("দেশের নাম পাঠান:", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ ফিরে যান", callback_data="admin_home")]]))
    await state.set_state(AdminStates.waiting_for_country)

@dp.message(AdminStates.waiting_for_country)
async def save_country(message: types.Message, state: FSMContext):
    set_db_val('country', message.text)
    await message.answer(f"✅ দেশ `{message.text}` সেভ হয়েছে।")
    await state.clear()

@dp.callback_query(F.data == "broadcast_msg")
async def ask_broadcast(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("মেসেজ পাঠান বা ফরোয়ার্ড করুন:", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ ফিরে যান", callback_data="admin_home")]]))
    await state.set_state(AdminStates.waiting_for_broadcast)

@dp.message(AdminStates.waiting_for_broadcast)
async def do_broadcast(message: types.Message, state: FSMContext):
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    count = 0
    for user in users:
        try:
            await message.copy_to(chat_id=user[0])
            count += 1
        except: pass
    await message.answer(f"✅ {count} জনকে পাঠানো হয়েছে।")
    await state.clear()

@dp.message(Command("gen"))
async def gen_handler(message: types.Message):
    cursor.execute('INSERT OR IGNORE INTO users VALUES (?)', (message.from_user.id,))
    conn.commit()
    
    args = message.text.split()
    bin_num, month, year = get_db_val('bin'), str(random.randint(1,12)).zfill(2), str(random.randint(2026, 2031))
    
    if len(args) > 1:
        parts = args[1].split('|')
        bin_num = "".join(filter(str.isdigit, parts[0]))[:6]
        if len(parts) > 1: month = parts[1].zfill(2)
        if len(parts) > 2: year = parts[2]

    is_group = message.chat.type in ["group", "supergroup"]
    if is_group:
        text = "✨ 〘 𝗖𝗛𝗘𝗖𝗞 𝗔𝗡𝗗 𝗦𝗔𝗩𝗘 𝗬𝗢𝗨𝗥 𝗣𝗥𝗘𝗠𝗜𝗨𝗠 𝗠𝗔𝗦𝗧𝗘𝗥𝗖𝗔𝗥𝗗 〙 ✨\n\n💳 **𝗖𝗔𝗥𝗗 𝗟𝗜𝗦𝗧:**\n`"
        for _ in range(10): text += f"{generate_card(bin_num)}|{month}|{year}|{random.randint(100,999)}\n"
        text += "`"
    else:
        text = "✨ 𝗖𝗛𝗘𝗖𝗞 𝗔𝗡𝗗 𝗦𝗔𝗩𝗘 𝗬𝗢𝗨𝗥 𝗣𝗥𝗘𝗠𝗜𝗨𝗠 𝗠𝗔𝗦𝗧𝗘𝗥𝗖𝗔𝗥𝗗 ✨\n\n"
        for _ in range(10):
            f = Faker()
            text += (f"💳 **𝗖𝗔𝗥𝗗 𝗡𝗨𝗠𝗕𝗘𝗥 :** `{generate_card(bin_num)}`\n\n📅 **𝗠𝗠/𝗬𝗬 :** `{month}/{year}`\n\n🔒 **𝗦𝗘𝗖𝗨𝗥𝗜𝗧𝗬 𝗖𝗢𝗗𝗘 / 𝗖𝗩𝗩 :** `{random.randint(100,999)}`\n\n"
                     f"🌍 **𝗖𝗢𝗨𝗡𝗧𝗥𝗬 :** {get_db_val('country')}\n\n👨‍💻 **NAME :** {f.name()}\n\n🏠 **𝗔𝗗𝗗𝗥𝗘𝗦𝗦 𝗟𝗜𝗡𝗘 𝟭 :** {f.street_address()}\n\n🏙️ **𝗧𝗢𝗪𝗡 / 𝗖𝗜𝗧𝗬 :** {f.city()}\n\n📮 **𝗣𝗢𝗦𝗧𝗖𝗢𝗗𝗘 :** {f.postcode()}\n\n📍 **𝗦𝗧𝗔𝗧𝗘 :** {f.state()}\n━━━━━━━━━━━━━━━━━━━━\n\n")
    
    await message.answer_photo(photo=PHOTO_URL, caption=text, parse_mode="Markdown")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
