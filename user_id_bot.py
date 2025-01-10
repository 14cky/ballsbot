# user_id_bot.py
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(f"Your Telegram User ID is: {user_id}")

def main():
    application = ApplicationBuilder().token("8050844334:AAHWT8zu72vKusQ4p0XRHq8DXUhCj2iV6BU").build()
    application.add_handler(CommandHandler("getid", get_id))
    application.run_polling()

if __name__ == '__main__':
    main()
