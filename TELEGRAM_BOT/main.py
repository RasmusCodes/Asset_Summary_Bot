import os
from telegram import *
from telegram.ext import *
import logging
from dotenv import load_dotenv

#Load environment variables form the .env file
load_dotenv()

API_KEY = os.getenv("API_KEY")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I'm your bot. How can I assist you today?")

# Define the function to handle messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "Hello":
        await update.message.reply_text(f"{text}, world!")
    elif text == "Start":
        reply_keyboard = [['Nordnet', 'Nordea', 'Seligson']]
        await update.message.reply_text(
            '<b> Welcome to Asset Summary Bot!\n'
            'Mihin palveluun haluat kirjautua?</b>',
            parse_mode='HTML', 
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard = True)
        )
    else: 
        await update.message.reply_text(f"You said: {text}")

async def stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! What have you invested in?")

if __name__ == '__main__':
    application = Application.builder().token(API_KEY).build()
    
    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    stock_handler = CommandHandler('stock', stock)
    application.add_handler(stock_handler)
    
    application.run_polling()