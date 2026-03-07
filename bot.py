import telebot
import os
import asyncio
import edge_tts
import fitz  # បណ្ណាល័យ pymupdf សម្រាប់អាន PDF
import google.generativeai as genai
from telebot import types
from deep_translator import GoogleTranslator
from flask import Flask
from threading import Thread

# --- Flask Server ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# --- Bot Config ---
API_TOKEN = os.getenv('BOT_TOKEN')
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')
bot = telebot.TeleBot(API_TOKEN)

user_settings = {}

def split_text(text, max_length=2000):
    return [text[i:i+max_length] for i in range(0, len(text), max_length)]

async def generate_voice(text, voice_name, output_file):
    communicate = edge_tts.Communicate(text, voice_name)
    await communicate.save(output_file)

def get_kb(chat_id):
    st = user_settings.get(chat_id, {'v': "km-KH-SreymomNeural", 'tr': False})
    tr_status = "🔔 បើក" if st['tr'] else "🔕 បិទ"
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("👩 សំឡេងស្រី", "👨 សំឡេងប្រុស", f"🌐 បកប្រែ៖ {tr_status}", "🤖 សួរ AI (Gemini)")
    return kb

# --- មុខងារអាន PDF ---
@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    if message.document.mime_type == 'application/pdf':
        wait = bot.reply_to(message, "📄 កំពុងអានឯកសារ PDF... សូមរង់ចាំ")
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        with open("temp.pdf", "wb") as f:
            f.write(downloaded_file)
        
        # ដកស្រង់អត្ថបទពី PDF
        text = ""
        with fitz.open("temp.pdf") as doc:
            for page in doc:
                text += page.get_text()
        
        os.remove("temp.pdf")
        
        if text.strip():
            bot.delete_message(message.chat.id, wait.message_id)
            process_logic(message, text)
        else:
            bot.edit_message_text("❌ មិនអាចទាញយកអត្ថបទពី PDF នេះបានទេ។", message.chat.id, wait.message_id)

def process_logic(message, text):
    cid = message.chat.id
    st = user_settings.get(cid, {'v': "km-KH-SreymomNeural", 'tr': False})
    
    chunks = split_text(text)
    for i, chunk in enumerate(chunks):
        final = GoogleTranslator(source='auto', target='km').translate(chunk) if st['tr'] else chunk
        fname = f"v_{cid}_{i}.mp3"
        bot.send_chat_action(cid, 'record_audio')
        asyncio.run(generate_voice(final, st['v'], fname))
        with open(fname, 'rb') as v:
            bot.send_voice(cid, v, caption=f"ផ្នែកទី {i+1}" if len(chunks)>1 else None)
        os.remove(fname)

@bot.message_handler(func=lambda m: True)
def handle_text(m):
    cid = m.chat.id
    t = m.text
    st = user_settings.get(cid, {'v': "km-KH-SreymomNeural", 'tr': False})

    if "👩 សំឡេងស្រី" in t:
        user_settings[cid] = {**st, 'v': "km-KH-SreymomNeural"}
        bot.send_message(cid, "✅ សំឡេងស្រី", reply_markup=get_kb(cid))
    elif "👨 សំឡេងប្រុស" in t:
        user_settings[cid] = {**st, 'v': "km-KH-PisethNeural"}
        bot.send_message(cid, "✅ សំឡេងប្រុស", reply_markup=get_kb(cid))
    elif "🌐 បកប្រែ" in t:
        st['tr'] = not st['tr']
        user_settings[cid] = st
        bot.send_message(cid, f"បកប្រែ៖ { 'បើក' if st['tr'] else 'បិទ' }", reply_markup=get_kb(cid))
    elif "🤖 សួរ AI (Gemini)" in t:
        user_settings[cid]['mode'] = 'ai'
        bot.send_message(cid, "🤖 សួរមក! ខ្ញុំនឹងឆ្លើយជាសម្លេងខ្មែរ។")
    else:
        if user_settings.get(cid, {}).get('mode') == 'ai':
            t = model.generate_content(f"Answer in Khmer: {t}").text
            user_settings[cid]['mode'] = None
        process_logic(m, t)

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.infinity_polling(skip_pending=True)
