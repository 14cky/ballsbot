# bot.py
import logging
import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)
from database import Session, User, Group
from datetime import datetime, timedelta
import random
from pytz import timezone
from telegram.helpers import escape_markdown
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants
RESET_COMMAND = "/reset"
COOLDOWN_HOURS = 24

# Replace with your actual Telegram User ID
ADMIN_USER_ID = 895101362  # <-- Replace this with your User ID

# --- Command Handlers ---

def get_user_rank(session, group_id, user_id):
    """
    Retrieves the rank of a user within a group based on their total_sum.
    """
    users = session.query(User).filter(User.group_id == group_id).order_by(User.total_sum.desc()).all()
    for index, user in enumerate(users, start=1):
        if user.user_id == user_id:
            return index
    return None  # User not found

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in ['group', 'supergroup']:
        await update.message.reply_text(
            "Hello, Group! Use /random to get a number, /top to see the leaderboard, and /profile to view your stats."
        )
    else:
        await update.message.reply_text(
            "Welcome! Use /random to get a number, /top to see the leaderboard, and /profile to view your stats."
        )

async def random_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    chat = update.effective_chat

    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("Please use this command within a group chat.")
        session.close()
        return

    group_id = chat.id
    group_name = chat.title

    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name

    try:
        # Fetch or create the group
        group = session.query(Group).filter(Group.group_id == group_id).first()
        if not group:
            group = Group(group_id=group_id, group_name=group_name)
            session.add(group)
            session.commit()

        # Fetch or create the user within the group
        user_record = session.query(User).filter(
            User.user_id == user_id,
            User.group_id == group_id
        ).first()

        if not user_record:
            # User hasn't used /random before; create a new record
            user_record = User(
                user_id=user_id,
                username=username,
                total_sum=0.0,
                last_random=None,
                group=group
            )
            session.add(user_record)
            session.commit()

        # Check if the user is allowed to use /random
        if user_record.last_random is not None:
            escaped_username = escape_markdown(username, version=2)
            await update.message.reply_text(
                f"{escaped_username}, у тебя кд на команду /random на сегодня\\. Следующая попытка будет завтра\\.",
                parse_mode='MarkdownV2'
            )
            return

        # Generate a random number between -10 and 10
        rand_num = random.randint(-10, 10)

        now = datetime.utcnow()

        # Update user record
        user_record.total_sum += rand_num
        user_record.last_random = now
        session.commit()

        escaped_username = escape_markdown(username, version=2)
        escaped_num_sign = escape_markdown(str(rand_num), version=2)
        escaped_total_sum = escape_markdown(str(user_record.total_sum), version=2)

        # Determine message based on rand_num
        if rand_num > 0:
            num_sign = f"+{rand_num}"
            action = "стали больше"
            motivation = "Продолжай в том же духе, ты сигма\\!"
        elif rand_num < 0:
            num_sign = f"{rand_num}"
            action = "уменьшились"
            motivation = "Сочувствую что ты такой лох\\. Удачи завтра\\!"
        else:
            num_sign = "0"
            action = "no changes to"
            motivation = "Ну зато не уменьшились, и то хорошо\\!"

        # Get user's current rank
        rank = get_user_rank(session, group_id, user_id)
        rank_suffix = get_rank_suffix(rank) if rank else ""

        if rand_num != 0:
            message = (
                f"{escaped_username}, твои яйца {action} на целых *{escaped_num_sign}* см\\!\n"
                f"Теперь они равны *{escaped_total_sum}* см\\.\n"
                f"Твое место в нашем рейтинге *{rank}{rank_suffix}*\\.\n"
                f"{motivation}"
            )
        else:
            message = (
                f"{escaped_username}, твои яйца не изменились в размере\\.\n"
                f"Теперь они равны *{escaped_total_sum}* см\\.\n"
                f"Твое место в нашем рейтинге *{rank}{rank_suffix}*\\.\n"
                f"{motivation}"
            )

        # Send the message with bold formatting using MarkdownV2
        await update.message.reply_markdown_v2(message)

    except Exception as e:
        logger.error(f"Error in /random command: {e}")
        await update.message.reply_text("An error occurred while processing your request.")
    finally:
        session.close()

