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
def home(): return "Bot is running (MP3 & Voice)!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- ការកំណត់ Bot ---
API_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

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
    st = user_data.get(chat_id, {'gender': 'f', 'target': '🇰🇭 Khmer', 'format': 'mp3'})
    gender_btn = "👨 ប្តូរទៅសំឡេងប្រុស" if st['gender'] == 'f' else "👩 ប្តូរទៅសំឡេងស្រី"
    format_btn = "🎤 ប្តូរទៅជា Voice" if st.get('format') == 'mp3' else "📁 ប្តូរទៅជា MP3"
    
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(types.KeyboardButton(gender_btn), types.KeyboardButton(format_btn))
    buttons = [types.KeyboardButton(lang) for lang in LANG_MAP.keys()]
    kb.add(*buttons)
    return kb

@bot.message_handler(commands=['start'])
def start(m):
    user_data[m.chat.id] = {'gender': 'f', 'target': '🇰🇭 Khmer', 'format': 'mp3'}
    msg = "👋 សួស្តី! ផ្ញើអត្ថបទមក ខ្ញុំនឹងបកប្រែជាសំឡេងឱ្យ។\n✅ កំណត់ដើម៖ **ឯកសារ MP3**"
    bot.send_message(m.chat.id, msg, reply_markup=get_kb(m.chat.id), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and "ប្តូរទៅ" in m.text)
def toggle_settings(m):
    cid = m.chat.id
    if cid not in user_data: user_data[cid] = {'gender': 'f', 'target': '🇰🇭 Khmer', 'format': 'mp3'}
    
    if "សំឡេង" in m.text:
        user_data[cid]['gender'] = 'm' if user_data[cid]['gender'] == 'f' else 'f'
        status = "ប្រុស" if user_data[cid]['gender'] == 'm' else "ស្រី"
        bot.send_message(cid, f"✅ ប្តូរទៅសំឡេង៖ {status}", reply_markup=get_kb(cid))
    elif "ជា" in m.text:
        user_data[cid]['format'] = 'voice' if user_data[cid].get('format') == 'mp3' else 'mp3'
        status = "Voice Note" if user_data[cid]['format'] == 'voice' else "ឯកសារ MP3"
        bot.send_message(cid, f"✅ ប្តូរទម្រង់ជា៖ {status}", reply_markup=get_kb(cid))

@bot.message_handler(func=lambda m: m.text in LANG_MAP.keys())
def set_language(m):
    cid = m.chat.id
    if cid not in user_data: user_data[cid] = {'gender': 'f', 'target': '🇰🇭 Khmer', 'format': 'mp3'}
    user_data[cid]['target'] = m.text
    bot.send_message(cid, f"🎯 គោលដៅបកប្រែ៖ {m.text}", reply_markup=get_kb(cid))

@bot.message_handler(func=lambda m: True)
def handle_message(m):
    if not m.text: return
    cid = m.chat.id
    if cid not in user_data: user_data[cid] = {'gender': 'f', 'target': '🇰🇭 Khmer', 'format': 'mp3'}
    
    st = user_data[cid]
    target_info = LANG_MAP[st['target']]
    bot.send_chat_action(cid, 'typing')

    try:
        translated_text = GoogleTranslator(source='auto', target=target_info['code']).translate(m.text)
        clean_text = translated_text.replace('`', '').replace('*', '')
        bot.send_message(cid, f"📝 **បកប្រែរួច៖**\n\n`{clean_text}`", parse_mode="Markdown")

        voice_name = target_info[st['gender']]
        fname = f"v_{cid}_{int(time.time())}.mp3"
        
        bot.send_chat_action(cid, 'record_audio')
        asyncio.run(generate_voice(translated_text, voice_name, fname))
        
        with open(fname, 'rb') as audio_file:
            cap = f"🌐 ភាសា៖ {st['target']}\n📣 https://t.me/nyvoicebot"
            if st.get('format') == 'voice':
                bot.send_voice(cid, audio_file, caption=cap)
            else:
                bot.send_document(cid, audio_file, caption=cap, visible_file_name=f"voice_{int(time.time())}.mp3")
        
        if os.path.exists(fname): os.remove(fname)
    except Exception as e:
        bot.send_message(cid, "❌ មានបញ្ហាបច្ចេកទេស!")

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    print("Bot is Live (No OCR)!")
    bot.infinity_polling(skip_pending=True)
