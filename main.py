import sqlite3
import telebot
import time
import requests
import threading
import io
import datetime
import openpyxl
from flask import Flask
from telebot import types
from contextlib import contextmanager

# ==================== KEEP-ALIVE & 1-MIN SELF-PING ENGINE ====================
app = Flask('')

@app.route('/')
def home():
    return "VoltXSMS OTP Bot is Alive 24/7!"

def run_flask():
    try:
        app.run(host='0.0.0.0', port=8080)
    except Exception as e:
        print(f"Flask Server Error: {e}")

def self_ping():
    time.sleep(10)
    url = "https://my-otp-bot-d7jk.onrender.com"  # আপনার Render ওয়েবসাইট লিংক
    while True:
        try:
            requests.get(url, timeout=10)
            print("🚀 1-Min Self-ping successful! Render kept awake.")
        except Exception:
            pass
        time.sleep(60)

threading.Thread(target=run_flask, daemon=True).start()
threading.Thread(target=self_ping, daemon=True).start()

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8842802759:AAFTzG_yyzHiirBiW2Canl2l0t_sG2HxKt8" # আপনার বটের টোকেন
ADMIN_ID = 8125384914                                       # আপনার Admin ID
DB_NAME = "fresh_master_shop.db"
# =======================================================

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

USER_STATES = {}

def set_user_state(user_id, key, value):
    if user_id not in USER_STATES:
        USER_STATES[user_id] = {}
    USER_STATES[user_id][key] = value

def get_user_state(user_id, key, default=None):
    return USER_STATES.get(user_id, {}).get(key, default)

def clear_user_state(user_id):
    if user_id in USER_STATES:
        USER_STATES[user_id].clear()

# Context Manager for Safe Database Connections
@contextmanager
def get_db():
    conn = sqlite3.connect(DB_NAME, timeout=15)
    try:
        yield conn
    finally:
        conn.close()

# Helper function to generate Excel File (.xlsx)
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
    stream.name = file_name
    return stream

