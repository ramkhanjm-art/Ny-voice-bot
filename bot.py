import telebot
import os
import asyncio
import edge_tts
import fitz  # បណ្ណាល័យ PyMuPDF សម្រាប់អាន PDF
from telebot import types
from deep_translator import GoogleTranslator
from flask import Flask
from threading import Thread

# --- ផ្នែកទប់ស្កាត់កុំឱ្យ Render បិទ Bot (Web Server) ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Alive!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run_web).start()

# --- ផ្នែក Bot ---
API_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)
user_settings = {}

def main_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("👩 សំឡេងស្រី"), types.KeyboardButton("👨 សំឡេងប្រុស"))
    markup.add(types.KeyboardButton("🌐 បកប្រែអង់គ្លេស -> ខ្មែរ"))
    markup.add(types.KeyboardButton("📊 ស្ថិតិប្រើប្រាស់"), types.KeyboardButton("❓ ជំនួយ"))
    return markup

async def generate_voice(text, voice_name, output_file):
    communicate = edge_tts.Communicate(text, voice_name)
    await communicate.save(output_file)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "👋 សួស្តី! ឥឡូវអ្នកអាចផ្ញើអត្ថបទ ឬឯកសារ PDF មកខ្ញុំបានហើយ។", reply_markup=main_menu_keyboard())

# --- មុខងារអាន PDF (កែសម្រួលថ្មីឱ្យហ្មត់ចត់) ---
@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    if message.document.file_name.lower().endswith('.pdf'):
        wait_msg = bot.reply_to(message, "⏳ កំពុងទាញយកអត្ថបទពី PDF... សូមរង់ចាំ")
        
        try:
            # ទាញយក File ពី Telegram
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            with open("temp.pdf", "wb") as f:
                f.write(downloaded_file)
            
            # ចាប់ផ្តើមអានអត្ថបទ
            text_content = ""
            with fitz.open("temp.pdf") as doc:
                for page in doc:
                    text_content += page.get_text()
            
            os.remove("temp.pdf") # លុប file បណ្តោះអាសន្ន
            
            if len(text_content.strip()) > 5:
                # បើមានអក្សរ ផ្ញើទៅបំប្លែងជាសំឡេង (យកត្រឹម ២០០០ តួអក្សរដំបូង)
                bot.delete_message(message.chat.id, wait_msg.message_id)
                process_text_to_voice(message, text_content[:2000])
            else:
                bot.edit_message_text("❌ មិនអាចអានបានទេ! PDF នេះប្រហែលជាប្រភេទរូបភាព (Scan) ដែលគ្មានអត្ថបទឱ្យ AI ចម្លងបានឡើយ។", message.chat.id, wait_msg.message_id)
        
        except Exception as e:
            bot.edit_message_text(f"❌ កំហុសបច្ចេកទេស៖ {e}", message.chat.id, wait_msg.message_id)
    else:
        bot.reply_to(message, "⚠️ សូមផ្ញើតែឯកសារប្រភេទ .pdf ប៉ុណ្ណោះ!")

def process_text_to_voice(message, text):
    chat_id = message.chat.id
    settings = user_settings.get(chat_id, {'voice': "km-KH-SreymomNeural", 'translate': False})
    
    final_text = text
    if settings.get('translate'):
        final_text = GoogleTranslator(source='en', target='km').translate(text)
        bot.send_message(chat_id, f"📝 អត្ថបទបកប្រែ៖\n{final_text[:500]}...")

    output_file = f"voice_{chat_id}.mp3"
    bot.send_chat_action(chat_id, 'record_audio')
    
    try:
        asyncio.run(generate_voice(final_text, settings.get('voice'), output_file))
        
        # ផ្ញើជម្រើសឱ្យ User (Voice ឬ MP3)
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🎤 សារសំឡេង", callback_data=f"v:{output_file}"),
            types.InlineKeyboardButton("📁 ឯកសារ MP3", callback_data=f"a:{output_file}")
        )
        bot.send_message(chat_id, "✅ បំប្លែង PDF រួចរាល់! សូមជ្រើសរើសប្រភេទឯកសារ៖", reply_markup=markup)
    except Exception:
        bot.send_message(chat_id, "❌ បរាជ័យក្នុងការបង្កើតសំឡេង។")

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    action, f_path = call.data.split(':')
    if os.path.exists(f_path):
        with open(f_path, 'rb') as f:
            if action == 'v': bot.send_voice(call.message.chat.id, f)
            else: bot.send_audio(call.message.chat.id, f, title="PDF_Audio")
        os.remove(f_path)
        bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    # កូដសម្រាប់ប៊ូតុង Menu (ដូចកូដចាស់របស់អ្នក)
    if "សំឡេង" in message.text or "បកប្រែ" in message.text:
        # ... កូដកំណត់ settings ...
        pass
    else:
        process_text_to_voice(message, message.text)

if __name__ == "__main__":
    keep_alive() # បើក Web Server ឱ្យ Render ឃើញ Port
    bot.remove_webhook()
    bot.infinity_polling()
