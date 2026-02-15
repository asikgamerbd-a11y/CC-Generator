import random, logging, asyncio, os, sqlite3
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
fake = Faker()

# --- ডাটাবেস ---
conn = sqlite3.connect('database.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
cursor.execute('CREATE TABLE IF NOT EXISTS bins (bin TEXT PRIMARY KEY, country TEXT)')
conn.commit()

class AdminStates(StatesGroup):
    add_bin = State()
    broadcast = State()
    user_bin_input = State()

# --- মেনু বাটনসমূহ (Reply Keyboard) ---
def main_menu(user_id):
    kb = [
        [types.KeyboardButton(text="💳 Create Credit Card")],
        [types.KeyboardButton(text="🌍 Create Fake Card Info")]
    ]
    # শুধুমাত্র এডমিনের জন্য আলাদা বাটন যোগ হবে
    if user_id == ADMIN_ID:
        kb.append([types.KeyboardButton(text="🛠 Admin Panel")])
    
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def card_menu():
    kb = [
        [types.KeyboardButton(text="💎 Choice Admin Card")],
        [types.KeyboardButton(text="⌨️ Create Your Bin Card")],
        [types.KeyboardButton(text="🔙 Back to Main Menu")]
    ]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- কার্ড জেনারেটর ---
def generate_card(bin_num):
    card = str(bin_num)[:12]
    while len(card) < 15: card += str(random.randint(0, 9))
    sum_val = 0
    for i, digit in enumerate(reversed(card)):
        n = int(digit); sum_val += (n*2 - 9 if n*2 > 9 else n*2) if i % 2 == 0 else n
    return card + str((10 - (sum_val % 10)) % 10)

# --- হ্যান্ডলারস ---

@dp.message(Command("start"))
@dp.message(F.text == "🔙 Back to Main Menu")
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    cursor.execute('INSERT OR IGNORE INTO users VALUES (?)', (message.from_user.id,))
    conn.commit()
    await message.answer("বট মেনু থেকে একটি অপশন বেছে নিন:", reply_markup=main_menu(message.from_user.id))

# --- ইউজার সেকশন ---
@dp.message(F.text == "💳 Create Credit Card")
async def create_card_options(message: types.Message):
    await message.answer("আপনি কীভাবে কার্ড জেনারেট করতে চান?", reply_markup=card_menu())

@dp.message(F.text == "⌨️ Create Your Bin Card")
async def ask_user_bin(message: types.Message, state: FSMContext):
    await message.answer("আপনার বিনটি দিন। উদাহরণ: `515462` বা `515462|05|2030`", parse_mode="Markdown")
    await state.set_state(AdminStates.user_bin_input)

@dp.message(AdminStates.user_bin_input)
async def gen_user_custom(message: types.Message, state: FSMContext):
    data = message.text.split('|')
    bin_n = "".join(filter(str.isdigit, data[0]))[:6]
    month = data[1] if len(data) > 1 else str(random.randint(1,12)).zfill(2)
    year = data[2] if len(data) > 2 else str(random.randint(2026, 2031))
    
    text = "✨ 〘 𝗖𝗛𝗘𝗖𝗞 𝗔𝗡𝗗 𝗦𝗔𝗩𝗘 𝗬𝗢𝗨𝗥 𝗣𝗥𝗘𝗠𝗜𝗨𝗠 〙 ✨\n\n`"
    for _ in range(10): text += f"{generate_card(bin_n)}|{month}|{year}|{random.randint(100,999)}\n"
    text += "`"
    await message.answer_photo(photo=PHOTO_URL, caption=text, parse_mode="Markdown")
    await state.clear()

@dp.message(F.text == "💎 Choice Admin Card")
async def show_admin_bins(message: types.Message):
    cursor.execute('SELECT bin, country FROM bins')
    bins = cursor.fetchall()
    if not bins: return await message.answer("বর্তমানে কোনো অ্যাডমিন কার্ড নেই।")
    
    kb = [[types.InlineKeyboardButton(text=f"{b[0]} ({b[1]})", callback_data=f"gen_{b[0]}")] for b in bins]
    await message.answer("নিচের লিস্ট থেকে একটি বিন বেছে নিন:", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("gen_"))
async def gen_from_admin_list(cb: types.CallbackQuery):
    bin_n = cb.data.split('_')[1]
    f = Faker()
    # অরিজিনাল ইনফো ফরম্যাট
    text = (f"✨ 𝗖𝗛𝗘𝗖𝗞 𝗔𝗡𝗗 𝗦𝗔𝗩𝗘 𝗬𝗢𝗨𝗥 𝗣𝗥𝗘𝗠𝗜𝗨𝗠 𝗠𝗔𝗦𝗧𝗘𝗥𝗖𝗔𝗥𝗗 ✨\n\n"
            f"💳 **𝗖𝗔𝗥𝗗 𝗡𝗨𝗠𝗕𝗘𝗥 :** `{generate_card(bin_n)}`\n"
            f"📅 **𝗠𝗠/𝗬𝗬 :** {random.randint(1,12)}/2028\n"
            f"🔒 **𝗦𝗘𝗖𝗨𝗥𝗜𝗧𝗬 𝗖𝗢𝗗𝗘 / 𝗖𝗩𝗩 :** {random.randint(100,999)}\n"
            f"🌍 **𝗖𝗢𝗨𝗡𝗧𝗥𝗬 :** Selected\n"
            f"👨‍💻 **NAME :** {f.name()}\n"
            f"🏠 **𝗔𝗗𝗗𝗥𝗘𝗦𝗦 𝗟𝗜𝗡𝗘 𝟭 :** {f.street_address()}\n"
            f"🏙️ **𝗧𝗢𝗪𝗡 / 𝗖𝗜𝗧𝗬 :** {f.city()}\n"
            f"📮 **𝗣𝗢𝗦𝗧𝗖𝗢𝗗𝗘 :** {f.postcode()}\n"
            f"📍 **𝗦𝗧𝗔𝗧𝗘 :** {f.state()}")
    await bot.send_photo(cb.message.chat.id, photo=PHOTO_URL, caption=text, parse_mode="Markdown")

@dp.message(F.text == "🌍 Create Fake Card Info")
async def fake_info_gen(message: types.Message):
    f = Faker()
    text = (f"🌍 **𝗖𝗢𝗨𝗡𝗧𝗥𝗬 :** Random\n"
            f"👨‍💻 **NAME :** {f.name()}\n"
            f"🏠 **𝗔𝗗𝗗𝗥𝗘𝗦𝗦 𝗟𝗜𝗡𝗘 𝟭 :** {f.street_address()}\n"
            f"🏙️ **𝗧𝗢𝗪𝗡 / 𝗖𝗜𝗧𝗬 :** {f.city()}\n"
            f"📮 **𝗣𝗢𝗦𝗧𝗖𝗢𝗗𝗘 :** {f.postcode()}\n"
            f"📍 **𝗦𝗧𝗔𝗧𝗘 :** {f.state()}")
    await message.answer(text)

# --- অ্যাডমিন সেকশন (শুধুমাত্র বাটন টিপলে আসবে) ---
@dp.message(F.text == "🛠 Admin Panel")
async def admin_panel_menu(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    cursor.execute('SELECT COUNT(*) FROM users'); total_u = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM bins'); total_b = cursor.fetchone()[0]
    
    kb = [
        [types.InlineKeyboardButton(text="➕ বিন যোগ", callback_data="add_b"), 
         types.InlineKeyboardButton(text="❌ বিন ডিলিট", callback_data="del_b")],
        [types.InlineKeyboardButton(text="📢 ব্রডকাস্ট", callback_data="bc_all")]
    ]
    await message.answer(f"🛠 **Admin Menu Builder**\n\n👥 মোট ইউজার: {total_u}\n💳 মোট বিন: {total_b}", 
                         reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "add_b")
async def add_b_start(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.answer("বিন এবং দেশের নাম দিন (যেমন: 515462|USA):")
    await state.set_state(AdminStates.add_bin)

@dp.message(AdminStates.add_bin)
async def add_b_save(message: types.Message, state: FSMContext):
    try:
        b, c = message.text.split('|')
        cursor.execute('INSERT OR REPLACE INTO bins VALUES (?, ?)', (b.strip(), c.strip()))
        conn.commit()
        await message.answer("✅ বিন সফলভাবে সেভ হয়েছে।")
    except: await message.answer("❌ ফরম্যাট ভুল! বিন|দেশ এভাবে দিন।")
    await state.clear()

@dp.callback_query(F.data == "bc_all")
async def bc_start(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.answer("ব্রডকাস্ট মেসেজটি দিন বা ফরোয়ার্ড করুন:")
    await state.set_state(AdminStates.broadcast)

@dp.message(AdminStates.broadcast)
async def bc_done(message: types.Message, state: FSMContext):
    cursor.execute('SELECT user_id FROM users'); users = cursor.fetchall()
    for u in users:
        try: await message.copy_to(u[0])
        except: pass
    await message.answer("✅ ব্রডকাস্ট সম্পন্ন।")
    await state.clear()

# --- রেন্ডার সার্ভার ---
async def handle(r): return web.Response(text="Bot is Live")
async def main():
    app = web.Application(); app.router.add_get('/', handle)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.getenv("PORT", 10000))).start()
    await dp.start_polling(bot)

if __name__ == "__main__": asyncio.run(main())
    
