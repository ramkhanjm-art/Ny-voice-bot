import telebot
import os
from gtts import gTTS

# ទាញយក Token ពី Environment Variable (ត្រូវប្រាកដថាអ្នកបានដាក់ក្នុង Render រួចហើយ)
API_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "🇰🇭 សួស្តី! Bot បានដំណើរការជោគជ័យហើយ។ ផ្ញើអត្ថបទមក!")

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    file_path = f"v_{message.chat.id}.mp3"
    try:
        tts = gTTS(text=message.text, lang='km')
        tts.save(file_path)
        with open(file_path, 'rb') as audio:
            bot.send_voice(message.chat.id, audio)
        os.remove(file_path)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()

import edge_tts
import asyncio

# មុខងារបំប្លែងសំឡេងឱ្យពិរោះជាមួយ Microsoft Edge TTS
async def generate_voice(text, file_path):
    # 'km-KH-PisethNeural' សម្រាប់សំឡេងប្រុស ឬ 'km-KH-SreymomNeural' សម្រាប់សំឡេងស្រី
    communicate = edge_tts.Communicate(text, "km-KH-SreymomNeural")
    await communicate.save(file_path)

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    file_path = f"v_{message.chat.id}.mp3"
    try:
        # រង់ចាំឱ្យវាបង្កើតសំឡេងឱ្យចប់
        asyncio.run(generate_voice(message.text, file_path))
        
        with open(file_path, 'rb') as audio:
            bot.send_voice(message.chat.id, audio)
        os.remove(file_path)
    except Exception as e:
        print(f"Error: {e}")
