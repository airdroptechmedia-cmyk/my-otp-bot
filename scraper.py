import os
import sqlite3
import time
import datetime
import asyncio
import aiohttp
import re
import requests
from contextlib import contextmanager
from telebot import TeleBot

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8842802759:AAF1UktFbWNVjBfZDamUPE-U_9UokYNUjBs" # Bot Token
ADMIN_ID = 8125384914                                       # Admin ID
BOT_NAME = "OTP RECIVER PRO BOT Scraper Engine"
DB_NAME = "fresh_master_shop.db"

bot = TeleBot(BOT_TOKEN, parse_mode="HTML")

BOT_USERNAME = ""
try:
    BOT_USERNAME = bot.get_me().username
except Exception:
    BOT_USERNAME = "otpreciverpro_bot"

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_NAME, timeout=15)
    try:
        yield conn
    finally:
        conn.close()

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

LAST_BACKUP_TIME = 0

def backup_db_to_telegram(force=False):
    global LAST_BACKUP_TIME
    now = time.time()
    if not force and (now - LAST_BACKUP_TIME < 10):
        return
        
    try:
        if os.path.exists(DB_NAME):
            with open(DB_NAME, 'rb') as doc:
                bot.send_document(
                    ADMIN_ID,
                    doc,
                    caption=f"#DB_BACKUP | Scraper Auto Sync | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    disable_notification=True
                )
            LAST_BACKUP_TIME = now
            print("☁️ DB Cloud Backup sent to Telegram from Scraper successfully!")
    except Exception as e:
        print(f"Backup DB Exception: {e}")

# ==================== EXPANDED MULTI-API CONFIGURATION ====================
# Structured dictionary with placeholders for 5 major SMS providers.
# Paste your API Keys, Tokens, and Base URLs here or customize via Admin Settings.
API_PROVIDERS_CONFIG = {
    "API1_VOLTX": {
        "enabled": True,
        "name": "VoltX SMS",
        "setting_key_url": "api_base_url",
        "setting_key_key": "number_api_key",
        "default_base_url": "https://api.2oo9.cloud/MXS47FLFX0U/tnevs/@public/api",
        "default_api_key": "M7D4REK5Y06"
    },
    "API2_STEX": {
        "enabled": True,
        "name": "StexSMS",
        "setting_key_url": "api_base_url_2",
        "setting_key_key": "number_api_key_2",
        "default_base_url": "https://api.2oo9.cloud/MXS47FLFX0U/tnevs/@public/api",
        "default_api_key": "M6SB7HZXXIX"
    },
    "API3_QUACKR": {
        "enabled": True,
        "name": "Quackr.io",
        "base_url": "https://quackr.io/api/v1",
        "api_key": "PASTE_YOUR_QUACKR_API_KEY_HERE",
        "getmsg_url": "https://quackr.io/api/v1/messages"
    },
    "API4_SMSTOME": {
        "enabled": True,
        "name": "SMS-tome.com",
        "base_url": "https://sms-tome.com/api/v1",
        "api_key": "PASTE_YOUR_SMSTOME_API_KEY_HERE",
        "getmsg_url": "https://sms-tome.com/api/v1/messages"
    },
    "API5_ANONYMSMS": {
        "enabled": True,
        "name": "AnonymSMS",
        "base_url": "https://anonymsms.com/api/v1",
        "api_key": "PASTE_YOUR_ANONYMSMS_API_KEY_HERE",
        "getmsg_url": "https://anonymsms.com/api/v1/messages"
    }
}