async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    chat = update.effective_chat

    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("Please use this command within a group chat.")
        session.close()
        return

    group_id = chat.id

    try:
        top_users = session.query(User).filter(
            User.group_id == group_id
        ).order_by(User.total_sum.desc()).limit(10).all()
    except Exception as e:
        logger.error(f"Error fetching top users: {e}")
        await update.message.reply_text("An error occurred while fetching the leaderboard.")
        session.close()
        return

    session.close()

    if not top_users:
        await update.message.reply_text("Никто ещё не использовал команду /random.")
        return

    message = "🏆 *Топ* 🏆\n"
    for idx, user in enumerate(top_users, start=1):
        name = user.username or f"{user.user_id}"
        escaped_name = escape_markdown(name, version=2)
        escaped_total_sum = escape_markdown(str(user.total_sum), version=2)
        message += f"{idx}\\) *{escaped_name}* \\- *{escaped_total_sum} см*\n"

    # Send the message with bold formatting using MarkdownV2
    await update.message.reply_markdown_v2(message)

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    chat = update.effective_chat

    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("Please use this command within a group chat.")
        session.close()
        return

    group_id = chat.id
    user = update.effective_user
    user_id = user.id

    try:
        user_record = session.query(User).filter(
            User.user_id == user_id,
            User.group_id == group_id
        ).first()
    except Exception as e:
        logger.error(f"Error fetching user profile: {e}")
        await update.message.reply_text("An error occurred while fetching your profile.")
        session.close()
        return

    session.close()

    if not user_record:
        await update.message.reply_text("Пустой лист. Нужно использовать команду /random для начала.")
        return

    escaped_name = escape_markdown(user_record.username, version=2)
    escaped_total_sum = escape_markdown(str(user_record.total_sum), version=2)
    profile_text = (
        f"👤 *Профиль*\n"
        f"Никнейм: *{escaped_name}*\n"
        f"Размер яиц: *{escaped_total_sum} см*"
    )
    await update.message.reply_markdown_v2(profile_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📋 *Все команды:*\n\n"
        "/start \\- дефолт\\.\n"
        "/random \\- Рост или уменьшение яиц\\.\n"
        "/top \\- Топ этой группы\\.\n"
        "/profile \\- Профиль с размером яиц\\.\n"
        "/help \\- Показывает это сообщение с командами\\.\n"
        "/reset \\- это для еблана luckar0 который может ресетнуть всю хуйню\\."
    )
    await update.message.reply_markdown_v2(help_text)

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Resets all users' stats and cooldowns. Only accessible by the admin in private chat.
    """
    user = update.effective_user
    chat = update.effective_chat

    # Check if the command is sent in a private chat
    if chat.type != 'private':
        await update.message.reply_text("The /reset command can only be used in a private chat with the bot.")
        return

    # Check if the user is the admin
    if user.id != ADMIN_USER_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    # Proceed to reset all user stats and cooldowns
    session = Session()
    try:
        # Reset total_sum and last_random for all users
        users = session.query(User).all()
        for user_record in users:
            user_record.total_sum = 0.0
            user_record.last_random = None  # Reset cooldown
        session.commit()
        await update.message.reply_text("All user stats and cooldowns have been reset successfully.")
    except Exception as e:
        logger.error(f"Error resetting stats: {e}")
        await update.message.reply_text("An error occurred while resetting the stats.")
        session.rollback()
    finally:
        session.close()

def get_rank_suffix(rank):
    """
    Returns the ordinal suffix for a given rank number.
    """
    return '\\-е'

def reset_cooldowns():
    """
    Resets the last_random field for all users to allow /random command usage.
    """
    session = Session()
    try:
        users = session.query(User).all()
        for user_record in users:
            user_record.last_random = None
        session.commit()
        logger.info("Кд ресетнулись")
    except Exception as e:
        logger.error(f"Error resetting cooldowns: {e}")
        session.rollback()
    finally:
        session.close()

# Main Function to Start the Bot
def main():
    # Initialize the bot application
    application = ApplicationBuilder().token("8050844334:AAHWT8zu72vKusQ4p0XRHq8DXUhCj2iV6BU").build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("random", random_command))
    application.add_handler(CommandHandler("top", top_command))
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("reset", reset_command))

    # Initialize the scheduler for cooldown reset
    scheduler = AsyncIOScheduler(timezone=pytz.timezone('Asia/Almaty'))
    scheduler.add_job(reset_cooldowns, 'cron', hour=0, minute=0)  # At midnight GMT+5
    scheduler.start()

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
