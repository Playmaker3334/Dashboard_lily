import logging
import os

# Create a directory for logs if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Basic logging configuration for file and console
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler("logs/app.log"),  # Save to file
        logging.StreamHandler()  # Also output to console
    ]
)
logger = logging.getLogger(__name__)
