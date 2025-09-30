import json
import re
from typing import List, Dict, Any
from app.core.config import settings
import google.generativeai as genai

async def search_connections(user_id: str, query: str, connections: List[dict]) -> List[dict]:
    # This is a placeholder for the actual AI search logic.
    # In a real application, you would use a more sophisticated search algorithm.
    
    # For now, we'll just filter by query terms in the description or headline.
    query_terms = query.lower().split()
    
    matching_connections = []
    for conn in connections:
        description = conn.get('description', '') or ''
        headline = conn.get('headline', '') or ''
        
        if any(term in description.lower() or term in headline.lower() for term in query_terms):
            matching_connections.append(conn)
            
    return matching_connections

async def generate_email_content(reason: str) -> str:
    """
    Generate email content using Gemini Pro.
    """
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not found in environment variables")

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(settings.GEMINI_GENERATION_MODEL)
        
        prompt = f"""You are a helpful assistant that writes professional outreach emails.

Write a professional outreach email for the following reason: {reason}

Please make the email:
- Professional and courteous
- Clear and concise
- Personalized and engaging
- Include a clear call to action
- Keep it under 200 words"""

        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error generating email content with Gemini ({settings.GEMINI_MODEL}): {e}")
        return "Error generating email content."