# ----------------- DATABASE INITIALIZATION -----------------
def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        
        # Users Table
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 6.00,
            referrals INTEGER DEFAULT 0,
            referred_by INTEGER,
            otp_count INTEGER DEFAULT 0,
            joined_date TEXT DEFAULT CURRENT_DATE
        )''')
        
        # Active API Number Orders Table (VoltXSMS Live Tracker)
        cursor.execute('''CREATE TABLE IF NOT EXISTS active_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            order_id TEXT,
            phone_number TEXT,
            service TEXT,
            country TEXT,
            status TEXT DEFAULT 'WAITING',
            last_code TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Dynamic Countries / Services Table
        cursor.execute('''CREATE TABLE IF NOT EXISTS countries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_name TEXT,
            service_code TEXT DEFAULT 'fb',
            country_name TEXT,
            country_flag TEXT DEFAULT '🌐',
            country_code TEXT,
            price REAL DEFAULT 0.00
        )''')
        
        # Products Table (Web Shop)
        cursor.execute('''CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            name TEXT,
            price REAL
        )''')
        
        # Inventory Stock Table
        cursor.execute('''CREATE TABLE IF NOT EXISTS item_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            content TEXT,
            status TEXT DEFAULT 'available'
        )''')
        
        # Deposits Table
        cursor.execute('''CREATE TABLE IF NOT EXISTS deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            method TEXT,
            trx_id TEXT UNIQUE,
            status TEXT DEFAULT 'pending'
        )''')
        
        # System Settings Table
        cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )''')
        
        # Default Settings
        defaults = {
            'bkash_num': '01833878871',
            'nagad_num': '01833878871',
            'binance_uid': '87654321',
            'min_deposit': '20.0',
            'deposit_bonus': '5',
            'refer_reward': '0.11',
            'number_api_key': 'YOUR_VOLTXSMS_API_KEY_HERE',
            'api_base_url': 'https://voltxsms.com/stubs/handler_api.php',
            'force_channels': '',
            'otp_group_link': 'https://t.me/your_otp_group'
        }
        for k, v in defaults.items():
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
            
        cursor.execute("SELECT COUNT(*) FROM countries")
        if cursor.fetchone()[0] == 0:
            default_countries = [
                ('Facebook', 'fb', 'Uzbekistan', '🇺🇿', 'uz', 0.00),
                ('Facebook', 'fb', 'Tanzania', '🇹🇿', 'tz', 0.00),
                ('Facebook', 'fb', 'Tajikistan', '🇹🇯', 'tj', 0.00),
                ('Facebook', 'fb', 'Egypt', '🇪🇬', 'eg', 0.00),
                ('Instagram', 'ig', 'Uzbekistan', '🇺🇿', 'uz', 0.00),
                ('Telegram', 'tg', 'Uzbekistan', '🇺🇿', 'uz', 0.00)
            ]
            cursor.executemany("INSERT INTO countries (service_name, service_code, country_name, country_flag, country_code, price) VALUES (?, ?, ?, ?, ?, ?)", default_countries)

        conn.commit()

init_db()

def get_setting(key):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
        res = cursor.fetchone()
        return res[0] if res else ""

def set_setting(key, value):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()

# ----------------- VOLTXSMS API ENGINE -----------------
def voltx_get_number(service_code, country_code):
    api_key = get_setting('number_api_key')
    base_url = get_setting('api_base_url') or "https://voltxsms.com/stubs/handler_api.php"
    
    url = f"{base_url}?api_key={api_key}&action=getNumber&service={service_code}&country={country_code}"
    try:
        res = requests.get(url, timeout=12).text.strip()
        if res.startswith("ACCESS_NUMBER"):
            parts = res.split(":")
            order_id = parts[1]
            phone_num = parts[2]
            return True, order_id, phone_num
        elif "NO_NUMBERS" in res:
            return False, "❌ প্রোভাইডারের কাছে বর্তমানে কোনো ফ্রি নম্বর নেই!", None
        elif "NO_BALANCE" in res:
            return False, "❌ API প্যানেলে পর্যাপ্ত ব্যালেন্স নেই!", None
        elif "BAD_KEY" in res:
            return False, "❌ VoltXSMS API Key ভুল দেওয়া হয়েছে!", None
        else:
            return False, f"⚠️ API Error: {res}", None
    except Exception as e:
        return False, f"⚠️ সংযোগ বিচ্ছিন্ন: {e}", None

def voltx_check_sms(order_id):
    api_key = get_setting('number_api_key')
    base_url = get_setting('api_base_url') or "https://voltxsms.com/stubs/handler_api.php"
    
    url = f"{base_url}?api_key={api_key}&action=getStatus&id={order_id}"
    try:
        res = requests.get(url, timeout=8).text.strip()
        if "STATUS_OK" in res:
            code = res.split(":")[1].strip()
            return "RECEIVED", code
        elif "STATUS_CANCEL" in res:
            return "CANCELLED", None
        else:
            return "WAITING", None
    except Exception:
        return "WAITING", None

# ----------------- 🔄 AUTO OTP POLLING THREAD (24/7 AUTO CHECK) -----------------
def auto_otp_checker_loop():
    print("🚀 Auto OTP Checker Thread Started...")
    while True:
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, user_id, order_id, phone_number, service FROM active_orders WHERE status='WAITING'")
                active_orders = cursor.fetchall()

            for order in active_orders:
                db_id, user_id, order_id, phone_num, service_name = order
                status, otp_code = voltx_check_sms(order_id)

                if status == "RECEIVED" and otp_code:
                    # Update Database Order Status
                    with get_db() as conn:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE active_orders SET status='COMPLETED', last_code=? WHERE id=?", (otp_code, db_id))
                        cursor.execute("UPDATE users SET otp_count = otp_count + 1 WHERE user_id=?", (user_id,))
                        conn.commit()

                    # Push Instant Telegram Message with Tap-To-Copy OTP
                    text = (
                        f"📩 <b>NEW OTP RECEIVED FOR {service_name.upper()}!</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"📱 <b>Number:</b> <code>{phone_num}</code>\n"
                        f"🔑 <b>Your OTP Code:</b> <code>{otp_code}</code>\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"👉 <i>কোডের ওপর টাচ করলেই অটোমেটিক কপি হয়ে যাবে!</i>"
                    )
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("📋 Copy Code", callback_data=f"dummy_copy"))
                    try:
                        bot.send_message(user_id, text, reply_markup=markup)
                    except Exception as e:
                        print(f"Failed to send OTP to user {user_id}: {e}")

                elif status == "CANCELLED":
                    with get_db() as conn:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE active_orders SET status='CANCELLED' WHERE id=?", (db_id,))
                        conn.commit()

        except Exception as e:
            print(f"Error in OTP Checker Loop: {e}")

        time.sleep(5)  # Runs every 5 seconds

threading.Thread(target=auto_otp_checker_loop, daemon=True).start()

# ----------------- FORCE JOIN CHECKER -----------------
def is_user_joined(user_id):
    if user_id == ADMIN_ID:
        return True
    raw_channels = get_setting('force_channels')
    if not raw_channels:
        return True
    
    channels = [c.strip() for c in raw_channels.split(',') if c.strip()]
    for ch in channels:
        try:
            member = bot.get_chat_member(ch, user_id)
            if member.status not in ['creator', 'administrator', 'member']:
                return False
        except Exception:
            pass
    return True

def send_force_join_msg(chat_id):
    raw_channels = get_setting('force_channels')
    channels = [c.strip() for c in raw_channels.split(',') if c.strip()]
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for idx, ch in enumerate(channels, start=1):
        clean_ch = ch.replace("@", "")
        markup.add(types.InlineKeyboardButton(f"📢 Join Channel #{idx}", url=f"https://t.me/{clean_ch}"))
        
    markup.add(types.InlineKeyboardButton("✅ Verify / I Have Joined", callback_data="check_join_verify"))
    bot.send_message(
        chat_id,
        "⚠️ <b>বট ব্যবহার করতে হলে আপনাকে আমাদের অফিশিয়াল চ্যানেলে জয়েন হতে হবে!</b>\n\n"
        "নিচের বাটনে চাপ দিয়ে চ্যানেলে জয়েন করুন, তারপর <b>Verify</b> বাটনে ক্লিক করুন:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "check_join_verify")
def check_join_verify_cb(call):
    if is_user_joined(call.from_user.id):
        bot.answer_callback_query(call.id, "🎉 ভেরিফিকেশন সফল হয়েছে!", show_alert=True)
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "👋 <b>স্বাগতম!</b> এখন আপনি বটের সকল সুবিধা উপভোগ করতে পারবেন।", reply_markup=main_reply_keyboard(call.from_user.id))
    else:
        bot.answer_callback_query(call.id, "❌ আপনি এখনো সবগুলো চ্যানেলে জয়েন করেননি! আগে জয়েন করুন।", show_alert=True)

# ----------------- MAIN KEYBOARD -----------------
def main_reply_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("📱 Get Free Number"), types.KeyboardButton("🛍️ Web Shop"))
    markup.add(types.KeyboardButton("👤 My Profile"), types.KeyboardButton("💳 Deposit"))
    markup.add(types.KeyboardButton("🔑 Get Code"), types.KeyboardButton("🚥 LIVE TRAFFIC"))
    markup.add(types.KeyboardButton("🎧 Support"))
    if user_id == ADMIN_ID:
        markup.add(types.KeyboardButton("👑 Admin Panel"))
    return markup

# ----------------- START COMMAND -----------------
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    
    if not is_user_joined(user_id):
        send_force_join_msg(message.chat.id)
        return

    args = message.text.split()
    referred_by = int(args[1]) if len(args) > 1 and args[1].isdigit() and int(args[1]) != user_id else None

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        user = cursor.fetchone()

        if not user:
            cursor.execute("INSERT INTO users (user_id, balance, referred_by) VALUES (?, 6.00, ?)", (user_id, referred_by))
            if referred_by:
                cursor.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id=?", (referred_by,))
            conn.commit()

    bot.send_message(message.chat.id, "👋 <b>VOLTXSMS AUTOMATED OTP BOT</b>-এ আপনাকে স্বাগতম!", reply_markup=main_reply_keyboard(user_id))

# ----------------- 📱 AUTOMATED VOLTXSMS NUMBER GETTER -----------------
@bot.message_handler(func=lambda msg: msg.text in ["📱 Get Number", "📱 Get Free Number", "📱 NUMBER'S"])
def numbers_cmd(message):
    if not is_user_joined(message.from_user.id):
        send_force_join_msg(message.chat.id)
        return

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT service_name, service_code FROM countries")
        services = cursor.fetchall()

    if not services:
        bot.send_message(message.chat.id, "⚠️ বর্তমানে কোনো সার্ভিস এভেলেবল নেই। এডমিন প্যানেল থেকে যোগ করুন।")
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    for s in services:
        markup.add(types.InlineKeyboardButton(f"⚙️ {s[0]}", callback_data=f"usr_srv_{s[0]}"))

    bot.send_message(message.chat.id, "⚙️ <b>Select a Service for OTP:</b>", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("usr_srv_"))
def user_service_click(call):
    bot.answer_callback_query(call.id)
    service_name = call.data.split("_")[2]
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT country_name, country_flag, country_code, service_code FROM countries WHERE service_name=?", (service_name,))
        countries = cursor.fetchall()
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for c in countries:
            c_name, c_flag, c_code, s_code = c
            btn_text = f"{c_flag} {c_name} (Auto API)"
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"buy_{s_code}_{c_code}_{service_name}"))

    markup.add(types.InlineKeyboardButton("⬅️ Back To Services", callback_data="back_to_services"))
    bot.edit_message_text(f"🌍 <b>Select country for {service_name}:</b> ⬇️", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_services")
def back_to_services_cb(call):
    bot.answer_callback_query(call.id)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT service_name FROM countries")
        services = cursor.fetchall()

    markup = types.InlineKeyboardMarkup(row_width=2)
    for s in services:
        markup.add(types.InlineKeyboardButton(f"⚙️ {s[0]}", callback_data=f"usr_srv_{s[0]}"))

    bot.edit_message_text("⚙️ <b>Select a Service:</b>", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def buy_number_click(call):
    bot.answer_callback_query(call.id, "⌛ API থেকে নম্বর নেওয়া হচ্ছে, অপেক্ষা করুন...", show_alert=False)
    _, s_code, c_code, service_name = call.data.split("_")
    user_id = call.from_user.id

    # Call VoltXSMS Live API
    success, order_id_or_err, phone_num = voltx_get_number(s_code, c_code)

    if not success:
        bot.send_message(call.message.chat.id, f"❌ <b>নম্বর আনা সম্ভব হয়নি!</b>\n\nকারন: {order_id_or_err}")
        return

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO active_orders (user_id, order_id, phone_number, service, country) VALUES (?, ?, ?, ?, ?)",
            (user_id, order_id_or_err, phone_num, service_name, c_code)
        )
        conn.commit()
        db_order_id = cursor.lastrowid

    otp_group_link = get_setting('otp_group_link') or 'https://t.me/your_otp_group'

    text = (
        f"📱 <b>{service_name.upper()} NUMBER ASSIGNED!</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📞 <b>Phone Number:</b> <code>{phone_num}</code>\n"
        f"<i>(নম্বরে ক্লিক করলেই অটোমেটিক কপি হয়ে যাবে)</i>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"⏳ <b>Waiting for OTP...</b>\n"
        f"<i>ফেসবুক/সার্ভিস থেকে কোড পাঠানোর সাথে সাথে অটোমেটিক মেসেজ চলে আসবে!</i>"
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🔄 Refresh / Check OTP", callback_data=f"check_otp_{db_order_id}"))
    markup.add(
        types.InlineKeyboardButton("⚙️ Get Another Number", callback_data=f"usr_srv_{service_name}"),
        types.InlineKeyboardButton("👀 OTP GROUP ↗️", url=otp_group_link)
    )

    bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("check_otp_"))
def check_otp_cb(call):
    db_id = call.data.split("_")[2]
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT order_id, phone_number, last_code, status FROM active_orders WHERE id=?", (db_id,))
        res = cursor.fetchone()

    if res:
        order_id, phone_num, last_code, status = res
        if last_code:
            bot.answer_callback_query(call.id, "✅ OTP পাওয়া গেছে!", show_alert=True)
            bot.send_message(
                call.message.chat.id,
                f"📩 <b>OTP Received for <code>{phone_num}</code></b>\n\n"
                f"🔑 Your Code: <code>{last_code}</code>\n\n"
                f"<i>(কোডের ওপর ক্লিক করলেই অটো কপি হয়ে যাবে)</i>"
            )
            return

        # Check API status on button click
        status_res, code = voltx_check_sms(order_id)
        if status_res == "RECEIVED" and code:
            bot.answer_callback_query(call.id, "✅ OTP পাওয়া গেছে!", show_alert=True)
            bot.send_message(
                call.message.chat.id,
                f"📩 <b>OTP Received for <code>{phone_num}</code></b>\n\n"
                f"🔑 Your Code: <code>{code}</code>\n\n"
                f"<i>(কোডের ওপর ক্লিক করলেই অটো কপি হয়ে যাবে)</i>"
            )
        else:
            bot.answer_callback_query(call.id, "⏳ এখনো কোনো OTP আসেনি! অনুগ্রহ করে অপেক্ষা করুন...", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "dummy_copy")
def dummy_copy_cb(call):
    bot.answer_callback_query(call.id, "📋 টেক্সটের ওপর ক্লিক করুন, অটো কপি হয়ে যাবে!", show_alert=False)

@bot.message_handler(func=lambda msg: msg.text == "🚥 LIVE TRAFFIC")
def live_traffic_cmd(message):
    bot.send_message(message.chat.id, "📊 <b>LIVE TRAFFIC</b>\n━━━━━━━━━━━━━━━━━━\n🌐 <b>VoltXSMS Engine:</b> Connected\nOTP Monitoring Running 24/7 Auto Polling...")

# ----------------- 🛍️ WEB SHOP SYSTEM -----------------
@bot.message_handler(func=lambda msg: msg.text == "🛍️ Web Shop")
def buy_products_cmd(message):
    if not is_user_joined(message.from_user.id):
        send_force_join_msg(message.chat.id)
        return

    text = "🛍️ <b>Buy Products</b>\n\nSelect a category:"
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🛡️ VPN", callback_data="cat_VPN"),
        types.InlineKeyboardButton("🌐 Proxy", callback_data="cat_Proxy")
    )
    markup.add(types.InlineKeyboardButton("📧 Mail", callback_data="cat_Mail"))
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("cat_"))
def category_select_cb(call):
    bot.answer_callback_query(call.id)
    category = call.data.split("_")[1]
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, price FROM products WHERE category=?", (category,))
        products = cursor.fetchall()
        
        if not products:
            bot.answer_callback_query(call.id, "⚠️ এই ক্যাটাগরিতে বর্তমানে কোনো প্রডাক্ট নেই!", show_alert=True)
            return

        text = f"<b>{category} — Select Product:</b>"
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        for p in products:
            p_id, p_name, p_price = p
            cursor.execute("SELECT COUNT(*) FROM item_stock WHERE product_id=? AND status='available'", (p_id,))
            p_stock = cursor.fetchone()[0]
            btn_text = f"📧 {p_name} · {p_price:.2f} BDT · {p_stock} in stock"
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"selectprod_{p_id}"))
            
    markup.add(types.InlineKeyboardButton("‹ Back", callback_data="back_to_shop"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_shop")
def back_to_shop_cb(call):
    bot.answer_callback_query(call.id)
    text = "🛍️ <b>Buy Products</b>\n\nSelect a category:"
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🛡️ VPN", callback_data="cat_VPN"),
        types.InlineKeyboardButton("🌐 Proxy", callback_data="cat_Proxy")
    )
    markup.add(types.InlineKeyboardButton("📧 Mail", callback_data="cat_Mail"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("selectprod_"))
def select_prod_cb(call):
    bot.answer_callback_query(call.id)
    p_id = call.data.split("_")[1]
    user_id = call.from_user.id
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, price FROM products WHERE id=?", (p_id,))
        prod = cursor.fetchone()
        
        if not prod:
            return
            
        p_name, p_price = prod
        cursor.execute("SELECT COUNT(*) FROM item_stock WHERE product_id=? AND status='available'", (p_id,))
        p_stock = cursor.fetchone()[0]
    
    set_user_state(user_id, "buying_p_id", str(p_id))
    set_user_state(user_id, "step", "await_qty")
    
    text = (
        f"📧 <b>{p_name}</b>\n"
        f"⚡ <b>{p_price:.2f} BDT / piece</b>\n"
        f"⚡ <b>Available: {p_stock}</b>\n\n"
        f"Enter quantity:"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_action"))
    bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("cfmbuy_"))
def confirm_order_cb(call):
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id
    
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except Exception:
        pass

    parts = call.data.split("_")
    p_id = int(parts[1])
    qty = int(parts[2])
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, price FROM products WHERE id=?", (p_id,))
        prod = cursor.fetchone()
        if not prod:
            bot.edit_message_text("❌ প্রোডাক্টটি পাওয়া যায়নি!", call.message.chat.id, call.message.message_id)
            return
            
        p_name, p_price = prod
        total_bdt = qty * p_price
        
        cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        user_row = cursor.fetchone()
        bal = user_row[0] if user_row else 0.0
        
        if bal < total_bdt:
            bot.edit_message_text(
                f"❌ <b>অর্ডার সম্পূর্ণ করা সম্ভব হয়নি!</b>\n\n"
                f"আপনার ব্যালেন্স: <b>{bal:.2f} BDT</b>\n"
                f"প্রয়োজন: <b>{total_bdt:.2f} BDT</b>\n\n"
                f"অনুগ্রহ করে 💳 Deposit সার্ভিস থেকে রিচার্জ করুন।",
                call.message.chat.id, call.message.message_id
            )
            return
            
        cursor.execute("SELECT id, content FROM item_stock WHERE product_id=? AND status='available' LIMIT ?", (p_id, qty))
        items = cursor.fetchall()
        
        if len(items) < qty:
            bot.edit_message_text("❌ পর্যাপ্ত স্টক খালি নেই!", call.message.chat.id, call.message.message_id)
            return
            
        delivered_lines = []
        for item in items:
            item_id, content = item
            delivered_lines.append(content)
            cursor.execute("UPDATE item_stock SET status='sold' WHERE id=?", (item_id,))
            
        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (total_bdt, user_id))
        conn.commit()
    
    excel_file = create_excel_document(p_name, delivered_lines)
    
    delivery_text = (
        f"✅ <b>Mail Delivered!</b>\n\n"
        f"📧 <b>{qty}x {p_name}</b>\n"
        f"💰 <b>Paid : {total_bdt:.2f} BDT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📱 <b>File below ↓</b>"
    )
    bot.edit_message_text(delivery_text, call.message.chat.id, call.message.message_id)
    bot.send_document(call.message.chat.id, excel_file)

# ----------------- 👤 PROFILE & REFERRAL SYSTEM -----------------
@bot.message_handler(func=lambda msg: msg.text == "👤 My Profile")
def profile_cmd(message):
    if not is_user_joined(message.from_user.id):
        send_force_join_msg(message.chat.id)
        return

    user_id = message.from_user.id
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT balance, referrals, joined_date, otp_count FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()

    bal = row[0] if row else 6.00
    refs = row[1] if row else 0
    joined = row[2] if row else "2026-06-27"
    otps = row[3] if row else 0
    usdt = bal / 125.0
    bot_uname = bot.get_me().username
    ref_link = f"https://t.me/{bot_uname}?start={user_id}"

    text = (
        f"👤 <b>My Profile</b>\n\n"
        f"👤 <b>Name     :</b> {message.from_user.first_name}\n"
        f"🆔 <b>User ID  :</b> <code>{user_id}</code>\n"
        f"💰 <b>Balance  :</b> {bal:.2f} BDT / {usdt:.4f} USDT\n"
        f"🥳 <b>Joined   :</b> {joined}\n"
        f"🔢 <b>OTP Received :</b> {otps}\n"
        f"🤝 <b>Referrals :</b> {refs}\n\n"
        f"🔗 <b>Referral Link:</b>\n<code>{ref_link}</code>"
    )
    bot.send_message(message.chat.id, text)

# ----------------- 💳 DEPOSIT SYSTEM -----------------
@bot.message_handler(func=lambda msg: msg.text == "💳 Deposit")
def deposit_cmd(message):
    if not is_user_joined(message.from_user.id):
        send_force_join_msg(message.chat.id)
        return

    text = (
        "💳 <b>Select Deposit Payment Method:</b>\n\n"
        "নিচের তালিকা থেকে আপনার সুবিধাজনক পেমেন্ট গেটওয়ে সিলেক্ট করুন:"
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💸 bKash (Personal)", callback_data="dep_bkash"),
        types.InlineKeyboardButton("💸 Nagad (Personal)", callback_data="dep_nagad")
    )
    markup.add(
        types.InlineKeyboardButton("💸 Binance (Pay / UID)", callback_data="dep_binance"),
        types.InlineKeyboardButton("🎟️ Cash Voucher", callback_data="dep_voucher")
    )
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("dep_"))
def dep_method_cb(call):
    bot.answer_callback_query(call.id)
    method = call.data.split("_")[1]
    user_id = call.from_user.id
    
    if method in ["bkash", "nagad", "binance"]:
        min_dep = get_setting('min_deposit') or '20.0'
        num = get_setting(f'{method}_num') if method != 'binance' else get_setting('binance_uid')
        
        set_user_state(user_id, "dep_method", method)
        set_user_state(user_id, "dep_num", num)
        set_user_state(user_id, "step", "await_dep_amt")
        
        header_badge = "🌸 <b>[ bKash Personal Payment ]</b>" if method == "bkash" else ("🟠 <b>[ Nagad Personal Payment ]</b>" if method == "nagad" else "🟡 <b>[ Binance USDT Payment ]</b>")
        
        text = f"{header_badge}\n\nEnter deposit amount in BDT:\n<i>(Minimum: {min_dep} BDT)</i>"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_action"))
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("paid_"))
def dep_paid_cb(call):
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id
    _, method, amt = call.data.split("_")
    
    set_user_state(user_id, "dep_final_m", method)
    set_user_state(user_id, "dep_final_a", amt)
    set_user_state(user_id, "step", "await_trxid")
    
    text = (
        f"🚩 <b>Enter Transaction ID (TrxID)</b>\n\n"
        f"Amount: <b>{float(amt):.2f} BDT</b> via <b>{method.upper()}</b>\n\n"
        f"Send the TrxID from your payment SMS below:\n"
        f"<i>(উদাহরণ: DF27TNVV17)</i>"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_action"))
    bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text == "🔑 Get Code")
def get_code_cmd(message):
    text = "🔑 <b>Get Code</b>\n\nSelect a link:"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🔗 Hotmail/Outlook ↗", url="https://dongvanfb.net"),
        types.InlineKeyboardButton("🔗 Fr Outlook Code ↗", url="https://dongvanfb.net"),
        types.InlineKeyboardButton("🔗 API Gmail Code ↗", url="https://dongvanfb.net")
    )
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "cancel_action")
def cancel_action_cb(call):
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id
    clear_user_state(user_id)
    bot.edit_message_text("❌ অপশনটি বাতিল করা হয়েছে।", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda msg: msg.text == "🎧 Support")
def support_cmd(message):
    bot.send_message(message.chat.id, "🎧 <b>Support:</b>\n\nযেকোনো সমস্যায় এডমিনের সাথে যোগাযোগ করুন: @your_telegram_username")

# ----------------- 👑 EDITABLE ADMIN CONTROL PANEL -----------------
@bot.message_handler(func=lambda msg: msg.text == "👑 Admin Panel" and msg.from_user.id == ADMIN_ID)
def admin_panel_cmd(message):
    text = "📊 <b>MASTER ADMIN CONTROL PANEL</b>\n\nসবকিছু কাস্টমাইজ করতে নিচের অপশনগুলো ব্যবহার করুন:"
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔑 VoltXSMS API Key", callback_data="adm_edit_apikey"),
        types.InlineKeyboardButton("🌐 VoltXSMS API URL", callback_data="adm_edit_apiurl")
    )
    markup.add(
        types.InlineKeyboardButton("📢 Force Join Channels", callback_data="adm_edit_force_join"),
        types.InlineKeyboardButton("⚙️ Edit Payment Numbers", callback_data="adm_edit_payments")
    )
    markup.add(
        types.InlineKeyboardButton("👀 Pending Deposits", callback_data="adm_view_pending_dep"),
        types.InlineKeyboardButton("🎁 Edit Bonus & Rewards", callback_data="adm_edit_bonuses")
    )
    markup.add(
        types.InlineKeyboardButton("🌐 Add Service/Country", callback_data="adm_add_country"),
        types.InlineKeyboardButton("🛍️ Add Shop Stock", callback_data="adm_add_shop_stock")
    )
    markup.add(
        types.InlineKeyboardButton("👤 Edit User Balance", callback_data="adm_edit_balance"),
        types.InlineKeyboardButton("📢 Broadcast Message", callback_data="adm_broadcast")
    )
    markup.add(
        types.InlineKeyboardButton("🗑️ Reset & Clear All Stock", callback_data="adm_clear_stock")
    )
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.from_user.id == ADMIN_ID)
def admin_cb_handler(call):
    data = call.data
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id

    if data == "adm_edit_apikey":
        curr_key = get_setting('number_api_key')
        set_user_state(user_id, "adm_step", "set_setting:number_api_key")
        bot.send_message(call.message.chat.id, f"🔑 <b>বর্তমান VoltXSMS API Key:</b>\n<code>{curr_key}</code>\n\nনতুন API Key লিখে মেসেজ দিন:")

    elif data == "adm_edit_apiurl":
        curr_url = get_setting('api_base_url')
        set_user_state(user_id, "adm_step", "set_setting:api_base_url")
        bot.send_message(call.message.chat.id, f"🌐 <b>বর্তমান API Base URL:</b>\n<code>{curr_url}</code>\n\nনতুন API URL লিখে মেসেজ দিন:")

    elif data == "adm_edit_force_join":
        curr = get_setting('force_channels') or "None"
        set_user_state(user_id, "adm_step", "set_setting:force_channels")
        bot.send_message(
            call.message.chat.id,
            f"📢 <b>Current Required Channels:</b> <code>{curr}</code>\n\n"
            f"ইউজারদের বাধ্যতামূলক জয়েন করানোর জন্য চ্যানেলগুলোর ইউজারনেম কমা দিয়ে দিয়ে লিখুন:\n"
            f"উদাহরণ: <code>@channel1,@channel2</code>"
        )

    elif data == "adm_clear_stock":
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM countries")
            cursor.execute("DELETE FROM products")
            cursor.execute("DELETE FROM item_stock")
            conn.commit()
        bot.send_message(call.message.chat.id, "🗑️ আগের সকল সার্ভিস ও ইনভেন্টরি ক্লিয়ার করা হয়েছে!")

    elif data == "adm_add_shop_stock":
        text = "🛍️ <b>Select Category to Add Product / Stock:</b>"
        markup = types.InlineKeyboardMarkup(row_width=3)
        markup.add(
            types.InlineKeyboardButton("📧 Mail Stock", callback_data="addstk_Mail"),
            types.InlineKeyboardButton("🌐 Proxy Stock", callback_data="addstk_Proxy"),
            types.InlineKeyboardButton("🛡️ VPN Stock", callback_data="addstk_VPN")
        )
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data.startswith("addstk_"):
        cat = data.split("_")[1]
        set_user_state(user_id, "adm_add_cat", cat)
        set_user_state(user_id, "adm_step", "add_prod_info")
        bot.send_message(call.message.chat.id, f"<b>{cat} Stock:</b>\n\nপ্রোডাক্টের নাম এবং প্রতি পিসের দাম লিখুন:\n\n<code>প্রোডাক্টের নাম, দাম</code>")

    elif data == "adm_view_pending_dep":
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, user_id, amount, method, trx_id FROM deposits WHERE status='pending'")
            deps = cursor.fetchall()
        
        if not deps:
            bot.send_message(call.message.chat.id, "✅ বর্তমানে কোনো পেন্ডিং ডিপোজিট রিকুয়েস্ট নেই।")
            return
            
        for d in deps:
            d_id, u_id, amt, method, trx = d
            t = f"📥 <b>Pending Deposit #{d_id}</b>\nUser: <code>{u_id}</code>\nMethod: {method}\nAmount: <b>{amt:.2f} BDT</b>\nTrxID: <code>{trx}</code>"
            m = types.InlineKeyboardMarkup(row_width=2)
            m.add(
                types.InlineKeyboardButton("✅ Approve", callback_data=f"adm_appr_dep_{d_id}"),
                types.InlineKeyboardButton("❌ Reject", callback_data=f"adm_rej_dep_{d_id}")
            )
            bot.send_message(call.message.chat.id, t, reply_markup=m)

    elif data.startswith("adm_appr_dep_"):
        dep_id = data.split("_")[3]
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, amount, status FROM deposits WHERE id=?", (dep_id,))
            row = cursor.fetchone()
            
            if row and row[2] == 'pending':
                u_id, amt, _ = row
                cursor.execute("UPDATE deposits SET status='approved' WHERE id=?", (dep_id,))
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt, u_id))
                conn.commit()
                
                bot.edit_message_text(f"✅ <b>Deposit Approved!</b> ({amt:.2f} BDT)", call.message.chat.id, call.message.message_id)
                try:
                    bot.send_message(u_id, f"🎉 আপনার ডিপোজিট এপ্রুভ হয়েছে এবং <b>{amt:.2f} BDT</b> অ্যাকাউন্টে যোগ হয়েছে!")
                except Exception:
                    pass
            
    elif data.startswith("adm_rej_dep_"):
        dep_id = data.split("_")[3]
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE deposits SET status='rejected' WHERE id=?", (dep_id,))
            conn.commit()
        bot.edit_message_text("❌ <b>Deposit Rejected!</b>", call.message.chat.id, call.message.message_id)

    elif data == "adm_edit_payments":
        bk = get_setting('bkash_num')
        ng = get_setting('nagad_num')
        bn = get_setting('binance_uid')
        text = f"⚙️ <b>Edit Payment Methods</b>\n\n🌸 bKash: {bk}\n🟠 Nagad: {ng}\n🟡 Binance UID: {bn}"
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🌸 Edit bKash Number", callback_data="set_pay_bkash"),
            types.InlineKeyboardButton("🟠 Edit Nagad Number", callback_data="set_pay_nagad"),
            types.InlineKeyboardButton("🟡 Edit Binance UID", callback_data="set_pay_binance")
        )
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data in ["set_pay_bkash", "set_pay_nagad", "set_pay_binance"]:
        m_name = data.split("_")[2]
        key = f"{m_name}_num" if m_name != "binance" else "binance_uid"
        set_user_state(user_id, "adm_step", f"set_setting:{key}")
        bot.send_message(call.message.chat.id, f"✏️ <b>নতুন {m_name.upper()} নম্বর / UID টি লিখে মেসেজ দিন:</b>")

    elif data == "adm_edit_bonuses":
        ref = get_setting('refer_reward')
        dep_b = get_setting('deposit_bonus')
        text = f"🎁 <b>Edit Bonuses</b>\n\nRefer Bonus: {ref} BDT\nDeposit Bonus: {dep_b}%"
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🎁 Change Refer Bonus", callback_data="set_bonus_refer"),
            types.InlineKeyboardButton("💵 Change Deposit Bonus %", callback_data="set_bonus_dep")
        )
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data in ["set_bonus_refer", "set_bonus_dep"]:
        key = "refer_reward" if data == "set_bonus_refer" else "deposit_bonus"
        set_user_state(user_id, "adm_step", f"set_setting:{key}")
        bot.send_message(call.message.chat.id, "✏️ <b>নতুন পরিমাণটি টাইপ করে পাঠান:</b>")

    elif data == "adm_add_country":
        set_user_state(user_id, "adm_step", "add_country")
        bot.send_message(
            call.message.chat.id,
            "🌐 <b>নতুন সার্ভিস / কান্ট্রি যোগ করার ফরম্যাট:</b>\n\n"
            "<code>SERVICE_NAME,SERVICE_CODE,COUNTRY_NAME,FLAG,COUNTRY_CODE</code>\n\n"
            "উদাহরণ (Facebook - Uzbekistan):\n"
            "<code>Facebook,fb,Uzbekistan,🇺🇿,uz</code>\n\n"
            "উদাহরণ (Instagram - Bangladesh):\n"
            "<code>Instagram,ig,Bangladesh,🇧🇩,bd</code>"
        )

    elif data == "adm_edit_balance":
        set_user_state(user_id, "adm_step", "edit_balance")
        bot.send_message(call.message.chat.id, "👤 <b>ইউজার ব্যালেন্স দিতে লিখুন:</b>\n\n<code>USER_ID,AMOUNT</code>")

    elif data == "adm_broadcast":
        set_user_state(user_id, "adm_step", "broadcast")
        bot.send_message(call.message.chat.id, "📢 <b>ইউজারদের কাছে পাঠাতে চাওয়া ব্রডকাস্ট মেসেজটি লিখুন:</b>")

# ----------------- GLOBAL TEXT & FILE HANDLER -----------------
@bot.message_handler(func=lambda m: True, content_types=['text', 'document'])
def global_message_handler(message):
    user_id = message.from_user.id
    txt = message.text.strip() if message.text else ""
    
    # Admin State Steps
    if user_id == ADMIN_ID:
        adm_step = get_user_state(user_id, "adm_step")
        if adm_step:
            if adm_step.startswith("set_setting:"):
                key = adm_step.split(":")[1]
                set_setting(key, txt)
                clear_user_state(user_id)
                bot.send_message(message.chat.id, f"✅ সফলভাবে <b>{key}</b> আপডেট হয়ে <b>{txt}</b> হয়েছে!")
                return

            elif adm_step == "add_country":
                try:
                    parts = txt.split(",")
                    srv_name = parts[0].strip()
                    srv_code = parts[1].strip()
                    c_name = parts[2].strip()
                    flag = parts[3].strip()
                    c_code = parts[4].strip()
                    
                    with get_db() as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO countries (service_name, service_code, country_name, country_flag, country_code, price) VALUES (?, ?, ?, ?, ?, 0.00)",
                            (srv_name, srv_code, c_name, flag, c_code)
                        )
                        conn.commit()
                    
                    clear_user_state(user_id)
                    bot.send_message(message.chat.id, f"✅ সফলভাবে <b>{flag} {c_name} ({srv_name})</b> সার্ভিস যোগ হয়েছে!")
                except Exception:
                    bot.send_message(message.chat.id, "❌ ফরম্যাট ভুল হয়েছে। ফরম্যাট: `SERVICE_NAME,SERVICE_CODE,COUNTRY_NAME,FLAG,COUNTRY_CODE`")
                return

            elif adm_step == "add_prod_info":
                try:
                    parts = txt.split(",")
                    p_name = parts[0].strip()
                    p_price = float(parts[1].strip())
                    cat = get_user_state(user_id, "adm_add_cat", "Mail")
                    
                    with get_db() as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT id FROM products WHERE category=? AND name=?", (cat, p_name))
                        res = cursor.fetchone()
                        
                        if res:
                            p_id = res[0]
                            cursor.execute("UPDATE products SET price=? WHERE id=?", (p_price, p_id))
                        else:
                            cursor.execute("INSERT INTO products (category, name, price) VALUES (?, ?, ?)", (cat, p_name, p_price))
                            p_id = cursor.lastrowid
                        conn.commit()
                    
                    set_user_state(user_id, "active_pid", str(p_id))
                    set_user_state(user_id, "active_pname", p_name)
                    set_user_state(user_id, "adm_step", "await_stock_items")
                    
                    bot.send_message(message.chat.id, f"✅ <b>{p_name} ({p_price:.2f} BDT)</b> সিলেক্ট হয়েছে!\n\nএখন ফাইল বা টেক্সট পাঠিয়ে স্টক দিন:")
                except Exception:
                    bot.send_message(message.chat.id, "❌ ফরম্যাট ভুল হয়েছে। লিখুন: `প্রোডাক্টের নাম, দাম`")
                return

            elif adm_step == "await_stock_items":
                p_id = get_user_state(user_id, "active_pid")
                p_name = get_user_state(user_id, "active_pname")
                lines = []
                
                if message.document:
                    file_info = bot.get_file(message.document.file_id)
                    downloaded_file = bot.download_file(file_info.file_path)
                    file_name = message.document.file_name or ""
                    
                    if file_name.endswith(('.xlsx', '.xls')):
                        try:
                            wb = openpyxl.load_workbook(io.BytesIO(downloaded_file))
                            ws = wb.active
                            for row in ws.iter_rows(values_only=True):
                                if row:
                                    row_vals = [str(cell).strip() for cell in row if cell is not None and str(cell).strip()]
                                    if row_vals:
                                        lines.append(" | ".join(row_vals))
                        except Exception as e:
                            bot.send_message(message.chat.id, f"❌ Excel ফাইল পড়তে সমস্যা: {e}")
                            return
                    else:
                        try:
                            text_data = downloaded_file.decode('utf-8', errors='ignore')
                        except Exception:
                            text_data = downloaded_file.decode('latin-1', errors='ignore')
                        lines = [line.strip() for line in text_data.split("\n") if line.strip()]
                else:
                    lines = [line.strip() for line in txt.split("\n") if line.strip()]

                if not lines:
                    bot.send_message(message.chat.id, "⚠️ কোনো অ্যাকাউন্ট পাওয়া যায়নি!")
                    return
                
                with get_db() as conn:
                    cursor = conn.cursor()
                    added_count = 0
                    for line in lines:
                        cursor.execute("INSERT INTO item_stock (product_id, content) VALUES (?, ?)", (p_id, line))
                        added_count += 1
                    conn.commit()
                
                clear_user_state(user_id)
                bot.send_message(message.chat.id, f"🎉 সফলভাবে <b>{added_count} টি {p_name}</b> স্টকে যুক্ত হয়েছে!")
                return

            elif adm_step == "edit_balance":
                try:
                    parts = txt.split(",")
                    target_id = int(parts[0].strip())
                    add_bal = float(parts[1].strip())
                    
                    with get_db() as conn:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (add_bal, target_id))
                        conn.commit()
                        
                    clear_user_state(user_id)
                    bot.send_message(message.chat.id, f"✅ ইউজার <code>{target_id}</code> এর ব্যালেন্সে <b>{add_bal:.2f} BDT</b> যোগ করা হয়েছে!")
                except Exception:
                    bot.send_message(message.chat.id, "❌ ফরম্যাট ভুল হয়েছে। ফরম্যাট: `USER_ID,AMOUNT`")
                return

            elif adm_step == "broadcast":
                with get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT user_id FROM users")
                    users = cursor.fetchall()
                s, f = 0, 0
                for u in users:
                    try:
                        bot.send_message(u[0], txt)
                        s += 1
                    except Exception:
                        f += 1
                clear_user_state(user_id)
                bot.send_message(message.chat.id, f"✅ ব্রডকাস্ট সম্পন্ন!\n\nসফল: {s} জন\nব্যর্থ: {f} জন")
                return

    # User State Steps
    usr_step = get_user_state(user_id, "step")
    if usr_step == "await_qty":
        try:
            qty = int(txt)
            p_id = get_user_state(user_id, "buying_p_id")
            
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name, price FROM products WHERE id=?", (p_id,))
                prod = cursor.fetchone()
                p_name, p_price = prod[0], prod[1]
                
                cursor.execute("SELECT COUNT(*) FROM item_stock WHERE product_id=? AND status='available'", (p_id,))
                p_stock = cursor.fetchone()[0]
                
                if qty <= 0 or qty > p_stock:
                    bot.send_message(message.chat.id, f"❌ পর্যাপ্ত স্টক নেই! সর্বোচ্চ {p_stock} টি নিতে পারবেন।")
                    return
                    
                total_bdt = qty * p_price
                total_usdt = total_bdt / 125.0
                
                cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
                bal = cursor.fetchone()[0]
            
            clear_user_state(user_id)
            
            text = (
                f"📬 <b>Order Summary</b>\n\n"
                f"⚡ <b>Category :</b> {p_name}\n"
                f"👥 <b>Quantity :</b> {qty}\n"
                f"💰 <b>Total    :</b> {total_bdt:.2f} BDT / {total_usdt:.4f} USDT\n"
                f"💳 <b>Balance  :</b> {bal:.2f} BDT"
            )
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("✅ Confirm Order", callback_data=f"cfmbuy_{p_id}_{qty}"),
                types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_action")
            )
            bot.send_message(message.chat.id, text, reply_markup=markup)
        except Exception:
            bot.send_message(message.chat.id, "❌ সঠিক সংখ্যা টাইপ করুন।")
        return

    elif usr_step == "await_dep_amt":
        try:
            amt = float(txt)
            min_dep = float(get_setting('min_deposit') or 20.0)
            if amt < min_dep:
                bot.send_message(message.chat.id, f"❌ সর্বনিম্ন ডিপোজিট {min_dep} BDT।")
                return
            
            method = get_user_state(user_id, "dep_method")
            num = get_user_state(user_id, "dep_num")
            clear_user_state(user_id)
            
            badge = "🌸 <b>bKash Personal Number</b>" if method == "bkash" else ("🟠 <b>Nagad Personal Number</b>" if method == "nagad" else "🟡 <b>Binance Pay / UID</b>")
            
            text = (
                f"{badge}\n\n"
                f"Send <b>{amt:.2f} BDT</b> to:\n"
                f"<code>{num}</code>\n\n"
                f"<i>(নম্বরটি কপি করতে লেখার ওপর ট্যাপ করুন)</i>\n\n"
                f"টাকা পাঠানোর পর নিচের Paid বাটনে ক্লিক করুন:"
            )
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(
                types.InlineKeyboardButton("✅ Paid", callback_data=f"paid_{method}_{amt}"),
                types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_action")
            )
            bot.send_message(message.chat.id, text, reply_markup=markup)
        except Exception:
            bot.send_message(message.chat.id, "❌ সঠিক সংখ্যা টাইপ করুন।")
        return

    elif usr_step == "await_trxid":
        trx_id = txt.upper()
        method = get_user_state(user_id, "dep_final_m")
        amt = float(get_user_state(user_id, "dep_final_a") or 20.0)
        
        dep_bonus_pct = float(get_setting('deposit_bonus') or 5.0)
        final_amt = amt + (amt * (dep_bonus_pct / 100.0))
        
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO deposits (user_id, amount, method, trx_id) VALUES (?, ?, ?, ?)", (user_id, final_amt, method.upper(), trx_id))
                conn.commit()
                dep_id = cursor.lastrowid
            
            clear_user_state(user_id)
            bot.send_message(message.chat.id, "✅ আপনার ডিপোজিট রিকুয়েস্ট সফলভাবে সাবমিট হয়েছে। এডমিন ভেরিফাই করে এপ্রুভ করে দেবে।")
            
            admin_text = (
                f"📥 <b>NEW DEPOSIT REQUEST!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>User ID:</b> <code>{user_id}</code>\n"
                f"💳 <b>Method:</b> {method.upper()}\n"
                f"💵 <b>Amount:</b> {amt} BDT (+{dep_bonus_pct}% Bonus = <b>{final_amt:.2f} BDT</b>)\n"
                f"🏷️ <b>TrxID:</b> <code>{trx_id}</code>"
            )
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("✅ Approve", callback_data=f"adm_appr_dep_{dep_id}"),
                types.InlineKeyboardButton("❌ Reject", callback_data=f"adm_rej_dep_{dep_id}")
            )
            try:
                bot.send_message(ADMIN_ID, admin_text, reply_markup=markup)
            except Exception:
                pass
        except sqlite3.IntegrityError:
            bot.send_message(message.chat.id, "❌ এই TrxID টি আগেই ব্যবহার করা হয়েছে!")
        return

# ----------------- 🔄 24/7 AUTO-RECONNECT ENGINE -----------------
print("🤖 VoltXSMS Automated OTP Bot Started Successfully & Running 24/7...")
while True:
    try:
        bot.infinity_polling(timeout=20, long_polling_timeout=10)
    except Exception as e:
        print(f"⚠️ Connection dropped: {e}. Reconnecting in 5 seconds...")
        time.sleep(5)
