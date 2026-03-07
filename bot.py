import os
import telebot
import fitz  # PyMuPDF
from gtts import gTTS
import os
import time
from flask import Flask
from threading import Thread

# --- ការកំណត់ (Configuration) ---
API_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)
app = Flask('')

# ផ្ទុកទិន្នន័យល្បឿនរបស់អ្នកប្រើ (Default: លឿនធម្មតា)
user_settings = {} 

# --- ផ្នែក Keep-Alive (សម្រាប់ Render.com កុំឱ្យ Bot ដេក) ---
@app.route('/')
def home():
    return "Bot is running 24/7!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- មុខងារជំនួយ (Helper Functions) ---
def get_main_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🐢 ល្បឿនយឺត (Slow)", "🏃 ល្បឿនធម្មតា (Normal)")
    return markup

def extract_text_from_pdf(file_path):
    text = ""
    with fitz.open(file_path) as doc:
        for page in doc:
            text += page.get_text()
    return text

# --- ផ្នែកបញ្ជា Bot (Bot Handlers) ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "🇰🇭 សួស្តី! ខ្ញុំជា Bot បំប្លែងអត្ថបទទៅជាសំឡេង (Full Option)\n\n"
        "👉 ផ្ញើអត្ថបទជាភាសាខ្មែរ ឬអង់គ្លេស\n"
        "👉 បោះឯកសារ PDF មកអានក៏បាន\n"
        "👉 ប្រើប៊ូតុងខាងក្រោមដើម្បីប្តូរល្បឿនអាន"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: message.text in ["🐢 ល្បឿនយឺត (Slow)", "🏃 ល្បឿនធម្មតា (Normal)"])
def change_speed(message):
    if "យឺត" in message.text:
        user_settings[message.chat.id] = True
        bot.reply_to(message, "✅ បានកំណត់មកល្បឿនយឺត (សម្រាប់អ្នករៀនអាន)")
    else:
        user_settings[message.chat.id] = False
        bot.reply_to(message, "✅ បានកំណត់មកល្បឿនធម្មតា")

@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    if message.document.mime_type == 'application/pdf':
        waiting_msg = bot.reply_to(message, "⏳ កំពុងទាញយកអត្ថបទពី PDF... សូមរង់ចាំ")
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        pdf_path = f"file_{message.chat.id}.pdf"
        voice_path = f"voice_{message.chat.id}.mp3"
        
        try:
            with open(pdf_path, 'wb') as f:
                f.write(downloaded_file)
            
            text = extract_text_from_pdf(pdf_path)
            if not text.strip():
                bot.edit_message_text("❌ មិនអាចអាន PDF នេះបានទេ (ប្រហែលជាវាជារូបភាព)", message.chat.id, waiting_msg.message_id)
                return

            bot.edit_message_text("🔊 កំពុងបំប្លែងទៅជាសំឡេង...", message.chat.id, waiting_msg.message_id)
            
            is_slow = user_settings.get(message.chat.id, False)
            tts = gTTS(text=text[:3000], lang='km', slow=is_slow) # កម្រិតត្រឹម ៣០០០ តួអក្សរដើម្បីល្បឿន
            tts.save(voice_path)
            
            with open(voice_path, 'rb') as audio:
                bot.send_voice(message.chat.id, audio, caption="📖 អានចេញពី PDF របស់អ្នក")
            bot.delete_message(message.chat.id, waiting_msg.message_id)
            
        except Exception as e:
            bot.reply_to(message, f"⚠️ Error: {e}")
        finally:
            if os.path.exists(pdf_path): os.remove(pdf_path)
            if os.path.exists(voice_path): os.remove(voice_path)

@bot.message_handler(func=lambda message: True)
def text_to_speech(message):
    is_slow = user_settings.get(message.chat.id, False)
    voice_path = f"v_{message.chat.id}.mp3"
    
    try:
        tts = gTTS(text=message.text, lang='km', slow=is_slow)
        tts.save(voice_path)
        with open(voice_path, 'rb') as audio:
            bot.send_voice(message.chat.id, audio)
        os.remove(voice_path)
    except Exception as e:
        bot.reply_to(message, f"⚠️ បញ្ហា៖ {e}")

# --- បើកដំណើរការ ---
if __name__ == "__main__":
    keep_alive()  # បើក Flask Server ទុកឱ្យ Render ឆែក
    print("Bot is ready on Render.com!")
    bot.infinity_polling()
