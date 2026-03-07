import telebot
import os
import asyncio
import edge_tts
import fitz
import easyocr
import google.generativeai as genai
from telebot import types
from deep_translator import GoogleTranslator
from flask import Flask
from threading import Thread

# --- ការកំណត់ AI ---
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
ai_model = genai.GenerativeModel('gemini-1.5-flash')
reader = easyocr.Reader(['kh', 'en']) # កំណត់ឱ្យអានខ្មែរ និងអង់គ្លេស

app = Flask('')
@app.route('/')
def home(): return "Ultimate Bot is Online!"

API_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)
user_settings = {}

def main_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("👩 សំឡេងស្រី"), types.KeyboardButton("👨 សំឡេងប្រុស"))
    markup.add(types.KeyboardButton("🌐 បកប្រែ"), types.KeyboardButton("⚡ ល្បឿនអាន"))
    markup.add(types.KeyboardButton("🤖 សួរ AI (Gemini)"), types.KeyboardButton("❓ ជំនួយ"))
    return markup

# --- មុខងារកំណត់ល្បឿន ---
def speed_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🐢 យឺត (0.8x)", callback_data="sp:0.8"),
        types.InlineKeyboardButton("🏃 ធម្មតា (1.0x)", callback_data="sp:1.0"),
        types.InlineKeyboardButton("🚀 លឿន (1.2x)", callback_data="sp:1.2")
    )
    return markup

async def generate_voice(text, voice_name, speed, output_file):
    # កែសម្រួលល្បឿន (ឧទាហរណ៍: +20% ឬ -20%)
    rate = f"{int((float(speed)-1)*100):+d}%"
    communicate = edge_tts.Communicate(text, voice_name, rate=rate)
    await communicate.save(output_file)

# --- ១. មុខងារអានអត្ថបទពីរូបភាព (OCR) ---
@bot.message_handler(content_types=['photo'])
def handle_ocr(message):
    wait = bot.reply_to(message, "📸 កំពុងស្កេនអក្សរពីរូបភាព...")
    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded = bot.download_file(file_info.file_path)
    
    with open("image.jpg", "wb") as f:
        f.write(downloaded)
    
    result = reader.readtext("image.jpg", detail=0)
    text = " ".join(result)
    os.remove("image.jpg")
    
    if text.strip():
        bot.delete_message(message.chat.id, wait.message_id)
        process_output(message, text)
    else:
        bot.edit_message_text("❌ មិនអាចរកឃើញអត្ថបទក្នុងរូបភាពនេះទេ។", message.chat.id, wait.message_id)

# --- ២. មុខងារជជែកជាមួយ AI (Gemini) ---
def chat_with_ai(message):
    chat_id = message.chat.id
    bot.send_chat_action(chat_id, 'typing')
    try:
        # ប្រាប់ AI ឱ្យឆ្លើយជាភាសាខ្មែរ
        prompt = f"Please answer in Khmer: {message.text}"
        response = ai_model.generate_content(prompt)
        process_output(message, response.text)
    except:
        bot.reply_to(message, "❌ AI រវល់បន្តិច សូមសួរម្តងទៀត។")

# --- មុខងាររួមសម្រេចលទ្ធផល ---
def process_output(message, text):
    chat_id = message.chat.id
    set_data = user_settings.get(chat_id, {'v': "km-KH-SreymomNeural", 's': "1.0", 'tr': False})
    
    final_text = text
    if set_data.get('tr'):
        final_text = GoogleTranslator(source='auto', target='km').translate(text)
    
    out = f"res_{chat_id}.mp3"
    asyncio.run(generate_voice(final_text, set_data['v'], set_data['s'], out))
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎤 Voice", callback_data=f"v:{out}"),
               types.InlineKeyboardButton("📁 MP3", callback_data=f"a:{out}"))
    bot.send_message(chat_id, f"✅ រួចរាល់!\n📝 អត្ថបទ៖ {final_text[:200]}...", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data.startswith("sp:"):
        speed = call.data.split(":")[1]
        user_settings[call.message.chat.id] = user_settings.get(call.message.chat.id, {'v': "km-KH-SreymomNeural", 's': "1.0", 'tr': False})
        user_settings[call.message.chat.id]['s'] = speed
        bot.answer_callback_query(call.id, f"ល្បឿនត្រូវបានកំណត់ទៅ {speed}x")
    else:
        # កូដផ្ញើ Voice/MP3 (ដូចមុន)
        pass

@bot.message_handler(func=lambda message: True)
def handle_all(message):
    t = message.text
    if t == "⚡ ល្បឿនអាន":
        bot.send_message(message.chat.id, "ជ្រើសរើសល្បឿនអាន៖", reply_markup=speed_keyboard())
    elif t == "🤖 សួរ AI (Gemini)":
        user_settings[message.chat.id] = user_settings.get(message.chat.id, {})
        user_settings[message.chat.id]['mode'] = 'ai'
        bot.reply_to(message, "តើអ្នកចង់សួរអ្វីដល់ខ្ញុំ?")
    elif user_settings.get(message.chat.id, {}).get('mode') == 'ai':
        chat_with_ai(message)
    else:
        process_output(message, t)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))).start()
    bot.infinity_polling()
