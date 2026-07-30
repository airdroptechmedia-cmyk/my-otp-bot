import os
import time
import threading
import requests
import telebot

# ----------------- কনফিগারেশন -----------------
# GitHub-এ আপলোড করার সময় এই টোকেনগুলো এভাবেই রাখবেন। 
# Render-এ হোস্ট করলে Environment Variables (Env) থেকে এগুলো অটোমেটিক সেট হবে।
BOT_TOKEN = os.getenv("BOT_TOKEN", "8842802759:AAFTzG_yyzHiirBiW2Canl2l0t_sG2HxKt8")
VOLTX_API_KEY = os.getenv("VOLTX_API_KEY", "M7D4REK5Y06")
STEX_API_KEY = os.getenv("STEX_API_KEY", "M6SB7HZXXIX")

bot = telebot.TeleBot(BOT_TOKEN)

# API Base URLs (প্রোভাইডারদের লেটেস্ট এপিআই এন্ডপয়েন্ট)
VOLTX_BASE_URL = "https://voltxsms.com"
STEX_BASE_URL = "https://stexsms.com"

# ----------------- ওটিপি চেকিং ফাংশন (Background Thread) -----------------
def check_otp_worker(chat_id, order_id, api_key, base_url, message_id):
    """
    এই ফাংশনটি ব্যাকগ্রাউন্ড থ্রেডে চলে, যার ফলে Render সার্ভার ওটিপির জন্য 
    অপেক্ষা করতে গিয়ে মেইন বটকে ব্লক বা টাইমআউট করে দেয় না।
    """
    max_wait_time = 240  # ওটিপির জন্য সর্বোচ্চ ৪ মিনিট অপেক্ষা করবে
    start_time = time.time()
    
    bot.edit_message_text("⏳ নাম্বার নেওয়া হয়েছে। ওটিপির জন্য অপেক্ষা করা হচ্ছে...", chat_id, message_id)
    
    while time.time() - start_time < max_wait_time:
        try:
            # স্ট্যাটাস চেক করার জন্য রিকোয়েস্ট ইউআরএল
            url = f"{base_url}?api_key={api_key}&action=getStatus&id={order_id}"
            response = requests.get(url, timeout=10)
            res_text = response.text
            
            # ওটিপি চলে আসলে
            if "STATUS_OK" in res_text:
                otp_code = res_text.split(":")[1] # STATUS_OK:12345 থেকে ওটিপি আলাদা করা
                bot.edit_message_text(f"✅ ওটিপি চলে এসেছে!\n\n🔢 OTP: `{otp_code}`\n📝 Full Response: {res_text}", chat_id, message_id, parse_mode="Markdown")
                return
                
            # ওটিপি এখনো না আসলে (অপেক্ষা করবে)
            elif "STATUS_WAIT" in res_text:
                time.sleep(6)  # রেট লিমিট এড়াতে ৬ সেকেন্ড পরপর চেক করবে
                
            # নাম্বার ক্যানসেল হয়ে গেলে
            elif "STATUS_CANCEL" in res_text:
                bot.edit_message_text("❌ ওটিপি আসার আগেই নাম্বারটি বাতিল বা ক্যানসেল হয়ে গেছে।", chat_id, message_id)
                return
                
        except Exception as e:
            # এপিআই সাময়িক ডাউন বা নেটওয়ার্ক এরর হলে ৩ সেকেন্ড পর আবার ট্রাই করবে
            time.sleep(3)
            
    # ৪ মিনিট পার হয়ে গেলে অটোমেটিক ক্যানসেল রিকোয়েস্ট পাঠাবে
    try:
        requests.get(f"{base_url}?api_key={api_key}&action=setStatus&status=8&id={order_id}", timeout=10)
    except:
        pass
    bot.edit_message_text("⏰ দুঃখিত, ওটিপি আসার নির্ধারিত সময় শেষ (Timeout)। নাম্বারটি অটো-ক্যানসেল করা হয়েছে।", chat_id, message_id)

