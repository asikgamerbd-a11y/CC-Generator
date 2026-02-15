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
    fake_info_country = State()
    fake_info_gender = State()

# --- মেনু বাটনসমূহ ---
def main_menu(user_id):
    kb = [
        [types.KeyboardButton(text="💳 Create Credit Card")],
        [types.KeyboardButton(text="🌍 Create Fake Card Info")]
    ]
    if user_id == ADMIN_ID:
        kb.append([types.KeyboardButton(text="🛠 Admin Control Panel")])
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
    welcome_text = (
        "👋 **Hello!** Welcome to our Premium Card Gen Bot.\n\n"
        "Please select an option from the menu below to get started! 🚀"
    )
    await message.answer(welcome_text, reply_markup=main_menu(message.from_user.id), parse_mode="Markdown")

# --- Fake Info Generator ---
@dp.message(F.text == "🌍 Create Fake Card Info")
async def ask_info_country(message: types.Message, state: FSMContext):
    await message.answer("📍 **Enter Country Name:**\n\nExample: `USA`, `UK`, `Canada`", parse_mode="Markdown")
    await state.set_state(AdminStates.fake_info_country)

@dp.message(AdminStates.fake_info_country)
async def ask_info_gender(message: types.Message, state: FSMContext):
    await state.update_data(country=message.text)
    kb = [[
        types.InlineKeyboardButton(text="♂️ Male", callback_data="gender_male"),
        types.InlineKeyboardButton(text="♀️ Female", callback_data="gender_female")
    ]]
    await message.answer("🧬 **Select Gender:**", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(AdminStates.fake_info_gender)

@dp.callback_query(F.data.startswith("gender_"))
async def send_fake_info(cb: types.CallbackQuery, state: FSMContext):
    gender = cb.data.split('_')[1]
    user_data = await state.get_data()
    country = user_data.get('country')
    
    f = Faker()
    name = f.name_male() if gender == "male" else f.name_female()
    info = (
        f"✨ **FAKE IDENTITY INFO** ✨\n\n"
        f"🌍 **𝗖𝗢𝗨𝗡𝗧𝗥𝗬 :** `{country}`\n\n"
        f"👨‍💻 **𝗡𝗔𝗠𝗘 :** `{name}`\n\n"
        f"🏠 **𝗔𝗗𝗗𝗥𝗘𝗦𝗦 :** `{f.street_address()}`\n\n"
        f"🏙️ **𝗖𝗜𝗧𝗬 :** `{f.city()}`\n\n"
        f"📮 **𝗣𝗢𝗦𝗧𝗖𝗢𝗗𝗘 :** `{f.postcode()}`\n\n"
        f"📍 **𝗦𝗧𝗔𝗧𝗘 :** `{f.state()}`"
    )
    await cb.message.edit_text(info, parse_mode="Markdown")
    await state.clear()

# --- কার্ড জেনারেটর ---
@dp.message(F.text == "⌨️ Create Your Bin Card")
async def ask_user_bin(message: types.Message, state: FSMContext):
    await message.answer("📥 **Enter Your BIN:**\n\nExample: `515462`", parse_mode="Markdown")
    await state.set_state(AdminStates.user_bin_input)

@dp.message(AdminStates.user_bin_input)
async def gen_user_custom(message: types.Message, state: FSMContext):
    bin_n = "".join(filter(str.isdigit, message.text))[:6]
    month, year = str(random.randint(1,12)).zfill(2), str(random.randint(2026, 2031))
    text = "✨ 〘 𝗖𝗛𝗘𝗖𝗞 𝗔𝗡𝗗 𝗦𝗔𝗩𝗘 𝗬𝗢𝗨𝗥 𝗣𝗥𝗘𝗠𝗜𝗨𝗠 〙 ✨\n\n"
    for _ in range(10):
        text += f"💳 `{generate_card(bin_n)}|{month}|{year}|{random.randint(100,999)}`\n\n"
    await message.answer_photo(photo=PHOTO_URL, caption=text, parse_mode="Markdown")
    await state.clear()

@dp.message(F.text == "💎 Choice Admin Card")
async def show_admin_bins(message: types.Message):
    cursor.execute('SELECT bin, country FROM bins')
    bins = cursor.fetchall()
    if not bins:
        return await message.answer("⚠️ **No premium bins set by admin yet!**")
    kb = [[types.InlineKeyboardButton(text=f"💳 {b[0]} ({b[1]})", callback_data=f"gen_{b[0]}")] for b in bins]
    await message.answer("💎 **Select a premium BIN from the list:**", 
                         reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("gen_"))
async def gen_from_admin_list(cb: types.CallbackQuery):
    bin_n = cb.data.split('_')[1]
    f = Faker()
    text = (
        f"✨ **𝗣𝗥𝗘𝗠𝗜𝗨𝗠 𝗠𝗔𝗦𝗧𝗘𝗥𝗖𝗔𝗥𝗗** ✨\n\n"
        f"💳 **𝗖𝗔𝗥𝗗 :** `{generate_card(bin_n)}`\n\n"
        f"📅 **𝗠𝗠/𝗬𝗬 :** `{random.randint(1,12)}/2028`\n\n"
        f"🔒 **𝗖𝗩𝗩 :** `{random.randint(100,999)}`\n\n"
        f"👨‍💻 **𝗡𝗔𝗠𝗘 :** `{f.name()}`\n\n"
        f"🏠 **𝗔𝗗𝗗𝗥𝗘𝗦𝗦 :** `{f.street_address()}`\n\n"
        f"🏙️ **𝗖𝗜𝗧𝗬 :** `{f.city()}`"
    )
    await bot.send_photo(cb.message.chat.id, photo=PHOTO_URL, caption=text, parse_mode="Markdown")

@dp.message(F.text == "💳 Create Credit Card")
async def card_options(message: types.Message):
    await message.answer("🚀 **Select Generation Method:**", reply_markup=card_menu())

# --- অ্যাডমিন প্যানেল ভিউ ---
@dp.callback_query(F.data == "admin_home")
@dp.message(F.text == "🛠 Admin Control Panel")
async def admin_panel_view(message: types.Message | types.CallbackQuery):
    user_id = message.from_user.id
    if user_id != ADMIN_ID: return
    
    cursor.execute('SELECT COUNT(*) FROM users'); total_u = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM bins'); total_b = cursor.fetchone()[0]
    
    kb = [
        [types.InlineKeyboardButton(text="➕ Add New BIN", callback_data="add_b"),
         types.InlineKeyboardButton(text="🗑 Delete BIN", callback_data="list_del_b")],
        [types.InlineKeyboardButton(text="📢 Broadcast", callback_data="bc_all")],
        [types.InlineKeyboardButton(text="🔄 Refresh", callback_data="admin_home")]
    ]
    
    admin_text = (
        f"🛠 **ADMIN DASHBOARD**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 **Total Users:** `{total_u}`\n\n"
        f"💳 **Stored BINs:** `{total_b}`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Select an action below to manage the bot:"
    )
    
    if isinstance(message, types.Message):
        await message.answer(admin_text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")
    else:
        await message.message.edit_text(admin_text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

# --- অ্যাডমিন অ্যাকশনস ---
@dp.callback_query(F.data == "list_del_b")
async def list_bins_to_delete(cb: types.CallbackQuery):
    cursor.execute('SELECT bin, country FROM bins')
    bins = cursor.fetchall()
    if not bins:
        return await cb.answer("No bins to delete!", show_alert=True)
    
    kb = [[types.InlineKeyboardButton(text=f"❌ Delete {b[0]}", callback_data=f"del_{b[0]}")] for b in bins]
    kb.append([types.InlineKeyboardButton(text="⬅️ Back", callback_data="admin_home")])
    await cb.message.edit_text("🗑 **Select a BIN to remove from database:**", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("del_"))
async def delete_bin_exec(cb: types.CallbackQuery):
    bin_to_del = cb.data.split('_')[1]
    cursor.execute('DELETE FROM bins WHERE bin=?', (bin_to_del,))
    conn.commit()
    await cb.answer(f"BIN {bin_to_del} Deleted!", show_alert=True)
    await list_bins_to_delete(cb)

@dp.callback_query(F.data == "add_b")
async def add_b_start(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.answer("📥 **Send New BIN & Country:**\n\nFormat: `BIN|Country` (Example: `515462|USA`)", parse_mode="Markdown")
    await state.set_state(AdminStates.add_bin)

@dp.message(AdminStates.add_bin)
async def add_b_save(message: types.Message, state: FSMContext):
    try:
        b, c = message.text.split('|')
        cursor.execute('INSERT OR REPLACE INTO bins VALUES (?, ?)', (b.strip(), c.strip()))
        conn.commit()
        await message.answer("✅ **BIN successfully added to database!**")
    except:
        await message.answer("❌ **Error!** Use format: `BIN|Country`")
    await state.clear()

@dp.callback_query(F.data == "bc_all")
async def bc_start(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.answer("📢 **Enter Broadcast Message:**")
    await state.set_state(AdminStates.broadcast)

@dp.message(AdminStates.broadcast)
async def bc_done(message: types.Message, state: FSMContext):
    cursor.execute('SELECT user_id FROM users'); users = cursor.fetchall()
    count = 0
    for u in users:
        try:
            await message.copy_to(u[0])
            count += 1
        except: pass
    await message.answer(f"✅ **Broadcast Done!**\n\nSent to `{count}` users.")
    await state.clear()

# --- রেন্ডার ওয়েব সার্ভার ---
async def handle(r): return web.Response(text="Bot Alive")
async def main():
    app = web.Application(); app.router.add_get('/', handle)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.getenv("PORT", 10000))).start()
    await dp.start_polling(bot)

if __name__ == "__main__": asyncio.run(main())
