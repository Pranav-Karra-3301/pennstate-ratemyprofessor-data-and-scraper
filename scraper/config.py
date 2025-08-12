"""
Configuration settings for Penn State RateMyProfessor scraper
"""

# Penn State University school ID on RateMyProfessors
PENN_STATE_SCHOOL_ID = 758

# URLs
BASE_RMP_URL = "https://www.ratemyprofessors.com"
PROFESSORS_SEARCH_URL = f"{BASE_RMP_URL}/search/professors/{PENN_STATE_SCHOOL_ID}?q=*"

# Scraping settings
BATCH_SIZE = 10  # For testing - process professors in small batches
MAX_RETRIES = 3
REQUEST_DELAY = 1  # Seconds between requests
PAGE_LOAD_TIMEOUT = 30  # Seconds

# Output settings
OUTPUT_DIR = "data"
PROFESSORS_FILE = f"{OUTPUT_DIR}/penn_state_professors.jsonl"
REVIEWS_FILE = f"{OUTPUT_DIR}/penn_state_reviews.jsonl"
COURSES_FILE = f"{OUTPUT_DIR}/penn_state_courses.jsonl"

# Chrome options for headless browsing
CHROME_OPTIONS = [
    "--headless",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-extensions",
    "--disable-logging",
    "--silent",
    "--log-level=3",
    "--disable-web-security",
    "--ignore-certificate-errors",
    "--ignore-ssl-errors",
    "--allow-running-insecure-content"
]
