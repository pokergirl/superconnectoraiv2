from pydantic_settings import BaseSettings
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "superconnector")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    AI_API_KEY: str = os.getenv("AI_API_KEY", "")
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Gemini Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    
    GEMINI_EMBEDDING_MODEL: str = os.getenv("GEMINI_EMBEDDING_MODEL", "text-embedding-004")
    
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    
    # Pinecone Configuration
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "profile-embeddings")
    PINECONE_CLOUD: str = os.getenv("PINECONE_CLOUD", "aws")
    PINECONE_REGION: str = os.getenv("PINECONE_REGION", "us-east-1")
    
    # Email Configuration
    FROM_EMAIL: str = os.getenv("FROM_EMAIL", " ha@nextstepfwd.com")
    FROM_NAME: str = os.getenv("FROM_NAME", "Superconnector Team")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    # Email Service Selection
    EMAIL_SERVICE: str = os.getenv("EMAIL_SERVICE", "gmail_api")  # Options: "gmail_api", "smtp"
    
    # SMTP Configuration (for automated email sending)
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    
    # Gmail API Configuration
    GMAIL_CREDENTIALS_FILE: str = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
    GMAIL_TOKEN_FILE: str = os.getenv("GMAIL_TOKEN_FILE", "token.json")
    GMAIL_SCOPES: list = ['https://www.googleapis.com/auth/gmail.send']
    
    def validate_api_keys(self) -> dict:
        """
        Validate API keys and return status information.
        
        Returns:
            dict: Status of each API key validation
        """
        validation_results = {
            "gemini": {"configured": False, "valid": False, "error": None},
            "openai": {"configured": False, "valid": False, "error": None},
            "pinecone": {"configured": False, "valid": False, "error": None}
        }
        
        # Validate Gemini API Key
        if self.GEMINI_API_KEY:
            validation_results["gemini"]["configured"] = True
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.GEMINI_API_KEY)
                
                # Test with a simple request using the configured model
                model = genai.GenerativeModel(self.GEMINI_MODEL)
                response = model.generate_content("Hello")
                
                if response and response.text:
                    validation_results["gemini"]["valid"] = True
                    logger.info(f"✅ Gemini API key validation successful with model: {self.GEMINI_MODEL}")
                else:
                    validation_results["gemini"]["error"] = "Empty response from Gemini API"
                    logger.warning("⚠️ Gemini API key configured but returned empty response")
                    
            except Exception as e:
                validation_results["gemini"]["error"] = str(e)
                logger.error(f"❌ Gemini API key validation failed: {e}")
        else:
            logger.warning("⚠️ GEMINI_API_KEY not configured")
        
        # Validate OpenAI API Key
        if self.OPENAI_API_KEY:
            validation_results["openai"]["configured"] = True
            try:
                import openai
                client = openai.OpenAI(api_key=self.OPENAI_API_KEY)
                
                # Test with a simple request
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=5
                )
                
                if response and response.choices:
                    validation_results["openai"]["valid"] = True
                    logger.info("✅ OpenAI API key validation successful")
                else:
                    validation_results["openai"]["error"] = "Empty response from OpenAI API"
                    logger.warning("⚠️ OpenAI API key configured but returned empty response")
                    
            except Exception as e:
                validation_results["openai"]["error"] = str(e)
                logger.error(f"❌ OpenAI API key validation failed: {e}")
        else:
            logger.info("ℹ️ OpenAI API key not configured (optional)")
        
        # Validate Pinecone API Key
        if self.PINECONE_API_KEY:
            validation_results["pinecone"]["configured"] = True
            try:
                from pinecone import Pinecone
                pc = Pinecone(api_key=self.PINECONE_API_KEY)
                
                # Test connection by listing indexes
                indexes = pc.list_indexes()
                validation_results["pinecone"]["valid"] = True
                logger.info("✅ Pinecone API key validation successful")
                
            except Exception as e:
                validation_results["pinecone"]["error"] = str(e)
                logger.error(f"❌ Pinecone API key validation failed: {e}")
        else:
            logger.warning("⚠️ PINECONE_API_KEY not configured")
        
        return validation_results
    
    def log_startup_diagnostics(self):
        """
        Log startup diagnostics for API configurations.
        """
        logger.info("🚀 Starting API configuration diagnostics...")
        logger.info(f"📊 Gemini Model: {self.GEMINI_MODEL}")
        
        validation_results = self.validate_api_keys()
        
        # Summary
        configured_count = sum(1 for result in validation_results.values() if result["configured"])
        valid_count = sum(1 for result in validation_results.values() if result["valid"])
        
        logger.info(f"📈 API Keys Summary: {valid_count}/{configured_count} configured keys are valid")
        
        # Critical check for Gemini
        if not validation_results["gemini"]["valid"]:
            logger.error("🚨 CRITICAL: Gemini API is not working - AI features will be limited!")
        
        return validation_results

settings = Settings()
