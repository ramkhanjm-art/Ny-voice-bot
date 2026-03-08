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
def home(): return "Multi-Language Bot is Online!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# --- ការកំណត់ Bot ---
API_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

user_settings = {}

# មុខងារបង្កើតសំឡេងឱ្យផ្អែមពិរោះ (Rate -10%)
async def generate_voice(text, voice_name, output_file):
    communicate = edge_tts.Communicate(text, voice_name, rate="-10%", pitch="-5Hz")
    await communicate.save(output_file)

# ប៊ូតុងបញ្ជាសម្រាប់ជ្រើសរើសភាសា
def get_kb(chat_id):
    st = user_settings.get(chat_id, {'v': "km-KH-SreymomNeural", 'tr': False})
    tr_status = "🔔 បើក" if st['tr'] else "🔕 បិទ"
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    kb.add(types.KeyboardButton("👩 សំឡេងស្រី"), types.KeyboardButton("👨 សំឡេងប្រុស"))
    kb.add(types.KeyboardButton(f"🌐 បកប្រែជាខ្មែរ៖ {tr_status}"))
    kb.add(types.KeyboardButton("🏳️ ភាសាដែលគាំទ្រ"))
    return kb

@bot.message_handler(commands=['start'])
def start(m):
    user_settings[m.chat.id] = {'v': "km-KH-SreymomNeural", 'tr': False}
    welcome = "👋 សួស្តី! ខ្ញុំអាចបកប្រែភាសាទាំង ១១ មកជាខ្មែរ និងអានឱ្យស្តាប់បាន។"
    bot.send_message(m.chat.id, welcome, reply_markup=get_kb(m.chat.id))

def process_output(message, text):
    cid = message.chat.id
    st = user_settings.get(cid, {'v': "km-KH-SreymomNeural", 'tr': False})
    
    # មុខងារបកប្រែស្វ័យប្រវត្តិ (Auto Detect)
    try:
        final_text = GoogleTranslator(source='auto', target='km').translate(text) if st['tr'] else text
    except:
        final_text = text
        
    fname = f"v_{cid}.mp3"
    bot.send_chat_action(cid, 'record_audio')
    try:
        asyncio.run(generate_voice(final_text, st['v'], fname))
        # ភ្ជាប់ Username និងបញ្ជីភាសា
        caption_text = "✨ អានដោយ៖ @Ny_voice_bot\n🌍 គាំទ្រ៖ 🇺🇸 🇫🇷 🇨🇳 🇻🇳 🇰🇷 🇯🇵 🇮🇳 🇱🇦 🇲🇾 🇵🇭 🇮🇩"
        with open(fname, 'rb') as v: 
            bot.send_voice(cid, v, caption=caption_text)
        os.remove(fname)
    except: 
        bot.send_message(cid, "❌ មិនអាចបង្កើតសំឡេងបានទេ។")

@bot.message_handler(func=lambda m: True)
def handle_all(m):
    cid = m.chat.id
    t = m.text
    if cid not in user_settings: user_settings[cid] = {'v': "km-KH-SreymomNeural", 'tr': False}
    st = user_settings[cid]

    if "👩 សំឡេងស្រី" in t:
        st['v'] = "km-KH-SreymomNeural"
        bot.send_message(cid, "✅ កំណត់យកសំឡេងស្រី", reply_markup=get_kb(cid))
    elif "👨 សំឡេងប្រុស" in t:
        st['v'] = "km-KH-PisethNeural"
        bot.send_message(cid, "✅ កំណត់យកសំឡេងប្រុស", reply_markup=get_kb(cid))
    elif "🌐 បកប្រែ" in t:
        st['tr'] = not st['tr']
        bot.send_message(cid, f"ការបកប្រែជាខ្មែរ៖ {'បើក' if st['tr'] else 'បិទ'}", reply_markup=get_kb(cid))
    elif t == "🏳️ ភាសាដែលគាំទ្រ":
        langs = (
            "🏳️ **បញ្ជីភាសាដែលគាំទ្រ (Auto Detect):**\n"
            "🇺🇸 អង់គ្លេស, 🇫🇷 បារាំង, 🇨🇳 ចិន, 🇻🇳 វៀតណាម, "
            "🇰🇷 កូរ៉េ, 🇯🇵 ជប៉ុន, 🇮🇳 ឥណ្ឌា, 🇱🇦 ឡាវ, "
            "🇲🇾 ម៉ាឡេស៊ី, 🇵🇭 ហ្វីលីពីន, 🇮🇩 ឥណ្ឌូនេស៊ី"
        )
        bot.send_message(cid, langs, parse_mode="Markdown")
    else:
        process_output(m, t)

if __name__ == "__main__":
    Thread(target=run_web).start()
    # ប្រើ skip_pending=True ដើម្បីកម្ចាត់ Conflict 409
    bot.infinity_polling(skip_pending=True)
