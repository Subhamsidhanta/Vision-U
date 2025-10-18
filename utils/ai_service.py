"""
AI service utilities for Vision U
Enhanced with caching, rate limiting, and error handling
"""
import time
import logging
import hashlib
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

import google.generativeai as genai
from flask import current_app, session

from utils.performance import cached, performance_monitor, cache

logger = logging.getLogger(__name__)

class AIService:
    """Enhanced AI service with caching and rate limiting"""
    
    def __init__(self, api_key: str, model_name: str = 'gemini-2.5-flash'):
        self.api_key = api_key
        self.model_name = model_name
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize Gemini model"""
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            logger.info(f"AI model {self.model_name} initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AI model: {e}")
            raise
    
    def _generate_cache_key(self, user_data: Dict[str, Any], prompt: str) -> str:
        """Generate cache key for AI responses"""
        # Create a hash of the input data
        data_string = f"{user_data.get('name', '')}-{user_data.get('age', '')}-" \
                     f"{user_data.get('education', '')}-{user_data.get('interest', '')}-" \
                     f"{user_data.get('hobby', '')}-{prompt}"
        return hashlib.md5(data_string.encode()).hexdigest()
    
    def _create_career_prompt(self, user_data: Dict[str, Any], goal: str) -> str:
        """Create structured prompt for career guidance"""
        return f"""
You are an expert student career counselor with 15+ years of experience.
Your task: Provide a **personalized, actionable career guide** for the student.

**Student Profile**:
- Name: {user_data.get('name', 'Student')}
- Age: {user_data.get('age', 'Not specified')}
- Education: {user_data.get('education', 'Not specified')}
- Interests: {user_data.get('interest', 'Not specified')}
- Hobbies: {user_data.get('hobby', 'Not specified')}
- Career Goal: "{goal}"

**Required Output Format** (Markdown):

# Personalized Career Guide for {user_data.get('name', 'Student')}

## 🎯 Executive Summary
- **Best Fit Career**: [Primary recommendation]
- **Success Probability**: [High/Medium based on profile]
- **Timeline to Goal**: [Realistic timeframe]

## 📊 Top 3 Career Recommendations

### 1. [Career Path Name]
- **Why Perfect Fit**: [1-2 lines explaining alignment with interests/skills]
- **Role Description**: [2-3 lines about typical responsibilities]
- **Required Skills**: 
  • [Skill 1] • [Skill 2] • [Skill 3]
- **Learning Path**:
  1. [Immediate step - course/certification]
  2. [Medium-term goal - project/internship]
  3. [Long-term milestone - degree/experience]
- **Salary Range**: [Entry level - Experienced level]
- **Industry Demand**: [High/Growing/Stable with brief explanation]

### 2. [Alternative Career Path]
[Same format as above]

### 3. [Backup Option]
[Same format as above]

## 🚀 Immediate Action Plan (Next 30 Days)
1. **Week 1**: [Specific action]
2. **Week 2**: [Specific action]
3. **Week 3**: [Specific action]
4. **Week 4**: [Specific action]

## 📚 Recommended Resources
- **Online Courses**: [2-3 specific recommendations]
- **Books**: [2 relevant books]
- **Communities**: [Professional groups/forums]
- **Mentorship**: [Where to find mentors]

## ⚠️ Potential Challenges & Solutions
- **Challenge 1**: [Issue] → **Solution**: [How to overcome]
- **Challenge 2**: [Issue] → **Solution**: [How to overcome]

**Remember**: Success comes from consistent action. Start with small steps today! 🌟

