from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from .models import FirebaseManager, DSAQuestionMatcher, GoogleSheetsManager
import asyncio
import logging
from datetime import datetime, timedelta
import random
import pytz

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

DIFFICULTY, TOPIC, COMPANY = range(3)
PRACTICE_TIME, DEADLINE_TIME, REMINDER_TIME = range(10, 13)

DIFFICULTIES = ["Easy", "Medium", "Hard", "Random"]
TOPICS = [
    "Array", "Linked List", "Tree", "Graph", "String",
    "Dynamic Programming", "Heap", "Stack", "Queue", "Random",
]
COMPANIES = [
    "Google", "Amazon", "Microsoft", "Facebook", "Apple", "Netflix",
    "Uber", "No preference", "Random",
]

class DSABotHandlers:
    def __init__(self):
        self.firebase = FirebaseManager()
        self.sheets = GoogleSheetsManager()
        self.question_matcher = DSAQuestionMatcher(self.firebase)
        self.current_questions = {}
        self.question_locks = {}
        self.is_reminder_running = False
        self.is_deadline_check_running = False
        logger.info("✅ DSABotHandlers initialized successfully.")

    def get_pkt_time(self):
        pkt_tz = pytz.timezone("Asia/Karachi")
        return datetime.now(pkt_tz)

    def convert_pkt_to_utc(self, pkt_time_str):
        try:
            pkt_tz = pytz.timezone("Asia/Karachi")
            utc_tz = pytz.UTC
            time_obj = datetime.strptime(pkt_time_str, "%H:%M").time()
            today = datetime.now(pkt_tz).date()
            pkt_datetime = pkt_tz.localize(datetime.combine(today, time_obj))
            utc_datetime = pkt_datetime.astimezone(utc_tz)
            return utc_datetime.strftime("%H:%M")
        except Exception as e:
            logger.error(f"Error converting PKT to UTC: {e}")
            return None

    def convert_utc_to_pkt(self, utc_time_str):
        try:
            utc_tz = pytz.UTC
            pkt_tz = pytz.timezone("Asia/Karachi")
            time_obj = datetime.strptime(utc_time_str, "%H:%M").time()
            today = datetime.now(utc_tz).date()
            utc_datetime = utc_tz.localize(datetime.combine(today, time_obj))
            pkt_datetime = utc_datetime.astimezone(pkt_tz)
            return pkt_datetime.strftime("%H:%M")
        except Exception as e:
            logger.error(f"Error converting UTC to PKT: {e}")
            return utc_time_str

    def validate_time_format(self, time_str):
        try:
            time_obj = datetime.strptime(time_str.strip(), "%H:%M")
            return time_obj.strftime("%H:%M")
        except ValueError:
            return None

    def calculate_time_difference(self, time1_str, time2_str):
        try:
            time1 = datetime.strptime(time1_str, "%H:%M")
            time2 = datetime.strptime(time2_str, "%H:%M")
            if time2 < time1:
                time2 += timedelta(days=1)
            diff = time2 - time1
            return int(diff.total_seconds() / 60)
        except Exception:
            return None

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        try:
            user_prefs = self.firebase.get_user_prefs(user_id)
            if not user_prefs:
                await update.message.reply_text("Welcome! Please set your preferences using /setup.")
            else:
                await update.message.reply_text("Welcome back! Your preferences are already set.")
        except Exception as e:
            logger.error(f"❌ Error in start_command: {e}")
            await update.message.reply_text("An error occurred. Please try again later.")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """
🤖 <b>DSA Mentor Bot - Complete Guide</b>

<b>🚀 GETTING STARTED:</b>
/start - Welcome screen and current status
/setup - Configure preferences (difficulty, topics, companies)
/setreminder - Set up your smart daily schedule
/help - Show this comprehensive guide

<b>📚 PRACTICE COMMANDS:</b>
/question - Get a new DSA question instantly
/done - Mark current question as completed ✅
/missed - Mark current question as skipped ⏭️
/stats - View detailed progress dashboard

<b>⏰ SMART REMINDER SYSTEM:</b>
Your daily schedule has 3 important times:

<b>1. 🎯 Practice Time</b> - When you receive daily questions
<b>2. ⏱️ Deadline Time</b> - When questions auto-mark as missed
<b>3. 🔔 Reminder Time</b> - When you get completion reminders

<b>Example Daily Flow:</b>
• <code>09:00</code> - Get question (Practice Time)
• <code>17:00</code> - Reminder: "Complete today's question!"
• <code>20:00</code> - Auto-mark as missed if not done (Deadline)

<b>🔧 SETUP PROCESS:</b>
<code>/setreminder</code> will ask you:
1. What time do you want daily questions? (e.g., 09:00)
2. What's your deadline for completion? (e.g., 20:00)  
3. When should I remind you? (e.g., 17:00)

<b>💡 SMART FEATURES:</b>
• All times in Pakistan Time (PKT) 🇵🇰
• Questions adapt to your preferences
• Progress tracking across sessions
• Streak counting for motivation
• Smart filtering (no repeated questions)

<b>📊 PROGRESS TRACKING:</b>
• Completion rates and streaks
• Daily, weekly, monthly stats
• Performance insights
• Goal achievement metrics

<b>🎯 TIPS FOR SUCCESS:</b>
• Set realistic practice times
• Give yourself enough time between question and deadline
• Use reminders strategically (not too early/late)
• Review stats regularly to track improvement

<b>🔧 EXAMPLE CONFIGURATION:</b>
Practice Time: 09:00 (Morning question delivery)
Deadline Time: 20:00 (11-hour window to solve)
Reminder Time: 17:00 (3-hour warning before deadline)

<b>❓ NEED HELP?</b>
• Use buttons on messages for quick actions
• Check /stats regularly for progress
• Reconfigure anytime with /setup or /setreminder
• All your data persists between sessions

<b>🚀 Ready to start? Use /setup then /setreminder!</b>

Happy coding! 💻✨
        """

        keyboard = [
            [InlineKeyboardButton("🚀 Setup Preferences", callback_data="setup")],
            [InlineKeyboardButton("⏰ Set Schedule", callback_data="setreminder_help")],
            [InlineKeyboardButton("📚 Get Question", callback_data="next_question")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.effective_message.reply_html(help_text, reply_markup=reply_markup)

    def parse_multi_selection(self, selection, valid_choices):
        selected = [x.strip() for x in selection.split(",")]
        if "Random" in selected or "random" in selected:
            return ["Random"]
        valid_choices_lower = [v.lower() for v in valid_choices]
        sanitized = []
        for x in selected:
            if x.lower() in valid_choices_lower:
                index = valid_choices_lower.index(x.lower())
                sanitized.append(valid_choices[index])
        return sanitized if sanitized else ["Random"]

    async def setup_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        existing_prefs = self.firebase.get_user_prefs(user_id)
        difficulty_keyboard = []

        if existing_prefs and "difficulty" in existing_prefs:
            for diff in DIFFICULTIES:
                prefix = "✅ " if diff in existing_prefs["difficulty"] else ""
                difficulty_keyboard.append([f"{prefix}{diff}"])
        else:
            difficulty_keyboard = [[diff] for diff in DIFFICULTIES]

        markup = ReplyKeyboardMarkup(difficulty_keyboard, one_time_keyboard=True)
        reply_target = update.effective_message
        if update.callback_query:
            reply_target = update.callback_query.message

        await reply_target.reply_html(
            "🎯 <b>Step 1/3: Choose Difficulty Levels</b>\n\n"
            "Select your preferred difficulty:\n"
            "• Multiple options: <code>Easy,Medium</code>\n"
            "• All difficulties: <code>Random</code>\n\n"
            "💡 <i>Tip: Start with Easy/Medium if you're beginning!</i>",
            reply_markup=markup
        )
        return DIFFICULTY

    async def setup_difficulty(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        difficulty = update.effective_message.text.replace("✅ ", "")
        selected = self.parse_multi_selection(difficulty, DIFFICULTIES)
        context.user_data['difficulty'] = selected

        user_id = update.effective_user.id
        existing_prefs = self.firebase.get_user_prefs(user_id)
        topic_keyboard = []

        if existing_prefs and "topic" in existing_prefs:
            for topic_item in TOPICS:
                prefix = "✅ " if topic_item in existing_prefs["topic"] else ""
                topic_keyboard.append([f"{prefix}{topic_item}"])
        else:
            topic_keyboard = [[t] for t in TOPICS]

        markup = ReplyKeyboardMarkup(topic_keyboard, one_time_keyboard=True)

        await update.effective_message.reply_html(
            "🎯 <b>Step 2/3: Choose Topics</b>\n\n"
            f"✅ <b>Difficulty:</b> <i>{', '.join(selected)}</i>\n\n"
            "Select your preferred topics:\n"
            "• Multiple topics: <code>Array,Tree,Graph</code>\n"
            "• All topics: <code>Random</code>\n\n"
            "💡 <i>Focus on 2-3 topics initially for better progress!</i>",
            reply_markup=markup
        )
        return TOPIC

    async def setup_topic(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        topic_text = update.effective_message.text.replace("✅ ", "")
        selected = self.parse_multi_selection(topic_text, TOPICS)
        context.user_data['topic'] = selected

        user_id = update.effective_user.id
        existing_prefs = self.firebase.get_user_prefs(user_id)
        company_keyboard = []

        if existing_prefs and "company" in existing_prefs:
            for company_item in COMPANIES:
                prefix = "✅ " if company_item in existing_prefs["company"] else ""
                company_keyboard.append([f"{prefix}{company_item}"])
        else:
            company_keyboard = [[c] for c in COMPANIES]

        markup = ReplyKeyboardMarkup(company_keyboard, one_time_keyboard=True)

        await update.effective_message.reply_html(
            "🎯 <b>Step 3/3: Choose Target Companies</b>\n\n"
            f"✅ <b>Difficulty:</b> <i>{', '.join(context.user_data['difficulty'])}</i>\n"
            f"✅ <b>Topics:</b> <i>{', '.join(selected)}</i>\n\n"
            "Target specific companies:\n"
            "• Multiple: <code>Google,Amazon,Microsoft</code>\n"
            "• General prep: <code>No preference</code>\n"
            "• All companies: <code>Random</code>\n\n"
            "💡 <i>Choose based on your target interviews!</i>",
            reply_markup=markup
        )
        return COMPANY

    async def setup_company(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        company_text = update.effective_message.text.replace("✅ ", "")
        selected = self.parse_multi_selection(company_text, COMPANIES)
        if "No preference" in selected or "no preference" in selected:
            selected = ["Random"]
        context.user_data['company'] = selected

        # Save preferences
        prefs = {
            "difficulty": context.user_data['difficulty'],
            "topic": context.user_data['topic'],
            "company": selected,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        user_id = update.effective_user.id
        self.firebase.set_user_prefs(user_id, prefs)

        keyboard = [
            [InlineKeyboardButton("⏰ Set Daily Schedule", callback_data="setreminder_help")],
            [InlineKeyboardButton("📚 Get Question Now", callback_data="next_question")],
            [InlineKeyboardButton("📊 View Stats", callback_data="stats")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.effective_message.reply_html(
            f"🎉 <b>Preferences Saved Successfully!</b>\n\n"
            f"✅ <b>Difficulty:</b> {', '.join(prefs['difficulty'])}\n"
            f"✅ <b>Topics:</b> {', '.join(prefs['topic'])}\n"
            f"✅ <b>Companies:</b> {', '.join(prefs['company'])}\n\n"
            f"🎯 <b>Next Step:</b> Set up your daily practice schedule!\n"
            f"Use <b>/setreminder</b> to configure when you want:\n"
            f"• Daily questions delivered\n"
            f"• Completion deadlines\n"
            f"• Reminder notifications\n\n"
            f"💡 <i>This creates a personalized study routine!</i>",
            reply_markup=reply_markup
        )
        context.user_data.clear()
        return ConversationHandler.END

    # ... (REMAINDER OF HANDLERS: Reminder, Question, Stats, Schedulers, etc.)
    # Please request any specific handler or section if you need its code in detail.

    async def setup_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.effective_message.reply_text(
            "❌ Setup cancelled. Your previous preferences remain unchanged.\n"
            "Use /setup anytime to configure preferences."
        )
        context.user_data.clear()
        return ConversationHandler.END

    # === REMINDER CONVERSATION HANDLER ===
    async def setreminder_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the reminder setup conversation."""
        pkt_time = self.get_pkt_time().strftime("%H:%M")
        
        # Handle if this was triggered by a callback query
        if update.callback_query:
            await update.callback_query.answer()  # Acknowledge the callback
            target_message = update.callback_query.message
        else:
            target_message = update.effective_message
        
        # Log that we're starting the conversation
        logger.info(f"Starting setreminder conversation for user {update.effective_user.id}")
        
        await target_message.reply_html(
            "⏰ <b>Smart Daily Schedule Setup</b>\n\n"
            f"🕐 <b>Current Time:</b> {pkt_time} PKT\n\n"
            "Let's set up your personalized study schedule! I'll ask for 3 times:\n\n"
            "🎯 <b>1. Practice Time</b> - When you want daily questions\n"
            "⏱️ <b>2. Deadline Time</b> - When questions auto-mark as missed\n"
            "🔔 <b>3. Reminder Time</b> - When you get completion reminders\n\n"
            "<b>📅 Step 1/3: Practice Time</b>\n"
            "When do you want to receive your daily DSA question?\n\n"
            "<b>Enter time in HH:MM format (Pakistan Time):</b>\n"
            "Examples: <code>09:00</code>, <code>14:30</code>, <code>20:15</code>\n\n"
            "💡 <i>Choose a time when you're most focused!</i>"
        )
        return PRACTICE_TIME

    async def setreminder_practice_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle practice time input."""
        time_input = update.effective_message.text.strip()
        practice_time = self.validate_time_format(time_input)

        if not practice_time:
            await update.effective_message.reply_html(
                "❌ <b>Invalid time format!</b>\n\n"
                "Please enter time in <b>HH:MM</b> format (24-hour):\n"
                "Examples: <code>09:00</code>, <code>14:30</code>, <code>20:15</code>"
            )
            return PRACTICE_TIME

        context.user_data['practice_time'] = practice_time

        await update.effective_message.reply_html(
            "✅ <b>Practice time set!</b> Questions will be delivered at "
            f"<b>{practice_time} PKT</b> daily.\n\n"
            "<b>📅 Step 2/3: Deadline Time</b>\n"
            "When should questions be automatically marked as missed?\n\n"
            "<b>Enter deadline time (HH:MM):</b>\n"
            "Examples: <code>20:00</code>, <code>23:30</code>\n\n"
            "💡 <i>Recommendation: Give yourself at least 8-10 hours!</i>\n"
            f"<i>Your question time: {practice_time} PKT</i>"
        )
        return DEADLINE_TIME

    async def setreminder_deadline_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle deadline time input."""
        time_input = update.effective_message.text.strip()
        deadline_time = self.validate_time_format(time_input)

        if not deadline_time:
            await update.effective_message.reply_html(
                "❌ <b>Invalid time format!</b>\n\n"
                "Please enter time in <b>HH:MM</b> format:\n"
                "Examples: <code>20:00</code>, <code>23:30</code>"
            )
            return DEADLINE_TIME

        practice_time = context.user_data['practice_time']

        # Validate deadline is after practice time (with day rollover consideration)
        time_diff = self.calculate_time_difference(practice_time, deadline_time)
        if time_diff is None or time_diff < 60:  # Less than 1 hour
            await update.effective_message.reply_html(
                "⚠️ <b>Invalid deadline time!</b>\n\n"
                f"Deadline must be at least 1 hour after practice time.\n"
                f"Your practice time: <b>{practice_time} PKT</b>\n"
                f"Your deadline: <b>{deadline_time} PKT</b>\n\n"
                "Please enter a later time:"
            )
            return DEADLINE_TIME

        context.user_data['deadline_time'] = deadline_time

        await update.effective_message.reply_html(
            "✅ <b>Deadline time set!</b> Questions will auto-mark as missed at "
            f"<b>{deadline_time} PKT</b>.\n\n"
            f"⏰ <b>Your window:</b> {time_diff} minutes to complete questions\n\n"
            "<b>📅 Step 3/3: Reminder Time</b>\n"
            "When should I remind you to complete the question?\n\n"
            "<b>Enter reminder time (HH:MM):</b>\n"
            "Examples: <code>17:00</code>, <code>19:30</code>\n\n"
            "💡 <i>Best practice: 1-3 hours before deadline</i>\n"
            f"<i>Your deadline: {deadline_time} PKT</i>"
        )
        return REMINDER_TIME

    async def setreminder_reminder_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle reminder time input and save all settings."""
        time_input = update.effective_message.text.strip()
        reminder_time = self.validate_time_format(time_input)

        if not reminder_time:
            await update.effective_message.reply_html(
                "❌ <b>Invalid time format!</b>\n\n"
                "Please enter time in <b>HH:MM</b> format:\n"
                "Examples: <code>17:00</code>, <code>19:30</code>"
            )
            return REMINDER_TIME

        practice_time = context.user_data['practice_time']
        deadline_time = context.user_data['deadline_time']

        # Validate reminder is between practice and deadline
        practice_to_reminder = self.calculate_time_difference(practice_time, reminder_time)
        reminder_to_deadline = self.calculate_time_difference(reminder_time, deadline_time)

        # 🔧 FIX: Check if reminder is AFTER deadline
        if reminder_to_deadline is None or reminder_to_deadline <= 0:
            await update.effective_message.reply_html(
                "⚠️ <b>Invalid reminder time!</b>\n\n"
                "❌ <b>Reminder time CANNOT be after deadline time!</b>\n\n"
                f"Practice: <b>{practice_time} PKT</b>\n"
                f"Deadline: <b>{deadline_time} PKT</b>\n"
                f"Your reminder: <b>{reminder_time} PKT</b>\n\n"
                "💡 <b>Reminder must be BEFORE deadline!</b>\n"
                "Example: If deadline is 19:53, reminder should be 19:00 or earlier.\n\n"
                "Please enter a time between practice and deadline:"
            )
            return REMINDER_TIME

        if practice_to_reminder is None or practice_to_reminder < 30:
            await update.effective_message.reply_html(
                "⚠️ <b>Invalid reminder time!</b>\n\n"
                "Reminder should be at least 30 minutes after practice time.\n\n"
                f"Practice: <b>{practice_time} PKT</b>\n"
                f"Reminder: <b>{reminder_time} PKT</b>\n"
                f"Deadline: <b>{deadline_time} PKT</b>\n\n"
                "Please enter a valid reminder time:"
            )
            return REMINDER_TIME

        # Convert all times to UTC for storage
        practice_time_utc = self.convert_pkt_to_utc(practice_time)
        deadline_time_utc = self.convert_pkt_to_utc(deadline_time)
        reminder_time_utc = self.convert_pkt_to_utc(reminder_time)

        if not all([practice_time_utc, deadline_time_utc, reminder_time_utc]):
            await update.effective_message.reply_text(
                "❌ Error converting times. Please try again."
            )
            context.user_data.clear()
            return ConversationHandler.END

        # Save to Firebase
        user_id = update.effective_user.id
        reminder_settings = {
            'practice_time_utc': practice_time_utc,
            'deadline_time_utc': deadline_time_utc,
            'reminder_time_utc': reminder_time_utc,
            'practice_time_pkt': practice_time,
            'deadline_time_pkt': deadline_time,
            'reminder_time_pkt': reminder_time,
            'created_at': datetime.now().isoformat(),
            'timezone': 'Asia/Karachi'
        }

        try:
            self.firebase.set_user_reminder_settings(user_id, reminder_settings)

            keyboard = [
                [InlineKeyboardButton("📚 Get First Question", callback_data="next_question")],
                [InlineKeyboardButton("📊 View Stats", callback_data="stats")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.effective_message.reply_html(
                "🎉 <b>Perfect! Your daily schedule is now active!</b>\n\n"
                f"📅 <b>Your Daily Routine (Pakistan Time):</b>\n"
                f"🎯 <b>{practice_time} PKT</b> - Daily question delivery\n"
                f"🔔 <b>{reminder_time} PKT</b> - Completion reminder\n"
                f"⏱️ <b>{deadline_time} PKT</b> - Auto-mark as missed\n\n"
                f"⏰ <b>Time Windows:</b>\n"
                f"• Practice to Reminder: {practice_to_reminder} minutes\n"
                f"• Reminder to Deadline: {reminder_to_deadline} minutes\n\n"
                f"🚀 <b>Starting tomorrow, you'll receive:</b>\n"
                f"• Personalized questions at {practice_time}\n"
                f"• Friendly reminders at {reminder_time}\n"
                f"• Smart progress tracking\n\n"
                f"💡 <i>Ready to start practicing? Get your first question!</i>",
                reply_markup=reply_markup
            )

            logger.info(f"User {user_id} set reminder schedule: {practice_time}-{reminder_time}-{deadline_time} PKT")

        except Exception as e:
            logger.error(f"Error saving reminder settings for user {user_id}: {e}")
            await update.effective_message.reply_text(
                "❌ Error saving settings. Please try /setreminder again."
            )

        context.user_data.clear()
        return ConversationHandler.END

    async def setreminder_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel reminder setup."""
        await update.effective_message.reply_text(
            "❌ Reminder setup cancelled. Your previous settings remain unchanged.\n"
            "Use /setreminder anytime to set up your schedule."
        )
        context.user_data.clear()
        return ConversationHandler.END

    async def question_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get a new question for the user."""
        user_id = update.effective_user.id
        if user_id in self.question_locks and self.question_locks[user_id].locked():
            await update.effective_message.reply_text("Please wait, fetching your question...")
            return

        async with self.question_locks.setdefault(user_id, asyncio.Lock()):
            try:
                # Use Firebase to get matching questions
                questions, error_message = await self.question_matcher.get_matching_questions(user_id)

                if error_message:
                    await update.effective_message.reply_text(error_message)
                    return

                if not questions:
                    await update.effective_message.reply_text("No matching questions found. Please update your preferences.")
                    return

                question = random.choice(questions)
                self.current_questions[user_id] = question
                self.firebase.update_question_status(user_id, question['Question'], "pending")

                await update.effective_message.reply_html(
                    f"Question: {question['Question']}\nDifficulty: {question['Difficulty']}\nUse /done or /missed to mark your progress."
                )
            except Exception as e:
                logger.error(f"Error fetching question: {e}", exc_info=True)
                await update.effective_message.reply_text(f"Error fetching question: {e}")

    async def done_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mark current question as done."""
        user_id = update.effective_user.id
        question = self.current_questions.pop(user_id, None)
        if not question:
            await update.effective_message.reply_text("No active question found.")
            return

        self.firebase.update_question_status(user_id, question['Question'], "done")
        await update.effective_message.reply_text("Question marked as done!")

    async def missed_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mark current question as missed."""
        user_id = update.effective_user.id
        question = self.current_questions.pop(user_id, None)
        if not question:
            await update.effective_message.reply_text("No active question found.")
            return

        self.firebase.update_question_status(user_id, question['Question'], "missed")
        await update.effective_message.reply_text("Question marked as missed!")

    async def set_reminder_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set a reminder for the user."""
        user_id = update.effective_user.id
        time_str = update.message.text.split()[1] if len(update.message.text.split()) > 1 else None

        if not time_str:
            await update.effective_message.reply_text("Please provide a time in HH:MM format.")
            return

        try:
            reminder_time = datetime.strptime(time_str, "%H:%M").strftime("%H:%M")
            self.firebase.set_user_reminder_settings(user_id, {'reminder_time_utc': reminder_time})
            await update.effective_message.reply_text(f"Reminder set for {reminder_time} UTC.")
        except ValueError:
            await update.effective_message.reply_text("Invalid time format. Use HH:MM.")

    def get_conversation_handler(self):
        """Get the conversation handler for setting up preferences."""
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("setup", self.setup_start)],
            states={
                DIFFICULTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.setup_difficulty)],
                TOPIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.setup_topic)],
                COMPANY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.setup_company)],
            },
            fallbacks=[CommandHandler("cancel", self.setup_cancel)],
        )
        return conv_handler

    def get_reminder_conversation_handler(self):
     """Get the conversation handler for setting up reminders."""
     conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("setreminder", self.setreminder_start),
            CallbackQueryHandler(self.setreminder_start, pattern="^setreminder_help$")
        ],
        states={
            PRACTICE_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.setreminder_practice_time)],
            DEADLINE_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.setreminder_deadline_time)],
            REMINDER_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.setreminder_reminder_time)],
        },
        fallbacks=[CommandHandler("cancel", self.setreminder_cancel)],
     )
     return conv_handler

    def get_handlers(self):
        """Get all command handlers."""
        handlers = [
            CommandHandler("start", self.start_command),
            CommandHandler("help", self.help_command),
            CommandHandler("question", self.question_command),
            CommandHandler("done", self.done_command),
            CommandHandler("missed", self.missed_command),
            CommandHandler("set_reminder", self.set_reminder_command),
            CallbackQueryHandler(self.handle_callback_query),
        ]
        return handlers

    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboard buttons."""
        query = update.callback_query
        await query.answer()  # Acknowledge the callback

        if query.data == "setup":
            await self.setup_start(update, context)
            return DIFFICULTY
        # elif query.data == "setreminder_help":
        #     await self.setreminder_start(update, context)
        #     return PRACTICE_TIME
        elif query.data == "next_question":
            await self.question_command(update, context)
        elif query.data == "stats":
            await self.stats_command(update, context)
        else:
            await query.message.reply_text(f"Callback query data: {query.data}")

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user statistics."""
        user_id = update.effective_user.id
        # TODO: Implement stats command logic here
        await update.effective_message.reply_text("Stats command is under development.")

    async def check_and_send_practice_questions(self, context):
        """Check for users with scheduled practice time and send questions."""
        now_utc = datetime.utcnow().strftime("%H:%M")
        user_ids = self.firebase.get_users_with_practice_time(now_utc)

        for user_id in user_ids:
            try:
                # Get the last question sent date
                last_question_sent_date = self.firebase.get_last_question_sent_date(user_id)
                today_date = datetime.utcnow().strftime("%Y-%m-%d")

                # Check if a question was already sent today
                if last_question_sent_date == today_date:
                    logger.info(f"Question already sent today to user {user_id}, skipping.")
                    continue

                # Fetch questions for the user
                questions, error_message = await self.question_matcher.get_matching_questions(user_id)

                if error_message:
                    logger.error(f"Error fetching questions for user {user_id}: {error_message}")
                    continue

                if not questions:
                    logger.info(f"No matching questions found for user {user_id}")
                    continue

                # Select a random question
                question = random.choice(questions)

                # Send the question to the user
                try:
                    bot = context.bot
                    await bot.send_message(
                        user_id,
                        f"It's practice time!\nQuestion: {question['Question']}\nDifficulty: {question['Difficulty']}\nUse /done or /missed to mark your progress.",
                    )
                    self.current_questions[user_id] = question
                    self.firebase.update_question_status(user_id, question['Question'], "pending")

                    # Update the last question sent date
                    self.firebase.update_last_question_sent_date(user_id, today_date)
                    logger.info(f"Practice question sent to user {user_id} at {now_utc} UTC.")

                except Exception as e:
                    logger.error(f"Error sending question to user {user_id}: {e}")

            except Exception as e:
                logger.error(f"Error in practice question scheduler for user {user_id}: {e}")

    async def check_and_send_reminders(self, context):
        """Check for users with scheduled completion reminders and send reminders."""
        if self.is_reminder_running:
            logger.info("Reminder check is already running, skipping...")
            return

        self.is_reminder_running = True
        try:
            now_utc = datetime.utcnow().strftime("%H:%M")
            user_ids = self.firebase.get_users_with_reminder_time(now_utc)

            for user_id in user_ids:
                try:
                    # Get the last reminder sent date
                    last_reminder_sent_date = self.firebase.get_last_reminder_sent_date(user_id)
                    today_date = datetime.utcnow().strftime("%Y-%m-%d")

                    # Check if a reminder was already sent today
                    if last_reminder_sent_date == today_date:
                        logger.info(f"Reminder already sent today to user {user_id}, skipping.")
                        continue

                    # Get the current question for the user
                    question = self.current_questions.get(user_id)
                    if not question:
                        logger.info(f"No active question found for user {user_id}, skipping reminder.")
                        continue

                    # Send the reminder to the user
                    try:
                        bot = context.bot
                        await bot.send_message(
                            user_id,
                            "Friendly reminder! Complete today's DSA question! Use /done or /missed to mark your progress.",
                        )

                        # Update the last reminder sent date
                        self.firebase.update_last_reminder_sent_date(user_id, today_date)
                        logger.info(f"Completion reminder sent to user {user_id} at {now_utc} UTC.")

                    except Exception as e:
                        logger.error(f"Error sending reminder to user {user_id}: {e}")

                except Exception as e:
                    logger.error(f"Error in reminder scheduler for user {user_id}: {e}")
        finally:
            self.is_reminder_running = False

    async def check_and_auto_mark_missed(self, context):
        """Check for users with missed deadlines and auto-mark questions as missed."""
        if self.is_deadline_check_running:
            logger.info("Deadline check is already running, skipping...")
            return

        self.is_deadline_check_running = True
        try:
            now_utc = datetime.utcnow().strftime("%H:%M")
            user_ids = self.firebase.get_users_with_deadline_time(now_utc)

            for user_id in user_ids:
                try:
                    # Get the last deadline processed date
                    last_deadline_processed_date = self.firebase.get_last_deadline_processed_date(user_id)
                    today_date = datetime.utcnow().strftime("%Y-%m-%d")

                    # Check if the deadline was already processed today
                    if last_deadline_processed_date == today_date:
                        logger.info(f"Deadline already processed today for user {user_id}, skipping.")
                        continue

                    # Get the current question for the user
                    question = self.current_questions.pop(user_id, None)
                    if not question:
                        logger.info(f"No active question found for user {user_id}, skipping auto-marking.")
                        continue

                    # Auto-mark the question as missed
                    try:
                        self.firebase.update_question_status(user_id, question['Question'], "missed")
                        logger.info(f"Question auto-marked as missed for user {user_id} at {now_utc} UTC.")

                        bot = context.bot
                        await bot.send_message(
                            user_id,
                            f"The deadline for today's question ({question['Question']}) has passed. It has been marked as missed.",
                        )

                        # Update the last deadline processed date
                        self.firebase.update_last_deadline_processed_date(user_id, today_date)

                    except Exception as e:
                        logger.error(f"Error auto-marking question as missed for user {user_id}: {e}")

                except Exception as e:
                    logger.error(f"Error in deadline scheduler for user {user_id}: {e}")
        finally:
            self.is_deadline_check_running = False
