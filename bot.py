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
def home(): return "Multi-Language Pro Bot is Live!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# --- ការកំណត់ Bot ---
API_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

# បញ្ជីសំឡេង និងកូដភាសា (១២ ភាសា)
LANG_MAP = {
    "🇺🇸 English": {"code": "en", "f": "en-US-AvaNeural", "m": "en-US-AndrewNeural"},
    "🇫🇷 French": {"code": "fr", "f": "fr-FR-DeniseNeural", "m": "fr-FR-HenriNeural"},
    "🇨🇳 Chinese": {"code": "zh-CN", "f": "zh-CN-XiaoxiaoNeural", "m": "zh-CN-YunxiNeural"},
    "🇻🇳 Vietnamese": {"code": "vi", "f": "vi-VN-HoaiMyNeural", "m": "vi-VN-NamMinhNeural"},
    "🇰🇷 Korean": {"code": "ko", "f": "ko-KR-SunHiNeural", "m": "ko-KR-InGooNeural"},
    "🇯🇵 Japanese": {"code": "ja", "f": "ja-JP-NanamiNeural", "m": "ja-JP-KeitaNeural"},
    "🇮🇳 Hindi": {"code": "hi", "f": "hi-IN-SwaraNeural", "m": "hi-IN-MadhurNeural"},
    "🇹🇭 Thai": {"code": "th", "f": "th-TH-AcharaNeural", "m": "th-TH-NiwatNeural"},
    "🇱🇦 Lao": {"code": "lo", "f": "lo-LA-KeomanyNeural", "m": "lo-LA-ChanthavongNeural"},
    "🇮🇩 Indonesian": {"code": "id", "f": "id-ID-GadisNeural", "m": "id-ID-ArdiNeural"},
    "🇵🇭 Filipino": {"code": "fil", "f": "fil-PH-BlessicaNeural", "m": "fil-PH-AngeloNeural"},
    "🇰🇭 Khmer": {"code": "km", "f": "km-KH-SreymomNeural", "m": "km-KH-PisethNeural"}
}

user_data = {}

async def generate_voice(text, voice_name, output_file):
    communicate = edge_tts.Communicate(text, voice_name, rate="-10%", pitch="-5Hz")
    await communicate.save(output_file)

def get_kb(chat_id):
    st = user_data.get(chat_id, {'gender': 'f', 'target': '🇰🇭 Khmer'})
    gender_btn = "👨 ប្តូរទៅសំឡេងប្រុស" if st['gender'] == 'f' else "👩 ប្តូរទៅសំឡេងស្រី"
    
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    kb.add(types.KeyboardButton(gender_btn))
    buttons = [types.KeyboardButton(lang) for lang in LANG_MAP.keys()]
    kb.add(*buttons)
    return kb

@bot.message_handler(commands=['start'])
def start(m):
    user_data[m.chat.id] = {'gender': 'f', 'target': '🇰🇭 Khmer'}
    bot.send_message(m.chat.id, "👋 សួស្តី! ផ្ញើអត្ថបទមក ខ្ញុំនឹងបកប្រែ ផ្ញើទាំងសំឡេង និងអត្ថបទឱ្យ Copy។", reply_markup=get_kb(m.chat.id))

@bot.message_handler(func=lambda m: "ប្តូរទៅសំឡេង" in m.text)
def toggle_gender(m):
    cid = m.chat.id
    if cid not in user_data: user_data[cid] = {'gender': 'f', 'target': '🇰🇭 Khmer'}
    user_data[cid]['gender'] = 'm' if user_data[cid]['gender'] == 'f' else 'f'
    status = "ប្រុស" if user_data[cid]['gender'] == 'm' else "ស្រី"
    bot.send_message(cid, f"✅ បានប្តូរទៅប្រើសំឡេង៖ {status}", reply_markup=get_kb(cid))

@bot.message_handler(func=lambda m: m.text in LANG_MAP.keys())
def set_language(m):
    cid = m.chat.id
    if cid not in user_data: user_data[cid] = {'gender': 'f', 'target': '🇰🇭 Khmer'}
    user_data[cid]['target'] = m.text
    bot.send_message(cid, f"🎯 គោលដៅបកប្រែ៖ {m.text}", reply_markup=get_kb(cid))

@bot.message_handler(func=lambda m: True)
def handle_message(m):
    cid = m.chat.id
    text = m.text
    if cid not in user_data: user_data[cid] = {'gender': 'f', 'target': '🇰🇭 Khmer'}
    
    st = user_data[cid]
    target_info = LANG_MAP[st['target']]

    bot.send_chat_action(cid, 'typing')
    try:
        translated_text = GoogleTranslator(source='auto', target=target_info['code']).translate(text)
        
        # ផ្ញើអត្ថបទដែលអាច Copy បាន (Monospace)
        bot.send_message(cid, f"📝 **បកប្រែរួច៖**\n\n`{translated_text}`", parse_mode="MarkdownV2")

        # បង្កើតសំឡេង
        voice_name = target_info[st['gender']]
        fname = f"v_{cid}.mp3"
        
        bot.send_chat_action(cid, 'record_audio')
        asyncio.run(generate_voice(translated_text, voice_name, fname))
        
        # ផ្ញើសំឡេង (ដោយគ្មានប៊ូតុង Inline)
        with open(fname, 'rb') as v:
            bot.send_voice(cid, v, caption=f"🌐 ភាសា៖ {st['target']}\n✨ @Ny_voice_bot")
        
        os.remove(fname)
    except:
        bot.send_message(cid, "❌ មិនអាចដំណើរការបានទេ។")

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.infinity_polling(skip_pending=True)
