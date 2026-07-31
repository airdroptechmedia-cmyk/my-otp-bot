import sys
import os
import sqlite3
import datetime
import io
import re
import asyncio
import subprocess
import openpyxl
import aiohttp
from aiohttp import web

from aiogram import Bot, Dispatcher, Router, F, types
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    BufferedInputFile
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# ==================== CONFIGURATION ====================
BOT_TOKEN = "BOT_TOKEN"
ADMIN_ID = 8125384914
BOT_NAME = "OTP RECIVER PRO BOT"
DB_NAME = "system.db"
# =======================================================

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

BOT_USERNAME = "otpreciverpro_bot"

# ----------------- DATABASE INITIALIZATION -----------------
def get_db():
    conn = sqlite3.connect(DB_NAME, timeout=15)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        balance REAL DEFAULT 0.00,
        reward_balance REAL DEFAULT 0.00,
        referrals INTEGER DEFAULT 0,
        referred_by INTEGER,
        otp_count INTEGER DEFAULT 0,
        joined_date TEXT DEFAULT CURRENT_DATE
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS verifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        phone_number TEXT,
        service_name TEXT,
        status TEXT DEFAULT 'WAITING',
        otp_code TEXT DEFAULT NULL,
        api_source TEXT DEFAULT 'API1',
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_name TEXT,
        category TEXT,
        qty INTEGER,
        total_price REAL,
        content TEXT,
        date TEXT DEFAULT CURRENT_DATE
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS withdrawals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        method TEXT,
        account_number TEXT,
        status TEXT DEFAULT 'pending',
        date TEXT DEFAULT CURRENT_DATE
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS deposits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        method TEXT,
        trx_id TEXT UNIQUE,
        status TEXT DEFAULT 'pending'
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS countries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service_name TEXT,
        service_code TEXT DEFAULT '26134',
        country_name TEXT,
        country_flag TEXT DEFAULT '🌐',
        country_code TEXT,
        price REAL DEFAULT 0.00
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        subcategory TEXT DEFAULT '',
        name TEXT,
        price REAL
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS item_stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        content TEXT,
        status TEXT DEFAULT 'available'
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    
    defaults = {
        'bkash_num': '01625212609',
        'nagad_num': '01625212609',
        'binance_uid': '1133157464',
        'min_deposit': '20.0',
        'min_withdraw': '50.0',
        'deposit_bonus': '5',
        'refer_reward': '0.11',
        'otp_reward': '0.30',
        'signup_bonus': '0.00',
        'number_api_key': 'M7D4REK5Y06',
        'api_base_url': 'https://api.2oo9.cloud/MXS47FLFX0U/tnevs/@public/api',
        'getnum_url': 'https://api.2oo9.cloud/MXS47FLFX0U/tnevs/@public/api/getnum',
        'getmsg_url': 'https://api.2oo9.cloud/MXS47FLFX0U/tnevs/@public/api/success-otp',
        'number_api_key_2': 'M6SB7HZXXIX',
        'api_base_url_2': 'https://api.2oo9.cloud/MXS47FLFX0U/tnevs/@public/api',
        'getnum_url_2': 'https://api.2oo9.cloud/MXS47FLFX0U/tnevs/@public/api/getnum',
        'getmsg_url_2': 'https://api.2oo9.cloud/MXS47FLFX0U/tnevs/@public/api/success-otp',
        'force_channels': '',
        'otp_group_id': '@otpreciverpro',
        'otp_group_link': 'https://t.me/otpreciverpro'
    }
    for k, v in defaults.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
        
    cursor.execute("SELECT COUNT(*) FROM countries")
    if cursor.fetchone()[0] == 0:
        default_countries = [
            ('Facebook', '26134', 'Uzbekistan', '🇺🇿', 'uz', 0.00),
            ('Facebook', '26134', 'United Kingdom', '🇬🇧', 'uk', 0.00),
            ('Instagram', '26135', 'Uzbekistan', '🇺🇿', 'uz', 0.00),
            ('Telegram', '26136', 'Uzbekistan', '🇺🇿', 'uz', 0.00)
        ]
        cursor.executemany("INSERT INTO countries (service_name, service_code, country_name, country_flag, country_code, price) VALUES (?, ?, ?, ?, ?, ?)", default_countries)

    conn.commit()
    conn.close()