# ==================== STRICT PASSCODE PARSING LOGIC ====================
def extract_passcode_from_text(res, clean_phone, order_id):
    if not res:
        return None
    
    clean_phone = str(clean_phone).replace("+", "").strip() if clean_phone else ""
    str_order_id = str(order_id).replace("+", "").strip() if order_id else ""
    
    def extract_code_from_str(s):
        if not s or not isinstance(s, (str, int)):
            return None
        s_str = str(s).strip()
        if not s_str:
            return None
        
        ignored_keywords = [
            "none", "null", "waiting", "pending", "false", "true", "ok", "success", 
            "status_ok", "200", "400", "404", "500", "error", "no_sms", "not_found", 
            "processing", "no_otp", "exist", "number_active", "received", "cancelled",
            "cancel", "timeout", "expire", "expired", "wait", "done"
        ]
        if s_str.lower() in ignored_keywords:
            return None

        if s_str.isdigit() and 4 <= len(s_str) <= 8:
            return s_str

        matches = re.findall(r'\b\d{4,8}\b', s_str)
        if matches:
            return matches[0]

        prefix_match = re.search(r'\b([A-Za-z]{1,4}[- ]?\d{4,8})\b', s_str)
        if prefix_match:
            return prefix_match.group(1)

        hyphen_match = re.search(r'\b\d{3,4}-\d{3,4}\b', s_str)
        if hyphen_match:
            return hyphen_match.group(0).replace('-', '')

        return None

    def get_code_from_dict(d):
        if not isinstance(d, dict):
            return None
        for field in ['otp', 'sms', 'last_code', 'text', 'message', 'msg', 'code']:
            val = d.get(field)
            extracted = extract_code_from_str(val)
            if extracted:
                return extracted
        return None

    def matches_target(d):
        if not isinstance(d, dict):
            return True
        possible_nums = []
        for k in ['full_number', 'number', 'phone', 'no_plus_number', 'order_id', 'id']:
            v = d.get(k)
            if v is not None:
                possible_nums.append(str(v).replace("+", "").strip())
        if not possible_nums:
            return True
        for num in possible_nums:
            if clean_phone and (clean_phone in num or num in clean_phone):
                return True
            if str_order_id and (str_order_id in num or num in str_order_id):
                return True
        return False

    if isinstance(res, (str, int)):
        return extract_code_from_str(res)

    if isinstance(res, dict):
        for key in ["data", "result", "messages", "orders", "sms"]:
            val = res.get(key)
            if val is not None:
                if isinstance(val, list):
                    for item in val:
                        if isinstance(item, dict) and matches_target(item):
                            c = get_code_from_dict(item)
                            if c:
                                return c
                        elif isinstance(item, (str, int)):
                            c = extract_code_from_str(item)
                            if c:
                                return c
                elif isinstance(val, dict):
                    if matches_target(val):
                        c = get_code_from_dict(val)
                        if c:
                            return c
                elif isinstance(val, (str, int)):
                    c = extract_code_from_str(val)
                    if c:
                        return c

        if matches_target(res):
            c = get_code_from_dict(res)
            if c:
                return c

    return None

# ==================== MULTI-PROVIDER SMS SCRAPING HANDLERS ====================
async def async_check_sms_multiprovider(session, phone_num, order_id, api_source="API1"):
    clean_phone = str(phone_num).replace("+", "").strip()
    clean_order_id = str(order_id).replace("+", "").strip() if order_id else clean_phone

    # Check API1 / API2 primary endpoints from settings
    if api_source == "API2":
        api_key = get_setting('number_api_key_2') or "M6SB7HZXXIX"
        base_url = get_setting('api_base_url_2') or "https://api.2oo9.cloud/MXS47FLFX0U/tnevs/@public/api"
        getmsg_setting = get_setting('getmsg_url_2')
    else:
        api_key = get_setting('number_api_key') or "M7D4REK5Y06"
        base_url = get_setting('api_base_url') or "https://api.2oo9.cloud/MXS47FLFX0U/tnevs/@public/api"
        getmsg_setting = get_setting('getmsg_url')
    
    headers = {
        "mauthapi": api_key,
        "Content-Type": "application/json"
    }
    
    endpoints = []
    if getmsg_setting and getmsg_setting.strip():
        endpoints.append(getmsg_setting.strip())
    
    default_endpoints = [
        f"{base_url.rstrip('/')}/success-otp",
        f"{base_url.rstrip('/')}/getmsg"
    ]
    for ep in default_endpoints:
        if ep not in endpoints:
            endpoints.append(ep)
            
    for url in endpoints:
        if not url:
            continue
        clean_url = url.split('?')[0]
        
        try:
            payload = {
                "number": clean_phone,
                "no_plus_number": clean_phone,
                "full_number": f"+{clean_phone}",
                "id": clean_order_id
            }
            async with session.post(clean_url, json=payload, headers=headers, timeout=5) as r:
                if r.status == 200:
                    json_res = await r.json()
                    code = extract_passcode_from_text(json_res, clean_phone, clean_order_id)
                    if code:
                        return "RECEIVED", code
        except Exception:
            pass

        for p_key, p_val in [('number', clean_phone), ('id', clean_order_id), ('phone', clean_phone)]:
            try:
                async with session.get(f"{clean_url}?{p_key}={p_val}", headers=headers, timeout=5) as r:
                    if r.status == 200:
                        json_res = await r.json()
                        code = extract_passcode_from_text(json_res, clean_phone, clean_order_id)
                        if code:
                            return "RECEIVED", code
            except Exception:
                pass

    # Backup Multi-API Providers Scraping Framework (Quackr / SMS-tome / AnonymSMS)
    for prov_key, cfg in API_PROVIDERS_CONFIG.items():
        if not cfg.get("enabled"):
            continue
        if prov_key in ["API1_VOLTX", "API2_STEX"]:
            continue  # Already checked above
            
        prov_url = cfg.get("getmsg_url")
        prov_key_val = cfg.get("api_key")
        
        if prov_url and not prov_key_val.startswith("PASTE_"):
            p_headers = {"Authorization": f"Bearer {prov_key_val}", "Content-Type": "application/json"}
            try:
                async with session.get(f"{prov_url}?number={clean_phone}", headers=p_headers, timeout=4) as r:
                    if r.status == 200:
                        json_res = await r.json()
                        code = extract_passcode_from_text(json_res, clean_phone, clean_order_id)
                        if code:
                            return "RECEIVED", code
            except Exception:
                pass

    return "WAITING", None

