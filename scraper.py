import sys
import sqlite3
import asyncio
import aiohttp
import re
import datetime

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8842802759:AAE04k_Lx1Bq_-pXpr14-4WF8gsOjZJUPR4"
DB_NAME = "system.db"
POLL_INTERVAL = 1.5  # High frequency 1.5s sleep loop
# =======================================================

def get_db():
    conn = sqlite3.connect(DB_NAME, timeout=15)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def get_setting(key):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
        res = cursor.fetchone()
        conn.close()
        return res[0] if res else ""
    except Exception:
        return ""

# ----------------- RIGID PASSCODE PARSING LOGIC -----------------
def extract_otp_from_response(res, clean_phone):
    if not res:
        return None
    
    clean_phone = str(clean_phone).replace("+", "").strip() if clean_phone else ""
    
    def extract_code_from_str(s):
        if not s or not isinstance(s, (str, int)):
            return None
        s_str = str(s).strip()
        
        ignored = [
            "none", "null", "waiting", "pending", "false", "true", "ok", "success", 
            "status_ok", "200", "400", "404", "500", "error", "no_sms", "not_found", 
            "processing", "no_otp", "exist", "number_active", "received", "cancelled",
            "cancel", "timeout", "expire", "expired", "wait", "done"
        ]
        if s_str.lower() in ignored:
            return None

        # Hyphenated OTP like 123-456
        hyphen_match = re.search(r'\b\d{3,4}-\d{3,4}\b', s_str)
        if hyphen_match:
            return hyphen_match.group(0).replace('-', '')

        # Standard 4 to 8 digit numbers
        matches = re.findall(r'\b\d{4,8}\b', s_str)
        if matches:
            return matches[0]

        # Letter prefixed codes like G-123456
        prefix_match = re.search(r'\b([A-Za-z]{1,4}[- ]?\d{4,8})\b', s_str)
        if prefix_match:
            return prefix_match.group(1)

        return None

    def get_code_from_dict(d):
        if not isinstance(d, dict):
            return None
        for field in ['otp', 'sms', 'last_code', 'text', 'message', 'msg', 'code']:
            val = d.get(field)
            c = extract_code_from_str(val)
            if c:
                return c
        return None

    if isinstance(res, (str, int)):
        return extract_code_from_str(res)

    if isinstance(res, dict):
        for key in ["data", "result", "messages", "orders", "sms"]:
            val = res.get(key)
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, dict):
                        c = get_code_from_dict(item)
                        if c:
                            return c
                    elif isinstance(item, (str, int)):
                        c = extract_code_from_str(item)
                        if c:
                            return c
            elif isinstance(val, dict):
                c = get_code_from_dict(val)
                if c:
                    return c
            elif isinstance(val, (str, int)):
                c = extract_code_from_str(val)
                if c:
                    return c

        return get_code_from_dict(res)

    return None

# ----------------- SMS API POLLING -----------------
async def fetch_sms_from_provider(session, phone_num, api_source="API1"):
    if api_source == "API2":
        api_key = get_setting('number_api_key_2') or "M6SB7HZXXIX"
        base_url = get_setting('api_base_url_2') or "https://api.2oo9.cloud/MXS47FLFX0U/tnevs/@public/api"
    else:
        api_key = get_setting('number_api_key') or "M7D4REK5Y06"
        base_url = get_setting('api_base_url') or "https://api.2oo9.cloud/MXS47FLFX0U/tnevs/@public/api"
    
    clean_phone = str(phone_num).replace("+", "").strip()
    headers = {"mauthapi": api_key, "Content-Type": "application/json"}
    
    url = f"{base_url.rstrip('/')}/success-otp"
    payload = {"number": clean_phone, "no_plus_number": clean_phone, "full_number": f"+{clean_phone}"}
    
    try:
        async with session.post(url, json=payload, headers=headers, timeout=4) as response:
            if response.status == 200:
                res = await response.json()
                otp_code = extract_otp_from_response(res, clean_phone)
                if otp_code:
                    return "RECEIVED", otp_code
    except Exception:
        pass
        
    return "WAITING", None

# ----------------- DIRECT TELEGRAM NOTIFICATION -----------------
async def send_direct_telegram_msg(session, chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        async with session.post(url, json=payload, timeout=5) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"Error delivering Telegram notification: {e}")
        return False

# ----------------- PROCESS SINGLE VERIFICATION -----------------
async def process_verification(session, ver_record):
    ver_id, user_id, phone_num, service_name, api_source = ver_record
    status, otp_code = await fetch_sms_from_provider(session, phone_num, api_source)

    if status == "RECEIVED" and otp_code:
        reward_val = 0.30

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE verifications SET status='COMPLETED', otp_code=? WHERE id=?", (otp_code, ver_id))
        cursor.execute("UPDATE users SET balance = balance + ?, reward_balance = reward_balance + ?, otp_count = otp_count + 1 WHERE user_id=?", (reward_val, reward_val, user_id))
        cursor.execute("SELECT balance, reward_balance FROM users WHERE user_id=?", (user_id,))
        user_row = cursor.fetchone()
        new_bal = user_row[0] if user_row else 0.0
        new_rew_bal = user_row[1] if user_row else 0.0
        conn.commit()
        conn.close()

        # HTML Click-to-Copy format
        user_text = (
            f"🎉 <b>NEW OTP RECEIVED!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"⚙️ <b>Service:</b> {service_name}\n"
            f"📱 <b>Number:</b> <code>{phone_num}</code>\n"
            f"📘 <b>OTP Code:</b> <code>{otp_code}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🎁 <b>OTP Reward Credited: +{reward_val:.2f} BDT</b>\n"
            f"💰 <b>Reward Balance: {new_rew_bal:.2f} BDT</b>\n"
            f"💼 <b>Total Balance: {new_bal:.2f} BDT</b>\n\n"
            f"👉 <i>(কোডের ওপর টাচ করলেই অটোমেটিক কপি হয়ে যাবে!)</i>"
        )
        await send_direct_telegram_msg(session, user_id, user_text)

        # Broadcast to public channel
        otp_group = get_setting('otp_group_id') or "@otpreciverpro"
        group_text = (
            f"🔔 <b>LIVE OTP TRAFFIC!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"⚙️ <b>Service:</b> {service_name}\n"
            f"📱 <b>Number:</b> <code>{phone_num}</code>\n"
            f"🔑 <b>OTP Code:</b> <code>{otp_code}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━"
        )
        await send_direct_telegram_msg(session, otp_group, group_text)

# ----------------- HIGH-FREQUENCY SCRAPER LOOP -----------------
async def main():
    print("🚀 Background SMS Broker Scraper Loop Started...")
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("SELECT id, user_id, phone_number, service_name, api_source FROM verifications WHERE status='WAITING'")
                active_verifications = cursor.fetchall()
                conn.close()

                if active_verifications:
                    tasks = [process_verification(session, ver) for ver in active_verifications]
                    await asyncio.gather(*tasks)

            except Exception as e:
                print(f"Error in Scraper Loop: {e}")

            await asyncio.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())
