import telebot
import os
import asyncio
import edge_tts
import sqlite3
from telebot import types
from deep_translator import GoogleTranslator

# --- ការកំណត់ ---
API_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

# បង្កើត Database សម្រាប់ស្ថិតិ
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def get_user_count():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    count = c.fetchone()[0]
    conn.close()
    return count

# --- ប៊ូតុងបញ្ជា (រៀបចំជា ៣ ជួរឱ្យស្អាត) ---
def main_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("👩 សំឡេងស្រី")
    btn2 = types.KeyboardButton("👨 សំឡេងប្រុស")
    btn3 = types.KeyboardButton("🌐 បកប្រែអង់គ្លេស -> ខ្មែរ")
    btn4 = types.KeyboardButton("📊 ស្ថិតិប្រើប្រាស់")
    btn5 = types.KeyboardButton("❓ ជំនួយ")
    
    markup.add(btn1, btn2) # ជួរទី១
    markup.add(btn3)       # ជួរទី២
    markup.add(btn4, btn5) # ជួរទី៣
    return markup

user_settings = {}

async def generate_voice(text, voice_name, output_file):
    communicate = edge_tts.Communicate(text, voice_name)
    await communicate.save(output_file)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    add_user(message.chat.id)
    bot.send_message(
        message.chat.id, 
        "🇰🇭 ស្វាគមន៍! សូមរើសមុខងារខាងក្រោម៖", 
        reply_markup=main_menu_keyboard()
    )

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    chat_id = message.chat.id
    text = message.text

    if text == "👩 សំឡេងស្រី":
        user_settings[chat_id] = {'voice': "km-KH-SreymomNeural", 'translate': False}
        bot.reply_to(message, "✅ កំណត់យកសំឡេងស្រី", reply_markup=main_menu_keyboard())
    
    elif text == "👨 សំឡេងប្រុស":
        user_settings[chat_id] = {'voice': "km-KH-PisethNeural", 'translate': False}
        bot.reply_to(message, "✅ កំណត់យកសំឡេងប្រុស", reply_markup=main_menu_keyboard())

    elif text == "🌐 បកប្រែអង់គ្លេស -> ខ្មែរ":
        current = user_settings.get(chat_id, {'translate': False, 'voice': "km-KH-SreymomNeural"})
        new_status = not current.get('translate', False)
        user_settings[chat_id] = {'voice': current.get('voice'), 'translate': new_status}
        status_text = "🔔 បើក" if new_status else "🔕 បិទ"
        bot.reply_to(message, f"{status_text} មុខងារបកប្រែរួចរាល់!", reply_markup=main_menu_keyboard())

    elif text == "📊 ស្ថិតិប្រើប្រាស់":
        count = get_user_count()
        bot.send_message(chat_id, f"📈 ចំនួនអ្នកប្រើសរុប៖ {count} នាក់")

    elif text == "❓ ជំនួយ":
        bot.send_message(chat_id, "ផ្ញើអត្ថបទធម្មតា ឬបើកមុខងារបកប្រែ រួចផ្ញើភាសាអង់គ្លេសមក។")

    else:
        # ផ្នែកបំប្លែងសំឡេង
        settings = user_settings.get(chat_id, {'voice': "km-KH-SreymomNeural", 'translate': False})
        final_text = text
        
        if settings.get('translate'):
            bot.send_chat_action(chat_id, 'typing')
            try:
                final_text = GoogleTranslator(source='en', target='km').translate(text)
                bot.reply_to(message, f"📝 បកប្រែ៖ {final_text}")
            except:
                pass

        output_file = f"v_{chat_id}.mp3"
        bot.send_chat_action(chat_id, 'record_audio')
        try:
            asyncio.run(generate_voice(final_text, settings.get('voice'), output_file))
            with open(output_file, 'rb') as audio:
                bot.send_voice(chat_id, audio)
            os.remove(output_file)
        except Exception as e:
            bot.reply_to(message, "❌ មិនអាចបង្កើតសំឡេងបានទេ។")

if __name__ == "__main__":
    init_db()
    bot.remove_webhook()
    print("Bot is running...")
    bot.infinity_polling()
