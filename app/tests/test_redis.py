"""
Test Redis integration and locking mechanism.
"""
import pytest
import fakeredis


class TestRedisIntegration:
    """Test Redis functionality."""

    def test_redis_connection(self, fake_redis):
        """Test basic Redis connection and operations."""
        # Set a value
        fake_redis.set("test_key", "test_value")
        
        # Get the value
        value = fake_redis.get("test_key")
        assert value == "test_value"

    def test_redis_lock_basic(self, fake_redis):
        """Test Redis lock acquisition and release."""
        lock = fake_redis.lock("test_lock", timeout=10)
        
        # Acquire lock
        acquired = lock.acquire(blocking=False)
        assert acquired is True
        
        # Release lock
        lock.release()

    def test_redis_lock_blocking(self, fake_redis):
        """Test that a lock cannot be acquired twice."""
        lock1 = fake_redis.lock("resource_lock", timeout=10)
        lock2 = fake_redis.lock("resource_lock", timeout=10)
        
        # First lock acquires successfully
        assert lock1.acquire(blocking=False) is True
        
        # Second lock should fail to acquire (non-blocking)
        assert lock2.acquire(blocking=False) is False
        
        # Release first lock
        lock1.release()
        
        # Now second lock can acquire
        assert lock2.acquire(blocking=False) is True
        lock2.release()

    def test_redis_lock_context_manager(self, fake_redis):
        """Test Redis lock using context manager."""
        lock = fake_redis.lock("ctx_lock", timeout=5)
        
        with lock:
            # Inside context, lock is held
            another_lock = fake_redis.lock("ctx_lock", timeout=5)
            assert another_lock.acquire(blocking=False) is False
        
        # Outside context, lock is released
        assert another_lock.acquire(blocking=False) is True
        another_lock.release()

    def test_redis_lock_timeout(self, fake_redis):
        """Test Redis lock with timeout."""
        lock = fake_redis.lock("timeout_lock", timeout=1)
        
        # Acquire the lock
        acquired = lock.acquire(blocking=False)
        assert acquired is True
        
        # Lock should be held
        another_lock = fake_redis.lock("timeout_lock", timeout=1)
        assert another_lock.acquire(blocking=False) is False
        
        # Clean up
        lock.release()

    def test_redis_multiple_locks(self, fake_redis):
        """Test multiple different locks can be held simultaneously."""
        lock1 = fake_redis.lock("lock_1", timeout=10)
        lock2 = fake_redis.lock("lock_2", timeout=10)
        
        # Both locks can be acquired
        assert lock1.acquire(blocking=False) is True
        assert lock2.acquire(blocking=False) is True
        
        # Release both
        lock1.release()
        lock2.release()

    def test_redis_data_persistence(self, fake_redis):
        """Test that Redis persists data during session."""
        # Set multiple keys
        fake_redis.set("key1", "value1")
        fake_redis.set("key2", "value2")
        fake_redis.set("key3", "value3")
        
        # Verify all are retrievable
        assert fake_redis.get("key1") == "value1"
        assert fake_redis.get("key2") == "value2"
        assert fake_redis.get("key3") == "value3"
        
        # Delete one key
        fake_redis.delete("key2")
        
        # Verify deletion
        assert fake_redis.get("key2") is None
        assert fake_redis.get("key1") == "value1"
        assert fake_redis.get("key3") == "value3"
