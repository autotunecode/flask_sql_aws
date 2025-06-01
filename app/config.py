import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database settings
    DB_HOST = os.getenv('DB_HOST', 'postgres')
    POSTGRES_DB = os.getenv('POSTGRES_DB', 'imagedb')
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'postgres')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'password')
    DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{DB_HOST}:5432/{POSTGRES_DB}"
    
    # MinIO/S3 settings
    MINIO_ENDPOINT_URL = os.getenv('MINIO_ENDPOINT_URL', 'http://minio:9000')
    MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
    MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
    MINIO_BUCKET_NAME = os.getenv('MINIO_BUCKET_NAME', 'images')
    
    # API settings
    API_KEY = os.getenv('API_KEY', 'your-secret-api-key-here')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB
    
    # Gemini API (optional)
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    
    # Development mode
    DEVELOPMENT_MODE = os.getenv('DEVELOPMENT_MODE', 'false').lower() == 'true' 