import logging
from telegram.ext import ApplicationBuilder
from telegram import Update
from bot.commands import DSABotHandlers
from datetime import datetime
import os
import pytz

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("dsa_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Initialize and run the bot with all schedulers."""
    try:
        # Get bot token from environment variable
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
            return
            
        app = ApplicationBuilder().token(token).build()

        logger.info("🔧 Initializing DSA Bot Handlers...")
        bot_handlers = DSABotHandlers()

        # Register conversation handlers
        logger.info("📝 Registering conversation handlers...")
        app.add_handler(bot_handlers.get_conversation_handler())
        app.add_handler(bot_handlers.get_reminder_conversation_handler())

        # Register other command/callback handlers
        logger.info("⚙️ Registering command handlers...")
        for handler in bot_handlers.get_handlers():
            app.add_handler(handler)

        # Job Schedulers
        job_queue = app.job_queue
        if job_queue:
            logger.info("⏰ Setting up job schedulers...")
            
            # Check for scheduled practice times every minute
            job_queue.run_repeating(
                bot_handlers.check_and_send_practice_questions,
                interval=60,  # every minute
                first=10,  # wait 10 seconds before first check
                name="practice_questions"
            )
            
            # Check for reminder times every minute
            job_queue.run_repeating(
                bot_handlers.check_and_send_reminders,
                interval=60,  # every minute
                first=20,  # wait 20 seconds before first check
                name="completion_reminders"
            )
            
            # Check for deadline times every minute
            job_queue.run_repeating(
                bot_handlers.check_and_auto_mark_missed,
                interval=60,  # every minute
                first=30,  # wait 30 seconds before first check
                name="auto_mark_missed"
            )
            
            logger.info("✅ All job schedulers started successfully.")

        # Start the bot
        current_time_pkt = datetime.now(pytz.timezone("Asia/Karachi")).strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"🚀 DSA Mentor Bot started successfully at {current_time_pkt} PKT")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

    except Exception as e:
        logger.error(f"❌ Critical error starting bot: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()