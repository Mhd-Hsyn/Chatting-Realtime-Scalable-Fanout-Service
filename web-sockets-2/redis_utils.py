import redis.asyncio as redis

from core.config import (
    redis_url
)
redis_client = redis.from_url(redis_url, decode_responses=True)

async def set_user_active_room(user_id, room_id):
    """Redis me likho: User 101 abhi Room 555 me h"""
    key = f"active_presence:{user_id}"
    await redis_client.set(key, str(room_id))

async def get_user_active_room(user_id):
    """Redis se poocho: User 101 abhi kahan h?"""
    key = f"active_presence:{user_id}"
    return await redis_client.get(key)

async def remove_user_active_room(user_id):
    """Jab user disconnect ho ya room chore"""
    key = f"active_presence:{user_id}"
    await redis_client.delete(key)

    