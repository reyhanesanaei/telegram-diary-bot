# main.py (with prompt options and admin checks)

import os
import logging
from datetime import datetime, timedelta
import requests
import base64
import io
# NEW: Imports for inline keyboard buttons
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from sqlalchemy import create_engine, Column, Integer, String, DateTime, BigInteger, Text
from sqlalchemy.orm import sessionmaker, declarative_base

# --- 1. CONFIGURATION ---
TELEGRAM_TOKEN = "8415670474:AAExcTxPMGcwIQ4PgbchnXyT9gLa5LALW08"
GEMINI_API_KEY = "AIzaSyAgYhQjV7hQyLJ402G9VbqGezCmlehvAEA"
MODERATECONTENT_API_KEY = "2+hKycGqo9HgyEPYAn2O3w=="

# --- 2. LOGGING SETUP ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- 3. DATABASE SETUP ---
engine = create_engine('sqlite:///chat_history.db')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# (Database models are unchanged)
class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(BigInteger)
    user_id = Column(Integer)
    username = Column(String)
    text = Column(String, nullable=True)
    photo_file_id = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Setting(Base):
    __tablename__ = "settings"
    chat_id = Column(BigInteger, primary_key=True)
    custom_prompt = Column(String, nullable=True)

class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(BigInteger)
    username = Column(String)
    comment = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

class DiaryLog(Base):
    __tablename__ = "diary_logs"
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(BigInteger)
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# --- NEW: PRE-DEFINED PROMPT OPTIONS ---
PROMPT_OPTIONS = {
    "default": "You are a helpful assistant that creates diary entries. Read the following Telegram chat log and summarize it into a fun, engaging diary entry from the perspective of the group.",
    "funny": "You are a witty and sarcastic assistant. Read the following chat log and summarize it into a very funny and slightly exaggerated diary entry. Make jokes about the conversation.",
    "pirate": "You are a pirate captain writing in your log. Read the following chat log and summarize the day's events as a swashbuckling pirate's diary entry. Use pirate slang like 'Ahoy!' and 'Shiver me timbers!'.",
    "serious": "You are a professional historian. Read the following chat log and summarize it into a serious, formal, and objective record of the group's activities and decisions."
}


# --- 4. CONTENT MODERATION FUNCTION ---
def check_comment_safety(comment_text: str) -> bool:
    """Checks a comment for harmful content. Returns True if safe, False if not."""
    try:
        api_url = f"https://api.moderatecontent.com/text/?key={MODERATECONTENT_API_KEY}&msg={comment_text}"
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Moderation result: {data}")
        return data.get("rating_label") == "everyone"
    except Exception as e:
        logger.error(f"ModerateContent API error: {e}")
        return False


