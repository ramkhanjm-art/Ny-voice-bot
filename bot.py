import telebot
import os
import asyncio
import edge_tts
import fitz  # សម្រាប់អាន PDF (PyMuPDF)
import google.generativeai as genai
from telebot import types
from deep_translator import GoogleTranslator
from flask import Flask
from threading import Thread

# --- Flask Server សម្រាប់ទប់ស្កាត់ Port Timeout លើ Render ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online & Healthy!"

def run_web():
    # Render ប្រើ Port 10000 ជាស្ដង់ដារ
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# --- ការកំណត់ Bot & AI ---
API_TOKEN = os.getenv('BOT_TOKEN')
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')
bot = telebot.TeleBot(API_TOKEN)

user_settings = {}

# មុខងារបំបែកអត្ថបទវែងៗ
def split_text(text, max_length=2000):
    return [text[i:i+max_length] for i in range(0, len(text), max_length)]

# មុខងារបង្កើតសំឡេងឱ្យពិរោះ (កែសម្រួល Pitch និង Rate)
async def generate_voice(text, voice_name, output_file):
    # កំណត់ rate="-10%" ឱ្យអានយឺតស្រទន់ និង pitch="-5Hz" ឱ្យសំឡេងផ្អែម
    communicate = edge_tts.Communicate(text, voice_name, rate="-10%", pitch="-5Hz")
    await communicate.save(output_file)

# មុខងារបង្កើតប៊ូតុងបញ្ជា (Keyboard)
def get_kb(chat_id):
    st = user_settings.get(chat_id, {'v': "km-KH-SreymomNeural", 'tr': False})
    tr_status = "🔔 បើក" if st['tr'] else "🔕 បិទ"
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("👩 សំឡេងស្រី (ផ្អែម)", "👨 សំឡេងប្រុស (ស្រទន់)")
    kb.add(f"🌐 បកប្រែ៖ {tr_status}", "🤖 សួរ AI (Gemini)")
    return kb

# --- គ្រប់គ្រងការផ្ញើឯកសារ PDF ---
@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    if message.document.mime_type == 'application/pdf':
        wait = bot.reply_to(message, "📄 កំពុងអានឯកសារ PDF... សូមរង់ចាំ")
        try:
            file_info = bot.get_file(message.document.file_id)
            downloaded = bot.download_file(file_info.file_path)
            with open("temp.pdf", "wb") as f: f.write(downloaded)
            
            text = ""
            with fitz.open("temp.pdf") as doc:
                for page in doc: text += page.get_text()
            os.remove("temp.pdf")
            
            if text.strip():
                bot.delete_message(message.chat.id, wait.message_id)
                process_logic(message, text)
            else:
                bot.edit_message_text("❌ PDF នេះគ្មានអត្ថបទដែលអាចអានបានទេ។", message.chat.id, wait.message_id)
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ កំហុស PDF: {e}")

# --- មុខងារចម្បងសម្រាប់បង្កើតសំឡេង និងបកប្រែ ---
def process_logic(message, text):
    cid = message.chat.id
    if cid not in user_settings: user_settings[cid] = {'v': "km-KH-SreymomNeural", 'tr': False}
    st = user_settings[cid]
    
    chunks = split_text(text)
    for i, chunk in enumerate(chunks):
        final = GoogleTranslator(source='auto', target='km').translate(chunk) if st['tr'] else chunk
        fname = f"v_{cid}_{i}.mp3"
        bot.send_chat_action(cid, 'record_audio')
        try:
            asyncio.run(generate_voice(final, st['v'], fname))
            with open(fname, 'rb') as v:
                bot.send_voice(cid, v, caption=f"ផ្នែកទី {i+1}" if len(chunks)>1 else None)
            os.remove(fname)
        except:
            bot.send_message(cid, "❌ មិនអាចបង្កើតសំឡេងបានទេ។")

# --- គ្រប់គ្រងការចុចប៊ូតុង និងអត្ថបទ ---
@bot.message_handler(commands=['start'])
def start(m):
    user_settings[m.chat.id] = {'v': "km-KH-SreymomNeural", 'tr': False}
    bot.send_message(m.chat.id, "👋 សួស្តី! ខ្ញុំជា Bot បកប្រែ និងអានអត្ថបទខ្មែរផ្អែមពិរោះ។", reply_markup=get_kb(m.chat.id))

@bot.message_handler(func=lambda m: True)
def handle_all(m):
    cid = m.chat.id
    t = m.text
    if cid not in user_settings: user_settings[cid] = {'v': "km-KH-SreymomNeural", 'tr': False}
    st = user_settings[cid]

    if "👩 សំឡេងស្រី" in t:
        st['v'] = "km-KH-SreymomNeural"
        bot.send_message(cid, "✅ កំណត់យកសំឡេងស្រី (Sreymom)", reply_markup=get_kb(cid))
    elif "👨 សំឡេងប្រុស" in t:
        st['v'] = "km-KH-PisethNeural"
        bot.send_message(cid, "✅ កំណត់យកសំឡេងប្រុស (Piseth)", reply_markup=get_kb(cid))
    elif "🌐 បកប្រែ" in t:
        st['tr'] = not st['tr']
        bot.send_message(cid, f"បកប្រែត្រូវបាន៖ {'បើក' if st['tr'] else 'បិទ'}", reply_markup=get_kb(cid))
    elif "🤖 សួរ AI" in t:
        st['mode'] = 'ai'
        bot.send_message(cid, "🤖 សួរមក! ខ្ញុំនឹងឆ្លើយជាសំឡេងខ្មែរ។")
    else:
        if st.get('mode') == 'ai':
            bot.send_chat_action(cid, 'typing')
            t = model.generate_content(f"Answer in Khmer: {t}").text
            st['mode'] = None
        process_logic(m, t)

if __name__ == "__main__":
    Thread(target=run_web).start()
    # ប្រើ skip_pending=True ដើម្បីដោះស្រាយបញ្ហា Conflict 409
    bot.infinity_polling(skip_pending=True)
