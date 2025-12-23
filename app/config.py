from dotenv import load_dotenv
import os


def load_env():
    load_dotenv()
    # Expose common settings via os.environ
    return {
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
        "GEMINI_ENDPOINT": os.getenv("GEMINI_ENDPOINT"),
    }