# ----------------- টেলিগ্রাম বট কমান্ড হ্যান্ডলার -----------------

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    help_text = (
        "👋 ভার্চুয়াল নাম্বার ও ওটিপি বট টেস্টারে স্বাগতম!\n\n"
        "**নাম্বার নেওয়ার কমান্ড ফরম্যাট:**\n"
        "`/get [provider] [country_id] [service_id]`\n\n"
        "**উদাহরণ:**\n"
        "🔹 Voltx থেকে নাম্বার নিতে: `/get voltx 1 tg`\n"
        "🔸 Stex থেকে নাম্বার নিতে: `/get stex 1 tg`\n\n"
        "_(এখানে ১ = ইন্ডিয়া/যেকোনো দেশের আইডি, tg = টেলিগ্রাম সার্ভিস আইডি)_"
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['get'])
def get_number(message):
    chat_id = message.chat.id
    args = message.text.split()
    
    # ইনপুট ভ্যালিডেশন চেক
    if len(args) < 4:
        bot.reply_to(message, "❌ ভুল ফরম্যাট! সঠিক ফরম্যাট: `/get voltx 1 tg`", parse_mode="Markdown")
        return
        
    provider = args[1].lower()
    country = args[2]
    service = args[3]
    
    # প্রোভাইডার অনুযায়ী API Key ও URL সেটআপ
    if provider == "voltx":
        api_key = VOLTX_API_KEY
        base_url = VOLTX_BASE_URL
    elif provider == "stex":
        api_key = STEX_API_KEY
        base_url = STEX_BASE_URL
    else:
        bot.reply_to(message, "❌ ভুল প্রোভাইডার! শুধু `voltx` অথবা `stex` লিখুন।")
        return

    # প্রাথমিক রিকোয়েস্ট মেসেজ
    status_msg = bot.reply_to(message, "🔄 এপিআই থেকে নাম্বার খোঁজা হচ্ছে, দয়া করে অপেক্ষা করুন...")
    
    try:
        # নাম্বার অর্ডার করার এপিআই কল
        order_url = f"{base_url}?api_key={api_key}&action=getNumber&service={service}&country={country}"
        response = requests.get(order_url, timeout=12)
        res_text = response.text
        
        # সফলভাবে নাম্বার আসলে রেসপন্স ফরম্যাট হয়: ACCESS_NUMBER:ORDER_ID:NUMBER
        if "ACCESS_NUMBER" in res_text:
            parts = res_text.split(":")
            order_id = parts[1]
            phone_number = parts[2]
            
            success_text = (
                f"📱 **নাম্বার পাওয়া গেছে!**\n\n"
                f"🆔 Order ID: `{order_id}`\n"
                f"📞 Number: `+{phone_number}`\n\n"
                f"⚠️ অ্যাপে নাম্বারটি বসান। ওটিপি ট্র্যাকিং শুরু হচ্ছে..."
            )
            bot.edit_message_text(success_text, chat_id, status_msg.message_id, parse_mode="Markdown")
            
            # 🚀 ম্যাজিক পার্ট: ওটিপি চেকিংয়ের জন্য আলাদা ব্যাকগ্রাউন্ড থ্রেড চালু করা হলো
            # এর ফলে Render-এর মেইন কানেকশন ব্লক হবে না এবং ওটিপি ওখানেই ক্যাচ হবে
            threading.Thread(
                target=check_otp_worker, 
                args=(chat_id, order_id, api_key, base_url, status_msg.message_id),
                daemon=True
            ).start()
            
        elif "NO_NUMBERS" in res_text:
            bot.edit_message_text("❌ এই মুহূর্তে এই সার্ভিসের কোনো নাম্বার খালি নেই।", chat_id, status_msg.message_id)
        elif "NO_BALANCE" in res_text:
            bot.edit_message_text("❌ আপনার এপিআই অ্যাকাউন্টে পর্যাপ্ত ব্যালেন্স নেই।", chat_id, status_msg.message_id)
        elif "BAD_KEY" in res_text:
            bot.edit_message_text("❌ এপিআই কি (API Key) ভুল বা ইনভ্যালিড।", chat_id, status_msg.message_id)
        else:
            bot.edit_message_text(f"❌ এপিআই এরর এসেছে। রেসপন্স: {res_text}", chat_id, status_msg.message_id)
            
    except Exception as e:
        bot.edit_message_text(f"💥 কানেকশনে সমস্যা হয়েছে! একটু পর আবার চেষ্টা করুন।", chat_id, status_msg.message_id)

# ----------------- বট রানিং মেকানিংশ -----------------
if __name__ == "__main__":
    print("🤖 ওটিপি টেস্টার বট সফলভাবে চালু হয়েছে...")
    # Render হোস্টিংয়ের জন্য ও নেটওয়ার্ক ড্রপ এড়াতে infinity_polling ব্যবহার করা হয়েছে
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
