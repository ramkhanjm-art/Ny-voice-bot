import telebot
import os
import asyncio
import edge_tts
from telebot import types
from deep_translator import GoogleTranslator
from flask import Flask
from threading import Thread

# --- Web Server សម្រាប់ Render ---
app = Flask('')
@app.route('/')
def home(): return "Multi-Language Bot is Live!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# --- ការកំណត់ Bot ---
API_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

# បញ្ជីភាសា និងសំឡេងសម្រាប់បកប្រែទៅមក
LANG_MAP = {
    "🇺🇸 English": {"code": "en", "voice": "en-US-AvaNeural"},
    "🇫🇷 French": {"code": "fr", "voice": "fr-FR-DeniseNeural"},
    "🇨🇳 Chinese": {"code": "zh-CN", "voice": "zh-CN-XiaoxiaoNeural"},
    "🇻🇳 Vietnamese": {"code": "vi", "voice": "vi-VN-HoaiMyNeural"},
    "🇰🇷 Korean": {"code": "ko", "voice": "ko-KR-SunHiNeural"},
    "🇯🇵 Japanese": {"code": "ja", "voice": "ja-JP-NanamiNeural"},
    "🇮🇳 Hindi": {"code": "hi", "voice": "hi-IN-SwaraNeural"},
    "🇹🇭 Thai": {"code": "th", "voice": "th-TH-AcharaNeural"},
    "🇱🇦 Lao": {"code": "lo", "voice": "lo-LA-KeomanyNeural"},
    "🇮🇩 Indonesian": {"code": "id", "voice": "id-ID-GadisNeural"},
    "🇵🇭 Filipino": {"code": "fil", "voice": "fil-PH-BlessicaNeural"},
    "🇰🇭 Khmer": {"code": "km", "voice": "km-KH-SreymomNeural"}
}

user_settings = {}

async def generate_voice(text, voice_name, output_file):
    # កំណត់ rate="-10%" ឱ្យអានយឺតស្រទន់
    communicate = edge_tts.Communicate(text, voice_name, rate="-10%", pitch="-5Hz")
    await communicate.save(output_file)

def get_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    buttons = [types.KeyboardButton(lang) for lang in LANG_MAP.keys()]
    kb.add(*buttons)
    return kb

@bot.message_handler(commands=['start'])
def start(m):
    user_settings[m.chat.id] = "🇰🇭 Khmer"
    bot.send_message(m.chat.id, "👋 សូមជ្រើសរើសភាសាគោលដៅ រួចផ្ញើអត្ថបទមក ខ្ញុំនឹងបកប្រែ និងអានឱ្យស្តាប់។", reply_markup=get_kb())

@bot.message_handler(func=lambda m: m.text in LANG_MAP.keys())
def set_language(m):
    user_settings[m.chat.id] = m.text
    bot.send_message(m.chat.id, f"✅ បានកំណត់៖ បកប្រែទៅជា {m.text}")

@bot.message_handler(func=lambda m: True)
def handle_message(m):
    cid = m.chat.id
    text = m.text
    target_lang_name = user_settings.get(cid, "🇰🇭 Khmer")
    target_info = LANG_MAP[target_lang_name]

    bot.send_chat_action(cid, 'record_audio')
    try:
        # បកប្រែពីគ្រប់ភាសាមកកាន់ភាសាគោលដៅ
        translated_text = GoogleTranslator(source='auto', target=target_info['code']).translate(text)
        
        fname = f"v_{cid}.mp3"
        asyncio.run(generate_voice(translated_text, target_info['voice'], fname))
        
        # ប៊ូតុង Inline ក្រោមសំឡេង
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Channel", url="https://t.me/YourChannel"),
                   types.InlineKeyboardButton("👤 Admin", url="https://t.me/YourAdminID"))
        
        caption = f"🌐 បកប្រែជា៖ {target_lang_name}\n✨ @Ny_voice_bot"
        with open(fname, 'rb') as v:
            bot.send_voice(cid, v, caption=caption, reply_markup=markup)
        os.remove(fname)
    except:
        bot.send_message(cid, "❌ មិនអាចបកប្រែបានទេ។ សូមព្យាយាមម្តងទៀត។")

if __name__ == "__main__":
    Thread(target=run_web).start()
    # សំខាន់៖ skip_pending=True ជួយទប់ស្កាត់ការគាំង Conflict
    bot.infinity_polling(skip_pending=True)