init_db()

def get_setting(key):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else ""

def set_setting(key, value):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def create_excel_document(product_name, lines):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Accounts"
    
    for idx, line in enumerate(lines, start=1):
        ws.cell(row=idx, column=1, value=line)
        
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    
    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_name = product_name.replace(" ", "_")
    file_name = f"{clean_name}_{now_str}.xlsx"
    return stream, file_name

# ----------------- FSM STATES -----------------
class UserState(StatesGroup):
    await_qty = State()
    await_w_acc = State()
    await_w_amt = State()
    await_dep_amt = State()
    await_trxid = State()

class AdminState(StatesGroup):
    setting_key = State()
    add_country = State()
    add_prod_info = State()
    await_stock_items = State()
    edit_balance = State()
    broadcast = State()

# ----------------- KEYBOARDS -----------------
def main_reply_keyboard(user_id):
    builder = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Get Free Number"), KeyboardButton(text="🛍️ Web Shop")],
            [KeyboardButton(text="👤 My Profile"), KeyboardButton(text="💳 Deposit")],
            [KeyboardButton(text="💸 Withdraw"), KeyboardButton(text="🔑 Get Code")],
            [KeyboardButton(text="🚥 LIVE TRAFFIC"), KeyboardButton(text="🎧 Support")]
        ],
        resize_keyboard=True
    )
    if user_id == ADMIN_ID:
        builder.keyboard.append([KeyboardButton(text="👑 Admin Panel")])
    return builder

# ----------------- API NUMBER FETCHER -----------------
async def async_fetch_number(range_id, api_source="API1"):
    if api_source == "API2":
        api_key = get_setting('number_api_key_2') or "M6SB7HZXXIX"
        url = get_setting('getnum_url_2') or "https://api.2oo9.cloud/MXS47FLFX0U/tnevs/@public/api/getnum"
    else:
        api_key = get_setting('number_api_key') or "M7D4REK5Y06"
        url = get_setting('getnum_url') or "https://api.2oo9.cloud/MXS47FLFX0U/tnevs/@public/api/getnum"
        
    headers = {"mauthapi": api_key, "Content-Type": "application/json"}
    payload = {"rid": str(range_id)}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=6) as response:
                if response.status == 200:
                    res = await response.json()
                    meta = res.get("meta", {})
                    if meta.get("code") == 200 and res.get("data"):
                        data = res["data"]
                        phone_num = data.get("full_number") or data.get("no_plus_number") or data.get("number")
                        return True, phone_num, api_source
                    return False, res.get("message") or meta.get("status") or "No Stock", api_source
                return False, "Server Error", api_source
    except Exception as e:
        return False, f"Connection Error: {e}", api_source