# ==================== TELEGRAM DIRECT NOTIFICATION HELPER ====================
async def send_telegram_direct_msg(session, chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        async with session.post(url, json=payload, timeout=8) as r:
            return r.status == 200
    except Exception as e:
        print(f"Direct Telegram Notification Error ({chat_id}): {e}")
        return False

# ==================== HIGH-SPEED ASYNC SINGLE ORDER BROKER ====================
async def async_check_single_order(session, order):
    db_id, user_id, order_id, phone_num, service_name, c_code, api_source = order
    status, otp_code = await async_check_sms_multiprovider(session, phone_num, order_id, api_source=api_source)

    if status == "RECEIVED" and otp_code:
        otp_reward_val = float(get_setting('otp_reward') or 0.10)
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE active_orders SET status='COMPLETED', last_code=? WHERE id=?", (otp_code, db_id))
            cursor.execute("UPDATE users SET balance = balance + ?, reward_balance = reward_balance + ?, otp_count = otp_count + 1 WHERE user_id=?", (otp_reward_val, otp_reward_val, user_id))
            cursor.execute("SELECT balance, reward_balance FROM users WHERE user_id=?", (user_id,))
            row_user = cursor.fetchone()
            new_bal = row_user[0] if row_user else 0.0
            new_rew_bal = row_user[1] if row_user and len(row_user) > 1 else 0.0
            
            cursor.execute("SELECT country_flag FROM countries WHERE service_name=? AND country_code=? LIMIT 1", (service_name, c_code))
            flag_row = cursor.fetchone()
            c_flag = flag_row[0] if flag_row else "🇺🇿"
            conn.commit()

        backup_db_to_telegram()

        user_text = (
            f"🎉 <b>NEW OTP RECEIVED!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"{c_flag} <b>Number:</b> <code>{phone_num}</code>\n"
            f"📘 <b>OTP Code:</b> <code>{otp_code}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🎁 <b>OTP Reward Credited: +{otp_reward_val:.2f} BDT</b>\n"
            f"💰 <b>Reward Balance: {new_rew_bal:.2f} BDT</b>\n"
            f"💼 <b>Total Balance: {new_bal:.2f} BDT</b>\n\n"
            f"👉 <i>(কোডের ওপর টাচ করলেই অটোমেটিক কপি হয়ে যাবে!)</i>"
        )
        await send_telegram_direct_msg(session, user_id, user_text)

        otp_group = get_setting('otp_group_id') or "@otpreciverpro"
        group_text = (
            f"🔔 <b>LIVE OTP TRAFFIC!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"⚙️ <b>Service:</b> {service_name}\n"
            f"{c_flag} <b>Number:</b> <code>{phone_num}</code>\n"
            f"🔑 <b>OTP Code:</b> <code>{otp_code}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🤖 <b>Bot:</b> @{BOT_USERNAME}"
        )
        await send_telegram_direct_msg(session, otp_group, group_text)

    elif status == "CANCELLED":
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE active_orders SET status='CANCELLED' WHERE id=?", (db_id,))
            conn.commit()

# ==================== HIGH-FREQUENCY ASYNC POLLING LOOP ====================
async def async_otp_checker_worker():
    print("🚀 Background Scraper Broker Loop Started (High-Speed Async Engine)...")
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                with get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT id, user_id, order_id, phone_number, service, country, api_source FROM active_orders WHERE status='WAITING'")
                    active_orders = cursor.fetchall()

                if active_orders:
                    tasks = [async_check_single_order(session, order) for order in active_orders]
                    await asyncio.gather(*tasks)

            except Exception as e:
                print(f"Error in Scraper Worker: {e}")

            await asyncio.sleep(1.5)  # High-frequency 1.5 second loop

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(async_otp_checker_worker())
    except KeyboardInterrupt:
        print("Scraper Broker stopped by user.")
