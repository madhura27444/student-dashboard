import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-student-academic-progression-secret-2026')
    
    # Database Configuration
    # Supports MySQL/TiDB Cloud: mysql://user:password@host:port/database?ssl_ca=...
    # Or fallback to SQLite when DB_TYPE is 'sqlite' or no MYSQL vars provided
    DB_TYPE = os.environ.get('DB_TYPE', 'sqlite')  # 'mysql' or 'sqlite'
    
    # MySQL / TiDB Cloud parameters
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = int(os.environ.get('DB_PORT', 3306))
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
    DB_NAME = os.environ.get('DB_NAME', 'student_progression_db')
    DB_SSL_CA = os.environ.get('DB_SSL_CA', '')  # Path or 'system' for TiDB cloud SSL
    
    # SQLite file path
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLITE_PATH = os.environ.get('SQLITE_PATH', os.path.join(BASE_DIR, 'student_progression.db'))
    
    # Google Sheets Webhook Configuration
    GOOGLE_SHEETS_WEBHOOK_URL = os.environ.get('GOOGLE_SHEETS_WEBHOOK_URL', '')
    GOOGLE_SHEETS_SECRET_TOKEN = os.environ.get('GOOGLE_SHEETS_SECRET_TOKEN', 'madhura-academic-sync-token-2026')
    GOOGLE_SHEET_URL = os.environ.get('GOOGLE_SHEET_URL', 'https://docs.google.com/spreadsheets/d/10vNUm7xkIFV43axJF2nbKnTb_jY-1vGxx1d1AsjCu50/edit')
    GOOGLE_SPREADSHEET_ID = os.environ.get('GOOGLE_SPREADSHEET_ID', '10vNUm7xkIFV43axJF2nbKnTb_jY-1vGxx1d1AsjCu50')
    
    # Academic grading constants
    GRADING_SYSTEM = {
        'O': {'min': 90, 'gp': 10, 'desc': 'Outstanding'},
        'A+': {'min': 80, 'gp': 9, 'desc': 'Excellent'},
        'A': {'min': 70, 'gp': 8, 'desc': 'Very Good'},
        'B+': {'min': 60, 'gp': 7, 'desc': 'Good'},
        'B': {'min': 55, 'gp': 6, 'desc': 'Above Average'},
        'C': {'min': 50, 'gp': 5, 'desc': 'Average'},
        'P': {'min': 40, 'gp': 4, 'desc': 'Pass'},
        'F': {'min': 0, 'gp': 0, 'desc': 'Fail'}
    }
