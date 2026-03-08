import telebot
import os
import asyncio
import edge_tts
import pytesseract
from PIL import Image
import time
from telebot import types
from deep_translator import GoogleTranslator
from flask import Flask
from threading import Thread

# --- Web Server ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Live (Tesseract)!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- Bot Config ---
API_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

LANG_MAP = {
    "🇺🇸 English": {"code": "en", "f": "en-US-AvaNeural", "m": "en-US-AndrewNeural"},
    "🇨🇵 French": {"code": "fr", "f": "fr-FR-DeniseNeural", "m": "fr-FR-HenriNeural"},
    "🇨🇳 Chinese": {"code": "zh-CN", "f": "zh-CN-XiaoxiaoNeural", "m": "zh-CN-YunxiNeural"},
    "🇻🇳 Vietnamese": {"code": "vi", "f": "vi-VN-HoaiMyNeural", "m": "vi-VN-NamMinhNeural"},
    "🇰🇷 Korean": {"code": "ko", "f": "ko-KR-SunHiNeural", "m": "ko-KR-InGooNeural"},
    "🇯🇵 Japanese": {"code": "ja", "f": "ja-JP-NanamiNeural", "m": "ja-JP-KeitaNeural"},
    "🇹🇭 Thai": {"code": "th", "f": "th-TH-AcharaNeural", "m": "th-TH-NiwatNeural"},
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
    bot.send_message(m.chat.id, "👋 សួស្តី! ផ្ញើអត្ថបទ ឬរូបភាពមកបកប្រែ (Default: MP3)", reply_markup=get_kb(m.chat.id))

@bot.message_handler(func=lambda m: m.text and "ប្តូរទៅ" in m.text)
def toggle_settings(m):
    cid = m.chat.id
    if cid not in user_data: user_data[cid] = {'gender': 'f', 'target': '🇰🇭 Khmer', 'format': 'mp3'}
    if "សំឡេង" in m.text:
        user_data[cid]['gender'] = 'm' if user_data[cid]['gender'] == 'f' else 'f'
        bot.send_message(cid, f"✅ ប្តូរភេទរួចរាល់", reply_markup=get_kb(cid))
    elif "ជា" in m.text:
        user_data[cid]['format'] = 'voice' if user_data[cid].get('format') == 'mp3' else 'mp3'
        bot.send_message(cid, f"✅ ប្តូរ Format រួចរាល់", reply_markup=get_kb(cid))

@bot.message_handler(func=lambda m: m.text in LANG_MAP.keys())
def set_language(m):
    user_data[m.chat.id] = user_data.get(m.chat.id, {'gender': 'f', 'target': '🇰🇭 Khmer', 'format': 'mp3'})
    user_data[m.chat.id]['target'] = m.text
    bot.send_message(m.chat.id, f"🎯 គោលដៅ៖ {m.text}", reply_markup=get_kb(m.chat.id))

# --- OCR រូបភាព ---
@bot.message_handler(content_types=['photo'])
def handle_photo(m):
    cid = m.chat.id
    bot.send_message(cid, "🔍 កំពុងអានរូបភាព...")
    try:
        file_info = bot.get_file(m.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        img_path = f"img_{cid}.jpg"
        with open(img_path, 'wb') as f: f.write(downloaded_file)
        
        # ប្រើ Tesseract អានអក្សរ (ភាសាអង់គ្លេសជាគោល)
        extracted_text = pytesseract.image_to_string(Image.open(img_path))
        os.remove(img_path)
        
        if not extracted_text.strip():
            bot.send_message(cid, "❌ រកមិនឃើញអត្ថបទ។")
            return
        process_translation(cid, extracted_text)
    except:
        bot.send_message(cid, "❌ បញ្ហា OCR (Render កំពុងមមាញឹក)")

@bot.message_handler(func=lambda m: True)
def handle_text(m):
    if m.text: process_translation(m.chat.id, m.text)

def process_translation(cid, text):
    st = user_data.get(cid, {'gender': 'f', 'target': '🇰🇭 Khmer', 'format': 'mp3'})
    target_info = LANG_MAP[st['target']]
    try:
        translated = GoogleTranslator(source='auto', target=target_info['code']).translate(text)
        bot.send_message(cid, f"📝 `{translated}`", parse_mode="Markdown")
        
        fname = f"v_{cid}.mp3"
        asyncio.run(generate_voice(translated, target_info[st['gender']], fname))
        
        with open(fname, 'rb') as v:
            if st.get('format') == 'voice': bot.send_voice(cid, v)
            else: bot.send_document(cid, v, visible_file_name="voice.mp3")
        os.remove(fname)
    except:
        bot.send_message(cid, "❌ Error!")

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    bot.infinity_polling(skip_pending=True)
