import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for grant grading system"""
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # Google Sheets Configuration (OAuth2)
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_REFRESH_TOKEN = os.getenv('GOOGLE_REFRESH_TOKEN')
    MEDIA_SHEET_URL = os.getenv('MEDIA_SHEET_URL')
    BLOG_SHEET_URL = os.getenv('BLOG_SHEET_URL')
    
    # Extract sheet ID from URL
    def get_sheet_id(self, sheet_url):
        if sheet_url:
            # Extract sheet ID from various Google Sheets URL formats
            import re
            match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', sheet_url)
            return match.group(1) if match else None
        return None
    
    @property
    def MEDIA_SHEET_ID(self):
        return self.get_sheet_id(self.MEDIA_SHEET_URL)
    
    @property
    def BLOG_SHEET_ID(self):
        return self.get_sheet_id(self.BLOG_SHEET_URL)
    
    
    @classmethod
    def validate_config(cls, require_openai=True):
        """Validate that all required environment variables are set"""
        missing = []
        
        if require_openai and not cls.OPENAI_API_KEY:
            missing.append('OPENAI_API_KEY')
        if not cls.GOOGLE_CLIENT_ID:
            missing.append('GOOGLE_CLIENT_ID')
        if not cls.GOOGLE_CLIENT_SECRET:
            missing.append('GOOGLE_CLIENT_SECRET')
        if not cls.GOOGLE_REFRESH_TOKEN:
            missing.append('GOOGLE_REFRESH_TOKEN')
        if not cls.MEDIA_SHEET_URL:
            missing.append('MEDIA_SHEET_URL')
        if not cls.BLOG_SHEET_URL:
            missing.append('BLOG_SHEET_URL')
            
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        return True

# Create global config instance
config = Config() 