import telebot
import os
import asyncio
import edge_tts
import easyocr
import time
from telebot import types
from deep_translator import GoogleTranslator
from flask import Flask
from threading import Thread

# --- Web Server សម្រាប់ Render ---
app = Flask('')
@app.route('/')
def home(): return "Bot is running with MP3 Default & OCR!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- ការកំណត់ Bot ---
API_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

# Initialize EasyOCR (អង់គ្លេស និង ខ្មែរ ជាភាសាគោល)
reader = easyocr.Reader(['en', 'km']) 

LANG_MAP = {
    "🇺🇸 English": {"code": "en", "f": "en-US-AvaNeural", "m": "en-US-AndrewNeural"},
    "🇫្រ French": {"code": "fr", "f": "fr-FR-DeniseNeural", "m": "fr-FR-HenriNeural"},
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
    # កំណត់ Default format ជា mp3 បើមិនទាន់មានទិន្នន័យ
    st = user_data.get(chat_id, {'gender': 'f', 'target': '🇰🇭 Khmer', 'format': 'mp3'})
    
    gender_btn = "👨 ប្តូរទៅសំឡេងប្រុស" if st['gender'] == 'f' else "👩 ប្តូរទៅសំឡេងស្រី"
    # បង្ហាញប៊ូតុងឆ្លាស់គ្នា៖ បើ mp3 ឱ្យប៊ូតុងប្តូរទៅជា Voice
    format_btn = "🎤 ប្តូរទៅជា Voice" if st.get('format') == 'mp3' else "📁 ប្តូរទៅជា MP3"
    
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(types.KeyboardButton(gender_btn), types.KeyboardButton(format_btn))
    
    buttons = [types.KeyboardButton(lang) for lang in LANG_MAP.keys()]
    kb.add(*buttons)
    return kb

@bot.message_handler(commands=['start'])
def start(m):
    # កំណត់ឱ្យជាប់ mp3 ពេលចុច start ដំបូង
    user_data[m.chat.id] = {'gender': 'f', 'target': '🇰🇭 Khmer', 'format': 'mp3'}
    msg = (
        "👋 សួស្តី! ខ្ញុំបកប្រែបាន ១២ ភាសា។\n\n"
        "✅ ការកំណត់បច្ចុប្បន្ន៖ **ឯកសារ MP3**\n"
        "👉 អ្នកអាចផ្ញើ **អត្ថបទ** ឬ **រូបភាព** មកឱ្យខ្ញុំបានភ្លាមៗ។"
    )
    bot.send_message(m.chat.id, msg, reply_markup=get_kb(m.chat.id), parse_mode="Markdown")

# --- ការប្តូរភេទ និងទម្រង់ឯកសារ ---
@bot.message_handler(func=lambda m: m.text and "ប្តូរទៅ" in m.text)
def toggle_settings(m):
    cid = m.chat.id
    if cid not in user_data: user_data[cid] = {'gender': 'f', 'target': '🇰🇭 Khmer', 'format': 'mp3'}
    
    if "សំឡេង" in m.text:
        user_data[cid]['gender'] = 'm' if user_data[cid]['gender'] == 'f' else 'f'
        status = "ប្រុស" if user_data[cid]['gender'] == 'm' else "ស្រី"
        bot.send_message(cid, f"✅ បានប្តូរទៅសំឡេង៖ {status}", reply_markup=get_kb(cid))
    elif "ជា" in m.text:
        # ប្តូររវាង mp3 និង voice
        user_data[cid]['format'] = 'voice' if user_data[cid].get('format') == 'mp3' else 'mp3'
        status = "Voice Note" if user_data[cid]['format'] == 'voice' else "ឯកសារ MP3"
        bot.send_message(cid, f"✅ បានប្តូរទម្រង់ជា៖ {status}", reply_markup=get_kb(cid))

@bot.message_handler(func=lambda m: m.text in LANG_MAP.keys())
def set_language(m):
    cid = m.chat.id
    if cid not in user_data: user_data[cid] = {'gender': 'f', 'target': '🇰🇭 Khmer', 'format': 'mp3'}
    user_data[cid]['target'] = m.text
    bot.send_message(cid, f"🎯 គោលដៅបកប្រែ៖ {m.text}", reply_markup=get_kb(cid))

# --- ការបកប្រែចេញពីរូបភាព ---
@bot.message_handler(content_types=['photo'])
def handle_photo(m):
    cid = m.chat.id
    bot.send_chat_action(cid, 'typing')
    bot.send_message(cid, "🔍 កំពុងអានអក្សរពីរូបភាព... សូមរង់ចាំ")
    
    try:
        file_info = bot.get_file(m.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        img_path = f"img_{cid}.jpg"
        
        with open(img_path, 'wb') as f:
            f.write(downloaded_file)
        
        # ដំណើរការ OCR
        result = reader.readtext(img_path, detail=0)
        extracted_text = " ".join(result)
        os.remove(img_path)
        
        if not extracted_text.strip():
            bot.send_message(cid, "❌ មិនអាចអានអត្ថបទពីរូបភាពនេះបានទេ។")
            return
            
        process_translation(cid, extracted_text)
    except Exception as e:
        print(f"OCR Error: {e}")
        bot.send_message(cid, "❌ មានបញ្ហាក្នុងការអានរូបភាព។")

# --- ការបកប្រែអត្ថបទធម្មតា ---
@bot.message_handler(func=lambda m: True)
def handle_text(m):
    if not m.text: return
    process_translation(m.chat.id, m.text)

def process_translation(cid, text):
    if cid not in user_data: user_data[cid] = {'gender': 'f', 'target': '🇰🇭 Khmer', 'format': 'mp3'}
    st = user_data[cid]
    target_info = LANG_MAP[st['target']]
    
    try:
        # បកប្រែភាសា
        translated_text = GoogleTranslator(source='auto', target=target_info['code']).translate(text)
        clean_text = translated_text.replace('`', '').replace('*', '')
        bot.send_message(cid, f"📝 **បកប្រែរួច៖**\n\n`{clean_text}`", parse_mode="Markdown")
        
        # បង្កើតសំឡេង (TTS)
        voice_name = target_info[st['gender']]
        fname = f"v_{cid}_{int(time.time())}.mp3"
        
        bot.send_chat_action(cid, 'record_audio')
        asyncio.run(generate_voice(translated_text, voice_name, fname))
        
        # ផ្ញើសំឡេងតាមប្រភេទដែល User រើស (Default គឺ MP3)
        with open(fname, 'rb') as audio_file:
            caption_text = f"🌐 ភាសា៖ {st['target']}\n📣 https://t.me/nyvoicebot"
            if st.get('format') == 'voice':
                bot.send_voice(cid, audio_file, caption=caption_text)
            else:
                # ផ្ញើជាឯកសារ MP3
                bot.send_document(cid, audio_file, caption=caption_text, visible_file_name=f"voice_{int(time.time())}.mp3")
        
        if os.path.exists(fname): os.remove(fname)
    except Exception as e:
        print(f"Translation Error: {e}")
        bot.send_message(cid, "❌ បញ្ហាបច្ចេកទេស! សូមព្យាយាមម្តងទៀត។")

if __name__ == "__main__":
    # បើក Web Server សម្រាប់ Render
    Thread(target=run_web, daemon=True).start()
    print("Bot is ready (Default: MP3)!")
    bot.infinity_polling(skip_pending=True)