# ----------------- COMMAND HANDLERS -----------------
@router.message(CommandStart())
def cmd_start(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split()
    referred_by = int(args[1]) if len(args) > 1 and args[1].isdigit() and int(args[1]) != user_id else None
    signup_bonus = float(get_setting('signup_bonus') or 0.00)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.execute("INSERT INTO users (user_id, balance, referred_by) VALUES (?, ?, ?)", (user_id, signup_bonus, referred_by))
        if referred_by:
            cursor.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id=?", (referred_by,))
        conn.commit()
    conn.close()

    return message.answer(f"👋 <b>{BOT_NAME}</b>-এ আপনাকে স্বাগতম!", reply_markup=main_reply_keyboard(user_id))

# ----------------- ULTRA-FAST NUMBER ALLOCATION -----------------
@router.message(F.text.in_(["📱 Get Number", "📱 Get Free Number", "📱 NUMBER'S"]))
async def numbers_cmd(message: types.Message):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT service_name FROM countries")
    services = cursor.fetchall()
    conn.close()

    if not services:
        await message.answer("⚠️ বর্তমানে কোনো সার্ভিস এভেলেবল নেই। এডমিন প্যানেল থেকে যোগ করুন।")
        return

    builder = InlineKeyboardMarkup(inline_keyboard=[])
    row = []
    for s in services:
        srv_name = s[0]
        row.append(InlineKeyboardButton(text=f"⚙️ {srv_name}", callback_data=f"usr_srv|{srv_name}"))
        if len(row) == 2:
            builder.inline_keyboard.append(row)
            row = []
    if row:
        builder.inline_keyboard.append(row)

    await message.answer("⚙️ <b>Select a Service for OTP:</b>", reply_markup=builder)

@router.callback_query(F.data.startswith("usr_srv|"))
async def user_service_click(call: types.CallbackQuery):
    await call.answer()
    service_name = call.data.split("|")[1]
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT country_name, country_flag, country_code, service_code FROM countries WHERE service_name=?", (service_name,))
    countries = cursor.fetchall()
    conn.close()

    builder = InlineKeyboardMarkup(inline_keyboard=[])
    for c in countries:
        c_name, c_flag, c_code, s_code = c
        builder.inline_keyboard.append([
            InlineKeyboardButton(text=f"{c_flag} {c_name} (Dual API)", callback_data=f"buy|{s_code}|{c_code}|{service_name}")
        ])
    builder.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Back To Services", callback_data="back_to_services")])

    await call.message.edit_text(f"🌍 <b>Select country for {service_name}:</b> ⬇️", reply_markup=builder)

@router.callback_query(F.data == "back_to_services")
async def back_to_services_cb(call: types.CallbackQuery):
    await call.answer()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT service_name FROM countries")
    services = cursor.fetchall()
    conn.close()

    builder = InlineKeyboardMarkup(inline_keyboard=[])
    row = []
    for s in services:
        srv_name = s[0]
        row.append(InlineKeyboardButton(text=f"⚙️ {srv_name}", callback_data=f"usr_srv|{srv_name}"))
        if len(row) == 2:
            builder.inline_keyboard.append(row)
            row = []
    if row:
        builder.inline_keyboard.append(row)

    await call.message.edit_text("⚙️ <b>Select a Service:</b>", reply_markup=builder)

@router.callback_query(F.data.startswith("buy|"))
async def buy_number_click(call: types.CallbackQuery):
    await call.answer("⌛ Dual API থেকে নম্বর আনা হচ্ছে...")
    
    parts = call.data.split("|")
    range_id, c_code, service_name = parts[1], parts[2], parts[3]
    user_id = call.from_user.id

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT country_name, country_flag FROM countries WHERE service_name=? AND country_code=? LIMIT 1", (service_name, c_code))
    c_row = cursor.fetchone()
    c_name = c_row[0] if c_row else "Uzbekistan"
    c_flag = c_row[1] if c_row else "🇺🇿"
    conn.close()

    # Parallel requests to dual API providers
    results = await asyncio.gather(
        async_fetch_number(range_id, "API1"),
        async_fetch_number(range_id, "API2")
    )

    assigned_numbers = []
    conn = get_db()
    cursor = conn.cursor()
    for success, phone_or_err, api_src in results:
        if success and phone_or_err:
            assigned_numbers.append(phone_or_err)
            cursor.execute(
                "INSERT INTO verifications (user_id, phone_number, service_name, status, api_source) VALUES (?, ?, ?, 'WAITING', ?)",
                (user_id, phone_or_err, service_name, api_src)
            )
    conn.commit()
    conn.close()

    otp_group_link = get_setting('otp_group_link') or 'https://t.me/otpreciverpro'
    otp_reward_val = float(get_setting('otp_reward') or 0.30)

    builder = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👀 OTP GROUP ↗️", url=otp_group_link)],
        [
            InlineKeyboardButton(text="⚙️ Next Number", callback_data=f"buy|{range_id}|{c_code}|{service_name}"),
            InlineKeyboardButton(text="🌐 Select Country", callback_data=f"usr_srv|{service_name}")
        ]
    ])

    if not assigned_numbers:
        err_text = f"❌ <b>নম্বর আনা সম্ভব হয়নি!</b>\n\nবর্তমানে {c_flag} <b>{c_name} ({service_name})</b> এর জন্য নম্বর স্টকে নেই।"
        await call.message.edit_text(err_text, reply_markup=builder)
        return

    num_str_list = "\n".join([f"{c_flag} 📋 <code>{p}</code>" for p in assigned_numbers])
    text = (
        f"{c_flag} <b>{c_name}</b> 📘 <b>Number Assigned</b>\n\n"
        f"💰 <b>Per OTP Reward : {otp_reward_val:.2f} BDT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"{num_str_list}\n\n"
        f"⏳ <i>Waiting for OTP... (Background Scraper Monitoring 24/7)</i>"
    )
    await call.message.edit_text(text, reply_markup=builder)

