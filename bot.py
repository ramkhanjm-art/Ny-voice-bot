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

# --- កំណត់ AI (Gemini) ---
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

app = Flask('')
@app.route('/')
def home(): return "Bot is Alive!"

API_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)
user_settings = {}

def main_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("👩 សំឡេងស្រី"), types.KeyboardButton("👨 សំឡេងប្រុស"))
    markup.add(types.KeyboardButton("🌐 បកប្រែអង់គ្លេស -> ខ្មែរ"), types.KeyboardButton("🤖 សួរ AI (Gemini)"))
    markup.add(types.KeyboardButton("⚡ ល្បឿនអាន"), types.KeyboardButton("❓ ជំនួយ"))
    return markup

async def generate_voice(text, voice_name, speed, output_file):
    rate = f"{int((float(speed)-1)*100):+d}%"
    communicate = edge_tts.Communicate(text, voice_name, rate=rate)
    await communicate.save(output_file)

# --- មុខងារអានរូបភាពដោយប្រើ Gemini (ជំនួស OCR) ---
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    wait = bot.reply_to(message, "🔍 កំពុងវិភាគរូបភាពដោយប្រើ AI... សូមរង់ចាំ")
    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    with open("input_img.jpg", "wb") as f:
        f.write(downloaded_file)
    
    try:
        # ប្រើ Gemini មើលរូបភាព និងទាញអត្ថបទ
        img_data = [{'mime_type': 'image/jpeg', 'data': downloaded_file}]
        prompt = "Please extract all text from this image. If it's in English, translate it to Khmer. If it's already in Khmer, just provide the text."
        response = model.generate_content([prompt, img_data[0]])
        
        bot.delete_message(message.chat.id, wait.message_id)
        process_voice_output(message, response.text)
        os.remove("input_img.jpg")
    except Exception as e:
        bot.edit_message_text(f"❌ កំហុស AI៖ {e}", message.chat.id, wait.message_id)

def process_voice_output(message, text):
    chat_id = message.chat.id
    st = user_settings.get(chat_id, {'v': "km-KH-SreymomNeural", 's': "1.0"})
    
    out = f"res_{chat_id}.mp3"
    bot.send_chat_action(chat_id, 'record_audio')
    try:
        asyncio.run(generate_voice(text, st['v'], st['s'], out))
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🎤 Voice", callback_data=f"v:{out}"),
                   types.InlineKeyboardButton("📁 MP3", callback_data=f"a:{out}"))
        bot.send_message(chat_id, f"✅ រួចរាល់!\n📝 អត្ថបទ៖ {text[:300]}...", reply_markup=markup)
    except:
        bot.send_message(chat_id, "❌ បរាជ័យក្នុងការបង្កើតសំឡេង។")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    data = call.data.split(':')
    if data[0] in ['v', 'a']:
        f_path = data[1]
        if os.path.exists(f_path):
            with open(f_path, 'rb') as f:
                if data[0] == 'v': bot.send_voice(call.message.chat.id, f)
                else: bot.send_audio(call.message.chat.id, f, title="AI_Voice")
            os.remove(f_path)
            bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda message: True)
def handle_msg(message):
    t = message.text
    if t == "🤖 សួរ AI (Gemini)":
        user_settings[message.chat.id] = user_settings.get(message.chat.id, {})
        user_settings[message.chat.id]['mode'] = 'ai'
        bot.reply_to(message, "តើអ្នកចង់សួរអ្វីដល់ AI Gemini?")
    elif user_settings.get(message.chat.id, {}).get('mode') == 'ai':
        bot.send_chat_action(message.chat.id, 'typing')
        resp = model.generate_content(f"Answer in Khmer: {t}")
        process_voice_output(message, resp.text)
    else:
        process_voice_output(message, t)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))).start()
    bot.infinity_polling()
