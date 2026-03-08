import telebot
import os
import asyncio
import edge_tts
import fitz
from telebot import types
from deep_translator import GoogleTranslator
from flask import Flask
from threading import Thread

# --- Web Server សម្រាប់ Render (Keep Alive) ---
app = Flask('')
@app.route('/')
def home(): return "Multi-Language Bot is Online!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# --- ការកំណត់ Bot ---
API_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

user_settings = {}

# មុខងារបង្កើតសំឡេងឱ្យផ្អែមពិរោះ (Rate -10% ឱ្យអានយឺតស្រទន់)
async def generate_voice(text, voice_name, output_file):
    communicate = edge_tts.Communicate(text, voice_name, rate="-10%", pitch="-5Hz")
    await communicate.save(output_file)

# ប៊ូតុងបញ្ជា
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
    bot.send_message(m.chat.id, "👋 សួស្តី! ខ្ញុំអាចបកប្រែភាសាទាំង ១១ មកជាខ្មែរ និងអានឱ្យស្តាប់បាន។", reply_markup=get_kb(m.chat.id))

# --- មុខងារអានឯកសារ PDF ---
@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    if message.document.mime_type == 'application/pdf':
        wait = bot.reply_to(message, "📄 កំពុងអាន PDF... សូមរង់ចាំ")
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
                process_output(message, text)
            else:
                bot.edit_message_text("❌ មិនអាចអានអត្ថបទពី PDF បានទេ។", message.chat.id, wait.message_id)
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ កំហុស PDF: {e}")

# --- មុខងារបកប្រែស្វ័យប្រវត្តិ និងបង្កើតសំឡេង ---
def process_output(message, text):
    cid = message.chat.id
    st = user_settings.get(cid, {'v': "km-KH-SreymomNeural", 'tr': False})
    
    # បកប្រែពីគ្រប់ភាសាមកខ្មែរ
    try:
        final_text = GoogleTranslator(source='auto', target='km').translate(text) if st['tr'] else text
    except:
        final_text = text
        
    fname = f"v_{cid}.mp3"
    bot.send_chat_action(cid, 'record_audio')
    try:
        asyncio.run(generate_voice(final_text, st['v'], fname))
        # ភ្ជាប់ Username និងបញ្ជីភាសាដែលគាំទ្រ
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
            "អង់គ្លេស, បារាំង, ចិន, វៀតណាម, កូរ៉េ, ជប៉ុន, "
            "ឥណ្ឌា, ឡាវ, ម៉ាឡេស៊ី, ហ្វីលីពីន, ឥណ្ឌូនេស៊ី"
        )
        bot.send_message(cid, langs, parse_mode="Markdown")
    else:
        process_output(m, t)

if __name__ == "__main__":
    Thread(target=run_web).start()
    # សំខាន់៖ ប្រើ skip_pending=True ដើម្បីជួយកាត់បន្ថយ Conflict
    bot.infinity_polling(skip_pending=True)
