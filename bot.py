import telebot
import os
import asyncio
import edge_tts
from telebot import types

# ទាញយក Token ពី Environment Variable
API_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

# រក្សាទុកជម្រើសសំឡេង (Default: ស្រី)
user_settings = {}

# មុខងារបង្កើតប៊ូតុងជាប់ខាងក្រោម (Main Menu)
def main_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("👩 សំឡេងស្រី (Sreymom)")
    btn2 = types.KeyboardButton("👨 សំឡេងប្រុស (Piseth)")
    markup.add(btn1, btn2)
    return markup

async def generate_voice(text, voice_name, output_file):
    communicate = edge_tts.Communicate(text, voice_name)
    await communicate.save(output_file)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id, 
        "🇰🇭 សួស្តី! ខ្ញុំជា Bot បំប្លែងអត្ថបទទៅជាសំឡេងពិរោះ។\n\nសូមជ្រើសរើសប្រភេទសំឡេងតាមប៊ូតុងខាងក្រោម រួចផ្ញើអត្ថបទមកខ្ញុំ៖", 
        reply_markup=main_menu_keyboard()
    )

# ផ្នែកចាប់យកការចុចប៊ូតុងប្តូរសំឡេង
@bot.message_handler(func=lambda message: message.text in ["👩 សំឡេងស្រី (Sreymom)", "👨 សំឡេងប្រុស (Piseth)"])
def handle_voice_change(message):
    if "ស្រី" in message.text:
        user_settings[message.chat.id] = "km-KH-SreymomNeural"
        bot.reply_to(message, "✅ បានប្តូរទៅជា **សំឡេងស្រី** រួចរាល់!", parse_mode="Markdown")
    else:
        user_settings[message.chat.id] = "km-KH-PisethNeural"
        bot.reply_to(message, "✅ បានប្តូរទៅជា **សំឡេងប្រុស** រួចរាល់!", parse_mode="Markdown")

# ផ្នែកបំប្លែងអត្ថបទជាសំឡេង
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    # ប្រសិនបើមិនទាន់រើស យកស្រីជា Default
    selected_voice = user_settings.get(chat_id, "km-KH-SreymomNeural")
    output_file = f"voice_{chat_id}.mp3"
    
    # បង្ហាញ Action ថា Bot កំពុងថតសំឡេង (ត្រង់ក្បាល Bot)
    bot.send_chat_action(chat_id, 'record_audio')
    
    try:
        asyncio.run(generate_voice(message.text, selected_voice, output_file))
        
        with open(output_file, 'rb') as audio:
            bot.send_voice(chat_id, audio, reply_to_message_id=message.message_id)
            
        os.remove(output_file)
    except Exception as e:
        bot.reply_to(message, f"❌ មានបញ្ហា៖ {e}")

if __name__ == "__main__":
    print("Bot ជាមួយប៊ូតុងបញ្ជា កំពុងដំណើរការ...")
    bot.infinity_polling()