# ----------------- WEB SHOP & MERCHANDISE -----------------
@router.message(F.text == "🛍️ Web Shop")
async def buy_products_cmd(message: types.Message):
    text = "🛍️ <b>Buy Products</b>\n\nSelect a category:"
    builder = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛡️ VPN", callback_data="cat_VPN"), InlineKeyboardButton(text="🌐 Proxy", callback_data="cat_Proxy")],
        [InlineKeyboardButton(text="📧 Mail", callback_data="cat_Mail")]
    ])
    await message.answer(text, reply_markup=builder)

@router.callback_query(F.data.startswith("cat_"))
async def category_select_cb(call: types.CallbackQuery):
    await call.answer()
    category = call.data.split("_")[1]
    
    if category == "VPN":
        text = "🛡️ <b>VPN — Select Duration:</b>"
        builder = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔐 3 Days", callback_data="vpndur_3 Days"), InlineKeyboardButton(text="🔐 7 Days", callback_data="vpndur_7 Days")],
            [InlineKeyboardButton(text="🔐 14 Days", callback_data="vpndur_14 Days"), InlineKeyboardButton(text="🔐 30 Days", callback_data="vpndur_30 Days")],
            [InlineKeyboardButton(text="‹ Back", callback_data="back_to_shop")]
        ])
        await call.message.edit_text(text, reply_markup=builder)
    else:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, price, subcategory FROM products WHERE category=?", (category,))
        products = cursor.fetchall()
        
        builder = InlineKeyboardMarkup(inline_keyboard=[])
        for p in products:
            p_id, p_name, p_price, p_sub = p
            cursor.execute("SELECT COUNT(*) FROM item_stock WHERE product_id=? AND status='available'", (p_id,))
            p_stock = cursor.fetchone()[0]
            plan_info = f" ({p_sub})" if p_sub else ""
            btn_text = f"📦 {p_name}{plan_info} · {p_price:.2f} BDT · {p_stock} in stock"
            builder.inline_keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=f"selectprod_{p_id}")])
            
        builder.inline_keyboard.append([InlineKeyboardButton(text="‹ Back", callback_data="back_to_shop")])
        conn.close()
        await call.message.edit_text(f"🛍️ <b>{category} Products:</b>", reply_markup=builder)

@router.callback_query(F.data == "back_to_shop")
async def back_to_shop_cb(call: types.CallbackQuery):
    await call.answer()
    text = "🛍️ <b>Buy Products</b>\n\nSelect a category:"
    builder = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛡️ VPN", callback_data="cat_VPN"), InlineKeyboardButton(text="🌐 Proxy", callback_data="cat_Proxy")],
        [InlineKeyboardButton(text="📧 Mail", callback_data="cat_Mail")]
    ])
    await call.message.edit_text(text, reply_markup=builder)

@router.callback_query(F.data.startswith("selectprod_"))
async def select_prod_cb(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    p_id = int(call.data.split("_")[1])
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name, price, category, subcategory FROM products WHERE id=?", (p_id,))
    prod = cursor.fetchone()
    
    if not prod:
        conn.close()
        return
        
    p_name, p_price, p_cat, p_sub = prod
    cursor.execute("SELECT COUNT(*) FROM item_stock WHERE product_id=? AND status='available'", (p_id,))
    p_stock = cursor.fetchone()[0]
    conn.close()

    await state.update_data(buying_p_id=p_id)
    await state.set_state(UserState.await_qty)
    
    sub_info = f" ({p_sub})" if p_sub else ""
    text = (
        f"📦 <b>{p_name}{sub_info}</b>\n"
        f"⚡ <b>Price: {p_price:.2f} BDT / piece</b>\n"
        f"⚡ <b>Available: {p_stock}</b>\n\n"
        f"Enter quantity to purchase:"
    )
    builder = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_action")]])
    await call.message.answer(text, reply_markup=builder)

@router.message(UserState.await_qty)
async def process_purchase_qty(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ সঠিক সংখ্যা টাইপ করুন।")
        return

    qty = int(message.text)
    data = await state.get_data()
    p_id = data.get("buying_p_id")
    user_id = message.from_user.id

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name, price, category, subcategory FROM products WHERE id=?", (p_id,))
    prod = cursor.fetchone()
    
    if not prod:
        conn.close()
        await message.answer("❌ প্রোডাক্টটি পাওয়া যায়নি!")
        await state.clear()
        return

    p_name, p_price, p_cat, p_sub = prod
    cursor.execute("SELECT COUNT(*) FROM item_stock WHERE product_id=? AND status='available'", (p_id,))
    p_stock = cursor.fetchone()[0]

    if qty <= 0 or qty > p_stock:
        conn.close()
        await message.answer(f"❌ পর্যাপ্ত স্টক নেই! সর্বোচ্চ {p_stock} টি নিতে পারবেন।")
        return

    total_bdt = qty * p_price
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    bal = cursor.fetchone()[0]
    conn.close()

    await state.clear()
    sub_info = f" ({p_sub})" if p_sub else ""
    text = (
        f"📬 <b>Order Summary</b>\n\n"
        f"⚡ <b>Item     :</b> {p_name}{sub_info}\n"
        f"👥 <b>Quantity :</b> {qty}\n"
        f"💰 <b>Total    :</b> {total_bdt:.2f} BDT\n"
        f"💳 <b>Balance  :</b> {bal:.2f} BDT"
    )
    builder = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Confirm Order", callback_data=f"cfmbuy_{p_id}_{qty}")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_action")]
    ])
    await message.answer(text, reply_markup=builder)

