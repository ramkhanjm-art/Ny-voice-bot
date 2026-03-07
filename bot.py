import telebot
import os
import asyncio
import edge_tts
import sqlite3
from telebot import types
from googletrans import Translator

# --- ការកំណត់ ---
API_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)
translator = Translator()

# បង្កើត Database សម្រាប់រក្សាទុកចំនួន User (ស្ថិតិ)
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

# --- ប៊ូតុងបញ្ជា ---
def main_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    row1 = [types.KeyboardButton("👩 សំឡេងស្រី"), types.KeyboardButton("👨 សំឡេងប្រុស")]
    row2 = [types.KeyboardButton("🌐 បកប្រែអង់គ្លេស -> ខ្មែរ")]
    row3 = [types.KeyboardButton("📊 ស្ថិតិប្រើប្រាស់"), types.KeyboardButton("❓ ជំនួយ")]
    markup.add(*row1)
    markup.add(*row2)
    markup.add(*row3)
    return markup

user_settings = {} # ចងចាំសំឡេង និងមុខងារបកប្រែ

async def generate_voice(text, voice_name, output_file):
    communicate = edge_tts.Communicate(text, voice_name)
    await communicate.save(output_file)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    add_user(message.chat.id)
    bot.send_message(
        message.chat.id, 
        "🇰🇭 ស្វាគមន៍មកកាន់ Bot ជំនាន់ថ្មី!\n\n- ផ្ញើអត្ថបទដើម្បីអាន\n- ផ្ញើឯកសារ .txt ដើម្បីឱ្យខ្ញុំអានឱ្យស្តាប់\n- ប្រើប៊ូតុងខាងក្រោមដើម្បីកំណត់មុខងារ", 
        reply_markup=main_menu_keyboard()
    )

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    chat_id = message.chat.id
    text = message.text

    # ១. មុខងារប្តូរសំឡេង
    if text == "👩 សំឡេងស្រី":
        user_settings[chat_id] = {'voice': "km-KH-SreymomNeural", 'translate': False}
        bot.reply_to(message, "✅ កំណត់យកសំឡេងស្រី")
    
    elif text == "👨 សំឡេងប្រុស":
        user_settings[chat_id] = {'voice': "km-KH-PisethNeural", 'translate': False}
        bot.reply_to(message, "✅ កំណត់យកសំឡេងប្រុស")

    # ២. មុខងារបកប្រែ (Toggle)
    elif text == "🌐 បកប្រែអង់គ្លេស -> ខ្មែរ":
        current = user_settings.get(chat_id, {'translate': False})
        new_status = not current.get('translate', False)
        user_settings[chat_id] = {'voice': current.get('voice', "km-KH-SreymomNeural"), 'translate': new_status}
        msg = "🔔 បើក" if new_status else "🔕 បិទ"
        bot.reply_to(message, f"{msg} មុខងារបកប្រែរួចរាល់! (ផ្ញើអង់គ្លេសមក ខ្ញុំនឹងអានជាខ្មែរ)")

    # ៤. មុខងារស្ថិតិ
    elif text == "📊 ស្ថិតិប្រើប្រាស់":
        count = get_user_count()
        bot.send_message(chat_id, f"📈 ចំនួនអ្នកប្រើប្រាស់សរុប៖ {count} នាក់")

    elif text == "❓ ជំនួយ":
        bot.send_message(chat_id, "ផ្ញើអត្ថបទធម្មតា ឬបើកមុខងារបកប្រែ រួចផ្ញើភាសាអង់គ្លេសមក។")

    else:
        process_text_to_voice(message, text)

# មុខងារបំប្លែងសំឡេង (Handle Text & Translation)
def process_text_to_voice(message, input_text):
    chat_id = message.chat.id
    settings = user_settings.get(chat_id, {'voice': "km-KH-SreymomNeural", 'translate': False})
    
    final_text = input_text
    if settings.get('translate'):
        bot.send_chat_action(chat_id, 'typing')
        final_text = translator.translate(input_text, dest='km').text
        bot.reply_to(message, f"📝 បកប្រែបានថា៖ {final_text}")

    output_file = f"v_{chat_id}.mp3"
    bot.send_chat_action(chat_id, 'record_audio')
    try:
        asyncio.run(generate_voice(final_text, settings.get('voice'), output_file))
        with open(output_file, 'rb') as audio:
            bot.send_voice(chat_id, audio)
        os.remove(output_file)
    except Exception as e:
        bot.reply_to(message, "❌ មិនអាចអានបានទេ សូមព្យាយាមអត្ថបទផ្សេង។")

# ៣. មុខងារអានឯកសារ (.txt)
@bot.message_handler(content_types=['document'])
def handle_docs(message):
    if message.document.file_name.endswith('.txt'):
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        content = downloaded_file.decode('utf-8')
        bot.reply_to(message, "📄 ទទួលបានឯកសារ! កំពុងចាប់ផ្តើមអាន...")
        process_text_to_voice(message, content[:2000]) # កំណត់ត្រឹម ២០០០ តួអក្សរការពារការគាំង
    else:
        bot.reply_to(message, "❌ ខ្ញុំអាចអានបានតែឯកសារប្រភេទ .txt ប៉ុណ្ណោះ។")

if __name__ == "__main__":
    init_db()
    bot.remove_webhook()
    print("Super Bot is running...")
    bot.infinity_polling()
