import firebase_admin
from firebase_admin import credentials, firestore
import gspread
from google.oauth2.service_account import Credentials
import logging
from datetime import datetime, timedelta
import os
import json
import pytz
import dotenv
import random

dotenv.load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FirebaseManager:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirebaseManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not FirebaseManager._initialized:
            self._initialize_firebase()
            FirebaseManager._initialized = True

    def _initialize_firebase(self):
        try:
            if not firebase_admin._apps:
                creds_json = os.getenv('FIREBASE_CREDENTIALS')
                if creds_json:
                    cred_dict = json.loads(creds_json)
                    cred = credentials.Certificate(cred_dict)
                else:
                    cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH', 'serviceAccountKey.json')
                    if not os.path.exists(cred_path):
                        raise FileNotFoundError(f"Firebase credentials file not found at '{cred_path}'.")
                    cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
            self.db = firestore.client()
            logger.info("Firebase initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Firebase: {e}")
            raise RuntimeError(f"Error initializing Firebase: {e}")

    def get_user_prefs(self, user_id):
        try:
            user_ref = self.db.collection('users').document(str(user_id))
            doc = user_ref.get()
            return doc.to_dict().get('preferences', {}) if doc.exists else {}
        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            return {}

    def set_user_prefs(self, user_id, preferences):
        try:
            user_ref = self.db.collection('users').document(str(user_id))
            user_ref.set({'preferences': preferences}, merge=True)
            return True
        except Exception as e:
            logger.error(f"Error setting user preferences: {e}")
            return False

    def set_user_reminder_settings(self, user_id, settings):
        try:
            user_ref = self.db.collection('users').document(str(user_id))
            user_ref.set({
                'reminder_settings': settings,
                'last_updated': datetime.now().isoformat()
            }, merge=True)
            return True
        except Exception as e:
            logger.error(f"Error saving reminder settings for user {user_id}: {e}")
            return False

    def get_user_reminder_settings(self, user_id):
        try:
            user_ref = self.db.collection('users').document(str(user_id))
            doc = user_ref.get()
            return doc.to_dict().get('reminder_settings', {}) if doc.exists else {}
        except Exception as e:
            logger.error(f"Error getting reminder settings: {e}")
            return {}

    def get_users_with_practice_time(self, utc_time_str):
        try:
            users_ref = self.db.collection('users')
            query = users_ref.where('reminder_settings.practice_time_utc', '==', utc_time_str)
            docs = query.stream()
            return [doc.id for doc in docs]
        except Exception as e:
            logger.error(f"Error getting users for practice time {utc_time_str}: {e}")
            return []

    def get_users_with_reminder_time(self, utc_time_str):
        try:
            users_ref = self.db.collection('users')
            query = users_ref.where('reminder_settings.reminder_time_utc', '==', utc_time_str)
            docs = query.stream()
            return [doc.id for doc in docs]
        except Exception as e:
            logger.error(f"Error getting users for reminder time {utc_time_str}: {e}")
            return []

    def get_users_with_deadline_time(self, utc_time_str):
        try:
            users_ref = self.db.collection('users')
            query = users_ref.where('reminder_settings.deadline_time_utc', '==', utc_time_str)
            docs = query.stream()
            return [doc.id for doc in docs]
        except Exception as e:
            logger.error(f"Error getting users for deadline time {utc_time_str}: {e}")
            return []

    def get_last_question_sent_date(self, user_id):
        try:
            user_ref = self.db.collection('users').document(str(user_id))
            doc = user_ref.get()
            if doc.exists:
                data = doc.to_dict()
                return data.get('last_question_sent_date', '')
            return ''
        except Exception as e:
            logger.error(f"Error getting last question sent date for user {user_id}: {e}")
            return ''

    def update_last_question_sent_date(self, user_id, date_str):
        try:
            user_ref = self.db.collection('users').document(str(user_id))
            user_ref.set({
                'last_question_sent_date': date_str,
                'last_question_sent_timestamp': datetime.now().isoformat()
            }, merge=True)
            return True
        except Exception as e:
            logger.error(f"Error updating last question sent date for user {user_id}: {e}")
            return False

    def get_last_reminder_sent_date(self, user_id):
        try:
            user_ref = self.db.collection('users').document(str(user_id))
            doc = user_ref.get()
            if doc.exists:
                data = doc.to_dict()
                return data.get('last_reminder_sent_date', '')
            return ''
        except Exception as e:
            logger.error(f"Error getting last reminder sent date for user {user_id}: {e}")
            return ''

    def update_last_reminder_sent_date(self, user_id, date_str):
        try:
            user_ref = self.db.collection('users').document(str(user_id))
            user_ref.set({
                'last_reminder_sent_date': date_str,
                'last_reminder_sent_timestamp': datetime.now().isoformat()
            }, merge=True)
            return True
        except Exception as e:
            logger.error(f"Error updating last reminder sent date for user {user_id}: {e}")
            return False

    def get_last_deadline_processed_date(self, user_id):
        try:
            user_ref = self.db.collection('users').document(str(user_id))
            doc = user_ref.get()
            if doc.exists:
                data = doc.to_dict()
                return data.get('last_deadline_processed_date', '')
            return ''
        except Exception as e:
            logger.error(f"Error getting last deadline processed date for user {user_id}: {e}")
            return ''

    def update_last_deadline_processed_date(self, user_id, date_str):
        try:
            user_ref = self.db.collection('users').document(str(user_id))
            user_ref.set({
                'last_deadline_processed_date': date_str,
                'last_deadline_processed_timestamp': datetime.now().isoformat()
            }, merge=True)
            return True
        except Exception as e:
            logger.error(f"Error updating last deadline processed date for user {user_id}: {e}")
            return False

    def get_user_data(self, user_id):
        try:
            user_ref = self.db.collection('users').document(str(user_id))
            doc = user_ref.get()
            if doc.exists:
                return doc.to_dict()
            return {}
        except Exception as e:
            logger.error(f"Error getting user data for user {user_id}: {e}")
            return {}

    def get_user_tracking(self, user_id):
        try:
            tracking_ref = self.db.collection('user_tracking').document(str(user_id))
            doc = tracking_ref.get()
            if doc.exists:
                return doc.to_dict()
            return {}
        except Exception as e:
            logger.error(f"Error getting user tracking for {user_id}: {e}")
            return {}

    def update_question_status(self, user_id, question_title, status):
        try:
            tracking_ref = self.db.collection('user_tracking').document(str(user_id))
            safe_title = question_title.replace('.', '_').replace('/', '_')[:100]
            update_data = {
                safe_title: {
                    'status': status,
                    'timestamp': datetime.now().isoformat(),
                    'original_title': question_title
                }
            }
            tracking_ref.set(update_data, merge=True)
            return True
        except Exception as e:
            logger.error(f"Error updating question status for {user_id}: {e}")
            return False

    def get_completed_questions(self, user_id):
        try:
            tracking_data = self.get_user_tracking(user_id)
            completed_questions = []
            for question_key, question_data in tracking_data.items():
                if isinstance(question_data, dict):
                    status = question_data.get('status')
                    original_title = question_data.get('original_title', question_key)
                    if status in ['done', 'missed']:
                        completed_questions.append(original_title)
                elif question_data in ['done', 'missed']:
                    completed_questions.append(question_key)
            return completed_questions
        except Exception as e:
            logger.error(f"Error getting completed questions for {user_id}: {e}")
            return []

    def increment_streak(self, user_id):
        try:
            user_ref = self.db.collection('users').document(str(user_id))
            doc = user_ref.get()
            current_streak = 1
            if doc.exists:
                data = doc.to_dict()
                current_streak = data.get('streak', 0) + 1
            user_ref.set({
                'streak': current_streak,
                'last_streak_update': datetime.now().isoformat()
            }, merge=True)
            return current_streak
        except Exception as e:
            logger.error(f"Error incrementing streak for user {user_id}: {e}")
            return 1

    def reset_streak(self, user_id):
        try:
            user_ref = self.db.collection('users').document(str(user_id))
            user_ref.set({
                'streak': 0,
                'last_streak_update': datetime.now().isoformat(),
                'streak_reset_reason': 'missed_question'
            }, merge=True)
            return True
        except Exception as e:
            logger.error(f"Error resetting streak for user {user_id}: {e}")
            return False

    def get_user_streak(self, user_id):
        try:
            user_ref = self.db.collection('users').document(str(user_id))
            doc = user_ref.get()
            if doc.exists:
                data = doc.to_dict()
                return data.get('streak', 0)
            return 0
        except Exception as e:
            logger.error(f"Error getting streak for user {user_id}: {e}")
            return 0