@router.callback_query(F.data.startswith("cfmbuy_"))
async def confirm_order_cb(call: types.CallbackQuery):
    await call.answer()
    parts = call.data.split("_")
    p_id, qty = int(parts[1]), int(parts[2])
    user_id = call.from_user.id

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name, price, category FROM products WHERE id=?", (p_id,))
    prod = cursor.fetchone()
    p_name, p_price, p_cat = prod[0], prod[1], prod[2]
    total_bdt = qty * p_price

    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    bal = cursor.fetchone()[0]

    if bal < total_bdt:
        conn.close()
        await call.message.edit_text(f"❌ পর্যাপ্ত ব্যালেন্স নেই! প্রয়োজন: {total_bdt:.2f} BDT")
        return

    cursor.execute("SELECT id, content FROM item_stock WHERE product_id=? AND status='available' LIMIT ?", (p_id, qty))
    items = cursor.fetchall()

    if len(items) < qty:
        conn.close()
        await call.message.edit_text("❌ পর্যাপ্ত স্টক খালি নেই!")
        return

    delivered_lines = []
    for item_id, content in items:
        delivered_lines.append(content)
        cursor.execute("UPDATE item_stock SET status='sold' WHERE id=?", (item_id,))

    cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (total_bdt, user_id))
    joined_content = "\n".join(delivered_lines)
    cursor.execute("INSERT INTO purchases (user_id, product_name, category, qty, total_price, content) VALUES (?, ?, ?, ?, ?, ?)",
                   (user_id, p_name, p_cat, qty, total_bdt, joined_content))
    conn.commit()
    conn.close()

    if p_cat == "Mail":
        excel_stream, file_name = create_excel_document(p_name, delivered_lines)
        input_file = BufferedInputFile(excel_stream.read(), filename=file_name)
        await call.message.answer_document(input_file, caption=f"✅ <b>{p_name} Delivered!</b> ({qty} pcs)")
    else:
        out_text = f"✅ <b>{p_name} Delivered!</b>\n\n" + "\n".join([f"<code>{line}</code>" for line in delivered_lines])
        await call.message.answer(out_text)

# ----------------- USER PROFILE & LEDGER -----------------
@router.message(F.text == "👤 My Profile")
async def profile_cmd(message: types.Message):
    user_id = message.from_user.id
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT balance, reward_balance, referrals, joined_date, otp_count FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    bal = row[0] if row else 0.00
    rew_bal = row[1] if row else 0.00
    refs = row[2] if row else 0
    joined = row[3] if row else "N/A"
    otps = row[4] if row else 0
    ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"

    text = (
        f"👤 <b>My Profile</b>\n\n"
        f"🆔 <b>User ID  :</b> <code>{user_id}</code>\n"
        f"💰 <b>Balance  :</b> {bal:.2f} BDT\n"
        f"🎁 <b>Reward Bal :</b> {rew_bal:.2f} BDT\n"
        f"🥳 <b>Joined   :</b> {joined}\n"
        f"🔢 <b>OTP Received :</b> {otps}\n"
        f"🤝 <b>Referrals :</b> {refs}\n\n"
        f"🔗 <b>Referral Link:</b>\n<code>{ref_link}</code>"
    )
    builder = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📜 Purchase History", callback_data="view_purchases")]])
    await message.answer(text, reply_markup=builder)

