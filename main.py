import sqlite3
import telebot
import time
import requests
import threading
from flask import Flask
from telebot import types

# Keep-Alive Web Server for Render
app = Flask('')
@app.route('/')
def home(): return "Bot is Alive!"
threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8842802759:AAHmWCdirv1RsZdineS-TpL3Oy6BmA648uQ" # আপনার নতুন সচল টোকেন
ADMIN_ID = 8125384914                                       # আপনার Admin ID
DB_NAME = "fresh_master_shop.db"
# =======================================================

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

user_state = {}
admin_state = {}

# ----------------- DATABASE INITIALIZATION -----------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Users Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        balance REAL DEFAULT 6.00,
        referrals INTEGER DEFAULT 0,
        referred_by INTEGER,
        otp_count INTEGER DEFAULT 0,
        joined_date TEXT DEFAULT CURRENT_DATE
    )''')
    
    # OTP Stock Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS numbers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone_number TEXT UNIQUE,
        service TEXT,
        country TEXT,
        price REAL,
        status TEXT DEFAULT 'available'
    )''')
    
    # Dynamic Countries Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS countries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service_name TEXT,
        country_name TEXT,
        country_code TEXT,
        price REAL
    )''')
    
    # Web Shop Products Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        name TEXT,
        price REAL,
        stock INTEGER DEFAULT 100,
        data_content TEXT DEFAULT ''
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
    
    # Default Editable Settings
    defaults = {
        'bkash_num': '01833878871',
        'nagad_num': '01833878871',
        'binance_uid': '87654321',
        'min_deposit': '20.0',
        'deposit_bonus': '5',
        'refer_reward': '0.11',
        'otp_reward': '0.10',
        'api_price': '0.11',
        'number_api_key': 'M455243ZFHT',
        'min_withdraw': '50.0',
        'bot_status': 'ON'
    }
    for k, v in defaults.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
        
    conn.commit()
    conn.close()

init_db()

def get_setting(key):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else ""

def set_setting(key, value):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

# ----------------- MAIN KEYBOARD -----------------
def main_reply_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("📱 NUMBER'S"), types.KeyboardButton("🛍️ Web Shop"))
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
    args = message.text.split()
    referred_by = int(args[1]) if len(args) > 1 and args[1].isdigit() else None

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.execute("INSERT INTO users (user_id, balance, referred_by) VALUES (?, 6.00, ?)", (user_id, referred_by))
        conn.commit()
    conn.close()

    bot.send_message(message.chat.id, "👋 <b>OTP Receiver Pro Bot</b>-এ আপনাকে স্বাগতম!", reply_markup=main_reply_keyboard(user_id))

# ----------------- 📱 NUMBER'S BOT SYSTEM -----------------
@bot.message_handler(func=lambda msg: msg.text == "📱 NUMBER'S")
def numbers_cmd(message):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT service_name FROM countries")
    services = cursor.fetchall()
    conn.close()

    if not services:
        bot.send_message(message.chat.id, "⚠️ বর্তমানে কোনো সার্ভিস বা কান্ট্রি এভেলেবল নেই। অ্যাডমিনকে অ্যাড করতে বলুন।")
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    for s in services:
        markup.add(types.InlineKeyboardButton(s[0], callback_data=f"usr_srv_{s[0]}"))

    bot.send_message(message.chat.id, "📍 <b>Select a service:</b>", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("usr_srv_"))
def user_service_click(call):
    service_name = call.data.split("_")[2]
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT country_name, country_code, price FROM countries WHERE service_name=?", (service_name,))
    countries = cursor.fetchall()
    conn.close()

    markup = types.InlineKeyboardMarkup(row_width=1)
    for c in countries:
        c_name, c_code, c_price = c
        markup.add(types.InlineKeyboardButton(f"API {c_name} | {c_price}৳", callback_data=f"buy_{service_name}_{c_code}_{c_price}"))

    bot.edit_message_text(f"📌 <b>Select a country for {service_name}:</b>", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def buy_number_click(call):
    _, service, country_code, price = call.data.split("_")
    price = float(price)
    user_id = call.from_user.id

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    bal = cursor.fetchone()[0]

    if bal < price:
        bot.answer_callback_query(call.id, "❌ আপনার পর্যাপ্ত ব্যালেন্স নেই! Deposit করুন।", show_alert=True)
        conn.close()
        return

    cursor.execute("SELECT id, phone_number FROM numbers WHERE service=? AND country=? AND status='available' LIMIT 1", (service, country_code))
    num_row = cursor.fetchone()

    if not num_row:
        bot.answer_callback_query(call.id, "⚠️ এই কান্ট্রির নম্বর স্টকে নেই!", show_alert=True)
        conn.close()
        return

    num_id, phone = num_row
    cursor.execute("UPDATE numbers SET status='assigned' WHERE id=?", (num_id,))
    cursor.execute("UPDATE users SET balance = balance - ?, otp_count = otp_count + 1 WHERE user_id=?", (price, user_id))
    
    # 10 OTP Referral Condition Check
    cursor.execute("SELECT referred_by, otp_count FROM users WHERE user_id=?", (user_id,))
    u_row = cursor.fetchone()
    if u_row and u_row[0] and u_row[1] == 10:
        ref_id = u_row[0]
        ref_rw = float(get_setting('refer_reward') or 0.11)
        cursor.execute("UPDATE users SET balance = balance + ?, referrals = referrals + 1 WHERE user_id=?", (ref_rw, ref_id))
        try:
            bot.send_message(ref_id, f"🎉 আপনার রেফারকৃত ইউজার ১০টি OTP রিসিভ করায় আপনি <b>{ref_rw}৳</b> বোনাস পেয়েছেন!")
        except:
            pass

    conn.commit()
    conn.close()

    bot.send_message(call.message.chat.id, f"✅ <b>Number Found!</b>\n\n📱 <b>Phone:</b> <code>{phone}</code> | {price}৳\n\n<i>Waiting for OTP... (অটোমেটিক চেক হচ্ছে)</i>")

@bot.message_handler(func=lambda msg: msg.text == "🚥 LIVE TRAFFIC")
def live_traffic_cmd(message):
    bot.send_message(message.chat.id, "📊 <b>LIVE TRAFFIC</b>\n━━━━━━━━━━━━━━━━━━\n🌐 <b>API Status:</b> Active\nOTP Monitoring Running...")

# ----------------- 🛍️ WEB SHOP SYSTEM -----------------
@bot.message_handler(func=lambda msg: msg.text == "🛍️ Web Shop")
def buy_products_cmd(message):
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
    category = call.data.split("_")[1]
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price, stock FROM products WHERE category=?", (category,))
    products = cursor.fetchall()
    conn.close()

    if not products:
        bot.answer_callback_query(call.id, "⚠️ এই ক্যাটাগরিতে বর্তমানে কোনো প্রডাক্ট নেই!", show_alert=True)
        return

    text = f"<b>{category} — Select Category / Plan:</b>"
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for p in products:
        p_id, p_name, p_price, p_stock = p
        btn_text = f"{p_name} · {p_price:.2f} BDT · {p_stock} in stock"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"selectprod_{p_id}"))
        
    markup.add(types.InlineKeyboardButton("‹ Back", callback_data="back_to_shop"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_shop")
def back_to_shop_cb(call):
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
    p_id = call.data.split("_")[1]
    user_id = call.from_user.id
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name, price, stock FROM products WHERE id=?", (p_id,))
    prod = cursor.fetchone()
    conn.close()
    
    if not prod:
        return
        
    p_name, p_price, p_stock = prod
    user_state[user_id] = {'p_id': p_id, 'p_name': p_name, 'p_price': p_price, 'p_stock': p_stock}
    
    text = (
        f"📧 <b>{p_name}</b>\n"
        f"⚡ <b>{p_price:.2f} BDT / piece</b>\n"
        f"⚡ <b>Available: {p_stock}</b>\n\n"
        f"Enter quantity:"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_action"))
    
    msg = bot.send_message(call.message.chat.id, text, reply_markup=markup)
    bot.register_next_step_handler(msg, process_product_quantity)

def process_product_quantity(message):
    user_id = message.from_user.id
    if message.text == "❌ Cancel":
        bot.send_message(message.chat.id, "অর্ডার বাতিল করা হয়েছে।")
        return

    try:
        qty = int(message.text.strip())
        st = user_state.get(user_id, {})
        p_price = st.get('p_price', 0.70)
        p_name = st.get('p_name', 'Item')
        p_stock = st.get('p_stock', 100)
        
        if qty <= 0 or qty > p_stock:
            bot.send_message(message.chat.id, f"❌ পর্যাপ্ত স্টক নেই! সর্বোচ্চ {p_stock} টি নিতে পারবেন।")
            return
            
        total_bdt = qty * p_price
        total_usdt = total_bdt / 125.0
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        bal = cursor.fetchone()[0]
        conn.close()
        
        st['qty'] = qty
        st['total_bdt'] = total_bdt
        user_state[user_id] = st
        
        text = (
            f"📬 <b>Order Summary</b>\n\n"
            f"⚡ <b>Category :</b> {p_name}\n"
            f"👥 <b>Quantity :</b> {qty}\n"
            f"💰 <b>Total    :</b> {total_bdt:.2f} BDT / {total_usdt:.4f} USDT\n"
            f"💳 <b>Balance  :</b> {bal:.2f} BDT"
        )
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ Confirm Order", callback_data="confirm_order"),
            types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_action")
        )
        bot.send_message(message.chat.id, text, reply_markup=markup)
    except:
        bot.send_message(message.chat.id, "❌ সঠিক সংখ্যা টাইপ করুন।")

@bot.callback_query_handler(func=lambda call: call.data == "confirm_order")
def confirm_order_cb(call):
    user_id = call.from_user.id
    st = user_state.get(user_id, {})
    
    p_id = st.get('p_id')
    qty = st.get('qty', 1)
    total_bdt = st.get('total_bdt', 0.70)
    p_name = st.get('p_name', 'Item')
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    bal = cursor.fetchone()[0]
    
    if bal < total_bdt:
        bot.answer_callback_query(call.id, "❌ আপনার পর্যাপ্ত ব্যালেন্স নেই! Deposit করুন।", show_alert=True)
        conn.close()
        return
        
    cursor.execute("SELECT data_content FROM products WHERE id=?", (p_id,))
    content = cursor.fetchone()[0]
    
    cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (total_bdt, user_id))
    cursor.execute("UPDATE products SET stock = stock - ? WHERE id=?", (qty, p_id))
    conn.commit()
    conn.close()
    
    delivery_text = (
        f"✅ <b>Mail Delivered!</b>\n\n"
        f"📧 <b>{qty}x {p_name}</b>\n"
        f"💰 <b>Paid : {total_bdt:.2f} BDT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📱 <b>File / Account below ↓</b>\n\n"
        f"<code>{content}</code>"
    )
    bot.edit_message_text(delivery_text, call.message.chat.id, call.message.message_id)

# ----------------- 👤 PROFILE & REFERRAL SYSTEM -----------------
@bot.message_handler(func=lambda msg: msg.text == "👤 My Profile")
def profile_cmd(message):
    user_id = message.from_user.id
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT balance, referrals, joined_date, otp_count FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()

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
        f"🔢 <b>OTP Used :</b> {otps}\n"
        f"🤝 <b>Referrals :</b> {refs}\n\n"
        f"🔗 <b>Referral Link:</b>\n<code>{ref_link}</code>\n"
        f"<i>(নোট: যাকে রেফার করবেন তাকে অন্তত ১০টি OTP নিতে হবে বোনাস পাওয়ার জন্য)</i>"
    )
    bot.send_message(message.chat.id, text)

# ----------------- 💳 DEPOSIT SYSTEM (Direct TrxID Prompt) -----------------
@bot.message_handler(func=lambda msg: msg.text == "💳 Deposit")
def deposit_cmd(message):
    text = "💳 <b>Deposit</b>\n\nSelect payment method:"
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🌸 bKash", callback_data="dep_bkash"),
        types.InlineKeyboardButton("🟠 Nagad", callback_data="dep_nagad")
    )
    markup.add(
        types.InlineKeyboardButton("🟡 Binance (USDT)", callback_data="dep_binance"),
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
        
        user_state[user_id] = {'method': method, 'num': num}
        
        text = f"🌸 <b>{method.upper()}</b>\n\nEnter deposit amount in BDT:\n<i>(Minimum: {min_dep} BDT)</i>"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_action"))
        
        msg = bot.send_message(call.message.chat.id, text, reply_markup=markup)
        bot.register_next_step_handler(msg, process_dep_amount)

def process_dep_amount(message):
    user_id = message.from_user.id
    if message.text == "❌ Cancel":
        bot.send_message(message.chat.id, "ডিপোজিট বাতিল করা হয়েছে।")
        return
        
    try:
        amt = float(message.text.strip())
        min_dep = float(get_setting('min_deposit') or 20.0)
        
        if amt < min_dep:
            bot.send_message(message.chat.id, f"❌ সর্বনিম্ন ডিপোজিট {min_dep} BDT।")
            return
            
        st = user_state.get(user_id, {})
        st['amount'] = amt
        user_state[user_id] = st
        
        method_name = st['method'].upper()
        num = st['num']
        
        text = (
            f"💳 <b>{method_name}</b>\n\n"
            f"Send <b>{amt:.2f} BDT</b> to:\n"
            f"<code>{num}</code>\n\n"
            f"<i>Tap above to copy number/UID</i>\n\n"
            f"After sending, tap Paid below:"
        )
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("✅ Paid", callback_data="dep_paid_clicked"),
            types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_action")
        )
        bot.send_message(message.chat.id, text, reply_markup=markup)
    except:
        bot.send_message(message.chat.id, "❌ সঠিক সংখ্যা লিখুন।")

@bot.callback_query_handler(func=lambda call: call.data == "dep_paid_clicked")
def dep_paid_cb(call):
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id
    st = user_state.get(user_id, {})
    amt = st.get('amount', 20.0)
    method = st.get('method', 'bKash').upper()
    
    text = (
        f"🚩 <b>Enter Transaction ID (TrxID)</b>\n\n"
        f"Amount: {amt:.2f} BDT via {method}\n\n"
        f"Send the TrxID from your payment SMS below:\n"
        f"<i>(উদাহরণ: DF27TNVV17)</i>"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_action"))
    
    msg = bot.send_message(call.message.chat.id, text, reply_markup=markup)
    bot.register_next_step_handler(msg, process_dep_trxid)

def process_dep_trxid(message):
    user_id = message.from_user.id
    trx_id = message.text.strip().upper()
    
    st = user_state.get(user_id, {})
    amt = st.get('amount', 20.0)
    method = st.get('method', 'bKash').upper()
    
    dep_bonus_pct = float(get_setting('deposit_bonus') or 5.0)
    final_amt = amt + (amt * (dep_bonus_pct / 100.0))
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO deposits (user_id, amount, method, trx_id) VALUES (?, ?, ?, ?)", (user_id, final_amt, method, trx_id))
        conn.commit()
        dep_id = cursor.lastrowid
        conn.close()
        
        bot.send_message(message.chat.id, "✅ আপনার ডিপোজিট রিকুয়েস্ট সাবমিট হয়েছে। এডমিন ভেরিফাই করে এপ্রুভ করে দেবে।")
        
        # Send Notification to Admin
        admin_text = (
            f"📥 <b>NEW DEPOSIT REQUEST!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>User ID:</b> <code>{user_id}</code>\n"
            f"💳 <b>Method:</b> {method}\n"
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
        except Exception as e:
            print(f"Admin Alert Error: {e}")
            
    except sqlite3.IntegrityError:
        conn.close()
        bot.send_message(message.chat.id, "❌ এই TrxID টি আগেই ব্যবহার করা হয়েছে!")

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
        types.InlineKeyboardButton("⚙️ Edit Payment Numbers", callback_data="adm_edit_payments"),
        types.InlineKeyboardButton("🎁 Edit Bonus & Rewards", callback_data="adm_edit_bonuses")
    )
    markup.add(
        types.InlineKeyboardButton("👀 Pending Deposits", callback_data="adm_view_pending_dep"),
        types.InlineKeyboardButton("🔑 Edit Number API Key", callback_data="adm_edit_apikey")
    )
    markup.add(
        types.InlineKeyboardButton("🌐 Add Country/Service", callback_data="adm_add_country"),
        types.InlineKeyboardButton("📥 Upload OTP Numbers", callback_data="adm_upload_otp")
    )
    markup.add(
        types.InlineKeyboardButton("🛍️ Add Shop Product", callback_data="adm_add_shop_stock"),
        types.InlineKeyboardButton("👤 Edit User Balance", callback_data="adm_edit_balance")
    )
    markup.add(
        types.InlineKeyboardButton("📢 Broadcast Message", callback_data="adm_broadcast"),
        types.InlineKeyboardButton("🗑️ Clear All Stock Data", callback_data="adm_clear_stock")
    )
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.from_user.id == ADMIN_ID)
def admin_cb_handler(call):
    data = call.data
    bot.answer_callback_query(call.id)
    
    if data == "adm_clear_stock":
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM countries")
        cursor.execute("DELETE FROM products")
        cursor.execute("DELETE FROM numbers")
        conn.commit()
        conn.close()
        bot.send_message(call.message.chat.id, "🗑️ আগের সকল কান্ট্রি ও শপ স্টক সম্পূর্ণ মুছে ফেলা হয়েছে! এখন আপনি নতুন ফ্রেশ ডেটা যোগ করতে পারেন।")

    elif data == "adm_view_pending_dep":
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, user_id, amount, method, trx_id FROM deposits WHERE status='pending'")
        deps = cursor.fetchall()
        conn.close()
        
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
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, amount, status FROM deposits WHERE id=?", (dep_id,))
        row = cursor.fetchone()
        
        if row and row[2] == 'pending':
            u_id, amt, _ = row
            cursor.execute("UPDATE deposits SET status='approved' WHERE id=?", (dep_id,))
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt, u_id))
            conn.commit()
            conn.close()
            
            bot.edit_message_text(f"✅ <b>Deposit Approved!</b> ({amt:.2f} BDT)", call.message.chat.id, call.message.message_id)
            try:
                bot.send_message(u_id, f"🎉 আপনার ডিপোজিট এপ্রুভ হয়েছে এবং <b>{amt:.2f} BDT</b> অ্যাকাউন্টে যোগ হয়েছে!")
            except:
                pass
        else:
            conn.close()
            
    elif data.startswith("adm_rej_dep_"):
        dep_id = data.split("_")[3]
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE deposits SET status='rejected' WHERE id=?", (dep_id,))
        conn.commit()
        conn.close()
        bot.edit_message_text("❌ <b>Deposit Rejected!</b>", call.message.chat.id, call.message.message_id)

    elif data == "adm_edit_payments":
        bk = get_setting('bkash_num')
        ng = get_setting('nagad_num')
        bn = get_setting('binance_uid')
        text = f"⚙️ <b>Edit Payment Methods</b>\n\nbKash: {bk}\nNagad: {ng}\nBinance UID: {bn}"
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🌸 Edit bKash Number", callback_data="set_pay_bkash"),
            types.InlineKeyboardButton("🟠 Edit Nagad Number", callback_data="set_pay_nagad"),
            types.InlineKeyboardButton("🟡 Edit Binance UID", callback_data="set_pay_binance")
        )
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data in ["set_pay_bkash", "set_pay_nagad", "set_pay_binance"]:
        m_name = data.split("_")[2]
        admin_state[call.from_user.id] = f"{m_name}_num" if m_name != "binance" else "binance_uid"
        msg = bot.send_message(call.message.chat.id, f"✏️ <b>নতুন {m_name.upper()} নম্বর / UID টি লিখুন:</b>")
        bot.register_next_step_handler(msg, process_setting_input)

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
        admin_state[call.from_user.id] = key
        msg = bot.send_message(call.message.chat.id, "✏️ <b>নতুন পরিমাণটি টাইপ করে পাঠান:</b>")
        bot.register_next_step_handler(msg, process_setting_input)

    elif data == "adm_edit_apikey":
        admin_state[call.from_user.id] = "number_api_key"
        curr_key = get_setting('number_api_key')
        msg = bot.send_message(call.message.chat.id, f"🔑 <b>বর্তমান API Key:</b> <code>{curr_key}</code>\n\nনতুন Virtual Number API Key টাইপ করে পাঠান:")
        bot.register_next_step_handler(msg, process_setting_input)

    elif data == "adm_add_country":
        msg = bot.send_message(call.message.chat.id, "🌐 <b>নতুন কান্ট্রি যোগ করার ফরম্যাট:</b>\n\n<code>SERVICE,COUNTRY_NAME,CODE,PRICE</code>\n\nউদাহরণ:\n<code>FACEBOOK,Bangladesh,BD,0.12</code>")
        bot.register_next_step_handler(msg, process_add_country_input)

    elif data == "adm_upload_otp":
        msg = bot.send_message(call.message.chat.id, "📥 <b>OTP নম্বর আপলোড ফরম্যাট:</b>\n\n<code>+23674584135,FACEBOOK,CF</code>")
        bot.register_next_step_handler(msg, process_upload_otp_input)

    elif data == "adm_add_shop_stock":
        msg = bot.send_message(call.message.chat.id, "🛍️ <b>নতুন প্রডাক্ট যোগ ফরম্যাট (VPN, Mail, Proxy):</b>\n\n<code>CATEGORY,NAME,PRICE,STOCK,DATA</code>\n\nউদাহরণ:\n<code>VPN,NordVPN 30 Days,100,50,nord_login_details</code>\n<code>Proxy,PIA Proxy,12,100,ip:port:user:pass</code>")
        bot.register_next_step_handler(msg, process_add_product_input)

    elif data == "adm_edit_balance":
        msg = bot.send_message(call.message.chat.id, "👤 <b>ইউজার ব্যালেন্স দিতে লিখুন:</b>\n\n<code>USER_ID,AMOUNT</code>\n\nউদাহরণ:\n<code>5455330929,100</code>")
        bot.register_next_step_handler(msg, process_edit_balance_input)

    elif data == "adm_broadcast":
        msg = bot.send_message(call.message.chat.id, "📢 <b>ইউজারদের কাছে পাঠাতে চাওয়া ব্রডকাস্ট মেসেজটি লিখুন:</b>")
        bot.register_next_step_handler(msg, process_broadcast_input)

def process_setting_input(message):
    user_id = message.from_user.id
    if user_id in admin_state:
        key = admin_state[user_id]
        val = message.text.strip()
        set_setting(key, val)
        del admin_state[user_id]
        bot.send_message(message.chat.id, f"✅ সফলভাবে <b>{key}</b> আপডেট হয়ে <b>{val}</b> হয়েছে!")

def process_add_country_input(message):
    try:
        parts = message.text.strip().split(",")
        srv = parts[0].strip().upper()
        c_name = parts[1].strip()
        c_code = parts[2].strip().upper()
        price = float(parts[3].strip())

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO countries (service_name, country_name, country_code, price) VALUES (?, ?, ?, ?)", (srv, c_name, c_code, price))
        conn.commit()
        conn.close()

        bot.send_message(message.chat.id, f"✅ সফলভাবে <b>{c_name} ({srv})</b> এর দাম <b>{price}৳</b> হিসেবে যোগ হয়েছে!")
    except:
        bot.send_message(message.chat.id, "❌ ফরম্যাট ভুল হয়েছে।")

def process_upload_otp_input(message):
    lines = message.text.strip().split("\n")
    added = 0
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    for line in lines:
        try:
            parts = line.split(",")
            phone = parts[0].strip()
            service = parts[1].strip().upper()
            country = parts[2].strip().upper()
            price = float(get_setting('api_price') or 0.11)
            cursor.execute("INSERT OR IGNORE INTO numbers (phone_number, service, country, price) VALUES (?, ?, ?, ?)", (phone, service, country, price))
            added += 1
        except:
            pass
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, f"✅ সফলভাবে <b>{added}</b> টি OTP নম্বর স্টকে যুক্ত হয়েছে!")

def process_add_product_input(message):
    try:
        parts = message.text.strip().split(",")
        cat = parts[0].strip()
        name = parts[1].strip()
        price = float(parts[2].strip())
        stock = int(parts[3].strip())
        content = parts[4].strip()

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO products (category, name, price, stock, data_content) VALUES (?, ?, ?, ?, ?)", (cat, name, price, stock, content))
        conn.commit()
        conn.close()

        bot.send_message(message.chat.id, f"✅ সফলভাবে <b>{name} ({cat})</b> প্রডাক্ট শপে যোগ করা হয়েছে!")
    except:
        bot.send_message(message.chat.id, "❌ ফরম্যাট ভুল হয়েছে।")

def process_edit_balance_input(message):
    try:
        parts = message.text.strip().split(",")
        u_id = int(parts[0].strip())
        amt = float(parts[1].strip())

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt, u_id))
        conn.commit()
        conn.close()

        bot.send_message(message.chat.id, f"✅ ইউজার <code>{u_id}</code> এর ব্যালেন্সে <b>{amt}৳</b> দেওয়া হয়েছে!")
        try:
            bot.send_message(u_id, f"🎁 অ্যাডমিন আপনার অ্যাকাউন্টে <b>{amt}৳</b> যুক্ত করেছেন!")
        except:
            pass
    except:
        bot.send_message(message.chat.id, "❌ ভুল তথ্য দেওয়া হয়েছে।")

def process_broadcast_input(message):
    text = message.text
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()
    
    success, fail = 0, 0
    for u in users:
        try:
            bot.send_message(u[0], text)
            success += 1
        except:
            fail += 1
    bot.send_message(message.chat.id, f"✅ ব্রডকাস্ট সম্পন্ন হয়েছে!\n\nসফল: {success} জন\nব্যর্থ: {fail} জন")

# ----------------- 🔄 24/7 AUTO-RECONNECT ENGINE -----------------
print("🤖 Master Bot Started Successfully & Running 24/7...")
while True:
    try:
        bot.infinity_polling(timeout=20, long_polling_timeout=10)
    except Exception as e:
        print(f"⚠️ Connection dropped: {e}. Reconnecting in 5 seconds...")
        time.sleep(5)
