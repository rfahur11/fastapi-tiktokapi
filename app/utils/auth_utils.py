import random
import string
import redis
from typing import Optional

# Initialize Redis client
redis_client = redis.StrictRedis(host='127.0.0.1', port=6379, db=0, decode_responses=True)

def generate_csrf_state() -> str:
    """Generate a CSRF state token and store it in Redis."""
    state = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    redis_client.setex(f'state:{state}', 600, 'valid')
    return state

def get_latest_token() -> Optional[str]:
    """Get the latest access token from Redis."""
    keys = redis_client.keys('access_token:*')
    if keys:
        return redis_client.get(sorted(keys, reverse=True)[0])
    return None