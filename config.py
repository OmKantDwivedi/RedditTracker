import os
from dotenv import load_dotenv

load_dotenv()

# Reddit API credentials
REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')
REDDIT_USER_AGENT = os.getenv('REDDIT_USER_AGENT', 'CommentTracker/1.0')

# Google Sheets credentials (optional)
GOOGLE_CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')

# Database
DB_PATH = 'comment_tracker.db'

# Tracking settings
TOP_N_COMMENTS = 5
REPLY_WINDOW_HOURS = 72

# Output
OUTPUT_COLUMNS = ['URL', 'Status', 'Present Rank', 'Previous Rank']
