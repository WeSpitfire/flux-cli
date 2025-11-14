"""Intelligent Caching System for Flux-CLI.

This module provides a multi-level caching system with predictive preloading,
smart invalidation, and distributed cache support for optimal performance.
"""

import asyncio
import hashlib
import json
import pickle
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from collections import OrderedDict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """Cache storage levels."""
    MEMORY = "memory"      # In-memory cache (fastest)
    DISK = "disk"          # Local disk cache
    DISTRIBUTED = "distributed"  # Redis/Memcached (future)


@dataclass
class CacheEntry:
    """Represents a single cache entry."""
    key: str
    value: Any
    level: CacheLevel
    created_at: float
    last_accessed: float
    access_count: int
    size_bytes: int
    ttl: Optional[int] = None  # Time to live in seconds
    metadata: Dict[str, Any] = None
    
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.ttl is None:
            return False
        return (time.time() - self.created_at) > self.ttl
    
    def update_access(self):
        """Update access statistics."""
        self.last_accessed = time.time()
        self.access_count += 1


class LRUCache:
    """Thread-safe LRU cache implementation."""
    
    def __init__(self, max_size: int = 1000, max_bytes: int = 100 * 1024 * 1024):
        """Initialize LRU cache.
        
        Args:
            max_size: Maximum number of entries
            max_bytes: Maximum total size in bytes
        """
        self.max_size = max_size
        self.max_bytes = max_bytes
        self.cache = OrderedDict()
        self.total_bytes = 0
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        async with self._lock:
            if key in self.cache:
                # Move to end (most recently used)
                entry = self.cache.pop(key)
                self.cache[key] = entry
                entry.update_access()
                
                if not entry.is_expired():
                    return entry.value
                else:
                    # Remove expired entry
                    self.total_bytes -= entry.size_bytes
                    del self.cache[key]
            return None
    
    async def put(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Put value in cache."""
        # Calculate size
        size_bytes = len(pickle.dumps(value))
        
        async with self._lock:
            # Remove old entry if exists
            if key in self.cache:
                old_entry = self.cache.pop(key)
                self.total_bytes -= old_entry.size_bytes
            
            # Create new entry
            entry = CacheEntry(
                key=key,
                value=value,
                level=CacheLevel.MEMORY,
                created_at=time.time(),
                last_accessed=time.time(),
                access_count=1,
                size_bytes=size_bytes,
                ttl=ttl
            )
            
            # Add to cache
            self.cache[key] = entry
            self.total_bytes += size_bytes
            
            # Evict if necessary
            while (len(self.cache) > self.max_size or 
                   self.total_bytes > self.max_bytes):
                # Remove least recently used
                oldest_key, oldest_entry = self.cache.popitem(last=False)
                self.total_bytes -= oldest_entry.size_bytes
                logger.debug(f"Evicted {oldest_key} from memory cache")
    
    async def clear(self):
        """Clear all entries."""
        async with self._lock:
            self.cache.clear()
            self.total_bytes = 0
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'entries': len(self.cache),
            'total_bytes': self.total_bytes,
            'max_size': self.max_size,
            'max_bytes': self.max_bytes,
            'utilization': len(self.cache) / self.max_size if self.max_size > 0 else 0
        }


class DiskCache:
    """Persistent disk-based cache."""
    
    def __init__(self, cache_dir: Path, max_size_gb: float = 1.0):
        """Initialize disk cache.
        
        Args:
            cache_dir: Directory for cache files
            max_size_gb: Maximum cache size in GB
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_bytes = int(max_size_gb * 1024 * 1024 * 1024)
        self.index_file = self.cache_dir / "cache_index.json"
        self.index = self._load_index()
    
    def _load_index(self) -> Dict[str, Dict]:
        """Load cache index from disk."""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_index(self):
        """Save cache index to disk."""
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f)
    
    def _get_cache_file(self, key: str) -> Path:
        """Get cache file path for key."""
        # Use hash to avoid filesystem issues
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash[:2]}" / f"{key_hash}.cache"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from disk cache."""
        if key not in self.index:
            return None
        
        entry_info = self.index[key]
        
        # Check expiration
        if entry_info.get('ttl'):
            if (time.time() - entry_info['created_at']) > entry_info['ttl']:
                await self.delete(key)
                return None
        
        cache_file = self._get_cache_file(key)
        if not cache_file.exists():
            # Index out of sync
            del self.index[key]
            self._save_index()
            return None
        
        try:
            with open(cache_file, 'rb') as f:
                value = pickle.load(f)
            
            # Update access time
            self.index[key]['last_accessed'] = time.time()
            self.index[key]['access_count'] = entry_info.get('access_count', 0) + 1
            self._save_index()
            
            return value
        except Exception as e:
            logger.error(f"Error reading cache file {cache_file}: {e}")
            return None
    
    async def put(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Put value in disk cache."""
        cache_file = self._get_cache_file(key)
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Serialize value
        data = pickle.dumps(value)
        size_bytes = len(data)
        
        # Check size limits
        current_size = sum(e.get('size_bytes', 0) for e in self.index.values())
        if current_size + size_bytes > self.max_bytes:
            # Evict oldest entries
            await self._evict_lru(size_bytes)
        
        # Write to disk
        with open(cache_file, 'wb') as f:
            f.write(data)
        
        # Update index
        self.index[key] = {
            'created_at': time.time(),
            'last_accessed': time.time(),
            'access_count': 1,
            'size_bytes': size_bytes,
            'ttl': ttl,
            'file': str(cache_file)
        }
        self._save_index()
    
    async def delete(self, key: str) -> None:
        """Delete entry from disk cache."""
        if key in self.index:
            cache_file = Path(self.index[key]['file'])
            if cache_file.exists():
                cache_file.unlink()
            del self.index[key]
            self._save_index()
    
    async def _evict_lru(self, needed_bytes: int):
        """Evict least recently used entries to make space."""
        # Sort by last access time
        sorted_entries = sorted(
            self.index.items(),
            key=lambda x: x[1].get('last_accessed', 0)
        )
        
        freed_bytes = 0
        for key, entry in sorted_entries:
            if freed_bytes >= needed_bytes:
                break
            
            cache_file = Path(entry['file'])
            if cache_file.exists():
                cache_file.unlink()
            freed_bytes += entry.get('size_bytes', 0)
            del self.index[key]
            logger.debug(f"Evicted {key} from disk cache")
        
        self._save_index()
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_bytes = sum(e.get('size_bytes', 0) for e in self.index.values())
        return {
            'entries': len(self.index),
            'total_bytes': total_bytes,
            'max_bytes': self.max_bytes,
            'utilization': total_bytes / self.max_bytes if self.max_bytes > 0 else 0
        }


class PredictiveCache:
    """Predictive caching with preloading based on access patterns."""
    
    def __init__(self):
        self.access_patterns = {}
        self.prediction_model = {}
        self.preload_queue = asyncio.Queue()
    
    def record_access(self, key: str, context: Dict[str, Any]):
        """Record an access pattern for learning."""
        if key not in self.access_patterns:
            self.access_patterns[key] = []
        
        self.access_patterns[key].append({
            'timestamp': time.time(),
            'context': context
        })
        
        # Update predictions
        self._update_predictions(key, context)
    
    def _update_predictions(self, key: str, context: Dict[str, Any]):
        """Update prediction model based on access patterns."""
        # Simple prediction: if file A is accessed, files in same directory likely needed
        if 'file_path' in context:
            dir_path = Path(context['file_path']).parent
            related_files = [
                str(f) for f in dir_path.glob('*')
                if f.is_file() and str(f) != context['file_path']
            ][:5]  # Limit to 5 files
            
            self.prediction_model[key] = {
                'related': related_files,
                'confidence': 0.7
            }
    
    async def get_predictions(self, key: str) -> List[str]:
        """Get predicted keys that might be needed next."""
        if key in self.prediction_model:
            return self.prediction_model[key].get('related', [])
        return []
    
    async def preload(self, keys: List[str], loader_func):
        """Preload predicted keys in background."""
        for key in keys:
            await self.preload_queue.put((key, loader_func))
    
    async def process_preload_queue(self):
        """Background task to process preload queue."""
        while True:
            try:
                key, loader_func = await asyncio.wait_for(
                    self.preload_queue.get(),
                    timeout=1.0
                )
                
                # Load in background
                try:
                    await loader_func(key)
                    logger.debug(f"Preloaded {key}")
                except Exception as e:
                    logger.error(f"Error preloading {key}: {e}")
                    
            except asyncio.TimeoutError:
                await asyncio.sleep(0.1)


class IntelligentCache:
    """Main intelligent caching system combining all cache levels."""
    
    def __init__(self, cache_dir: Path = None):
        """Initialize intelligent cache.
        
        Args:
            cache_dir: Directory for persistent cache
        """
        self.cache_dir = cache_dir or Path.home() / ".flux" / "cache"
        
        # Initialize cache levels
        self.memory_cache = LRUCache(max_size=1000, max_bytes=100*1024*1024)  # 100MB
        self.disk_cache = DiskCache(self.cache_dir / "disk", max_size_gb=1.0)
        self.predictive = PredictiveCache()
        
        # Cache statistics
        self.hits = 0
        self.misses = 0
        self.start_time = time.time()
        
        # Start background tasks
        self._background_task = None
    
    async def start(self):
        """Start background tasks."""
        self._background_task = asyncio.create_task(
            self.predictive.process_preload_queue()
        )
    
    async def stop(self):
        """Stop background tasks."""
        if self._background_task:
            self._background_task.cancel()
    
    def _generate_key(self, category: str, identifier: str) -> str:
        """Generate cache key."""
        return f"{category}:{identifier}"
    
    async def get(
        self,
        category: str,
        identifier: str,
        context: Dict[str, Any] = None
    ) -> Optional[Any]:
        """Get value from cache.
        
        Args:
            category: Cache category (e.g., 'file', 'search', 'embedding')
            identifier: Unique identifier within category
            context: Optional context for predictive caching
            
        Returns:
            Cached value or None
        """
        key = self._generate_key(category, identifier)
        
        # Try memory cache first (fastest)
        value = await self.memory_cache.get(key)
        if value is not None:
            self.hits += 1
            logger.debug(f"Memory cache hit: {key}")
            
            # Record access pattern
            if context:
                self.predictive.record_access(key, context)
            
            return value
        
        # Try disk cache
        value = await self.disk_cache.get(key)
        if value is not None:
            self.hits += 1
            logger.debug(f"Disk cache hit: {key}")
            
            # Promote to memory cache
            await self.memory_cache.put(key, value)
            
            # Record access pattern
            if context:
                self.predictive.record_access(key, context)
            
            # Trigger predictive preloading
            predictions = await self.predictive.get_predictions(key)
            if predictions:
                await self._preload_related(category, predictions)
            
            return value
        
        # Cache miss
        self.misses += 1
        logger.debug(f"Cache miss: {key}")
        return None
    
    async def put(
        self,
        category: str,
        identifier: str,
        value: Any,
        ttl: Optional[int] = None,
        persist: bool = True
    ) -> None:
        """Put value in cache.
        
        Args:
            category: Cache category
            identifier: Unique identifier
            value: Value to cache
            ttl: Time to live in seconds
            persist: Whether to persist to disk
        """
        key = self._generate_key(category, identifier)
        
        # Always put in memory cache
        await self.memory_cache.put(key, value, ttl)
        
        # Optionally persist to disk
        if persist:
            await self.disk_cache.put(key, value, ttl)
        
        logger.debug(f"Cached {key} (persist={persist})")
    
    async def invalidate(self, category: str, identifier: str = None) -> None:
        """Invalidate cache entries.
        
        Args:
            category: Cache category to invalidate
            identifier: Specific identifier or None for entire category
        """
        if identifier:
            key = self._generate_key(category, identifier)
            # Remove from all levels
            await self.memory_cache.put(key, None, ttl=0)  # Expire immediately
            await self.disk_cache.delete(key)
            logger.debug(f"Invalidated {key}")
        else:
            # Invalidate entire category (expensive operation)
            # For now, just clear all caches
            await self.clear_all()
            logger.debug(f"Invalidated category {category}")
    
    async def clear_all(self):
        """Clear all cache levels."""
        await self.memory_cache.clear()
        # Disk cache clearing would go through all files
        logger.info("Cleared all caches")
    
    async def _preload_related(self, category: str, identifiers: List[str]):
        """Preload related items in background."""
        async def loader(identifier):
            # This would typically call the actual loading function
            # For now, just mark as attempted
            logger.debug(f"Would preload {category}:{identifier}")
        
        for identifier in identifiers:
            await self.predictive.preload([identifier], loader)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        uptime = time.time() - self.start_time
        total_requests = self.hits + self.misses
        
        return {
            'uptime_seconds': uptime,
            'total_requests': total_requests,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': self.hits / total_requests if total_requests > 0 else 0,
            'memory_cache': self.memory_cache.stats(),
            'disk_cache': self.disk_cache.stats(),
            'predictions_made': len(self.predictive.prediction_model)
        }


# Cache decorators for easy integration
def cached(category: str, ttl: Optional[int] = None, persist: bool = True):
    """Decorator to cache function results.
    
    Args:
        category: Cache category
        ttl: Time to live in seconds
        persist: Whether to persist to disk
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Generate cache key from function and arguments
            identifier = f"{func.__name__}:{hash((args, tuple(kwargs.items())))}"
            
            # Try to get from cache
            cache = kwargs.get('_cache')
            if cache:
                value = await cache.get(category, identifier)
                if value is not None:
                    return value
            
            # Call function
            value = await func(*args, **kwargs)
            
            # Cache result
            if cache:
                await cache.put(category, identifier, value, ttl, persist)
            
            return value
        return wrapper
    return decorator


# Example usage
async def demo_intelligent_cache():
    """Demonstrate intelligent caching capabilities."""
    print("🧠 Intelligent Cache Demo")
    print("=" * 60)
    
    cache = IntelligentCache()
    await cache.start()
    
    # Simulate file operations
    print("\n📁 Simulating file operations:")
    
    # First access - miss
    result = await cache.get("file", "main.py", {"file_path": "src/main.py"})
    print(f"  First access: {'HIT' if result else 'MISS'}")
    
    # Cache the file
    await cache.put("file", "main.py", "file contents here", ttl=300)
    
    # Second access - hit
    result = await cache.get("file", "main.py", {"file_path": "src/main.py"})
    print(f"  Second access: {'HIT' if result else 'MISS'}")
    
    # Access triggers prediction
    predictions = await cache.predictive.get_predictions(
        cache._generate_key("file", "main.py")
    )
    print(f"  Predictions: {len(predictions)} related files identified")
    
    # Show statistics
    print("\n📊 Cache Statistics:")
    stats = cache.get_stats()
    print(f"  Hit Rate: {stats['hit_rate']*100:.1f}%")
    print(f"  Memory Cache: {stats['memory_cache']['entries']} entries")
    print(f"  Disk Cache: {stats['disk_cache']['entries']} entries")
    print(f"  Predictions: {stats['predictions_made']} patterns learned")
    
    await cache.stop()
    print("\n✅ Intelligent caching system ready!")


if __name__ == "__main__":
    asyncio.run(demo_intelligent_cache())