# --- 5. TELEGRAM BOT HANDLERS (UPDATED) ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message."""
    await update.message.reply_text(
        'Hello! I am the Group Diary Bot. I learn from your feedback!\n\n'
        'Available commands:\n'
        '/diary_today - Generate today\'s diary entry.\n'
        '/set_prompt - (Admins only) Choose a personality for the diary.\n'
        '/feedback [comment] - Leave feedback to improve the diary.\n'
        '/help - Show this message.'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start(update, context)

async def is_user_admin(chat_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        chat_admins = await context.bot.get_chat_administrators(chat_id)
        return user_id in [admin.user.id for admin in chat_admins]
    except Exception: return False

# UPDATED: This command now sends buttons instead of taking text
async def set_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """(Admins Only) Shows a menu of prompt options."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if not await is_user_admin(chat_id, user_id, context):
        await update.message.reply_text("Sorry, only group admins can use this command.")
        return

    # Create the buttons
    keyboard = [
        [InlineKeyboardButton("Default", callback_data="prompt_default")],
        [InlineKeyboardButton("Funny & Sarcastic", callback_data="prompt_funny")],
        [InlineKeyboardButton("Pirate's Log", callback_data="prompt_pirate")],
        [InlineKeyboardButton("Serious Historian", callback_data="prompt_serious")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text('Please choose a personality for the diary:', reply_markup=reply_markup)

# NEW: This function handles the button clicks
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the prompt."""
    query = update.callback_query
    await query.answer() # Acknowledge the button press

    user_id = query.from_user.id
    chat_id = query.message.chat_id
    
    # SECURITY CHECK: Make sure the person clicking the button is an admin
    if not await is_user_admin(chat_id, user_id, context):
        await query.edit_message_text(text="Sorry, only group admins can change the prompt.")
        return

    # Get the chosen option from the button's callback_data
    chosen_option = query.data.split('_')[1]
    prompt_text = PROMPT_OPTIONS.get(chosen_option)

    if not prompt_text:
        await query.edit_message_text(text="Error: Invalid option selected.")
        return

    db_session = SessionLocal()
    try:
        setting = db_session.query(Setting).filter(Setting.chat_id == chat_id).first()
        if not setting:
            setting = Setting(chat_id=chat_id)
            db_session.add(setting)
        
        setting.custom_prompt = prompt_text
        db_session.commit()
        await query.edit_message_text(text=f"Diary personality set to: **{chosen_option.capitalize()}**", parse_mode='Markdown')
    finally:
        db_session.close()


# (feedback_command and message listeners are unchanged)
async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    comment_text = " ".join(context.args)
    if not comment_text:
        await update.message.reply_text("Please provide your feedback after the command.")
        return
    if not check_comment_safety(comment_text):
        await update.message.reply_text("Sorry, your feedback could not be saved.")
        return
    db_session = SessionLocal()
    try:
        new_feedback = Feedback(chat_id=update.effective_chat.id, username=update.effective_user.username or update.effective_user.first_name, comment=comment_text)
        db_session.add(new_feedback)
        db_session.commit()
        await update.message.reply_text("Thank you for your feedback!")
    finally:
        db_session.close()

async def text_message_listener(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db_session = SessionLocal()
    try:
        new_message = Message(chat_id=update.effective_chat.id, user_id=update.message.from_user.id, username=update.message.from_user.username or update.message.from_user.first_name, text=update.message.text, timestamp=update.message.date)
        db_session.add(new_message)
        db_session.commit()
    finally:
        db_session.close()

async def photo_message_listener(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db_session = SessionLocal()
    try:
        photo_file = await context.bot.get_file(update.message.photo[-1].file_id)
        new_message = Message(chat_id=update.effective_chat.id, user_id=update.message.from_user.id, username=update.message.from_user.username or update.message.from_user.first_name, text=update.message.caption, photo_file_id=photo_file.file_id, timestamp=update.message.date)
        db_session.add(new_message)
        db_session.commit()
    finally:
        db_session.close()

# (The call_gemini_api function is unchanged)
async def call_gemini_api(messages: list, custom_prompt: str, feedback_list: list, context: ContextTypes.DEFAULT_TYPE) -> str:
    if custom_prompt: base_prompt = custom_prompt
    else: base_prompt = PROMPT_OPTIONS['default'] # Use the default from our options
    feedback_text = "\n\nConsider the following user feedback:\n"
    for fb in feedback_list: feedback_text += f"- {fb.comment}\n"
    prompt_text = base_prompt + (feedback_text if feedback_list else "")
    api_parts = [{"text": prompt_text}]
    for msg in messages:
        time_str = msg.timestamp.strftime('%I:%M %p')
        if msg.text: api_parts.append({"text": f"\n[{time_str}] {msg.username}: {msg.text}"})
        if msg.photo_file_id:
            try:
                photo_file = await context.bot.get_file(msg.photo_file_id)
                photo_bytes = await photo_file.download_as_bytearray()
                photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')
                api_parts.append({"inline_data": {"mime_type": "image/jpeg", "data": photo_base64}})
                if not msg.text: api_parts.append({"text": f"\n[{time_str}] {msg.username} sent an image:"})
            except Exception as e: logger.error(f"Photo error: {e}")
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": api_parts}]}
    try:
        response = requests.post(api_url, json=payload)
        response.raise_for_status()
        result = response.json()
        if (result.get('candidates') and result['candidates'][0].get('content') and result['candidates'][0]['content'].get('parts')):
            return result['candidates'][0]['content']['parts'][0]['text']
        else: return "Sorry, I couldn't generate a diary entry."
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        return "Sorry, I had trouble connecting to the AI."

# --- CORRECTED diary_today FUNCTION ---
async def diary_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Let me think... I'm reading today's chat to write the diary. This might take a moment!")
    chat_id = update.effective_chat.id
    db_session = SessionLocal()
    try:
        setting = db_session.query(Setting).filter(Setting.chat_id == chat_id).first()
        custom_prompt = setting.custom_prompt if setting else None
        
        # This part was missing. We need to get the feedback list.
        # For this version, we'll just get the last 5 comments.
        feedback_list = db_session.query(Feedback).filter(Feedback.chat_id == chat_id).order_by(Feedback.timestamp.desc()).limit(5).all()
        
        one_day_ago = datetime.utcnow() - timedelta(days=1)
        messages = db_session.query(Message).filter(Message.chat_id == chat_id, Message.timestamp >= one_day_ago).order_by(Message.timestamp).all()
        
        if not messages:
            await update.message.reply_text("No messages in the last 24 hours.")
            return

        diary_entry = await call_gemini_api(messages, custom_prompt, feedback_list, context)
        await update.message.reply_text(f"**Today's Diary Entry**\n\n{diary_entry}", parse_mode='Markdown')
        
        # We don't have the DiaryLog table in this version, so we remove this part.
        # new_log = DiaryLog(chat_id=chat_id, timestamp=datetime.utcnow())
        # db_session.add(new_log)
        # db_session.commit()
    finally:
        db_session.close()

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Sorry, I didn't understand that command. Type /help to see what I can do.")


# --- 6. MAIN FUNCTION TO RUN THE BOT (UPDATED) ---
def main() -> None:
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("diary_today", diary_today))
    application.add_handler(CommandHandler("set_prompt", set_prompt))
    application.add_handler(CommandHandler("feedback", feedback_command))
    
    # NEW: Add a handler for the button clicks
    application.add_handler(CallbackQueryHandler(button_handler))

    # Add message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_listener))
    application.add_handler(MessageHandler(filters.PHOTO, photo_message_listener))

    # Add a handler for unknown commands
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    logger.info("Bot is running...")
    application.run_polling()


if __name__ == '__main__':
    main()