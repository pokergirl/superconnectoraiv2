import json
import re
from typing import List, Dict, Any
from anthropic import Anthropic
from app.core.config import settings

client = Anthropic(api_key=settings.AI_API_KEY)

def fallback_search(user_query: str, connections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enhanced fallback search with location and follower analysis
    """
    query_lower = user_query.lower()
    query_words = re.findall(r'\b\w+\b', query_lower)
    
    # Extract numeric criteria (follower counts, etc.)
    import re as regex
    follower_numbers = regex.findall(r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:k|thousand|m|million)?', query_lower)
    has_follower_criteria = any(word in query_lower for word in ['follower', 'followers', 'following'])
    
    results = []
    
    for conn in connections:
        # Convert MongoDB document to JSON-serializable dict
        clean_conn = {}
        for key, value in conn.items():
            if key == "_id":
                clean_conn["id"] = str(value)
            else:
                clean_conn[key] = value
        
        score = 0
        matched_fields = []
        
        # Enhanced fields with location and followers
        search_fields = {
            'title': 4,
            'company': 4,
            'company_industry': 3,
            'description': 2,
            'city': 2,
            'state': 2,
            'country': 2,
            'first_name': 1,
            'last_name': 1,
            'followers': 1
        }
        
        # Standard text matching
        for field, weight in search_fields.items():
            field_value = str(clean_conn.get(field, '')).lower()
            if field_value:
                # Check for exact phrase match
                if query_lower in field_value:
                    score += weight * 2
                    matched_fields.append(field)
                
                # Check for individual word matches
                for word in query_words:
                    if len(word) >= 3 and word in field_value:
                        score += weight
                        if field not in matched_fields:
                            matched_fields.append(field)
        
        # Enhanced follower count matching
        if has_follower_criteria and clean_conn.get('followers'):
            follower_str = str(clean_conn.get('followers', ''))
            try:
                # Parse follower count (handle K, M suffixes)
                follower_count = 0
                if 'k' in follower_str.lower():
                    follower_count = float(follower_str.lower().replace('k', '').replace(',', '')) * 1000
                elif 'm' in follower_str.lower():
                    follower_count = float(follower_str.lower().replace('m', '').replace(',', '')) * 1000000
                else:
                    follower_count = float(follower_str.replace(',', ''))
                
                # Check against criteria in query
                for num_str in follower_numbers:
                    query_num = float(num_str.replace(',', ''))
                    if 'k' in query_lower or 'thousand' in query_lower:
                        query_num *= 1000
                    elif 'm' in query_lower or 'million' in query_lower:
                        query_num *= 1000000
                    
                    if follower_count >= query_num:
                        score += 6  # High score for meeting follower criteria
                        matched_fields.append('followers')
                        break
                        
            except (ValueError, TypeError):
                pass
        
        # Location-specific scoring
        location_terms = ['san francisco', 'sf', 'bay area', 'silicon valley', 'palo alto', 'mountain view',
                         'san mateo', 'menlo park', 'redwood city', 'new york', 'nyc', 'manhattan',
                         'brooklyn', 'los angeles', 'la', 'seattle', 'boston', 'austin', 'chicago']
        
        for location in location_terms:
            if location in query_lower:
                city = str(clean_conn.get('city', '')).lower()
                state = str(clean_conn.get('state', '')).lower()
                country = str(clean_conn.get('country', '')).lower()
                
                full_location = f"{city} {state} {country}"
                if location in full_location or any(loc in full_location for loc in location.split()):
                    score += 3
                    matched_fields.append('location')
                    break
        
        if score >= 3:  # Minimum score threshold
            # Generate enhanced summary
            summary_parts = []
            if 'title' in matched_fields:
                summary_parts.append(f"role: {clean_conn.get('title', '')}")
            if 'company' in matched_fields:
                summary_parts.append(f"company: {clean_conn.get('company', '')}")
            if 'company_industry' in matched_fields:
                summary_parts.append(f"industry: {clean_conn.get('company_industry', '')}")
            if 'location' in matched_fields:
                location_str = ', '.join(filter(None, [clean_conn.get('city'), clean_conn.get('state')]))
                summary_parts.append(f"location: {location_str}")
            if 'followers' in matched_fields:
                summary_parts.append(f"followers: {clean_conn.get('followers', '')}")
            
            summary = f"Matches your criteria: {', '.join(summary_parts[:3])}" if summary_parts else "Relevant match found"
            
            # Enhanced pros and cons
            pros = []
            cons = []
            
            if 'title' in matched_fields:
                pros.append(f"Job title matches: {clean_conn.get('title', '')}")
            if 'company' in matched_fields:
                pros.append(f"Company relevance: {clean_conn.get('company', '')}")
            if 'company_industry' in matched_fields:
                pros.append(f"Industry alignment: {clean_conn.get('company_industry', '')}")
            if 'location' in matched_fields:
                location_str = ', '.join(filter(None, [clean_conn.get('city'), clean_conn.get('state')]))
                pros.append(f"Located in target area: {location_str}")
            if 'followers' in matched_fields:
                pros.append(f"Meets follower criteria: {clean_conn.get('followers', '')} followers")
            
            if not pros:
                pros.append("Basic keyword match found")
            
            # Enhanced cons
            if score < 8:
                cons.append("Partial keyword matching")
            if has_follower_criteria and 'followers' not in matched_fields:
                cons.append("Follower count may not meet criteria")
            if not clean_conn.get('company_industry'):
                cons.append("Industry information not available")
            if not clean_conn.get('city'):
                cons.append("Location information not available")
            if not cons:
                cons.append("None relevant")
            
            results.append({
                "connection": clean_conn,
                "score": min(10, max(1, score)),
                "summary": summary,
                "pros": pros,
                "cons": cons
            })
    
    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    
    return results[:20]  # Return top 20 results

async def search_connections(user_query: str, connections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Use Claude to analyze and rank connections based on the user's query
    """
    print(f"Search query: {user_query}")
    print(f"Number of connections to search: {len(connections)}")
    
    # If too many connections, use fallback search to avoid token limits
    if len(connections) > 100:
        print("Too many connections for AI analysis, using fallback search...")
        return fallback_search(user_query, connections)
    
    # Prepare the connection data for the AI with indexed references
    connection_data = []
    connection_lookup = {}  # Index -> actual connection
    
    for i, conn in enumerate(connections):
        # Convert MongoDB document to clean dict
        clean_conn = {}
        for key, value in conn.items():
            if key == "_id":
                clean_conn["id"] = str(value)
            else:
                clean_conn[key] = value
        
        # Use simple index instead of complex ID
        connection_data.append({
            "index": i,
            "first_name": clean_conn.get("first_name", ""),
            "last_name": clean_conn.get("last_name", ""),
            "email_address": clean_conn.get("email_address", ""),
            "company": clean_conn.get("company", ""),
            "title": clean_conn.get("title", ""),
            "company_industry": clean_conn.get("company_industry", ""),
            "city": clean_conn.get("city", ""),
            "state": clean_conn.get("state", ""),
            "country": clean_conn.get("country", ""),
            "description": clean_conn.get("description", ""),
            "followers": clean_conn.get("followers", ""),
            "company_size": clean_conn.get("company_size", ""),
            "connected_on": clean_conn.get("connected_on", "")
        })
        
        # Store the clean connection for later lookup
        connection_lookup[i] = clean_conn
    
    print(f"Prepared {len(connection_data)} connections for AI analysis")
    
    # Create the prompt for Claude
    prompt = f"""
You are an AI assistant helping someone find the most relevant professional connections from their network.

USER QUERY: "{user_query}"

CONNECTION DATA:
{json.dumps(connection_data, indent=2)}

Please analyze each connection and return a JSON array of the most relevant ones. For each relevant connection, provide:
1. The index (use the "index" field from the data)
2. A relevance score from 1-10 (10 being most relevant)
3. A brief summary explaining why this connection is relevant to the query
4. Pros: List of reasons why this may be a good match (2-4 bullet points)
5. Cons: List of reasons why this may not be a good match (1-3 bullet points)

Only return connections with a score of 6 or higher. Return the results in JSON format like this:
[
  {{
    "index": 0,
    "score": 8,
    "summary": "Brief explanation of relevance",
    "pros": [
      "Specific reason why this is a good match",
      "Another positive aspect"
    ],
    "cons": [
      "Potential limitation or concern",
      "Another reason why it might not be perfect"
    ]
  }}
]

Focus on matching:
- Job titles and roles
- Company names and industries
- Skills and expertise areas
- Professional backgrounds
- Investment focus and stage preferences
- Geographic location and market focus

Return only the JSON array, no other text.
"""

    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            temperature=0.3,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        # Parse the AI response
        ai_response = response.content[0].text.strip()
        print(f"Claude AI Response: {ai_response}")
        
        # Try to parse as JSON
        try:
            search_results = json.loads(ai_response)
            print(f"Parsed search results: {search_results}")
        except json.JSONDecodeError:
            print(f"JSON parsing failed, trying to extract...")
            # If JSON parsing fails, try to extract JSON from the response
            start_idx = ai_response.find('[')
            end_idx = ai_response.rfind(']') + 1
            if start_idx != -1 and end_idx != 0:
                json_str = ai_response[start_idx:end_idx]
                search_results = json.loads(json_str)
            else:
                return []
        
        # Validate and enrich the results
        enriched_results = []
        for result in search_results:
            if not isinstance(result, dict):
                continue
                
            index = result.get("index")
            score = result.get("score", 0)
            summary = result.get("summary", "")
            pros = result.get("pros", [])
            cons = result.get("cons", [])
            
            # Look up the connection using the index
            if index is not None and index in connection_lookup and score >= 6:
                matching_connection = connection_lookup[index]
                enriched_results.append({
                    "connection": matching_connection,
                    "score": min(10, max(1, int(score))),  # Ensure score is between 1-10
                    "summary": summary,
                    "pros": pros if isinstance(pros, list) else [],
                    "cons": cons if isinstance(cons, list) else []
                })
        
        # Sort by score descending
        enriched_results.sort(key=lambda x: x["score"], reverse=True)
        
        print(f"Final enriched results count: {len(enriched_results)}")
        print(f"Sample enriched result: {enriched_results[0] if enriched_results else 'None'}")
        
        return enriched_results
        
    except Exception as e:
        print(f"AI Service Error: {e}")
        # If AI fails (e.g., invalid API key), fall back to basic text search
        print("Falling back to basic text search...")
        return fallback_search(user_query, connections)