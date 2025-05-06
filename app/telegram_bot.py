import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from config import BOT_TOKEN

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

# Configure logging to both console and file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/telegram_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        f"Hi {user.mention_html()}! I'm a simple Telegram bot. How can I help you today?"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text('I can respond to /start and /help commands!')

import asyncio
from agent import main as agent_main

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log message, call agent, and respond."""
    user = update.effective_user
    message = update.message.text
    
    # Log detailed message information
    # Sanitize input to reject non-ASCII characters
    def is_ascii_safe(text):
        try:
            text.encode('ascii')
            return True
        except UnicodeEncodeError:
            return False

    # Check if message contains only ASCII characters
    if not is_ascii_safe(message):
        logger.warning(f'Rejected non-ASCII message from {user.first_name} (@{user.username})')
        await update.message.reply_text('Sorry, only ASCII characters are allowed.')
        return

    logger.info(f'Received message from {user.first_name} (@{user.username}): {message}')
    
    # Call agent's main method with the message
    try:
        # Run agent main method with the message and get the response
        agent_response = await agent_main(external_input=message)
        
        # Send back the agent's response
        await update.message.reply_text(agent_response or "I processed your request, but no response was generated.")
    except Exception as e:
        logger.error(f'Error processing message: {e}')
        await update.message.reply_text(f'Sorry, I encountered an error: {e}')

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token
    application = Application.builder().token(BOT_TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # on non-command messages, echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
