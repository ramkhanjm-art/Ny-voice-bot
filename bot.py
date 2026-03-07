import telebot
import os
import asyncio
import edge_tts
from telebot import types

# ទាញយក Token ពី Environment Variable
API_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

user_settings = {}

# មុខងារបង្កើតប៊ូតុងជាប់ខាងក្រោម (Main Menu)
def main_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    row1 = [types.KeyboardButton("👩 សំឡេងស្រី (Sreymom)"), types.KeyboardButton("👨 សំឡេងប្រុស (Piseth)")]
    row2 = [types.KeyboardButton("ℹ️ អំពីយើង"), types.KeyboardButton("❓ ជំនួយ")]
    markup.add(*row1)
    markup.add(*row2)
    return markup

async def generate_voice(text, voice_name, output_file):
    communicate = edge_tts.Communicate(text, voice_name)
    await communicate.save(output_file)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id, 
        "🇰🇭 សួស្តី! ខ្ញុំជា Bot បំប្លែងអត្ថបទទៅជាសំឡេងពិរោះបំផុត។\n\nសូមប្រើប៊ូតុងខាងក្រោមដើម្បីកំណត់សំឡេង រួចផ្ញើអត្ថបទមកខ្ញុំ៖", 
        reply_markup=main_menu_keyboard()
    )

# ផ្នែកចាប់យកការចុចប៊ូតុងប្តូរសំឡេង និងព័ត៌មាន
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    chat_id = message.chat.id
    text = message.text

    if text == "👩 សំឡេងស្រី (Sreymom)":
        user_settings[chat_id] = "km-KH-SreymomNeural"
        bot.reply_to(message, "✅ បានប្តូរទៅជា **សំឡេងស្រី** (Sreymom)!")
    
    elif text == "👨 សំឡេងប្រុស (Piseth)":
        user_settings[chat_id] = "km-KH-PisethNeural"
        bot.reply_to(message, "✅ បានប្តូរទៅជា **សំឡេងប្រុស** (Piseth)!")
    
    elif text == "ℹ️ អំពីយើង":
        bot.send_message(chat_id, "🤖 **Ny-Voice-Bot**\nបង្កើតឡើងដើម្បីជួយបំប្លែងអត្ថបទខ្មែរទៅជាសំឡេង AI ពិរោះៗ។\nសម្រួលដោយ៖ Gemini AI")
        
    elif text == "❓ ជំនួយ":
        bot.send_message(chat_id, "របៀបប្រើ៖\n1. រើសសំឡេងប្រុស ឬស្រី\n2. ផ្ញើអត្ថបទជាភាសាខ្មែរ\n3. រង់ចាំទទួលសារសំឡេង!")

    else:
        # បើជាអត្ថបទធម្មតា គឺបំប្លែងជាសំឡេង
        selected_voice = user_settings.get(chat_id, "km-KH-SreymomNeural")
        output_file = f"voice_{chat_id}.mp3"
        bot.send_chat_action(chat_id, 'record_audio')
        
        try:
            asyncio.run(generate_voice(text, selected_voice, output_file))
            with open(output_file, 'rb') as audio:
                bot.send_voice(chat_id, audio, reply_to_message_id=message.message_id)
            os.remove(output_file)
        except Exception as e:
            bot.reply_to(message, f"❌ បញ្ហា៖ {e}")

if __name__ == "__main__":
    bot.remove_webhook() # លុប Webhook ចាស់ដើម្បីកាត់បន្ថយ Error 409
    print("Bot is ready!")
    bot.infinity_polling()