class GoogleSheetsManager:
    def __init__(self):
        try:
            credentials_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
            creds_path = os.getenv('GOOGLE_SHEETS_CREDENTIALS_PATH', 'google-cloud-service-creds-for-sheets.json')
            sheet_name = os.getenv('GSHEET_NAME', "Copy of DSA by Shradha Ma'am")
            sheet_tab = os.getenv('GSHEET_TAB', "DSA in 2.5 Months")
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets.readonly',
                'https://www.googleapis.com/auth/drive.readonly'
            ]
            if credentials_json:
                creds_info = json.loads(credentials_json)
                self.creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
            elif os.path.exists(creds_path):
                self.creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
            else:
                raise FileNotFoundError("Google Sheets credentials not found in env or file.")

            self.gc = gspread.authorize(self.creds)
            self.sheet = self.gc.open(sheet_name).worksheet(sheet_tab)
            logger.info(f"Google Sheets initialized successfully: {sheet_name} - {sheet_tab}")
        except Exception as e:
            logger.error(f"Error initializing Google Sheets: {e}")
            raise RuntimeError(f"Error initializing Google Sheets: {e}")

    def fetch_questions(self):
        try:
            records = self.sheet.get_all_records()
            questions = []
            for row in records:
                questions.append({
                    "Topics": row.get("Topics", ""),
                    "Question": row.get("Question (375)", row.get("Question", "")),
                    "Companies": row.get("Companies", ""),
                    "Difficulty": row.get("Difficulty", ""),
                })
            valid_questions = [q for q in questions if q["Question"] and q["Difficulty"] and q["Topics"]]
            logger.info(f"Fetched {len(valid_questions)} valid DSA questions")
            return valid_questions
        except Exception as e:
            logger.error(f"Error fetching questions: {e}")
            return []

