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

# មុខងារបង្កើតសំឡេងឱ្យពិរោះ (កែសម្រួល Pitch និង Rate)
async def generate_voice(text, voice_name, output_file):
    # កំណត់ឱ្យអានយឺតបន្តិច និងសម្លេងស្រទន់ (+0Hz ទៅ -10Hz សម្រាប់ភាពធម្មជាតិ)
    communicate = edge_tts.Communicate(text, voice_name, rate="-5%", pitch="-1Hz")
    await communicate.save(output_file)

def get_kb(chat_id):
    st = user_settings.get(chat_id, {'v': "km-KH-SreymomNeural", 'tr': False})
    tr_status = "🔔 បើក" if st['tr'] else "🔕 បិទ"
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("👩 សំឡេងស្រី (ពិរោះ)", "👨 សំឡេងប្រុស (ស្រទន់)")
    kb.add(f"🌐 បកប្រែ៖ {tr_status}", "🤖 សួរ AI (Gemini)")
    return kb

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "👋 សួស្តី! ខ្ញុំបានកែលម្អសំឡេងឱ្យពិរោះជាងមុនហើយ។", reply_markup=get_kb(m.chat.id))

@bot.message_handler(func=lambda m: True)
def handle_all(m):
    cid = m.chat.id
    t = m.text
    # បង្កើត settings បើមិនទាន់មាន
    if cid not in user_settings:
        user_settings[cid] = {'v': "km-KH-SreymomNeural", 'tr': False}
    
    st = user_settings[cid]

    if "👩 សំឡេងស្រី" in t:
        user_settings[cid]['v'] = "km-KH-SreymomNeural"
        bot.send_message(cid, "✅ បានប្តូរទៅសំឡេងស្រី (បែបផ្អែមល្ហែម)", reply_markup=get_kb(cid))
    elif "👨 សំឡេងប្រុស" in t:
        user_settings[cid]['v'] = "km-KH-PisethNeural"
        bot.send_message(cid, "✅ បានប្តូរទៅសំឡេងប្រុស (បែបស្រទន់)", reply_markup=get_kb(cid))
    elif "🌐 បកប្រែ" in t:
        st['tr'] = not st['tr']
        bot.send_message(cid, f"បកប្រែ៖ {'បើក' if st['tr'] else 'បិទ'}", reply_markup=get_kb(cid))
    elif "🤖 សួរ AI" in t:
        user_settings[cid]['mode'] = 'ai'
        bot.send_message(cid, "🤖 តើអ្នកចង់សួរអ្វី?")
    else:
        # ដំណើរការអានអត្ថបទ
        process_voice(m, t)

def process_voice(m, text):
    cid = m.chat.id
    st = user_settings[cid]
    
    if st.get('mode') == 'ai':
        text = model.generate_content(f"Answer in Khmer: {text}").text
        user_settings[cid]['mode'] = None

    final_text = GoogleTranslator(source='auto', target='km').translate(text) if st['tr'] else text
    fname = f"voice_{cid}.mp3"
    
    bot.send_chat_action(cid, 'record_audio')
    try:
        asyncio.run(generate_voice(final_text, st['v'], fname))
        with open(fname, 'rb') as v:
            bot.send_voice(cid, v)
        os.remove(fname)
    except:
        bot.send_message(cid, "❌ បញ្ហាក្នុងការបង្កើតសំឡេង")

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.infinity_polling(skip_pending=True)
