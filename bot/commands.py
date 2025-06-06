import re
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
        self._user_busy = {}
        logger.info("✅ DSABotHandlers initialized successfully.")

    def parse_user_time(self, time_str):
        time_str = time_str.strip().upper().replace('.', '').replace(' ', '')
        match_12 = re.match(r'^(\d{1,2}):(\d{2})(AM|PM)$', time_str)
        if match_12:
            hour = int(match_12.group(1))
            minute = int(match_12.group(2))
            ampm = match_12.group(3)
            if hour < 1 or hour > 12 or minute > 59:
                return None
            if ampm == "PM" and hour != 12:
                hour += 12
            if ampm == "AM" and hour == 12:
                hour = 0
            return f"{hour:02d}:{minute:02d}"
        try:
            dt = datetime.strptime(time_str, "%H:%M")
            return dt.strftime("%H:%M")
        except Exception:
            return None

    def display_time_12h(self, time_str):
        try:
            dt = datetime.strptime(time_str, "%H:%M")
            return dt.strftime("%I:%M %p").lstrip("0")
        except Exception:
            return time_str

    def is_user_busy(self, user_id):
        return self._user_busy.get(user_id, False)

    def set_user_busy(self, user_id, busy=True):
        self._user_busy[user_id] = busy

    def clear_user_busy(self, user_id):
        self._user_busy.pop(user_id, None)

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
                await update.message.reply_text("Welcome! Please set your preferences using /setup. For getting started use /help.")
            else:
                await update.message.reply_text("Welcome back! Your preferences are already set. For more commands enter /help.")
        except Exception as e:
            logger.error(f"❌ Error in start_command: {e}")
            await update.message.reply_text("An error occurred. Please try again later.")

    async def help_command(self, update, context):
        help_text = """
🤖 <b>DSA Mentor Bot - Complete Guide</b>

<b>🚀 GETTING STARTED:</b>
/start - Show welcome screen and your current setup status.
/setup - Configure or update your practice preferences (difficulty, topics, companies).
/setreminder - Set up or change your smart daily schedule (practice, deadline, and reminder times).
/help - Show this guide at any time for instructions and command list.

/exit - Cancel any ongoing multi-step operation instantly.
/cancel - Cancel any ongoing multi-step operation instantly.

<b>📚 PRACTICE COMMANDS:</b>
/question - Instantly get a new DSA question according to your preferences.
/done - Mark the current question as completed (counts toward your streak).
/missed - Mark the current question as missed (resets streak).
/stats - View your detailed progress dashboard and streak data.

<b>⏰ SMART REMINDER SYSTEM:</b>
Your daily schedule has 3 important times:
1. 🎯 Practice Time — When you receive daily questions
2. ⏱️ Deadline Time — When questions are auto-marked as missed
3. 🔔 Reminder Time — When you receive completion reminders

Example Daily Flow:
• 9:00 AM — Get your question (Practice Time)
• 5:00 PM — Reminder: "Complete today's question!"
• 8:00 PM — Auto-mark as missed if not done (Deadline)

🛠️ SETUP PROCESS:
/setreminder will ask you:
1. What time do you want to receive daily questions? (e.g., 9:00 AM)
2. What's your preferred deadline for completion? (e.g., 8:00 PM)
3. When should I remind you to complete the question? (e.g., 5:00 PM)

<b>💡 SMART FEATURES:</b>
• All times are in Pakistan Time (PKT) 🇵🇰
• Questions adapt to your selected preferences
• Tracks your progress and streaks automatically
• Smart filtering to avoid repeated questions

<b>📊 PROGRESS TRACKING:</b>
• Tracks your completion rates and streaks
• Daily, weekly, and monthly stats
• Performance insights and goal tracking

<b>🎯 TIPS FOR SUCCESS:</b>
• Set realistic and consistent practice times
• Allow enough time between question and deadline
• Use reminders to maximize consistency
• Check /stats regularly to monitor your improvement


📝 EXAMPLE CONFIGURATION:
Practice Time: 9:00 AM (Morning delivery)
Deadline Time: 8:00 PM (11-hour window)
Reminder Time: 5:00 PM (3 hours before deadline)


<b>❓ NEED HELP?</b>
• Use the buttons below messages for quick actions
• Check /stats for your progress and streak
• Re-run /setup or /setreminder to change your preferences anytime
• Your progress and settings are always saved

<b>🛑 COMMAND SUMMARY:</b>
/start, /setup, /setreminder, /question, /done, /missed, /stats, /help, /exit, /cancel

🚀 <b>Ready to start?</b> Use <code>/setup</code> then <code>/setreminder</code>!

Happy coding! 💻✨
        """
        keyboard = [
            [InlineKeyboardButton("🚀 Setup Preferences", callback_data="setup")],
            [InlineKeyboardButton("⏰ Set Schedule", callback_data="setreminder_help")],
            [InlineKeyboardButton("📚 Get Question", callback_data="next_question")],
            [InlineKeyboardButton("📊 View Stats", callback_data="stats")]
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

    # ... keep your setup/exit/stats/other handlers unchanged,
    # replacing all time parsing and display with parse_user_time and display_time_12h as shown above.
    # Also update all messages/examples to 12-hour format as in the previous responses.
    # For brevity, they are not repeated here, but the code structure remains the same.

    # The rest of the class (setup, reminders, questions, stats, etc.) should follow the same pattern as the examples above.


    async def setup_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if self.is_user_busy(user_id):
            await update.effective_message.reply_text(
                "⚠️ You're already in the middle of another operation. Finish it or use /exit or /cancel before starting a new one."
            )
            return ConversationHandler.END
        self.set_user_busy(user_id, True)
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
        user_id = update.effective_user.id
        company_text = update.effective_message.text.replace("✅ ", "")
        selected = self.parse_multi_selection(company_text, COMPANIES)
        if "No preference" in selected or "no preference" in selected:
            selected = ["Random"]
        context.user_data['company'] = selected

        prefs = {
            "difficulty": context.user_data['difficulty'],
            "topic": context.user_data['topic'],
            "company": selected,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

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
        self.clear_user_busy(user_id)
        return ConversationHandler.END

    async def setup_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        await update.effective_message.reply_text(
            "❌ Setup cancelled. Your previous preferences remain unchanged.\n"
            "Use /setup anytime to configure preferences."
        )
        context.user_data.clear()
        self.clear_user_busy(user_id)
        return ConversationHandler.END

    async def exit_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        await update.effective_message.reply_text(
            "❌ Operation cancelled and any unsaved changes have been rolled back. You can now start a new operation."
        )
        context.user_data.clear()
        self.clear_user_busy(user_id)
        return ConversationHandler.END

    # === REMINDER CONVERSATION HANDLER ===
    # === REMINDER CONVERSATION HANDLER ===
    async def setreminder_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if self.is_user_busy(user_id):
            await update.effective_message.reply_text(
                "⚠️ You're already in the middle of another operation. Finish it or use /exit or /cancel before starting a new one."
            )
            return ConversationHandler.END
        self.set_user_busy(user_id, True)
        pkt_time = self.display_time_12h(self.get_pkt_time().strftime("%H:%M"))
        if update.callback_query:
            await update.callback_query.answer()
            target_message = update.callback_query.message
        else:
            target_message = update.effective_message
        logger.info(f"Starting setreminder conversation for user {user_id}")
        await target_message.reply_html(
            "⏰ <b>Smart Daily Schedule Setup</b>\n\n"
            f"🕐 <b>Current Time:</b> {pkt_time} PKT\n\n"
            "Let's set up your personalized study schedule! I'll ask for 3 times:\n\n"
            "🎯 <b>1. Practice Time</b> - When you want daily questions\n"
            "⏱️ <b>2. Deadline Time</b> - When questions auto-mark as missed\n"
            "🔔 <b>3. Reminder Time</b> - When you get completion reminders\n\n"
            "<b>📅 Step 1/3: Practice Time</b>\n"
            "When do you want to receive your daily DSA question?\n\n"
            "<b>Enter time in 12-hour format (Pakistan Time):</b>\n"
            "Examples: <code>9:00 AM</code>, <code>2:30 PM</code>, <code>8:15 PM</code>\n\n"
            "💡 <i>Choose a time when you're most focused!</i>"
        )
        return PRACTICE_TIME

    async def setreminder_practice_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        time_input = update.effective_message.text.strip()
        practice_time = self.parse_user_time(time_input)
        if not practice_time:
            await update.effective_message.reply_html(
                "❌ <b>Invalid time format!</b>\n\n"
                "Please enter time as <b>h:mm AM/PM</b>:\n"
                "Examples: <code>9:00 AM</code>, <code>2:30 PM</code>, <code>8:15 PM</code>"
            )
            return PRACTICE_TIME
        context.user_data['practice_time'] = practice_time
        await update.effective_message.reply_html(
            "✅ <b>Practice time set!</b> Questions will be delivered at "
            f"<b>{self.display_time_12h(practice_time)} PKT</b> daily.\n\n"
            "<b>📅 Step 2/3: Deadline Time</b>\n"
            "When should questions be automatically marked as missed?\n\n"
            "<b>Enter deadline time (h:mm AM/PM):</b>\n"
            "Examples: <code>8:00 PM</code>, <code>11:30 PM</code>\n\n"
            "💡 <i>Recommendation: Give yourself at least 8-10 hours!</i>\n"
            f"<i>Your question time: {self.display_time_12h(practice_time)} PKT</i>"
        )
        return DEADLINE_TIME


    async def setreminder_deadline_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        time_input = update.effective_message.text.strip()
        deadline_time = self.parse_user_time(time_input)
        if not deadline_time:
            await update.effective_message.reply_html(
                "❌ <b>Invalid time format!</b>\n\n"
                "Please enter time as <b>h:mm AM/PM</b>:\n"
                "Examples: <code>8:00 PM</code>, <code>11:30 PM</code>"
            )
            return DEADLINE_TIME
        practice_time = context.user_data['practice_time']
        time_diff = self.calculate_time_difference(practice_time, deadline_time)
        if time_diff is None or time_diff < 60:
            await update.effective_message.reply_html(
                "⚠️ <b>Invalid deadline time!</b>\n\n"
                f"Deadline must be at least 1 hour after practice time.\n"
                f"Your practice time: <b>{self.display_time_12h(practice_time)} PKT</b>\n"
                f"Your deadline: <b>{self.display_time_12h(deadline_time)} PKT</b>\n\n"
                "Please enter a later time:"
            )
            return DEADLINE_TIME
        context.user_data['deadline_time'] = deadline_time
        await update.effective_message.reply_html(
            "✅ <b>Deadline time set!</b> Questions will auto-mark as missed at "
            f"<b>{self.display_time_12h(deadline_time)} PKT</b>.\n\n"
            f"⏰ <b>Your window:</b> {time_diff} minutes to complete questions\n\n"
            "<b>📅 Step 3/3: Reminder Time</b>\n"
            "When should I remind you to complete the question?\n\n"
            "<b>Enter reminder time (h:mm AM/PM):</b>\n"
            "Examples: <code>5:00 PM</code>, <code>7:30 PM</code>\n\n"
            "💡 <i>Best practice: 1-3 hours before deadline</i>\n"
            f"<i>Your deadline: {self.display_time_12h(deadline_time)} PKT</i>"
        )
        return REMINDER_TIME

    async def setreminder_reminder_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        time_input = update.effective_message.text.strip()
        reminder_time = self.parse_user_time(time_input)
        if not reminder_time:
            await update.effective_message.reply_html(
                "❌ <b>Invalid time format!</b>\n\n"
                "Please enter time as <b>h:mm AM/PM</b>:\n"
                "Examples: <code>5:00 PM</code>, <code>7:30 PM</code>"
            )
            return REMINDER_TIME
        practice_time = context.user_data['practice_time']
        deadline_time = context.user_data['deadline_time']
        practice_to_reminder = self.calculate_time_difference(practice_time, reminder_time)
        reminder_to_deadline = self.calculate_time_difference(reminder_time, deadline_time)
        if reminder_to_deadline is None or reminder_to_deadline <= 0:
            await update.effective_message.reply_html(
                "⚠️ <b>Invalid reminder time!</b>\n\n"
                "❌ <b>Reminder time CANNOT be after deadline time!</b>\n\n"
                f"Practice: <b>{self.display_time_12h(practice_time)} PKT</b>\n"
                f"Deadline: <b>{self.display_time_12h(deadline_time)} PKT</b>\n"
                f"Your reminder: <b>{self.display_time_12h(reminder_time)} PKT</b>\n\n"
                "💡 <b>Reminder must be BEFORE deadline!</b>\n"
                "Example: If deadline is 7:53 PM, reminder should be 7:00 PM or earlier.\n\n"
                "Please enter a time between practice and deadline:"
            )
            return REMINDER_TIME
        if practice_to_reminder is None or practice_to_reminder < 30:
            await update.effective_message.reply_html(
                "⚠️ <b>Invalid reminder time!</b>\n\n"
                "Reminder should be at least 30 minutes after practice time.\n\n"
                f"Practice: <b>{self.display_time_12h(practice_time)} PKT</b>\n"
                f"Reminder: <b>{self.display_time_12h(reminder_time)} PKT</b>\n"
                f"Deadline: <b>{self.display_time_12h(deadline_time)} PKT</b>\n\n"
                "Please enter a valid reminder time:"
            )
            return REMINDER_TIME
        practice_time_utc = self.convert_pkt_to_utc(practice_time)
        deadline_time_utc = self.convert_pkt_to_utc(deadline_time)
        reminder_time_utc = self.convert_pkt_to_utc(reminder_time)
        if not all([practice_time_utc, deadline_time_utc, reminder_time_utc]):
            await update.effective_message.reply_text(
                "❌ Error converting times. Please try again."
            )
            context.user_data.clear()
            self.clear_user_busy(user_id)
            return ConversationHandler.END
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
                f"🎯 <b>{self.display_time_12h(practice_time)} PKT</b> - Daily question delivery\n"
                f"🔔 <b>{self.display_time_12h(reminder_time)} PKT</b> - Completion reminder\n"
                f"⏱️ <b>{self.display_time_12h(deadline_time)} PKT</b> - Auto-mark as missed\n\n"
                f"⏰ <b>Time Windows:</b>\n"
                f"• Practice to Reminder: {practice_to_reminder} minutes\n"
                f"• Reminder to Deadline: {reminder_to_deadline} minutes\n\n"
                f"🚀 <b>Starting tomorrow, you'll receive:</b>\n"
                f"• Personalized questions at {self.display_time_12h(practice_time)}\n"
                f"• Friendly reminders at {self.display_time_12h(reminder_time)}\n"
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
        self.clear_user_busy(user_id)
        return ConversationHandler.END

    # --- Practice/Question/Stats (busy-guard not needed as they are single-action) ---

    async def question_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id in self.question_locks and self.question_locks[user_id].locked():
            await update.effective_message.reply_text("Please wait, fetching your question...")
            return
        async with self.question_locks.setdefault(user_id, asyncio.Lock()):
            try:
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
        user_id = update.effective_user.id
        question = self.current_questions.pop(user_id, None)
        if not question:
            await update.effective_message.reply_text("No active question found.")
            return
        self.firebase.update_question_status(user_id, question['Question'], "done")
        await update.effective_message.reply_text("Question marked as done!")

    async def missed_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        question = self.current_questions.pop(user_id, None)
        if not question:
            await update.effective_message.reply_text("No active question found.")
            return
        self.firebase.update_question_status(user_id, question['Question'], "missed")
        await update.effective_message.reply_text("Question marked as missed!")

    async def set_reminder_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    async def setreminder_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
     user_id = update.effective_user.id
     await update.effective_message.reply_text(
         "❌ Reminder setup cancelled. Your previous settings remain unchanged.\n"
         "Use /setreminder anytime to set up your schedule."
     )
     context.user_data.clear()
     self.clear_user_busy(user_id)
     return ConversationHandler.END

    def get_conversation_handler(self):
        return ConversationHandler(
            entry_points=[CommandHandler("setup", self.setup_start)],
            states={
                DIFFICULTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.setup_difficulty)],
                TOPIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.setup_topic)],
                COMPANY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.setup_company)],
            },
            fallbacks=[
                CommandHandler("cancel", self.setup_cancel),
                CommandHandler("exit", self.exit_command)
            ],
        )

    def get_reminder_conversation_handler(self):
        return ConversationHandler(
            entry_points=[
                CommandHandler("setreminder", self.setreminder_start),
                CallbackQueryHandler(self.setreminder_start, pattern="^setreminder_help$")
            ],
            states={
                PRACTICE_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.setreminder_practice_time)],
                DEADLINE_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.setreminder_deadline_time)],
                REMINDER_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.setreminder_reminder_time)],
            },
            fallbacks=[
                CommandHandler("cancel", self.setreminder_cancel),
                CommandHandler("exit", self.exit_command)
            ],
        )

    def get_handlers(self):
        handlers = [
            CommandHandler("start", self.start_command),
            CommandHandler("help", self.help_command),
            CommandHandler("question", self.question_command),
            CommandHandler("done", self.done_command),
            CommandHandler("missed", self.missed_command),
            CommandHandler("set_reminder", self.set_reminder_command),
            CommandHandler("exit", self.exit_command),
            CommandHandler("cancel", self.exit_command),
            CommandHandler("stats", self.stats_command),
            CallbackQueryHandler(self.handle_callback_query),
        ]
        return handlers

    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.data == "setup":
            await self.setup_start(update, context)
            return DIFFICULTY
        elif query.data == "next_question":
            await self.question_command(update, context)
        elif query.data == "stats":
            await self.stats_command(update, context)
        else:
            await query.message.reply_text(f"Callback query data: {query.data}")

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        try:
            data = self.firebase.get_user_data(user_id)
            tracking = self.firebase.get_user_tracking(user_id)
            streak = data.get("streak", 0)
            completed = 0
            missed = 0
            if tracking:
                for qdata in tracking.values():
                    if isinstance(qdata, dict):
                        if qdata.get("status") == "done":
                            completed += 1
                        elif qdata.get("status") == "missed":
                            missed += 1
            await update.effective_message.reply_html(
                f"📊 <b>Your Stats</b>\n\n"
                f"✅ Questions Completed: <b>{completed}</b>\n"
                f"❌ Missed: <b>{missed}</b>\n"
                f"🔥 Current Streak: <b>{streak}</b>\n"
                f"\n<i>Use /setup or /setreminder to update your routine!</i>"
            )
        except Exception as e:
            logger.error(f"Error in /stats: {e}", exc_info=True)
            await update.effective_message.reply_text("Could not fetch your stats, please try later.")

    # --- Schedulers (no change, as before) ---

    async def check_and_send_practice_questions(self, context):
        now_utc = datetime.utcnow().strftime("%H:%M")
        user_ids = self.firebase.get_users_with_practice_time(now_utc)
        for user_id in user_ids:
            try:
                last_question_sent_date = self.firebase.get_last_question_sent_date(user_id)
                today_date = datetime.utcnow().strftime("%Y-%m-%d")
                if last_question_sent_date == today_date:
                    logger.info(f"Question already sent today to user {user_id}, skipping.")
                    continue
                questions, error_message = await self.question_matcher.get_matching_questions(user_id)
                if error_message:
                    logger.error(f"Error fetching questions for user {user_id}: {error_message}")
                    continue
                if not questions:
                    logger.info(f"No matching questions found for user {user_id}")
                    continue
                question = random.choice(questions)
                try:
                    bot = context.bot
                    await bot.send_message(
                        user_id,
                        f"It's practice time!\nQuestion: {question['Question']}\nDifficulty: {question['Difficulty']}\nUse /done or /missed to mark your progress.",
                    )
                    self.current_questions[user_id] = question
                    self.firebase.update_question_status(user_id, question['Question'], "pending")
                    self.firebase.update_last_question_sent_date(user_id, today_date)
                    logger.info(f"Practice question sent to user {user_id} at {now_utc} UTC.")
                except Exception as e:
                    logger.error(f"Error sending question to user {user_id}: {e}")
            except Exception as e:
                logger.error(f"Error in practice question scheduler for user {user_id}: {e}")

    async def check_and_send_reminders(self, context):
        if self.is_reminder_running:
            logger.info("Reminder check is already running, skipping...")
            return
        self.is_reminder_running = True
        try:
            now_utc = datetime.utcnow().strftime("%H:%M")
            user_ids = self.firebase.get_users_with_reminder_time(now_utc)
            for user_id in user_ids:
                try:
                    last_reminder_sent_date = self.firebase.get_last_reminder_sent_date(user_id)
                    today_date = datetime.utcnow().strftime("%Y-%m-%d")
                    if last_reminder_sent_date == today_date:
                        logger.info(f"Reminder already sent today to user {user_id}, skipping.")
                        continue
                    question = self.current_questions.get(user_id)
                    if not question:
                        logger.info(f"No active question found for user {user_id}, skipping reminder.")
                        continue
                    try:
                        bot = context.bot
                        await bot.send_message(
                            user_id,
                            "Friendly reminder! Complete today's DSA question! Use /done or /missed to mark your progress.",
                        )
                        self.firebase.update_last_reminder_sent_date(user_id, today_date)
                        logger.info(f"Completion reminder sent to user {user_id} at {now_utc} UTC.")
                    except Exception as e:
                        logger.error(f"Error sending reminder to user {user_id}: {e}")
                except Exception as e:
                    logger.error(f"Error in reminder scheduler for user {user_id}: {e}")
        finally:
            self.is_reminder_running = False

    async def check_and_auto_mark_missed(self, context):
        if self.is_deadline_check_running:
            logger.info("Deadline check is already running, skipping...")
            return
        self.is_deadline_check_running = True
        try:
            now_utc = datetime.utcnow().strftime("%H:%M")
            user_ids = self.firebase.get_users_with_deadline_time(now_utc)
            for user_id in user_ids:
                try:
                    last_deadline_processed_date = self.firebase.get_last_deadline_processed_date(user_id)
                    today_date = datetime.utcnow().strftime("%Y-%m-%d")
                    if last_deadline_processed_date == today_date:
                        logger.info(f"Deadline already processed today for user {user_id}, skipping.")
                        continue
                    question = self.current_questions.pop(user_id, None)
                    if not question:
                        logger.info(f"No active question found for user {user_id}, skipping auto-marking.")
                        continue
                    try:
                        self.firebase.update_question_status(user_id, question['Question'], "missed")
                        logger.info(f"Question auto-marked as missed for user {user_id} at {now_utc} UTC.")
                        bot = context.bot
                        await bot.send_message(
                            user_id,
                            f"The deadline for today's question ({question['Question']}) has passed. It has been marked as missed.",
                        )
                        self.firebase.update_last_deadline_processed_date(user_id, today_date)
                    except Exception as e:
                        logger.error(f"Error auto-marking question as missed for user {user_id}: {e}")
                except Exception as e:
                    logger.error(f"Error in deadline scheduler for user {user_id}: {e}")
        finally:
            self.is_deadline_check_running = False