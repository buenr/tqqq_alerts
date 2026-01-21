import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Email Credentials
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
TO_EMAIL = "oninebuenr@yahoo.com"

# Trading Constants
TICKER_SYMBOL = "TQQQ"
SMA_WINDOW = 150

# TQQQ Dashboard Metrics
RET_WINDOW = 63      # 63-day return window
RSI_WINDOW = 21      # 21-day RSI window