class DSAQuestionMatcher:
    def __init__(self, firebase_manager=None, google_sheets_manager=None):
        self.firebase = firebase_manager if firebase_manager else FirebaseManager()
        self.sheets = google_sheets_manager if google_sheets_manager else GoogleSheetsManager()
        self.questions_cache = None
        self.cache_timestamp = None
        self.cache_duration = 3600  # 1 hour

    def _is_cache_valid(self):
        if not self.questions_cache or not self.cache_timestamp:
            return False
        current_time = datetime.now()
        return (current_time - self.cache_timestamp).total_seconds() < self.cache_duration

    def get_all_questions(self):
        if not self._is_cache_valid():
            self.questions_cache = self.sheets.fetch_questions()
            self.cache_timestamp = datetime.now()
        return self.questions_cache

    async def get_matching_questions(self, user_id):
        try:
            user_prefs = self.firebase.get_user_prefs(user_id)
            if not user_prefs:
                return [], "No preferences set. Use /setup to set your preferences."
            all_questions = self.get_all_questions()
            if not all_questions:
                return [], "No questions available. Please try again later."
            completed_questions = self.firebase.get_completed_questions(user_id)
            filtered_questions = []
            for question in all_questions:
                question_title = question.get('Question', '')
                if question_title in completed_questions:
                    continue
                difficulty_prefs = user_prefs.get('difficulty', [])
                if 'Random' not in difficulty_prefs:
                    question_difficulty = question.get('Difficulty', '')
                    if question_difficulty not in difficulty_prefs:
                        continue
                topic_prefs = user_prefs.get('topic', [])
                if 'Random' not in topic_prefs:
                    question_topics = question.get('Topics', '')
                    topic_match = any(topic.strip().lower() in question_topics.lower() for topic in topic_prefs)
                    if not topic_match:
                        continue
                company_prefs = user_prefs.get('company', [])
                if 'Random' not in company_prefs and 'No preference' not in company_prefs:
                    question_companies = question.get('Companies', '')
                    company_match = any(company.strip().lower() in question_companies.lower() for company in company_prefs)
                    if not company_match:
                        continue
                filtered_questions.append(question)
            if not filtered_questions:
                return [], "No matching questions found based on your preferences, or all questions completed."
            return filtered_questions, None
        except Exception as e:
            logger.error(f"Error getting matching questions for user {user_id}: {e}")
            return [], f"Error retrieving questions: {str(e)}"