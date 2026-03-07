import telebot
import os
import asyncio
import edge_tts
import fitz
import google.generativeai as genai
from telebot import types
from deep_translator import GoogleTranslator
from flask import Flask
from threading import Thread

# --- Flask Server ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Alive!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# --- Bot Config ---
API_TOKEN = os.getenv('BOT_TOKEN')
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')
bot = telebot.TeleBot(API_TOKEN)

user_settings = {}

# មុខងារបង្កើនគុណភាពសំឡេង (Pitch & Rate)
async def generate_voice(text, voice_name, output_file):
    # កំណត់ rate=-10% ដើម្បីឱ្យអានមួយៗ និង pitch=-5Hz ដើម្បីឱ្យសំឡេងស្រទន់
    communicate = edge_tts.Communicate(text, voice_name, rate="-10%", pitch="-5Hz")
    await communicate.save(output_file)

def get_kb(chat_id):
    st = user_settings.get(chat_id, {'v': "km-KH-SreymomNeural", 'tr': False})
    tr_status = "🔔 បើក" if st['tr'] else "🔕 បិទ"
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    # បន្ថែមប៊ូតុងឱ្យបានពេញលេញ
    kb.add(types.KeyboardButton("👩 សំឡេងស្រី (ផ្អែម)"), types.KeyboardButton("👨 សំឡេងប្រុស (ស្រទន់)"))
    kb.add(types.KeyboardButton(f"🌐 បកប្រែ៖ {tr_status}"), types.KeyboardButton("🤖 សួរ AI (Gemini)"))
    return kb

@bot.message_handler(commands=['start'])
def start(m):
    user_settings[m.chat.id] = {'v': "km-KH-SreymomNeural", 'tr': False}
    bot.send_message(m.chat.id, "👋 សួស្តី! ខ្ញុំបានកែលម្អសំឡេងឱ្យផ្អែមជាងមុនហើយ។", reply_markup=get_kb(m.chat.id))

@bot.message_handler(func=lambda m: True)
def handle_all(m):
    cid = m.chat.id
    t = m.text
    if cid not in user_settings: user_settings[cid] = {'v': "km-KH-SreymomNeural", 'tr': False}
    st = user_settings[cid]

    if "👩 សំឡេងស្រី" in t:
        st['v'] = "km-KH-SreymomNeural"
        bot.send_message(cid, "✅ បានប្តូរទៅសំឡេងស្រី (Sreymom)", reply_markup=get_kb(cid))
    elif "👨 សំឡេងប្រុស" in t:
        st['v'] = "km-KH-PisethNeural"
        bot.send_message(cid, "✅ បានប្តូរទៅសំឡេងប្រុស (Piseth)", reply_markup=get_kb(cid))
    elif "🌐 បកប្រែ" in t:
        st['tr'] = not st['tr']
        bot.send_message(cid, f"បកប្រែត្រូវបាន៖ {'បើក' if st['tr'] else 'បិទ'}", reply_markup=get_kb(cid))
    elif "🤖 សួរ AI" in t:
        st['mode'] = 'ai'
        bot.send_message(cid, "🤖 តើអ្នកចង់សួរអ្វីដល់ AI?")
    else:
        # ដំណើរការបង្កើតសំឡេង
        process_text(m, t)

def process_text(m, text):
    cid = m.chat.id
    st = user_settings[cid]
    if st.get('mode') == 'ai':
        text = model.generate_content(f"Answer in Khmer: {text}").text
        st['mode'] = None

    final_text = GoogleTranslator(source='auto', target='km').translate(text) if st['tr'] else text
    fname = f"v_{cid}.mp3"
    bot.send_chat_action(cid, 'record_audio')
    try:
        asyncio.run(generate_voice(final_text, st['v'], fname))
        with open(fname, 'rb') as v: bot.send_voice(cid, v)
        os.remove(fname)
    except: bot.send_message(cid, "❌ កំហុសបច្ចេកទេសសំឡេង")

if __name__ == "__main__":
    Thread(target=run_web).start()
    # ប្រើ skip_pending=True ដើម្បីកុំឱ្យ Bot គាំងសារចាស់ៗ
    bot.infinity_polling(skip_pending=True)
