# telegram-diary-bot
AI-Powered Telegram Group Diary Bot
This is a Python-based Telegram bot that acts as an intelligent, evolving historian for a group chat. It silently listens to conversations, analyzes both text and images, and uses the Gemini AI to generate a daily diary entry summarizing the group's activities.

The bot is designed to be interactive and safe, featuring customizable AI personalities, a user feedback loop, and built-in content moderation to ensure a positive experience.

Key Features
Automatic Message Logging: Silently saves all text messages and photos sent in the group to a local SQLite database.

AI-Powered Diary Generation: Uses the Gemini API to read the chat history and generate a coherent, engaging diary entry with a single command (/diary_today).

Multimodal Analysis: The bot can analyze images sent in the chat and incorporate descriptions of them into the diary entries.

Admin-Controlled AI Personality: Group admins can use the /set_prompt command to choose from a pre-defined list of personalities (e.g., "Funny," "Pirate's Log," "Serious Historian") to change the tone of the diary.

User Feedback Loop: Any user can provide feedback on the diary with the /feedback command. The bot considers recent feedback when generating the next entry, allowing it to "learn" and adapt to the group's preferences.

Content Moderation: All user feedback is pre-screened using the ModerateContent API to prevent harmful or inappropriate content from being saved or sent to the AI.

Technology Stack
Backend: Python

Telegram API Wrapper: python-telegram-bot

Database: SQLite (managed with SQLAlchemy)

AI Language Model: Google Gemini API

Content Moderation: ModerateContent API

HTTP Requests: requests library

How to Run This Project Locally
Clone the repository.

Set up the environment:

Make sure you have Python 3.11+ installed.

Create a Python virtual environment: py -3.11 -m venv venv

Activate it: .\venv\Scripts\activate

Install dependencies:

pip install python-telegram-bot sqlalchemy requests

Get API Keys:

Create a bot with the BotFather on Telegram to get your TELEGRAM_TOKEN.

Get a GEMINI_API_KEY from Google AI Studio.

Get a free MODERATECONTENT_API_KEY from the ModerateContent website.

Configure the Bot:

Open main.py and fill in your three secret API keys at the top of the file.

Run the application:

python main.py

Set up in Telegram:

Add your bot to a group chat.

Promote the bot to be an administrator.

Use the BotFather's /setprivacy command to disable privacy mode for your bot.