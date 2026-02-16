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

# --- ডাটাবেস সেটআপ ---
conn = sqlite3.connect('premium_bot.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
cursor.execute('CREATE TABLE IF NOT EXISTS bins (bin TEXT PRIMARY KEY, country TEXT, service TEXT)')
conn.commit()

class BotStates(StatesGroup):
    add_bin_num = State()
    add_bin_service = State()
    add_bin_country = State()
    broadcast_msg = State()
    user_bin_input = State()

# --- কিবোর্ড ---
def main_menu(user_id):
    kb = [[types.KeyboardButton(text="💳 𝗖𝗥𝗘𝗔𝗧𝗘 𝗖𝗔𝗥𝗗"), types.KeyboardButton(text="🌍 𝗙𝗔𝗞𝗘 𝗜𝗡𝗙𝗢")],
          [types.KeyboardButton(text="🆘 𝗦𝗨𝗣𝗣𝗢𝗥𝗧")]]
    if user_id == ADMIN_ID:
        kb.append([types.KeyboardButton(text="🛠 𝗔𝗗𝗠𝗜𝗡 𝗖𝗢𝗡𝗧𝗥𝗢𝗟")])
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- স্মার্ট ব্রডকাস্ট সিস্টেম (ফরোয়ার্ড সাপোর্টসহ) ---
@dp.callback_query(F.data == "bc_all")
async def broadcast_start(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.answer("📢 **ব্রডকাস্ট মেসেজটি দিন:**\n\n(আপনি কোনো মেসেজ ফরোয়ার্ড করে দিলেও সেটি সবার কাছে পৌঁছে যাবে)")
    await state.set_state(BotStates.broadcast_msg)

@dp.message(BotStates.broadcast_msg)
async def broadcast_handler(message: types.Message, state: FSMContext):
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    count = 0
    
    status_msg = await message.answer("⏳ **ব্রডকাস্ট চলছে...**")
    
    for u in users:
        try:
            # এটি ইউজারের মেসেজটি (ফটো, টেক্সট বা ফরোয়ার্ড করা মেসেজ) হুবহু কপি করে পাঠাবে
            await message.copy_to(chat_id=u[0])
            count += 1
            await asyncio.sleep(0.05) # সার্ভার ওভারলোড এড়াতে সামান্য বিরতি
        except (TelegramForbiddenError, TelegramBadRequest):
            pass
            
    await status_msg.edit_text(f"✅ **ব্রডকাস্ট সম্পন্ন!**\n\n🎯 মোট ইউজার: `{count}`")
    await state.clear()

# --- কার্ড মেকার লজিক ---
def generate_card(bin_num):
    card = str(bin_num)[:12]
    while len(card) < 15: card += str(random.randint(0, 9))
    sum_val = 0
    for i, digit in enumerate(reversed(card)):
        n = int(digit); sum_val += (n*2 - 9 if n*2 > 9 else n*2) if i % 2 == 0 else n
    return card + str((10 - (sum_val % 10)) % 10)

# --- গ্রুপ কমান্ড সাপোর্ট ---
@dp.message(Command("gen"))
async def group_gen(message: types.Message, command: CommandObject):
    if not command.args:
        return await message.reply("❌ **সঠিক বিন দিন!**")
    bin_n = "".join(filter(str.isdigit, command.args))[:6]
    text = "✨ 〘 𝗖𝗛𝗘𝗖𝗞 𝗔𝗡𝗗 𝗦𝗔𝗩𝗘 𝗬𝗢𝗨𝗥 𝗣𝗥𝗘𝗠𝗜𝗨𝗠 〙 ✨\n\n\n"
    for _ in range(10):
        text += f"💳 `{generate_card(bin_n)}|{random.randint(1,12):02}|2028|{random.randint(100,999)}`\n\n"
    await message.answer_photo(photo=PHOTO_URL, caption=text, parse_mode="Markdown")

# --- ৩ ধাপের বিন অ্যাড ---
@dp.callback_query(F.data == "add_b")
async def add_bin_step1(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.answer("📥 **STEP 1: বিন দিন (যেমন: 515462)**")
    await state.set_state(BotStates.add_bin_num)

@dp.message(BotStates.add_bin_num)
async def add_bin_step2(message: types.Message, state: FSMContext):
    bin_c = "".join(filter(str.isdigit, message.text.split('|')[0]))[:6]
    await state.update_data(bin=bin_c)
    await message.answer("🛠 **STEP 2: সার্ভিসের নাম (যেমন: Netflix)**")
    await state.set_state(BotStates.add_bin_service)

@dp.message(BotStates.add_bin_service)
async def add_bin_step3(message: types.Message, state: FSMContext):
    await state.update_data(service=message.text)
    await message.answer("🌍 **STEP 3: দেশের নাম (যেমন: USA)**")
    await state.set_state(BotStates.add_bin_country)

@dp.message(BotStates.add_bin_country)
async def add_bin_save(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cursor.execute('INSERT OR REPLACE INTO bins VALUES (?, ?, ?)', (data['bin'], message.text, data['service']))
    conn.commit()
    await message.answer("✅ **বিন সেভ হয়েছে!**", reply_markup=main_menu(ADMIN_ID))
    await state.clear()

# --- কার্ড আউটপুট ডিজাইন ---
@dp.callback_query(F.data.startswith("gen_"))
async def gen_output(cb: types.CallbackQuery):
    bin_n = cb.data.split('_')[1]
    cursor.execute('SELECT country, service FROM bins WHERE bin=?', (bin_n,))
    info = cursor.fetchone()
    f = Faker()
    text = (
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
    await bot.send_photo(cb.message.chat.id, photo=PHOTO_URL, caption=text, parse_mode="Markdown")

# --- অ্যাডমিন প্যানেল ---
@dp.message(F.text == "🛠 𝗔𝗗𝗠𝗜𝗡 𝗖𝗢𝗡𝗧𝗥𝗢𝗟")
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    cursor.execute('SELECT COUNT(*) FROM users'); u = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM bins'); b = cursor.fetchone()[0]
    kb = [[types.InlineKeyboardButton(text="➕ অ্যাড বিন", callback_data="add_b"), types.InlineKeyboardButton(text="🗑 ডিলিট বিন", callback_data="list_del_b")],
          [types.InlineKeyboardButton(text="📢 ব্রডকাস্ট", callback_data="bc_all")]]
    await message.answer(f"🛠 **Admin Panel**\n\nUsers: `{u}` | Bins: `{b}`", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))

@dp.message(Command("start"))
@dp.message(F.text == "🔙 𝗕𝗔𝗖𝗞 𝗧𝗢 𝗠𝗘𝗡𝗨")
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    cursor.execute('INSERT OR IGNORE INTO users VALUES (?)', (message.from_user.id,))
    conn.commit()
    await message.answer("👋 **স্বাগতম!** নিচের মেনু ব্যবহার করুন:", reply_markup=main_menu(message.from_user.id))

@dp.message(F.text == "💳 𝗖𝗥𝗘𝗔𝗧𝗘 𝗖𝗔𝗥𝗗")
async def card_menu_handler(message: types.Message):
    kb = [[types.KeyboardButton(text="💎 𝗖𝗛𝗢𝗜𝗖𝗘 𝗔𝗗𝗠𝗜𝗡 𝗕𝗜𝗡")], [types.KeyboardButton(text="⌨️ 𝗘𝗡𝗧𝗘𝗥 𝗬𝗢𝗨𝗥 𝗕𝗜𝗡")], [types.KeyboardButton(text="🔙 𝗕𝗔𝗖𝗞 𝗧𝗢 𝗠𝗘𝗡𝗨")]]
    await message.answer("🚀 **মেথড বেছে নিন:**", reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

@dp.message(F.text == "💎 𝗖𝗛𝗢𝗜𝗖𝗘 𝗔𝗗𝗠𝗜𝗡 𝗕𝗜𝗡")
async def list_bins(message: types.Message):
    cursor.execute('SELECT bin, country, service FROM bins')
    res = cursor.fetchall()
    if not res: return await message.answer("⚠️ কোনো বিন নেই।")
    kb = [[types.InlineKeyboardButton(text=f"💳 {b[0]} | {b[2]}", callback_data=f"gen_{b[0]}")] for b in res]
    await message.answer("💎 **বিন লিস্ট:**", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
