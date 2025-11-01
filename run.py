"""
Application entry point.
"""

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app import create_app
from app.utils.logger import get_logger

logger = get_logger(__name__)

app = create_app()

if __name__ == '__main__':
    logger.info("Starting Flask application")
    app.run(host='0.0.0.0', port=5000, debug=False)