@router.callback_query(F.data == "view_purchases")
async def view_purchases_cb(call: types.CallbackQuery):
    await call.answer()
    user_id = call.from_user.id
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT product_name, category, total_price, content, date FROM purchases WHERE user_id=? ORDER BY id DESC LIMIT 5", (user_id,))
    purchases = cursor.fetchall()
    conn.close()

    if not purchases:
        await call.message.answer("📜 আপনার কোনো পারচেজ হিস্ট্রি নেই।")
        return

    for p_name, p_cat, p_price, p_content, p_date in purchases:
        hist_text = f"⚡ <b>Purchase Details</b>\nDate: {p_date}\nTotal: {p_price:.2f} BDT\nItem: {p_name}\n<code>{p_content}</code>"
        await call.message.answer(hist_text)

# ----------------- DEPOSIT & WITHDRAWAL HANDLERS -----------------
@router.message(F.text.in_(["💸 Withdraw", "Withdraw"]))
async def withdraw_cmd(message: types.Message):
    user_id = message.from_user.id
    min_w = float(get_setting('min_withdraw') or 50.0)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT reward_balance FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    rew_bal = row[0] if row else 0.0
    conn.close()

    if rew_bal < min_w:
        await message.answer(f"❌ উইথড্র করার জন্য পর্যাপ্ত রিওয়ার্ড ব্যালেন্স নেই!\nসর্বনিম্ন: {min_w:.2f} BDT")
        return

    builder = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌸 bKash", callback_data="w_method_BKASH"), InlineKeyboardButton(text="🟠 Nagad", callback_data="w_method_NAGAD")],
        [InlineKeyboardButton(text="🟡 Binance", callback_data="w_method_BINANCE")]
    ])
    await message.answer("💸 <b>Select Withdrawal Method:</b>", reply_markup=builder)

@router.callback_query(F.data.startswith("w_method_"))
async def withdraw_method_cb(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    method = call.data.split("_")[2]
    await state.update_data(w_method=method)
    await state.set_state(UserState.await_w_acc)
    await call.message.answer(f"✏️ Enter your {method} Account Number / Pay UID:")

@router.message(UserState.await_w_acc)
async def process_w_acc(message: types.Message, state: FSMContext):
    await state.update_data(w_acc=message.text.strip())
    await state.set_state(UserState.await_w_amt)
    await message.answer("💸 Enter withdrawal amount in BDT:")

@router.message(UserState.await_w_amt)
async def process_w_amt(message: types.Message, state: FSMContext):
    if not message.text.replace('.', '', 1).isdigit():
        await message.answer("❌ সঠিক সংখ্যা টাইপ করুন।")
        return

    amt = float(message.text)
    user_id = message.from_user.id
    data = await state.get_data()
    method, acc = data.get("w_method"), data.get("w_acc")
    min_w = float(get_setting('min_withdraw') or 50.0)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT reward_balance FROM users WHERE user_id=?", (user_id,))
    rew_bal = cursor.fetchone()[0]

    if amt < min_w or rew_bal < amt:
        conn.close()
        await message.answer("❌ পর্যাপ্ত ব্যালেন্স নেই বা পরিমাণ সর্বনিম্ন উইথড্র থেকে কম।")
        await state.clear()
        return

    cursor.execute("UPDATE users SET reward_balance = reward_balance - ? WHERE user_id=?", (amt, user_id))
    cursor.execute("INSERT INTO withdrawals (user_id, amount, method, account_number) VALUES (?, ?, ?, ?)", (user_id, amt, method, acc))
    conn.commit()
    conn.close()

    await state.clear()
    await message.answer(f"✅ আপনার {amt:.2f} BDT উইথড্র রিকুয়েস্ট সফলভাবে সাবমিট হয়েছে!")

@router.message(F.text == "💳 Deposit")
async def deposit_cmd(message: types.Message):
    builder = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 bKash", callback_data="dep_bkash"), InlineKeyboardButton(text="💸 Nagad", callback_data="dep_nagad")],
        [InlineKeyboardButton(text="💸 Binance", callback_data="dep_binance")]
    ])
    await message.answer("💳 <b>Select Deposit Payment Method:</b>", reply_markup=builder)

