import telebot
import os
import asyncio
import edge_tts
from threading import Thread

# ទាញយក Token ពី Environment Variable
API_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

# មុខងារបង្កើតសំឡេងឱ្យពិរោះ (ប្រើ Microsoft Sreymom)
async def amain(TEXT, VOICE, OUTPUT_FILE):
    communicate = edge_tts.Communicate(TEXT, VOICE)
    await communicate.save(OUTPUT_FILE)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "🇰🇭 សួស្តី! ឥឡូវនេះខ្ញុំមានសំឡេងពិរោះជាងមុនហើយ។ ផ្ញើអត្ថបទមក!")

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    output_file = f"voice_{chat_id}.mp3"
    
    # បង្ហាញសញ្ញាថា Bot កំពុងអាន
    waiting_msg = bot.reply_to(message, "⌛ កំពុងអាន... សូមរង់ចាំបន្តិច")
    
    try:
        # កំណត់យកសំឡេង 'km-KH-SreymomNeural' (សំឡេងស្រីពិរោះ) 
        # ឬដូរទៅ 'km-KH-PisethNeural' (សំឡេងប្រុស)
        asyncio.run(amain(message.text, "km-KH-SreymomNeural", output_file))
        
        # ផ្ញើឯកសារសំឡេងទៅកាន់អ្នកប្រើប្រាស់
        with open(output_file, 'rb') as audio:
            bot.send_voice(chat_id, audio)
        
        # លុបសាររង់ចាំ និងលុប File ចោល
        bot.delete_message(chat_id, waiting_msg.message_id)
        os.remove(output_file)
        
    except Exception as e:
        bot.edit_message_text(f"⚠️ កំហុស៖ {e}", chat_id, waiting_msg.message_id)

if __name__ == "__main__":
    print("Bot ជាមួយសំឡេងពិរោះ កំពុងដំណើរការ...")
    bot.infinity_polling()
