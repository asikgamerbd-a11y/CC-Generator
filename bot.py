import random, asyncio, sqlite3, os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from faker import Faker

# --- কনফিগারেশন ---
API_TOKEN = '8527092463:AAF0Kj3grq53tUJn10YmjyDIo3Z7iOexkYg'
ADMIN_ID = 8197284774
PHOTO_URL = 'https://res.cloudinary.com/dv6ugwzk8/image/upload/v1758564178/jnzm7tnz7qyab3jionie.jpg'

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- ডাটাবেস ম্যানেজমেন্ট ---
conn = sqlite3.connect('premium_bot.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
cursor.execute('CREATE TABLE IF NOT EXISTS bins (bin TEXT PRIMARY KEY, country TEXT, service TEXT)')
conn.commit()

class BotStates(StatesGroup):
    add_bin_num = State()
    add_bin_service = State()
    add_bin_country = State()
    broadcast = State()
    user_bin_input = State()
    fake_info_country = State()
    fake_info_gender = State()

# --- প্রিমিয়াম কিবোর্ড ডিজাইন ---
def main_menu(user_id):
    kb = [
        [types.KeyboardButton(text="💳 𝗖𝗥𝗘𝗔𝗧𝗘 𝗖𝗔𝗥𝗗"), types.KeyboardButton(text="🌍 𝗙𝗔𝗞𝗘 𝗜𝗡𝗙𝗢")],
        [types.KeyboardButton(text="🆘 𝗦𝗨𝗣𝗣𝗢𝗥𝗧")]
    ]
    if user_id == ADMIN_ID:
        kb.append([types.KeyboardButton(text="🛠 𝗔𝗗𝗠𝗜𝗡 𝗖𝗢𝗡𝗧𝗥𝗢𝗟")])
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def card_menu():
    kb = [
        [types.KeyboardButton(text="💎 𝗖𝗛𝗢𝗜𝗖𝗘 𝗔𝗗𝗠𝗜𝗡 𝗕𝗜𝗡")],
        [types.KeyboardButton(text="⌨️ 𝗘𝗡𝗧𝗘𝗥 𝗬𝗢𝗨𝗥 𝗕𝗜𝗡")],
        [types.KeyboardButton(text="🔙 𝗕𝗔𝗖𝗞 𝗧𝗢 𝗠𝗘𝗡𝗨")]
    ]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- কার্ড জেনারেটর কোড ---
def generate_card(bin_num):
    card = str(bin_num)[:12]
    while len(card) < 15: card += str(random.randint(0, 9))
    sum_val = 0
    for i, digit in enumerate(reversed(card)):
        n = int(digit); sum_val += (n*2 - 9 if n*2 > 9 else n*2) if i % 2 == 0 else n
    return card + str((10 - (sum_val % 10)) % 10)

# --- গ্রুপ কমান্ড সাপোর্ট: /gen 515462 ---
@dp.message(Command("gen"))
async def group_gen_handler(message: types.Message, command: CommandObject):
    if not command.args:
        return await message.reply("❌ **ERROR:** বিন দিতে ভুলে গেছেন!\n\nউদাহরণ: `/gen 515462`", parse_mode="Markdown")
    
    bin_n = "".join(filter(str.isdigit, command.args))[:6]
    if len(bin_n) < 6:
        return await message.reply("❌ **ERROR:** বিন কমপক্ষে ৬ ডিজিটের হতে হবে।")

    text = "✨ 〘 𝗖𝗛𝗘𝗖𝗞 𝗔𝗡𝗗 𝗦𝗔𝗩𝗘 𝗬𝗢𝗨𝗥 𝗣𝗥𝗘𝗠𝗜𝗨𝗠 〙 ✨\n\n\n"
    for _ in range(10):
        text += f"💳 `{generate_card(bin_n)}|{random.randint(1,12):02}|2028|{random.randint(100,999)}`\n\n"
    
    await message.answer_photo(photo=PHOTO_URL, caption=text, parse_mode="Markdown")

# --- ধাপে ধাপে বিন অ্যাড (অ্যাডমিন) ---
@dp.callback_query(F.data == "add_b")
async def step_1_bin(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.answer("📥 **STEP 1: এন্টার বিন**\n\nউদাহরণ: `515462` বা `51546200`", parse_mode="Markdown")
    await state.set_state(BotStates.add_bin_num)

@dp.message(BotStates.add_bin_num)
async def step_2_service(message: types.Message, state: FSMContext):
    bin_clean = "".join(filter(str.isdigit, message.text.split('|')[0]))[:6]
    await state.update_data(bin=bin_clean)
    await message.answer("🛠 **STEP 2: সার্ভিসের নাম**\n\nউদাহরণ: `Netflix`, `Amazon` বা `Mastercard`")
    await state.set_state(BotStates.add_bin_service)

@dp.message(BotStates.add_bin_service)
async def step_3_country(message: types.Message, state: FSMContext):
    await state.update_data(service=message.text)
    await message.answer("🌍 **STEP 3: দেশের নাম**\n\nউদাহরণ: `USA`, `UK` বা `BD`")
    await state.set_state(BotStates.add_bin_country)

@dp.message(BotStates.add_bin_country)
async def final_bin_save(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cursor.execute('INSERT OR REPLACE INTO bins VALUES (?, ?, ?)', (data['bin'], message.text, data['service']))
    conn.commit()
    res_text = (
        f"✅ **𝗦𝗨𝗖𝗖𝗘𝗦𝗦𝗙𝗨𝗟𝗟𝗬 𝗦𝗔𝗩𝗘𝗗!**\n\n"
        f"💳 **𝗕𝗜𝗡 :** `{data['bin']}`\n\n"
        f"🛠 **𝗦𝗘𝗥𝗩𝗜𝗖𝗘 :** `{data['service']}`\n\n"
        f"🌍 **𝗖𝗢𝗨𝗡𝗧𝗥𝗬 :** `{message.text}`"
    )
    await message.answer(res_text, parse_mode="Markdown")
    await state.clear()

# --- প্রিমিয়াম ডিজাইন আউটপুট ---
@dp.callback_query(F.data.startswith("gen_"))
async def premium_card_output(cb: types.CallbackQuery):
    bin_n = cb.data.split('_')[1]
    cursor.execute('SELECT country, service FROM bins WHERE bin=?', (bin_n,))
    info = cursor.fetchone()
    f = Faker()
    
    output = (
        f"✨ **𝗖𝗛𝗘𝗖𝗞 𝗔𝗡𝗗 𝗦𝗔𝗩𝗘 𝗬𝗢𝗨𝗥 {info[1].upper()}** ✨\n\n\n"
        f"💳 **𝗖𝗔𝗥𝗗 𝗡𝗨𝗠𝗕𝗘𝗥 :** `{generate_card(bin_n)}`\n\n"
        f"📅 **𝗠𝗠/𝗬𝗬 :** `{random.randint(1,12):02}/2028`\n\n"
        f"🔒 **𝗦𝗘𝗖𝗨𝗥𝗜𝗧𝗬 𝗖𝗢𝗗𝗘 / 𝗖𝗩𝗩 :** `{random.randint(100,999)}`\n\n"
        f"🌍 **𝗖𝗢𝗨𝗡𝗧𝗥𝗬 :** `{info[0]}`\n\n"
        f"👨‍💻 **NAME :** `{f.name()}`\n\n"
        f"🏠 **𝗔𝗗𝗗𝗥𝗘𝗦𝗦 𝗟𝗜𝗡𝗘 𝟭 :** `{f.street_address()}`\n\n"
        f"🏙️ **𝗧𝗢𝗪𝗡 / 𝗖𝗜𝗧𝗬 :** `{f.city()}`\n\n"
        f"📮 **𝗣𝗢𝗦𝗧𝗖𝗢𝗗𝗘 :** `{f.postcode()}`\n\n"
        f"📍 **𝗦𝗧𝗔𝗧𝗘 :** `{f.state()}`"
    )
    await bot.send_photo(cb.message.chat.id, photo=PHOTO_URL, caption=output, parse_mode="Markdown")

# --- মূল হ্যান্ডলারস ---
@dp.message(Command("start"))
@dp.message(F.text == "🔙 𝗕𝗔𝗖𝗞 𝗧𝗢 𝗠𝗘𝗡𝗨")
async def welcome_handler(message: types.Message, state: FSMContext):
    await state.clear()
    cursor.execute('INSERT OR IGNORE INTO users VALUES (?)', (message.from_user.id,))
    conn.commit()
    await message.answer("👋 **𝗪𝗘𝗟𝗖𝗢𝗠𝗘!** নিচের মেনু থেকে অপশন বেছে নিন:", reply_markup=main_menu(message.from_user.id))

@dp.message(F.text == "🛠 𝗔𝗗𝗠𝗜𝗡 𝗖𝗢𝗡𝗧𝗥𝗢𝗟")
async def admin_main(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    kb = [[types.InlineKeyboardButton(text="➕ 𝗔𝗗𝗗 𝗕𝗜𝗡", callback_data="add_b"), 
           types.InlineKeyboardButton(text="🗑 𝗗𝗘𝗟𝗘𝗧𝗘 𝗕𝗜𝗡", callback_data="list_del_b")]]
    await message.answer("🛠 **ADMIN DASHBOARD**", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))

@dp.message(F.text == "💳 𝗖𝗥𝗘𝗔𝗧𝗘 𝗖𝗔𝗥𝗗")
async def method_selection(message: types.Message):
    await message.answer("🚀 **জেনারেশন মেথড সিলেক্ট করুন:**", reply_markup=card_menu())

@dp.message(F.text == "💎 𝗖𝗛𝗢𝗜𝗖𝗘 𝗔𝗗𝗠𝗜𝗡 𝗕𝗜𝗡")
async def list_admin_bins(message: types.Message):
    cursor.execute('SELECT bin, country, service FROM bins')
    bins = cursor.fetchall()
    if not bins: return await message.answer("⚠️ কোনো বিন এখনো সেট করা হয়নি।")
    kb = [[types.InlineKeyboardButton(text=f"💳 {b[0]} | {b[2]}", callback_data=f"gen_{b[0]}")] for b in bins]
    await message.answer("💎 **প্রিমিয়াম বিন লিস্ট:**", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))

async def main():
    print("Bot is Live on Termux!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
