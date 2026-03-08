import telebot
import os
import asyncio
import edge_tts
import fitz
from telebot import types
from deep_translator import GoogleTranslator
from flask import Flask
from threading import Thread

# --- Web Server សម្រាប់ Render ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# --- ការកំណត់ Bot ---
API_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

user_settings = {}

# មុខងារបង្កើតសំឡេងឱ្យពិរោះ (Rate -10% ឱ្យអានយឺតស្រទន់)
async def generate_voice(text, voice_name, output_file):
    communicate = edge_tts.Communicate(text, voice_name, rate="-10%", pitch="-5Hz")
    await communicate.save(output_file)

def get_kb(chat_id):
    st = user_settings.get(chat_id, {'v': "km-KH-SreymomNeural", 'tr': False})
    tr_status = "🔔 បើក" if st['tr'] else "🔕 បិទ"
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("👩 សំឡេងស្រី (ផ្អែម)", "👨 សំឡេងប្រុស (ស្រទន់)")
    kb.add(f"🌐 បកប្រែ៖ {tr_status}")
    return kb

@bot.message_handler(commands=['start'])
def start(m):
    user_settings[m.chat.id] = {'v': "km-KH-SreymomNeural", 'tr': False}
    bot.send_message(m.chat.id, "👋 សួស្តី! ផ្ញើអត្ថបទមក ខ្ញុំនឹងបកប្រែ និងអានឱ្យអ្នកស្តាប់។", reply_markup=get_kb(m.chat.id))

def process_voice(m, text):
    cid = m.chat.id
    st = user_settings.get(cid, {'v': "km-KH-SreymomNeural", 'tr': False})
    
    # មុខងារបកប្រែ
    try:
        final_text = GoogleTranslator(source='auto', target='km').translate(text) if st['tr'] else text
    except:
        final_text = text
        
    fname = f"v_{cid}.mp3"
    bot.send_chat_action(cid, 'record_audio')
    try:
        asyncio.run(generate_voice(final_text, st['v'], fname))
        with open(fname, 'rb') as v: bot.send_voice(cid, v)
        os.remove(fname)
    except: 
        bot.send_message(cid, "❌ មិនអាចបង្កើតសំឡេងបានទេ។")

@bot.message_handler(func=lambda m: True)
def handle_all(m):
    cid = m.chat.id
    t = m.text
    if cid not in user_settings: user_settings[cid] = {'v': "km-KH-SreymomNeural", 'tr': False}
    st = user_settings[cid]

    if t == "👩 សំឡេងស្រី (ផ្អែម)":
        st['v'] = "km-KH-SreymomNeural"
        bot.send_message(cid, "✅ បានប្តូរទៅសំឡេងស្រី", reply_markup=get_kb(cid))
    elif t == "👨 សំឡេងប្រុស (ស្រទន់)":
        st['v'] = "km-KH-PisethNeural"
        bot.send_message(cid, "✅ បានប្តូរទៅសំឡេងប្រុស", reply_markup=get_kb(cid))
    elif "🌐 បកប្រែ" in t:
        st['tr'] = not st['tr']
        bot.send_message(cid, f"បកប្រែ៖ {'បើក' if st['tr'] else 'បិទ'}", reply_markup=get_kb(cid))
    else:
        process_voice(m, t)

if __name__ == "__main__":
    Thread(target=run_web).start()
    # ទប់ស្កាត់បញ្ហា Conflict 409
    bot.infinity_polling(skip_pending=True)
