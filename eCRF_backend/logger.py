import logging
import os
from datetime import datetime

# Create 'logs' directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Generate log file name with current date and time
log_filename = datetime.now().strftime("logs/%Y-%m-%d_%H-%M-%S_logs.log")

# Create a custom logger
logger = logging.getLogger("eCRF_backend")

# Set the default logging level
logger.setLevel(logging.DEBUG)

# Create handlers
console_handler = logging.StreamHandler()  # Logs to console
file_handler = logging.FileHandler(log_filename)  # Logs to dynamically named file

console_handler.setLevel(logging.INFO)
file_handler.setLevel(logging.DEBUG)

# Create formatters and add to handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)
