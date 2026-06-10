import asyncio, logging, sqlite3
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = "8702209630:AAEjJfWNQ0rf-d6LJA_81dCxioj8NF7_Gm8"
CHANNEL_ID = -1003908319383
OWNER_ID = 116599098

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

conn = sqlite3.connect("barakholka.db", check_same_thread=False)
cur = conn.cursor()
cur.executescript("""
CREATE TABLE IF NOT EXISTS ads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER, username TEXT, category TEXT,
    title TEXT, description TEXT, price TEXT,
    photo_id TEXT, status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")
conn.commit()

CATEGORIES = [
    "📱 Электроника","👗 Одежда и обувь","🛋 Мебель и интерьер",
    "🚗 Авто и мото","🧸 Детские товары","🔧 Инструменты",
    "🏠 Для дома и дачи","📚 Книги и хобби","🐾 Животные",
    "🎮 Игры и приставки","💄 Красота и здоровье","🎁 Отдам даром",
    "🔍 Ищу / Куплю","📦 Другое"
]

class NewAd(StatesGroup):
    category = State(); title = State(); description = State()
    price = State(); photo = State(); confirm = State()

class SearchAd(StatesGroup):
    query = State()

def kb_main():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📝 Подать объявление")],
        [KeyboardButton(text="🔍 Поиск"), KeyboardButton(text="📋 Мои объявления")],
        [KeyboardButton(text="ℹ️ Правила")]
    ], resize_keyboard=True)

def kb_cats():
    rows = [[KeyboardButton(text=c)] for c in CATEGORIES]
    rows.append([KeyboardButton(text="❌ Отмена")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

def kb_cancel():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)

def kb_skip():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⏭ Без фото"), KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)

def kb_confirm():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="✅ Отправить"), KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)

def kb_mod(ad_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{ad_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{ad_id}")
    ]])

def kb_contact(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💬 Написать продавцу", url=f"tg://user?id={user_id}")
    ]])

def fmt_ad(data, user=None):
    seller = f"@{user.username}" if user and user.username else (user.full_name if user else data.get("username","—"))
    return f"{data['category']}\n\n<b>{data['title']}</b>\n\n{data['description']}\n\n💰 <b>Цена:</b> {data['price']}\n👤 <b>Продавец:</b> {seller}"

@router.message(CommandStart())
async def start(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer(f"Привет, <b>{msg.from_user.first_name}</b>! 👋\n\nДобро пожаловать в <b>Барахолку Марьина Роща</b>.\n\nПодайте объявление или найдите нужный товар.", parse_mode="HTML", reply_markup=kb_main())

@router.message(F.text == "ℹ️ Правила")
async def rules(msg: Message):
    await msg.answer("<b>Правила:</b>\n1. Только личные вещи\n2. Запрещено: оружие, наркотики\n3. Одно объявление — один товар\n4. Указывайте реальную цену", parse_mode="HTML")

@router.message(F.text == "📝 Подать объявление")
async def ad_start(msg: Message, state: FSMContext):
    await state.set_state(NewAd.category)
    await msg.answer("Выберите категорию:", reply_markup=kb_cats())

@router.message(NewAd.category)
async def ad_cat(msg: Message, state: FSMContext):
    if msg.text == "❌ Отмена": await state.clear(); return await msg.answer("Отменено.", reply_markup=kb_main())
    if msg.text not in CATEGORIES: return await msg.answer("Выберите из списка.")
    await state.update_data(category=msg.text); await state.set_state(NewAd.title)
    await msg.answer("Введите <b>название</b> (до 60 символов):", parse_mode="HTML", reply_markup=kb_cancel())

@router.message(NewAd.title)
async def ad_title(msg: Message, state: FSMContext):
    if msg.text == "❌ Отмена": await state.clear(); return await msg.answer("Отменено.", reply_markup=kb_main())
    if len(msg.text) > 60: return await msg.answer("Не более 60 символов.")
    await state.update_data(title=msg.text); await state.set_state(NewAd.description)
    await msg.answer("Введите <b>описание</b>:", parse_mode="HTML")

@router.message(NewAd.description)
async def ad_desc(msg: Message, state: FSMContext):
    if msg.text == "❌ Отмена": await state.clear(); return await msg.answer("Отменено.", reply_markup=kb_main())
    await state.update_data(description=msg.text); await state.set_state(NewAd.price)
    await msg.answer("Укажите <b>цену</b>:", parse_mode="HTML")

@router.message(NewAd.price)
async def ad_price(msg: Message, state: FSMContext):
    if msg.text == "❌ Отмена": await state.clear(); return await msg.answer("Отменено.", reply_markup=kb_main())
    await state.update_data(price=msg.text); await state.set_state(NewAd.photo)
    await msg.answer("Прикрепите <b>фото</b> или нажмите «Без фото»:", parse_mode="HTML", reply_markup=kb_skip())

@router.message(NewAd.photo, F.photo)
async def ad_photo(msg: Message, state: FSMContext):
    await state.update_data(photo_id=msg.photo[-1].file_id); await show_preview(msg, state)

@router.message(NewAd.photo, F.text == "⏭ Без фото")
async def ad_nophoto(msg: Message, state: FSMContext):
    await state.update_data(photo_id=None); await show_preview(msg, state)

@router.message(NewAd.photo, F.text == "❌ Отмена")
async def ad_cancel_photo(msg: Message, state: FSMContext):
    await state.clear(); await msg.answer("Отменено.", reply_markup=kb_main())

async def show_preview(msg, state):
    data = await state.get_data(); await state.set_state(NewAd.confirm)
    text = f"<b>Предпросмотр:</b>\n\n{fmt_ad(data, msg.from_user)}"
    if data.get("photo_id"): await msg.answer_photo(data["photo_id"], caption=text, parse_mode="HTML", reply_markup=kb_confirm())
    else: await msg.answer(text, parse_mode="HTML", reply_markup=kb_confirm())

@router.message(NewAd.confirm, F.text == "✅ Отправить")
async def ad_submit(msg: Message, state: FSMContext):
    data = await state.get_data(); u = msg.from_user
    cur.execute("INSERT INTO ads (user_id,username,category,title,description,price,photo_id,status) VALUES(?,?,?,?,?,?,?,?)",
                (u.id, u.username or u.full_name, data["category"], data["title"], data["description"], data["price"], data.get("photo_id"), "pending"))
    conn.commit(); ad_id = cur.lastrowid; await state.clear()
    await msg.answer("✅ Объявление отправлено на модерацию! Обычно это 1-2 часа.", reply_markup=kb_main())
    mod_text = f"<b>🆕 Новое объявление #{ad_id}</b>\n\n{fmt_ad(data, u)}\n\nde>user_id: {u.id}</code>"
    try:
        if data.get("photo_id"): await bot.send_photo(OWNER_ID, data["photo_id"], caption=mod_text, parse_mode="HTML", reply_markup=kb_mod(ad_id))
        else: await bot.send_message(OWNER_ID, mod_text, parse_mode="HTML", reply_markup=kb_mod(ad_id))
    except Exception as e: logging.error(e)

@router.message(NewAd.confirm, F.text == "❌ Отмена")
async def ad_cancel(msg: Message, state: FSMContext):
    await state.clear(); await msg.answer("Отменено.", reply_markup=kb_main())

@router.callback_query(F.data.startswith("approve_"))
async def approve(cb: CallbackQuery):
    if cb.from_user.id != OWNER_ID: return await cb.answer("Нет прав.", show_alert=True)
    ad_id = int(cb.data.split("_")[1])
    cur.execute("SELECT * FROM ads WHERE id=?", (ad_id,)); row = cur.fetchone()
    if not row: return await cb.answer("Не найдено.", show_alert=True)
    if row[8] != "pending": return await cb.answer("Уже обработано.", show_alert=True)
    cur.execute("UPDATE ads SET status='approved' WHERE id=?", (ad_id,)); conn.commit()
    data = {"category":row[3],"title":row[4],"description":row[5],"price":row[6],"username":row[2]}
    pub = fmt_ad(data)
    try:
        if row[7]: await bot.send_photo(CHANNEL_ID, row[7], caption=pub, parse_mode="HTML", reply_markup=kb_contact(row[1]))
        else: await bot.send_message(CHANNEL_ID, pub, parse_mode="HTML", reply_markup=kb_contact(row[1]))
        await bot.send_message(row[1], "✅ Ваше объявление одобрено и опубликовано в канале!")
    except Exception as e: logging.error(e)
    await cb.message.edit_reply_markup(); await cb.answer("✅ Опубликовано!")

@router.callback_query(F.data.