@router.callback_query(F.data.startswith("dep_"))
async def dep_method_cb(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    method = call.data.split("_")[1]
    min_dep = get_setting('min_deposit') or '20.0'
    num = get_setting(f'{method}_num') if method != 'binance' else get_setting('binance_uid')

    await state.update_data(dep_method=method, dep_num=num)
    await state.set_state(UserState.await_dep_amt)
    await call.message.answer(f"Enter deposit amount in BDT (Min {min_dep} BDT):")

@router.message(UserState.await_dep_amt)
async def process_dep_amt(message: types.Message, state: FSMContext):
    if not message.text.replace('.', '', 1).isdigit():
        await message.answer("❌ সঠিক সংখ্যা টাইপ করুন।")
        return

    amt = float(message.text)
    data = await state.get_data()
    method, num = data.get("dep_method"), data.get("dep_num")

    await state.update_data(dep_amt=amt)
    await state.set_state(UserState.await_trxid)

    builder = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_action")]])
    await message.answer(f"Send <b>{amt:.2f} BDT</b> to <code>{num}</code> ({method.upper()}).\n\nEnter TrxID below:", reply_markup=builder)

@router.message(UserState.await_trxid)
async def process_trxid(message: types.Message, state: FSMContext):
    trx_id = message.text.strip().upper()
    user_id = message.from_user.id
    data = await state.get_data()
    method, amt = data.get("dep_method"), data.get("dep_amt")

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO deposits (user_id, amount, method, trx_id) VALUES (?, ?, ?, ?)", (user_id, amt, method.upper(), trx_id))
        conn.commit()
        await message.answer("✅ ডিপোজিট রিকুয়েস্ট সফলভাবে সাবমিট হয়েছে। এডমিন ভেরিফাই করে এপ্রুভ করে দেবে।")
    except sqlite3.IntegrityError:
        await message.answer("❌ এই TrxID টি আগেই ব্যবহার করা হয়েছে!")
    finally:
        conn.close()
        await state.clear()

@router.callback_query(F.data == "cancel_action")
async def cancel_action_cb(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    await call.message.edit_text("❌ অপশনটি বাতিল করা হয়েছে।")

@router.message(F.text == "🔑 Get Code")
async def get_code_cmd(message: types.Message):
    builder = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Hotmail/Outlook Reader ↗", url="https://dongvanfb.net/read_mail_box/")]
    ])
    await message.answer("🔑 <b>Get Mail Code Reader:</b>", reply_markup=builder)

@router.message(F.text == "🚥 LIVE TRAFFIC")
async def live_traffic_cmd(message: types.Message):
    await message.answer("📊 <b>LIVE TRAFFIC ENGINE</b>\nStatus: Dual API SMS Broker Active 24/7.")

@router.message(F.text == "🎧 Support")
async def support_cmd(message: types.Message):
    await message.answer("🎧 <b>Support:</b> @your_telegram_username")

# ----------------- ADMIN PANEL -----------------
@router.message(F.text == "👑 Admin Panel")
async def admin_panel_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    builder = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Pending Deposits", callback_data="adm_view_pending_dep")],
        [InlineKeyboardButton(text="📤 Pending Withdrawals", callback_data="adm_view_pending_w")]
    ])
    await message.answer("👑 <b>Admin Control Panel</b>", reply_markup=builder)

# ----------------- EMBEDDED WEB SERVER -----------------
async def handle_web_ping(request):
    return web.Response(text="OTP Receiver Pro Bot & Background Scraper Alive 24/7!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_web_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    print("🚀 Embedded Web Server started on port 8080.")

# ----------------- SUBPROCESS LAUNCHER & BOT START -----------------
def launch_background_scraper():
    try:
        subprocess.Popen([sys.executable, "scraper.py"])
        print("⚡ Background Scraper process launched (scraper.py).")
    except Exception as e:
        print(f"❌ Failed to launch background scraper: {e}")

async def main():
    launch_background_scraper()
    await start_web_server()
    print(f"🤖 {BOT_NAME} Customer Panel Started Successfully...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
