import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def setup_environment():
    """
    Load environment variables from .env file and set up the application environment.
    Returns a dictionary with configuration settings.
    """
    # Load environment variables from .env file
    load_dotenv()

    # Check for API keys and set up config
    openai_api_key = os.getenv("OPENAI_API_KEY")
    google_api_key = os.getenv("GOOGLE_API_KEY")

    # Validate API keys
    if not openai_api_key:
        logger.warning(
            "OPENAI_API_KEY not set in environment. OpenAI-based agents will not work."
        )
    else:
        os.environ["OPENAI_API_KEY"] = openai_api_key
        logger.info("OpenAI API key configured.")

    if not google_api_key:
        logger.warning(
            "GOOGLE_API_KEY not set in environment. Google-based agents will not work."
        )
    else:
        os.environ["GOOGLE_API_KEY"] = google_api_key
        logger.info("Google API key configured.")

    # Database configuration
    db_config = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5433"),
        "user": os.getenv("DB_USER", "devuser"),
        "password": os.getenv("DB_PASSWORD", "devpassword"),
        "dbname": os.getenv("DB_NAME", "devdb"),
    }

    # Set log level
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logging.getLogger().setLevel(log_level)

    return {
        "openai_api_key": openai_api_key,
        "google_api_key": google_api_key,
        "db_config": db_config,
        "log_level": log_level,
    }
