import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database configuration
HOST = os.getenv('DB_HOST')
USER = os.getenv('DB_USER')
PASSWORD = os.getenv('DB_PASSWORD')
DATABASE = os.getenv('DB_NAME')
SSL_CA = os.getenv('DB_SSL_CA')  # Añadir la variable para el certificado SSL

# Server configuration
SERVER_IP = os.getenv('SERVER_IP', '0.0.0.0')

