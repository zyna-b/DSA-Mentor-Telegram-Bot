import logging
from telegram.ext import ApplicationBuilder
from telegram import Update
from bot.commands import DSABotHandlers
from datetime import datetime
import os
import pytz

import os
print("FIREBASE_CREDENTIALS_PATH:", os.getenv("FIREBASE_CREDENTIALS_PATH"))
print("File exists:", os.path.exists(os.getenv("FIREBASE_CREDENTIALS_PATH")))

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
            job_queue.run_repeating(
                bot_handlers.check_and_send_practice_questions,
                interval=60, first=10, name="practice_questions"
            )
            job_queue.run_repeating(
                bot_handlers.check_and_send_reminders,
                interval=60, first=20, name="completion_reminders"
            )
            job_queue.run_repeating(
                bot_handlers.check_and_auto_mark_missed,
                interval=60, first=30, name="auto_mark_missed"
            )
            logger.info("✅ All job schedulers started successfully.")

        current_time_pkt = datetime.now(pytz.timezone("Asia/Karachi")).strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"🚀 DSA Mentor Bot started successfully at {current_time_pkt} PKT")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

    except Exception as e:
        logger.error(f"❌ Critical error starting bot: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()