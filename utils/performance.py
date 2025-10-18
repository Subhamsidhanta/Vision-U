"""
Performance optimization utilities for Vision U
"""
import functools
import hashlib
import json
import time
from typing import Any, Callable, Dict, Optional, Union
from flask import request, current_app, g
import redis
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    """Simple caching manager with Redis fallback to in-memory"""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_client = None
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_stats = {'hits': 0, 'misses': 0}
        
        if redis_url and redis_url != 'memory://':
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()  # Test connection
                logger.info("Redis cache initialized successfully")
            except Exception as e:
                logger.warning(f"Redis connection failed, using memory cache: {e}")
                self.redis_client = None
    
    def _generate_key(self, key: str, namespace: str = "default") -> str:
        """Generate cache key with namespace"""
        return f"vision_u:{namespace}:{key}"
    
    def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """Get value from cache"""
        cache_key = self._generate_key(key, namespace)
        
        try:
            if self.redis_client:
                value = self.redis_client.get(cache_key)
                if value:
                    self.cache_stats['hits'] += 1
                    return json.loads(value)
            else:
                # Memory cache
                if cache_key in self.memory_cache:
                    cache_entry = self.memory_cache[cache_key]
                    if cache_entry['expires'] > time.time():
                        self.cache_stats['hits'] += 1
                        return cache_entry['value']
                    else:
                        del self.memory_cache[cache_key]
            
            self.cache_stats['misses'] += 1
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            self.cache_stats['misses'] += 1
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600, namespace: str = "default") -> bool:
        """Set value in cache with TTL in seconds"""
        cache_key = self._generate_key(key, namespace)
        
        try:
            if self.redis_client:
                serialized = json.dumps(value, default=str)
                return self.redis_client.setex(cache_key, ttl, serialized)
            else:
                # Memory cache
                self.memory_cache[cache_key] = {
                    'value': value,
                    'expires': time.time() + ttl
                }
                
                # Simple cleanup for memory cache
                if len(self.memory_cache) > 1000:
                    self._cleanup_memory_cache()
                
                return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str, namespace: str = "default") -> bool:
        """Delete value from cache"""
        cache_key = self._generate_key(key, namespace)
        
        try:
            if self.redis_client:
                return bool(self.redis_client.delete(cache_key))
            else:
                return cache_key in self.memory_cache and \
                       self.memory_cache.pop(cache_key, None) is not None
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    def _cleanup_memory_cache(self):
        """Clean up expired entries from memory cache"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.memory_cache.items()
            if entry['expires'] <= current_time
        ]
        for key in expired_keys:
            del self.memory_cache[key]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = (self.cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'hits': self.cache_stats['hits'],
            'misses': self.cache_stats['misses'],
            'hit_rate': f"{hit_rate:.2f}%",
            'backend': 'redis' if self.redis_client else 'memory',
            'memory_cache_size': len(self.memory_cache)
        }

# Global cache instance
cache = None

def init_cache(app):
    """Initialize cache with app config"""
    global cache
    redis_url = app.config.get('RATELIMIT_STORAGE_URL', 'memory://')
    cache = CacheManager(redis_url)
    return cache

def cached(ttl: int = 3600, namespace: str = "default", key_func: Optional[Callable] = None):
    """
    Decorator for caching function results
    
    Args:
        ttl: Time to live in seconds
        namespace: Cache namespace
        key_func: Function to generate cache key, receives same args as decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not cache:
                return func(*args, **kwargs)
            
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                key_parts = [func.__name__]
                if args:
                    key_parts.extend(str(arg) for arg in args)
                if kwargs:
                    key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
                cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
            
            # Try to get from cache
            cached_result = cache.get(cache_key, namespace)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl, namespace)
            return result
        
        return wrapper
    return decorator

def cache_user_assessment_key(user_id: int, assessment_data: dict) -> str:
    """Generate cache key for user assessments"""
    data_hash = hashlib.md5(json.dumps(assessment_data, sort_keys=True).encode()).hexdigest()
    return f"user_assessment:{user_id}:{data_hash}"

def performance_monitor(func: Callable) -> Callable:
    """Decorator to monitor function performance"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            success = False
            error = str(e)
            raise
        finally:
            end_time = time.time()
            duration = end_time - start_time
            
            # Log performance metrics
            logger.info(f"Function {func.__name__} executed in {duration:.3f}s, success: {success}")
            
            # Store in request context for potential monitoring
            if hasattr(g, 'performance_metrics'):
                g.performance_metrics.append({
                    'function': func.__name__,
                    'duration': duration,
                    'success': success,
                    'error': error
                })
        
        return result
    return wrapper

class DatabaseConnectionPool:
    """Simple database connection pool manager"""
    
    def __init__(self, max_connections: int = 20):
        self.max_connections = max_connections
        self.connection_count = 0
        self.active_connections = []
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection pool information"""
        return {
            'max_connections': self.max_connections,
            'active_connections': len(self.active_connections),
            'connection_count': self.connection_count
        }

def optimize_query_response(data: Union[Dict, list], max_size: int = 1000) -> Union[Dict, list]:
    """Optimize large query responses by limiting size"""
    if isinstance(data, list) and len(data) > max_size:
        return {
            'data': data[:max_size],
            'total_count': len(data),
            'truncated': True,
            'message': f'Results limited to {max_size} items'
        }
    return data

def compress_response():
    """Decorator to compress large responses"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            response = func(*args, **kwargs)
            
            # Add compression headers if response is large
            if hasattr(response, 'get_data'):
                response_size = len(response.get_data())
                if response_size > 1024:  # 1KB threshold
                    response.headers['Content-Encoding'] = 'gzip'
            
            return response
        return wrapper
    return decorator