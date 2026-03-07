import telebot
import os
import asyncio
import edge_tts
import google.generativeai as genai
from telebot import types
from deep_translator import GoogleTranslator
from flask import Flask
from threading import Thread

# --- ១. កំណត់ Web Server សម្រាប់ Render ---
app = Flask('')
@app.route('/')
def home(): return "Super Bot is Online!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- ២. ការកំណត់ Bot & AI ---
API_TOKEN = os.getenv('BOT_TOKEN')
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
ai_model = genai.GenerativeModel('gemini-1.5-flash')
bot = telebot.TeleBot(API_TOKEN)

user_settings = {}

# --- ៣. បង្កើតប៊ូតុង Menu ពេញលេញ ---
def main_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("👩 សំឡេងស្រី")
    btn2 = types.KeyboardButton("👨 សំឡេងប្រុស")
    btn3 = types.KeyboardButton("🌐 បកប្រែ៖ បិទ") # ប៊ូតុងនេះនឹងប្តូរតាមស្ថានភាព
    btn4 = types.KeyboardButton("🤖 សួរ AI (Gemini)")
    btn5 = types.KeyboardButton("❓ ជំនួយ")
    markup.add(btn1, btn2, btn3, btn4, btn5)
    return markup

async def generate_voice(text, voice_name, output_file):
    communicate = edge_tts.Communicate(text, voice_name)
    await communicate.save(output_file)

# --- ៤. មុខងារបញ្ចេញសំឡេង ---
def process_output(message, text):
    chat_id = message.chat.id
    settings = user_settings.get(chat_id, {'voice': "km-KH-SreymomNeural", 'translate': False})
    
    final_text = text
    # បើបើកមុខងារបកប្រែ
    if settings.get('translate'):
        bot.send_chat_action(chat_id, 'typing')
        final_text = GoogleTranslator(source='auto', target='km').translate(text)
        bot.send_message(chat_id, f"📝 **អត្ថបទបកប្រែ៖**\n{final_text}")

    output_file = f"voice_{chat_id}.mp3"
    bot.send_chat_action(chat_id, 'record_audio')
    
    try:
        asyncio.run(generate_voice(final_text, settings['voice'], output_file))
        with open(output_file, 'rb') as audio:
            bot.send_voice(chat_id, audio)
        os.remove(output_file)
    except Exception as e:
        bot.send_message(chat_id, f"❌ បញ្ហាសំឡេង៖ {e}")

# --- ៥. គ្រប់គ្រងប៊ូតុងបញ្ជា ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "👋 សួស្តី! ជ្រើសរើសមុខងារខាងក្រោម៖", reply_markup=main_menu_keyboard())

@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    chat_id = message.chat.id
    t = message.text

    if "👩 សំឡេងស្រី" in t:
        user_settings[chat_id] = user_settings.get(chat_id, {'translate': False})
        user_settings[chat_id]['voice'] = "km-KH-SreymomNeural"
        bot.reply_to(message, "✅ កំណត់យក **សំឡេងស្រី**")

    elif "👨 សំឡេងប្រុស" in t:
        user_settings[chat_id] = user_settings.get(chat_id, {'translate': False})
        user_settings[chat_id]['voice'] = "km-KH-PisethNeural"
        bot.reply_to(message, "✅ កំណត់យក **សំឡេងប្រុស**")

    elif "🌐 បកប្រែ" in t:
        current_settings = user_settings.get(chat_id, {'voice': "km-KH-SreymomNeural", 'translate': False})
        new_status = not current_settings['translate']
        user_settings[chat_id] = {'voice': current_settings['voice'], 'translate': new_status}
        
        status_text = "🔔 បើក" if new_status else "🔕 បិទ"
        # ប្តូរឈ្មោះប៊ូតុង
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("👩 សំឡេងស្រី", "👨 សំឡេងប្រុស", f"🌐 បកប្រែ៖ {status_text}", "🤖 សួរ AI (Gemini)", "❓ ជំនួយ")
        bot.send_message(chat_id, f"{status_text} មុខងារបកប្រែរួចរាល់!", reply_markup=markup)

    elif "🤖 សួរ AI (Gemini)" in t:
        user_settings[chat_id] = user_settings.get(chat_id, {'voice': "km-KH-SreymomNeural", 'translate': False})
        user_settings[chat_id]['mode'] = 'ai'
        bot.reply_to(message, "🤖 តើអ្នកចង់សួរអ្វីដល់ Gemini?")

    else:
        if user_settings.get(chat_id, {}).get('mode') == 'ai':
            bot.send_chat_action(chat_id, 'typing')
            response = ai_model.generate_content(f"Answer in Khmer: {t}")
            process_output(message, response.text)
            user_settings[chat_id]['mode'] = None 
        else:
            process_output(message, t)

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.remove_webhook()
    bot.infinity_polling()
