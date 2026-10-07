import os
from dotenv import load_dotenv

load_dotenv()

# External API key
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

# AI availability flag — False when no key is configured
AI_AVAILABLE: bool = bool(GROQ_API_KEY)

# Matching algorithm constants
TIME_TOLERANCE_MIN: int = 90       # minutes window for grouping requests
DEST_MATCH_KM: float = 5.0         # km radius to consider destinations the same
ORIGIN_RADIUS_KM: float = 10.0     # km radius to cluster pickup origins
GROUP_SCORE_THRESHOLD: float = 0.55 # minimum score to form a valid group
