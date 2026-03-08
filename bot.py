import telebot
import os
import asyncio
import edge_tts
import time
from telebot import types
from deep_translator import GoogleTranslator
from flask import Flask
from threading import Thread

# --- Web Server សម្រាប់ Render ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online with 19 Languages!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- ការកំណត់ Bot ---
API_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

# បញ្ជី ១៩ ភាសា (19 Languages)
LANG_MAP = {
    "🇰🇭 Khmer": {"code": "km", "f": "km-KH-SreymomNeural", "m": "km-KH-PisethNeural"},
    "🇺🇸 English": {"code": "en", "f": "en-US-AvaNeural", "m": "en-US-AndrewNeural"},
    "🇹🇭 Thai": {"code": "th", "f": "th-TH-AcharaNeural", "m": "th-TH-NiwatNeural"},
    "🇻🇳 Vietnamese": {"code": "vi", "f": "vi-VN-HoaiMyNeural", "m": "vi-VN-NamMinhNeural"},
    "🇱🇦 Lao": {"code": "lo", "f": "lo-LA-KeomanyNeural", "m": "lo-LA-ChanthavongNeural"},
    "🇲🇾 Malay": {"code": "ms", "f": "ms-MY-YasminNeural", "m": "ms-MY-OsmanNeural"},
    "🇮🇩 Indonesian": {"code": "id", "f": "id-ID-GadisNeural", "m": "id-ID-ArdiNeural"},
    "🇵🇭 Filipino": {"code": "fil", "f": "fil-PH-BlessicaNeural", "m": "fil-PH-AngeloNeural"},
    "🇲🇲 Myanmar": {"code": "my", "f": "my-MM-NilarNeural", "m": "my-MM-ThihaNeural"},
    "🇨🇳 Chinese": {"code": "zh-CN", "f": "zh-CN-XiaoxiaoNeural", "m": "zh-CN-YunxiNeural"},
    "🇰🇷 Korean": {"code": "ko", "f": "ko-KR-SunHiNeural", "m": "ko-KR-InGooNeural"},
    "🇯🇵 Japanese": {"code": "ja", "f": "ja-JP-NanamiNeural", "m": "ja-JP-KeitaNeural"},
    "🇫🇷 French": {"code": "fr", "f": "fr-FR-DeniseNeural", "m": "fr-FR-HenriNeural"},
    "🇷🇺 Russian": {"code": "ru", "f": "ru-RU-SvetlanaNeural", "m": "ru-RU-DmitryNeural"},
    "🇩🇪 German": {"code": "de", "f": "de-DE-KatjaNeural", "m": "de-DE-ConradNeural"},
    "🇸🇦 Arabic": {"code": "ar", "f": "ar-SA-ZariyahNeural", "m": "ar-SA-HamedNeural"},
    "🇧🇩 Bengali": {"code": "bn", "f": "bn-BD-NabanitaNeural", "m": "bn-BD-PradeepNeural"},
    "🇵🇹 Portuguese": {"code": "pt", "f": "pt-PT-RaquelNeural", "m": "pt-PT-DuarteNeural"},
    "🇮🇳 Hindi": {"code": "hi", "f": "hi-IN-SwaraNeural", "m": "hi-IN-MadhurNeural"}
}

user_data = {}

async def generate_voice(text, voice_name, output_file):
    communicate = edge_tts.Communicate(text, voice_name, rate="-10%", pitch="-5Hz")
    await communicate.save(output_file)

def get_kb(chat_id):
    st = user_data.get(chat_id, {'gender': 'f', 'target': '🇰🇭 Khmer', 'format': 'mp3'})
    g_btn = "👨 ប្តូរទៅសំឡេងប្រុស" if st['gender'] == 'f' else "👩 ប្តូរទៅសំឡេងស្រី"
    f_btn = "🎤 ប្តូរទៅជា Voice" if st.get('format') == 'mp3' else "📁 ប្តូរទៅជា MP3"
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(types.KeyboardButton(g_btn), types.KeyboardButton(f_btn))
    kb.add(*[types.KeyboardButton(l) for l in LANG_MAP.keys()])
    return kb

@bot.message_handler(commands=['start'])
def start(m):
    user_data[m.chat.id] = {'gender': 'f', 'target': '🇰🇭 Khmer', 'format': 'mp3'}
    bot.send_message(m.chat.id, f"👋 សួស្តី {m.from_user.first_name}! ផ្ញើអត្ថបទមកដើម្បីបកប្រែជា MP3/Voice", reply_markup=get_kb(m.chat.id))

@bot.message_handler(func=lambda m: m.text and "ប្តូរទៅ" in m.text)
def settings(m):
    cid = m.chat.id
    if cid not in user_data: user_data[cid] = {'gender': 'f', 'target': '🇰🇭 Khmer', 'format': 'mp3'}
    if "សំឡេង" in m.text:
        user_data[cid]['gender'] = 'm' if user_data[cid]['gender'] == 'f' else 'f'
    elif "ជា" in m.text:
        user_data[cid]['format'] = 'voice' if user_data[cid].get('format') == 'mp3' else 'mp3'
    bot.send_message(cid, "✅ រក្សាទុកការកំណត់រួចរាល់", reply_markup=get_kb(cid))

@bot.message_handler(func=lambda m: m.text in LANG_MAP.keys())
def set_lang(m):
    user_data[m.chat.id] = user_data.get(m.chat.id, {'gender': 'f', 'target': '🇰🇭 Khmer', 'format': 'mp3'})
    user_data[m.chat.id]['target'] = m.text
    bot.send_message(m.chat.id, f"🎯 គោលដៅ៖ {m.text}", reply_markup=get_kb(m.chat.id))

@bot.message_handler(func=lambda m: True)
def process(m):
    cid = m.chat.id
    if cid not in user_data: user_data[cid] = {'gender': 'f', 'target': '🇰🇭 Khmer', 'format': 'mp3'}
    st = user_data[cid]
    target = LANG_MAP[st['target']]
    try:
        translated = GoogleTranslator(source='auto', target=target['code']).translate(m.text)
        bot.send_message(cid, f"📝 `{translated}`", parse_mode="Markdown")
        fname = f"v_{cid}_{int(time.time())}.mp3"
        asyncio.run(generate_voice(translated, target[st['gender']], fname))
        with open(fname, 'rb') as v:
            caption_text = "📣 @nyvoicebot" 
            if st.get('format') == 'voice':
                bot.send_voice(cid, v, caption=caption_text)
            else:
                bot.send_document(cid, v, caption=caption_text, visible_file_name="voice.mp3")
        os.remove(fname)
    except:
        bot.send_message(cid, "❌ មានបញ្ហាបច្ចេកទេស!")

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    bot.infinity_polling(skip_pending=True)