**CRITICAL REQUIREMENTS**:
- Keep each section concise but actionable
- Use bullet points and numbered lists
- Include specific, searchable course/resource names
- Make recommendations age-appropriate
- Focus on practical, achievable steps
"""
    
    @cached(ttl=3600, namespace="ai_responses")  # Cache for 1 hour
    @performance_monitor
    def generate_career_guidance(self, user_data: Dict[str, Any], goal: str) -> Tuple[str, Dict[str, Any]]:
        """
        Generate career guidance with caching and monitoring
        
        Returns:
            Tuple of (response_text, metadata)
        """
        if not self.model:
            raise RuntimeError("AI model not initialized")
        
        start_time = time.time()
        
        try:
            prompt = self._create_career_prompt(user_data, goal)
            
            # Generate response with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = self.model.generate_content(prompt)
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"AI generation attempt {attempt + 1} failed: {e}")
                    time.sleep(2 ** attempt)  # Exponential backoff
            
            end_time = time.time()
            
            # Prepare metadata
            metadata = {
                'response_time': end_time - start_time,
                'model_used': self.model_name,
                'prompt_length': len(prompt),
                'response_length': len(response.text) if response.text else 0,
                'user_age': user_data.get('age'),
                'timestamp': datetime.utcnow().isoformat(),
                'cache_hit': False  # Will be set to True by caching decorator if cached
            }
            
            logger.info(f"AI response generated in {metadata['response_time']:.2f}s")
            
            return response.text.strip(), metadata
            
        except Exception as e:
            logger.error(f"AI generation failed: {e}")
            raise

    def check_rate_limit(self, user_id: Optional[int] = None, ip_address: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if user/IP has exceeded rate limits
        
        Returns:
            Tuple of (is_allowed, limit_info)
        """
        if not cache:
            return True, {}
        
        current_time = datetime.utcnow()
        hour_key = current_time.strftime('%Y%m%d%H')
        
        # Check user-based rate limit (if logged in)
        if user_id:
            user_key = f"rate_limit:user:{user_id}:{hour_key}"
            user_requests = cache.get(user_key, "rate_limits") or 0
            
            if user_requests >= 10:  # 10 requests per hour for logged-in users
                return False, {
                    'limit_type': 'user',
                    'limit': 10,
                    'current': user_requests,
                    'reset_time': (current_time + timedelta(hours=1)).isoformat()
                }
            
            # Increment counter
            cache.set(user_key, user_requests + 1, ttl=3600, namespace="rate_limits")
        
        # Check IP-based rate limit
        if ip_address:
            ip_key = f"rate_limit:ip:{ip_address}:{hour_key}"
            ip_requests = cache.get(ip_key, "rate_limits") or 0
            
            if ip_requests >= 5:  # 5 requests per hour for anonymous users
                return False, {
                    'limit_type': 'ip',
                    'limit': 5,
                    'current': ip_requests,
                    'reset_time': (current_time + timedelta(hours=1)).isoformat()
                }
            
            # Increment counter
            cache.set(ip_key, ip_requests + 1, ttl=3600, namespace="rate_limits")
        
        return True, {}

    def get_usage_stats(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get AI usage statistics"""
        if not cache:
            return {}
        
        current_time = datetime.utcnow()
        hour_key = current_time.strftime('%Y%m%d%H')
        day_key = current_time.strftime('%Y%m%d')
        
        stats = {
            'current_hour': current_time.strftime('%H:00'),
            'current_date': current_time.strftime('%Y-%m-%d')
        }
        
        if user_id:
            user_hour_key = f"rate_limit:user:{user_id}:{hour_key}"
            user_day_key = f"usage_stats:user:{user_id}:{day_key}"
            
            stats.update({
                'user_requests_this_hour': cache.get(user_hour_key, "rate_limits") or 0,
                'user_requests_today': cache.get(user_day_key, "usage_stats") or 0
            })
        
        return stats

# Global AI service instance
ai_service = None

def init_ai_service(app) -> AIService:
    """Initialize AI service with app config"""
    global ai_service
    api_key = app.config.get('API_KEY')
    
    if not api_key:
        logger.warning("No API key configured for AI service")
        return None
    
    try:
        ai_service = AIService(api_key)
        logger.info("AI service initialized successfully")
        return ai_service
    except Exception as e:
        logger.error(f"Failed to initialize AI service: {e}")
        return None

def generate_enhanced_career_guidance(user_data: Dict[str, Any], goal: str) -> Tuple[str, Dict[str, Any]]:
    """
    Main function to generate career guidance with all enhancements
    """
    if not ai_service:
        raise RuntimeError("AI service not initialized")
    
    user_id = session.get('user_id')
    ip_address = None  # Would be passed from request context
    
    # Check rate limits
    is_allowed, limit_info = ai_service.check_rate_limit(user_id, ip_address)
    if not is_allowed:
        raise RuntimeError(f"Rate limit exceeded: {limit_info}")
    
    # Generate guidance
    response_text, metadata = ai_service.generate_career_guidance(user_data, goal)
    
    # Add usage stats to metadata
    metadata['usage_stats'] = ai_service.get_usage_stats(user_id)
    
    return response_text, metadata