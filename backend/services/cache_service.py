"""
Cache Service using Redis
Provides caching for API responses to minimize token consumption
"""
import json
import logging
from typing import Optional, Any, Dict
from datetime import timedelta
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class CacheService:
    """Service for caching API responses with Redis"""
    
    def __init__(self, redis_url: str = "redis://redis:6379"):
        """Initialize cache service with Redis connection"""
        self.redis_client: Optional[redis.Redis] = None
        self.redis_url = redis_url
        
        # TTL configurations (in seconds)
        self.TTL_CONFIG = {
            "fixtures": 3600,          # 1 hour - fixtures update frequently
            "opponent_stats": 86400,   # 24 hours - team stats are more stable
            "tactical_plan": 86400,    # 24 hours - tactical analysis remains valid
            "match_details": 7200,     # 2 hours - match details
        }
    
    async def connect(self):
        """Establish Redis connection"""
        if not self.redis_client:
            try:
                self.redis_client = await redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                await self.redis_client.ping()
                logger.info("Redis cache connection established")
            except Exception as e:
                logger.error(f"Redis connection failed: {e}")
                self.redis_client = None
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")
    
    def _get_cache_key(self, cache_type: str, identifier: str) -> str:
        """Generate cache key with namespace"""
        return f"football_tactical:{cache_type}:{identifier}"
    
    async def get(self, cache_type: str, identifier: str) -> Optional[Dict[str, Any]]:
        """
        Get cached data
        
        Args:
            cache_type: Type of cache (fixtures, opponent_stats, tactical_plan)
            identifier: Unique identifier for the cached item
        
        Returns:
            Cached data as dict or None if not found
        """
        if not self.redis_client:
            await self.connect()
        
        if not self.redis_client:
            logger.warning("Cache unavailable - Redis not connected")
            return None
        
        try:
            cache_key = self._get_cache_key(cache_type, identifier)
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                logger.info(f"Cache HIT: {cache_key}")
                return json.loads(cached_data)
            else:
                logger.info(f"Cache MISS: {cache_key}")
                return None
                
        except Exception as e:
            logger.error(f"Cache get error for {cache_type}:{identifier}: {e}")
            return None
    
    async def set(
        self, 
        cache_type: str, 
        identifier: str, 
        data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set cached data with TTL
        
        Args:
            cache_type: Type of cache
            identifier: Unique identifier
            data: Data to cache
            ttl: Time to live in seconds (optional, uses default from TTL_CONFIG)
        
        Returns:
            True if cached successfully, False otherwise
        """
        if not self.redis_client:
            await self.connect()
        
        if not self.redis_client:
            logger.warning("Cannot cache - Redis not connected")
            return False
        
        try:
            cache_key = self._get_cache_key(cache_type, identifier)
            
            # Use provided TTL or default from config
            ttl_seconds = ttl or self.TTL_CONFIG.get(cache_type, 3600)
            
            # Serialize and store
            serialized_data = json.dumps(data, default=str)
            await self.redis_client.setex(
                cache_key,
                ttl_seconds,
                serialized_data
            )
            
            logger.info(f"Cached: {cache_key} (TTL: {ttl_seconds}s)")
            return True
            
        except Exception as e:
            logger.error(f"Cache set error for {cache_type}:{identifier}: {e}")
            return False
    
    async def delete(self, cache_type: str, identifier: str) -> bool:
        """Delete cached item"""
        if not self.redis_client:
            await self.connect()
        
        if not self.redis_client:
            return False
        
        try:
            cache_key = self._get_cache_key(cache_type, identifier)
            deleted = await self.redis_client.delete(cache_key)
            
            if deleted:
                logger.info(f"Deleted cache: {cache_key}")
            
            return bool(deleted)
            
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    async def clear_all(self, cache_type: Optional[str] = None) -> int:
        """
        Clear all cached items of a specific type or all cache
        
        Args:
            cache_type: Specific cache type to clear, or None for all
        
        Returns:
            Number of keys deleted
        """
        if not self.redis_client:
            await self.connect()
        
        if not self.redis_client:
            return 0
        
        try:
            if cache_type:
                pattern = f"football_tactical:{cache_type}:*"
            else:
                pattern = "football_tactical:*"
            
            keys = []
            async for key in self.redis_client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                deleted = await self.redis_client.delete(*keys)
                logger.info(f"Cleared {deleted} cache entries matching '{pattern}'")
                return deleted
            
            return 0
            
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.redis_client:
            await self.connect()
        
        if not self.redis_client:
            return {"status": "disconnected"}
        
        try:
            info = await self.redis_client.info()
            
            # Count keys by type
            fixtures_count = 0
            opponent_stats_count = 0
            tactical_plan_count = 0
            
            async for key in self.redis_client.scan_iter(match="football_tactical:*"):
                if ":fixtures:" in key:
                    fixtures_count += 1
                elif ":opponent_stats:" in key:
                    opponent_stats_count += 1
                elif ":tactical_plan:" in key:
                    tactical_plan_count += 1
            
            return {
                "status": "connected",
                "redis_version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": info.get("used_memory_human"),
                "total_keys": fixtures_count + opponent_stats_count + tactical_plan_count,
                "fixtures_cached": fixtures_count,
                "opponent_stats_cached": opponent_stats_count,
                "tactical_plans_cached": tactical_plan_count,
            }
            
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {"status": "error", "error": str(e)}


# Global cache service instance
_cache_service: Optional[CacheService] = None

def get_cache_service() -> CacheService:
    """Get or create global cache service instance"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service
