# DSA Mentor Telegram Bot 🤖

A Telegram bot built using Python and the Telegram Bot API to help users learn Data Structures and Algorithms (DSA). This bot serves as an interactive DSA mentor and is designed with a simple command-based interface to guide users through key concepts, schedule reminders, and track your progress.

---

## ✨ Features

* 📚 **Personalized Practice**: Deliver questions based on user-selected difficulty, topics, and companies.
* ⏰ **Smart Scheduling**: Set practice time, reminder time, and deadline time for daily questions.
* 🔄 **Progress Tracking**: Mark questions as done or missed; view streaks and stats.
* 🤖 **Real-Time Interaction**: Instant commands for onboarding, help, questions, and stats.
* 🛠️ **Tech Stack**: Python, python-telegram-bot, Firebase, Google Sheets.

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/zyna-b/DSA-Mentor-Telegram-Bot.git
cd DSA-Mentor-Telegram-Bot
```

### 2. Set up environment

Create and activate a virtual environment (recommended):

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the project root with:

```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
FIREBASE_CREDENTIALS_PATH=path/to/firebase_credentials.json
GOOGLE_SHEETS_ID=your_google_sheets_id
```

### 4. Run the bot

```bash
python bot.py
```

---

## 🗂 Project Structure

```
DSA-Mentor-Telegram-Bot/
├── bot.py                  # Entry point and dispatcher setup
├── handlers.py             # DSABotHandlers class and all command handlers
├── models/                 # Business logic and integrations
│   ├── FirebaseManager.py  # Firebase CRUD operations
│   ├── GoogleSheetsManager.py # Google Sheets data fetch
│   └── DSAQuestionMatcher.py   # Logic to match questions from Sheets to user
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (gitignored)
└── README.md               # Project documentation
```

---

## 🤖 Available Commands

| Command         | Description                                                              |
| --------------- | ------------------------------------------------------------------------ |
| `/start`        | Welcome message and status check                                         |
| `/help`         | Show help guide with available actions                                   |
| `/setup`        | Configure or update practice preferences (difficulty, topics, companies) |
| `/setreminder`  | Set up or modify daily schedule (practice, reminder, deadline)           |
| `/question`     | Fetch a new DSA question based on your preferences                       |
| `/done`         | Mark the current question as completed                                   |
| `/missed`       | Mark the current question as missed                                      |
| `/stats`        | Display your performance statistics and streaks                          |
| `/set_reminder` | Quick set reminder time using `HH:MM` UTC format                         |
| `/exit`         | Cancel any ongoing multi-step operation                                  |
| `/cancel`       | Alias for `/exit`, cancel current operation                              |

---

## 🎯 Usage Example

1. **Onboarding**: `/start` → `/setup` → select difficulty, topics, companies.
2. **Schedule**: `/setreminder` → enter practice time (e.g., "9:00 AM"), deadline ("8:00 PM"), and reminder ("5:00 PM").
3. **Daily Practice**: At practice time, bot sends question. Mark with `/done` or `/missed`.
4. **Stats**: `/stats` to view completed count and streak.

---

## 🙌 Contributing

Contributions are welcome! Feel free to:

* Add new DSA topic commands or improve explanations
* Enhance scheduling or reminder logic
* Refactor code for better modularity

Please fork the repo, make your changes, and open a pull request.

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## 🌐 Links

* **Repository**: [https://github.com/zyna-b/DSA-Mentor-Telegram-Bot](https://github.com/zyna-b/DSA-Mentor-Telegram-Bot)
* **Contact**: [zainabhamid2468@gmail.com](mailto:zainabhamid2468@gmail.com)
